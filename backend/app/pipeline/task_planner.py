from __future__ import annotations
import logging
import re

from pydantic import BaseModel, Field
from typing import Optional, List

from app.domains.books.types import (
    NodeType,
    SINGLE_BOOK_RETRIEVAL,
)

from app.common.base_node import BaseNode

logger = logging.getLogger(__name__)


class Task(BaseModel):
    """
    Represents a single task in the execution plan with dependencies.
    """

    model_config = {"extra": "forbid"}

    id: str
    depends_on: Optional[List[str]] = Field(
        default_factory=list, description="Task dependencies"
    )
    refusal: bool = Field(default=False, description="Whether this task was refused")
    reasoning: str = Field(default="", description="Reasoning for task state")

    def model_post_init(self, __context) -> None:
        """Remove self-dependencies and duplicate dependency IDs."""
        if not self.depends_on:
            self.depends_on = []
            return

        cleaned_depends_on = set(self.depends_on)
        if self.id in cleaned_depends_on:
            logger.warning(f"Task {self.id} had dependency on itself - removing")
            cleaned_depends_on.remove(self.id)

        self.depends_on = list(cleaned_depends_on)

    def validate_dependencies(self, valid_ids: set[str]) -> Task:
        """
        Validate dependencies against available node IDs.

        Args:
            valid_ids: Set of valid node IDs

        Returns:
            New Task instance with only valid dependencies
        """
        if not self.depends_on:
            return self

        valid_deps = []
        invalid_deps = []

        for dep in self.depends_on:
            if dep in valid_ids:
                valid_deps.append(dep)
            else:
                invalid_deps.append(dep)

        if invalid_deps:
            logger.warning(f"Task {self.id} had invalid dependencies: {invalid_deps}")

        return self.model_copy(update={"depends_on": valid_deps})


