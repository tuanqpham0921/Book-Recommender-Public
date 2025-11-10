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
    model_config = {"extra": "forbid"}

    id: str
    depends_on: Optional[List[str]] = Field(
        default_factory=list, description="Task dependencies"
    )
    refusal: bool = Field(default=False, description="Whether this task was refused")
    reasoning: str = Field(default="", description="Reasoning for task state")

    def model_post_init(self, __context) -> None:
        """Basic cleanup - remove self-dependencies and duplicates."""
        if not self.depends_on:
            self.depends_on = []
            return

        # Remove duplicates and self-references
        cleaned_depends_on = set(self.depends_on)
        if self.id in cleaned_depends_on:
            logger.warning(f"⚠️ Task {self.id} had dependency on itself - removing")
            cleaned_depends_on.remove(self.id)

        self.depends_on = list(cleaned_depends_on)

    def validate_dependencies(self, valid_ids: set[str]) -> Task:
        """Validate and clean dependencies against valid node IDs."""
        if not self.depends_on:
            return self

        # Remove invalid dependencies
        valid_deps = []
        invalid_deps = []

        for dep in self.depends_on:
            if dep in valid_ids:
                valid_deps.append(dep)
            else:
                invalid_deps.append(dep)

        if invalid_deps:
            logger.warning(f"⚠️ Task {self.id} had invalid dependencies: {invalid_deps}")

        # Create new task with cleaned dependencies
        return self.model_copy(update={"depends_on": valid_deps})


class TaskPlan(BaseModel):
    model_config = {"extra": "forbid"}

    accepted: List[Task] = Field(default_factory=list)
    refused: List[Task] = Field(default_factory=list)
    missing_ids: List[str] = Field(default_factory=list)
    missing_strategies: List[str] = Field(default_factory=list)
    execution_order: List[str] = Field(default_factory=list)

    def get_accepted_ids(self) -> set[str]:
        return {task.id for task in self.accepted}

    def order_task_plan(self):
        # Build adjacency list and indegree map
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

        # Start with nodes that have no dependencies
        queue = deque([t for t, d in indegree.items() if d == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles in the dependency graph
        if len(order) != len(indegree):
            remaining_nodes = [node for node, degree in indegree.items() if degree > 0]
            logger.error(
                f"❌ Cycle detected in dependency graph! Remaining nodes: {remaining_nodes}"
            )
            # raise ValueError(
            #     f"Cycle detected in dependency graph! Nodes involved: {remaining_nodes}"
            # )

        logger.info(
            f"📋 Task execution order: {' -> '.join(order) if order else 'No tasks'}"
        )

        self.execution_order = order

    # Here we should know that the ids are valid nodes
    def validate_accepted(self, node_ids: dict[str, BaseNode]) -> None:
        """Enforce the rules for accepted strategies. Add to refuse if fails"""
        cleaned_accepted = []
        for task in self.accepted:
            node = node_ids[task.id]
            type = node.get_type()

            if type in SINGLE_BOOK_RETRIEVAL and len(task.depends_on) != 0:
                logger.warning(f"⚠️ Single Book Retrieval ID {task.id} has dependencies")
                task.depends_on = []
            elif type == NodeType.COMPARE and len(task.depends_on) < 2:
                logger.warning(
                    f"⚠️ Compare Book Strategy ID {task.id} doesn't have enough dependencies"
                )
                self.refused.append(task)
                continue

            cleaned_accepted.append(task)

        self.accepted = cleaned_accepted

    def get_accepted_diagram(self, node_ids):
        accepted_ids = self.get_accepted_ids()
        
        def is_retrieval_node(node_id: str) -> bool:
            return node_id.endswith(("_tit", "_isbn", "_traits"))
        
        def is_analyze_node(node_id: str) -> bool:
            return node_id.endswith(("_cmp", "_rec"))

        result = "flowchart LR\n"

        # Retrieval subgraph
        
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
        # Analyze subgraph  
        result += "\n\tsubgraph Analyze\n\t\tdirection LR\n"
        result += "\n".join(analyze_nodes) + "\n\t\tend\n"

        # Dependencies
        result += "\n\tRetrieval ~~~ Analyze\n"
        for task in self.accepted:
            for depends_on in task.depends_on:
                result += f"\t{depends_on} ---> {task.id}\n"

        return result
    
    def to_payload(self) -> dict:
        """Convert to simple dictionary format."""
        return {
            "accepted": [task.model_dump() for task in self.accepted],
            "refused": [task.model_dump() for task in self.refused],
            "missing_ids": self.missing_ids,
            "missing_strategies": self.missing_strategies,
            "execution_order": self.execution_order,
            "summary": f"{len(self.accepted)} accepted, {len(self.refused)} refused"
        }
    
    def export(self, file_name: str = "dev"):
        """Export the full request payload for logging/debugging."""
        from app.common.utils import save_file
        
        payload = self.to_payload()
        save_file(payload, file_name=f"{file_name}_task_plan")
        logger.debug(f"📋 Exported OpenAI request payload: {payload}")


class TaskGenerationNode(BaseModel):
    model_config = {"extra": "forbid"}

    tasks: List[Task] = Field(
        ..., description="create a list of tasks with dependency resolve"
    )
    missing_strategies: List[str] = Field(
        ..., description="part of the query that we don't support yet"
    )

    async def __call__(self, node_ids) -> TaskPlan:
        logger.debug("🔍 Processing TaskGenerationNode")

        valid_ids = set(node_ids.keys())
        accepted, refused, requested_ids = [], [], set()

        for task in self.tasks:
            if task.id not in valid_ids:
                logger.warning(f"⚠️ TaskGeneration hallucinated ID: {task.id}")
                continue

            if task.id in requested_ids:
                logger.warning(f"⚠️ TaskGeneration classified duplicates ID: {task.id}")
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

        # result.validate_accepted(node_ids)
        result.order_task_plan()

        return result

    @classmethod
    def modify_schema(cls, tool, valid_ids):
        """Quick fix for your notebook."""
        # Modify the schema
        schema = tool["function"]["parameters"]["$defs"]["Task"]

        # Fix the id field to have proper enum
        schema["properties"]["id"] = {
            "type": "string",
            "enum": valid_ids,
            "description": f"Task ID must be one of: {', '.join(valid_ids)}",
        }

        # Fix the depends_on field to have proper enum
        schema["properties"]["depends_on"] = {
            "type": "array",
            "items": {"type": "string", "enum": valid_ids},
            "description": f"Available dependency IDs: {', '.join(valid_ids)}",
        }

        return tool


def clean_string_mermaid(text):
    # Remove parentheses, quotes, and Mermaid-reserved symbols
    return re.sub(r'[()"\'<>{}\[\]|`#%@:;\\/]', "", text)