class TaskPlan(BaseModel):
    """
    Complete task execution plan with dependency resolution and ordering.
    """

    model_config = {"extra": "forbid"}

    accepted: List[Task] = Field(default_factory=list)
    refused: List[Task] = Field(default_factory=list)
    missing_ids: List[str] = Field(default_factory=list)
    missing_strategies: List[str] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)

    def get_accepted_ids(self) -> set[str]:
        """Return set of accepted task IDs."""
        return {task.id for task in self.accepted}

    def order_task_plan(self):
        """
        Perform topological sort on task dependencies to determine execution order.
        Uses Kahn's algorithm for dependency resolution.
        """
        from collections import defaultdict, deque

        tasks = self.accepted

        graph = defaultdict(list)
        indegree = defaultdict(int)

        for task in tasks:
            task_id = task.id
            for dep in task.depends_on:
                graph[dep].append(task_id)
                indegree[task_id] += 1
            indegree.setdefault(task_id, 0)

        queue = deque([t for t, d in indegree.items() if d == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(indegree):
            remaining_nodes = [node for node, degree in indegree.items() if degree > 0]
            logger.error(
                f"Cycle detected in dependency graph! Remaining nodes: {remaining_nodes}"
            )

        logger.info(
            f"Task execution order: {' -> '.join(order) if order else 'No tasks'}"
        )

        self.execution_order = order

    def validate_accepted(self, node_ids: dict[str, BaseNode]) -> None:
        """
        Validate accepted tasks against node type rules.
        Moves invalid tasks to refused list.

        Args:
            node_ids: Dictionary mapping node IDs to node instances
        """
        cleaned_accepted = []
        for task in self.accepted:
            node = node_ids[task.id]
            type = node.get_type()

            if type in SINGLE_BOOK_RETRIEVAL and len(task.depends_on) != 0:
                logger.warning(f"Single Book Retrieval ID {task.id} has dependencies")
                task.depends_on = []
            elif type == NodeType.COMPARE and len(task.depends_on) < 2:
                logger.warning(
                    f"Compare Book Strategy ID {task.id} doesn't have enough dependencies"
                )
                self.refused.append(task)
                continue

            cleaned_accepted.append(task)

        self.accepted = cleaned_accepted

    def get_accepted_diagram(self, node_ids):
        """
        Generate Mermaid flowchart diagram of accepted tasks.

        Args:
            node_ids: Dictionary of node IDs to node instances

        Returns:
            Mermaid diagram string
        """
        accepted_ids = self.get_accepted_ids()

        def is_retrieval_node(node_id: str) -> bool:
            return node_id.endswith(("_tit", "_isbn", "_traits"))

        def is_analyze_node(node_id: str) -> bool:
            return node_id.endswith(("_cmp", "_rec"))

        result = "flowchart LR\n"

        retrieval_nodes, analyze_nodes = [], []
        for id in node_ids:
            if id not in accepted_ids:
                continue

            description = clean_string_mermaid(node_ids[id].description)
            if is_retrieval_node(id) and id:
                retrieval_nodes.append(f"\t\t{id}[{description}]")
            elif is_analyze_node(id):
                analyze_nodes.append(f"\t\t{id}[{description}]")

        result += "\n\tsubgraph Retrieval\n\t\tdirection LR\n"
        result += "\n".join(retrieval_nodes) + "\n\t\tend\n"

        result += "\n\tsubgraph Analyze\n\t\tdirection LR\n"
        result += "\n".join(analyze_nodes) + "\n\t\tend\n"

        result += "\n\tRetrieval ~~~ Analyze\n"
        for task in self.accepted:
            for depends_on in task.depends_on:
                result += f"\t{depends_on} ---> {task.id}\n"

        return result

    def to_payload(self) -> dict:
        """Convert task plan to dictionary for serialization."""
        return {
            "accepted": [task.model_dump() for task in self.accepted],
            "refused": [task.model_dump() for task in self.refused],
            "missing_ids": self.missing_ids,
            "missing_strategies": self.missing_strategies,
            "execution_order": self.execution_order,
            "summary": f"{len(self.accepted)} accepted, {len(self.refused)} refused",
        }

    def export(self, file_name: str = "dev"):
        """
        Export task plan to file for debugging.

        Args:
            file_name: Base filename for export
        """
        from app.common.utils import save_file

        payload = self.to_payload()
        save_file(payload, file_name=f"{file_name}_task_plan")
        logger.debug(f"Exported OpenAI request payload: {payload}")


class TaskGenerationNode(BaseModel):
    """
    Pydantic model for LLM-generated task planning tool.
    """

    model_config = {"extra": "forbid"}

    tasks: List[Task] = Field(
        ..., description="create a list of tasks with dependency resolve"
    )
    missing_strategies: List[str] = Field(
        ..., description="part of the query that we don't support yet"
    )

    async def __call__(self, node_ids) -> TaskPlan:
        """
        Process LLM-generated tasks into validated TaskPlan.

        Args:
            node_ids: Dictionary of valid node IDs

        Returns:
            Validated and ordered TaskPlan
        """
        logger.debug("Processing TaskGenerationNode")

        valid_ids = set(node_ids.keys())
        accepted, refused, requested_ids = [], [], set()

        for task in self.tasks:
            if task.id not in valid_ids:
                logger.warning(f"TaskGeneration hallucinated ID: {task.id}")
                continue

            if task.id in requested_ids:
                logger.warning(f"TaskGeneration classified duplicates ID: {task.id}")
                continue

            cleaned_task = task.validate_dependencies(valid_ids)

            if not cleaned_task.refusal:
                accepted.append(cleaned_task)
            else:
                refused.append(cleaned_task)

            requested_ids.add(task.id)

        processed_ids = set(task.id for task in accepted + refused)
        missing_ids = list(requested_ids - processed_ids)

        result = TaskPlan(
            accepted=accepted,
            refused=refused,
            missing_ids=missing_ids,
            missing_strategies=self.missing_strategies,
        )

        result.order_task_plan()

        return result

    @classmethod
    def modify_schema(cls, tool, valid_ids):
        """
        Modify tool schema to constrain LLM output to valid IDs.

        Args:
            tool: OpenAI function tool definition
            valid_ids: List of valid task IDs

        Returns:
            Modified tool schema
        """
        schema = tool["function"]["parameters"]["$defs"]["Task"]

        schema["properties"]["id"] = {
            "type": "string",
            "enum": valid_ids,
            "description": f"Task ID must be one of: {', '.join(valid_ids)}",
        }

        schema["properties"]["depends_on"] = {
            "type": "array",
            "items": {"type": "string", "enum": valid_ids},
            "description": f"Available dependency IDs: {', '.join(valid_ids)}",
        }

        return tool


def clean_string_mermaid(text):
    """Remove Mermaid-reserved characters from text."""
    return re.sub(r'[()"\'<>{}\[\]|`#%@:;\\/]', "", text)
