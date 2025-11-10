import json
import logging
import asyncio
import time

from openai import pydantic_function_tool

from app.clients.openai_client import OpenAIRequest
from app.common.sse_stream import SSEStream
from app.orchestration.request_context import RequestContext
from app.common.messages import AssistantMessage, ToolMessage, SystemMessage

from app.pipeline import (
    TaskPlan,
    InitialParseNode,
    InitialParseResult,
    TaskGenerationNode,
    BookClassificationResult,
    BookClassificationNode,
)

from app.common.prompt_loader import format_prompt, load_prompt

from app.domains.books.strategies import BOOK_STRAT_REGISTRY


logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main orchestration engine for processing user queries through AI pipelines.

    Coordinates the execution of multi-step pipelines including query parsing,
    task classification, dependency resolution, and task execution.
    """

    def __init__(self):
        """Initialize the orchestrator."""
        pass

    async def _handle_tool_call(
        self, tool_calls, max_calls: int = 10, **extra_kwargs
    ) -> list[ToolMessage]:
        """
        Execute LLM tool calls and collect results.

        Args:
            tool_calls: List of OpenAI tool calls to execute
            max_calls: Maximum number of calls to process
            **extra_kwargs: Additional arguments passed to tool instances

        Returns:
            List of ToolMessage results
        """
        results = []
        for tool_call in tool_calls[:max_calls]:
            try:

                tool_name = tool_call.function.name
                tool_id = tool_call.id
                logger.info(f"Starting tool call: {tool_name} (id: {tool_id})")

                raw_args = json.loads(tool_call.function.arguments)
                tool_instance = tool_call.function.parsed_arguments

                start = time.monotonic()
                logger.info(f"Executing {tool_name}")

                result = await tool_instance(**extra_kwargs)
                elapsed = round(time.monotonic() - start, 2)

                logger.info(f"Tool {tool_name} completed successfully in {elapsed}s")

                results.append(
                    ToolMessage(
                        name=tool_call.function.name,
                        tool_call_id=tool_call.id,
                        content=result,
                        elapsed=elapsed,
                    )
                )
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed for tool {tool_name}: {e}")
                continue
            except Exception as e:
                logger.error(
                    f"Tool execution failed for {tool_name}: {e}", exc_info=True
                )
                continue

        return results

    async def _run_initial_step(self, request_context, sse_stream) -> str | None:
        """
        Run initial parsing to classify query scope and determine pipeline continuation.

        Args:
            request_context: Current request context with conversation history
            sse_stream: Server-sent events stream for real-time updates

        Returns:
            InitialParseResult containing classification and reasoning
        """

        await sse_stream.send_ui_loading("Thinking...")

        tool_name = InitialParseNode.__name__
        tool = pydantic_function_tool(
            InitialParseNode,
            name=tool_name,
            description=f"Fill the schema for {tool_name}",
        )
        tool_choice = {"type": "function", "function": {"name": tool_name}}

        request_context.set_current_step("initial_parse")

        pipeline_messages = request_context.get_conversation_for_llm(
            include_pipeline=True
        )

        prompt = load_prompt(prompt_path="pipeline/initial_system.txt")
        req = OpenAIRequest(
            system=SystemMessage(content=prompt),
            messages=pipeline_messages,
            tools=[tool],
            tool_choice=tool_choice,
            temperature=0.3,
            top_p=0.8,
        )
        assistant_msg = await request_context.llm_client.execute(req)

        if not assistant_msg or not assistant_msg.tool_calls:
            raise RuntimeError(f"{tool_name} parse failed")

        request_context.add_message(assistant_msg)
        tool_message = await self._handle_tool_call(
            assistant_msg.tool_calls, max_calls=1
        )

        if not tool_message:
            raise RuntimeError(f"{tool_name} call failed")

        request_context.add_message(tool_message[0])

        parse_result = tool_message[0].content
        request_context.set_step_result("initial_parse", parse_result)

        no_in_domain_msg = tool_message[0].content.model_dump_json(
            include={"small_talk", "out_of_scope", "continue_pipeline"}
        )

        prompt = load_prompt(prompt_path="pipeline/initial_parse_response.txt")
        req = OpenAIRequest(
            system=SystemMessage(content=prompt),
            messages=[AssistantMessage(content=no_in_domain_msg)],
            sse_stream=sse_stream,
            temperature=0.7,
            top_p=1.0,
        )

        response = await request_context.llm_client.execute(req)

        await sse_stream.send_divider()

        request_context.add_message(response)

        return tool_message[0].content

    async def _run_analyze_classification(
        self,
        request_context: RequestContext,
        initial_parse_result: InitialParseResult,
    ) -> BookClassificationResult:
        """
        Classify user query into specific book-related strategies.

        Args:
            request_context: Current request context
            initial_parse_result: Result from initial parsing step

        Returns:
            BookClassificationResult with classified strategies
        """
        tool_name = BookClassificationNode.__name__
        tool = pydantic_function_tool(
            BookClassificationNode,
            name=tool_name,
            description=f"Fill the schema for {tool_name}",
        )
        tool_choice = {"type": "function", "function": {"name": tool_name}}

        in_domain_msg = initial_parse_result.model_dump_json(
            include={"user_query_domain", "continue_pipeline", "reasoning"}
        )

        from app.config.constants import BookConstraints, BookGuides

        prompt = format_prompt(
            prompt_path="books/strategy_classification.txt",
            book_constraints=str(BookConstraints()),
            book_guides=str(BookGuides()),
        )
        req = OpenAIRequest(
            system=SystemMessage(content=prompt),
            messages=[AssistantMessage(content=in_domain_msg)],
            tools=[tool],
            tool_choice=tool_choice,
            temperature=0.4,
            top_p=0.5,
        )

        assistant_msg = await request_context.llm_client.execute(req)

        if not assistant_msg or not assistant_msg.tool_calls:
            raise RuntimeError(
                f"Failed to execute {tool_name} - no tool calls received"
            )

        request_context.add_message(assistant_msg)
        tool_message = await self._handle_tool_call(
            assistant_msg.tool_calls, max_calls=1
        )
        if not tool_message:
            raise RuntimeError(f"{tool_name} call failed")

        request_context.add_message(tool_message[0])

        return tool_message[0].content

    async def _run_create_task_plan(
        self,
        request_context: RequestContext,
        initial_parse_result: InitialParseResult,
        node_ids,
    ) -> TaskPlan:
        """
        Generate task execution plan with dependency resolution.

        Args:
            request_context: Current request context
            initial_parse_result: Result from initial parsing
            node_ids: Dictionary of available node IDs and their definitions

        Returns:
            TaskPlan with ordered task execution strategy
        """

        tool_name = TaskGenerationNode.__name__
        tool_choice = {"type": "function", "function": {"name": tool_name}}
        tool = pydantic_function_tool(
            TaskGenerationNode,
            name=tool_name,
            description=f"Fill the schema for {tool_name}",
        )
        TaskGenerationNode.modify_schema(tool=tool, valid_ids=list(node_ids.keys()))

        in_domain_msg = initial_parse_result.model_dump_json(
            include={"user_query_domain", "reasoning"}
        )

        formatted_node_ids = {}
        for id in node_ids:
            formatted_node_ids[id] = node_ids[id].model_dump()

        prompt = load_prompt(prompt_path="pipeline/dependency_resolution.txt")
        req = OpenAIRequest(
            system=SystemMessage(content=prompt),
            messages=[
                AssistantMessage(content=in_domain_msg),
                AssistantMessage(
                    content=json.dumps(formatted_node_ids, separators=(",", ":"))
                ),
            ],
            tools=[tool],
            tool_choice=tool_choice,
            temperature=0.4,
            top_p=0.5,
        )

        assistant_msg = await request_context.llm_client.execute(req)

        if not assistant_msg or not assistant_msg.tool_calls:
            raise RuntimeError(f"{tool_name} parse failed")

        request_context.add_message(assistant_msg)
        tool_message = await self._handle_tool_call(
            assistant_msg.tool_calls, max_calls=1, node_ids=node_ids
        )
        if not tool_message:
            raise RuntimeError(f"{tool_name} call failed")

        request_context.add_message(tool_message[0])

        return tool_message[0].content

    async def run_tasks(
        self, node_ids, task_planner_: TaskPlan, sse_stream: SSEStream, request_context
    ):
        """
        Execute tasks according to dependency-resolved plan.

        Args:
            node_ids: Available task node definitions
            task_planner_: Resolved task execution plan
            sse_stream: Stream for sending updates
            request_context: Current request context

        Returns:
            Dictionary mapping task IDs to their results
        """

        depends_map = {cur.id: cur.depends_on for cur in task_planner_.accepted}
        results = {}

        for tid in task_planner_.execution_order:
            task = node_ids[tid]
            deps = {d: results[d] for d in depends_map[tid]}

            node_type = task.node_type

            strategy_class = BOOK_STRAT_REGISTRY[node_type]
            strategy_instance = strategy_class()

            result = await strategy_instance(
                task=task, dependent_results=deps, request_context=request_context
            )

            results[tid] = result

        return results

    async def _run_conversation_step(
        self,
        request_context: RequestContext,
        sse_stream: SSEStream,
    ):
        """
        Execute complete conversation pipeline from parsing to task execution.

        Steps:
        1. Initial parsing and scope classification
        2. Strategy classification
        3. Task plan generation
        4. Task execution with dependency resolution

        Args:
            request_context: Current request context
            sse_stream: Stream for real-time updates
        """
        try:
            initial_parse_result = await self._run_initial_step(
                request_context, sse_stream
            )
            if (
                not initial_parse_result.continue_pipeline
                or not initial_parse_result.user_query_domain
            ):
                logger.info(
                    "User query classified as out-of-scope or no domain identified. Ending pipeline."
                )
                return

            request_context.pipeline_context["in_domain_message"] = (
                initial_parse_result.model_dump_json(
                    include={"user_query_domain", "continue_pipeline", "reasoning"}
                )
            )

            await sse_stream.send_ui_loading("Classifying User Request...")

            classified_strategy_ = await self._run_analyze_classification(
                request_context=request_context,
                initial_parse_result=initial_parse_result,
            )

            node_ids = classified_strategy_.get_accepted_node_ids()

            await sse_stream.send_ui_loading("Planning The Tasks...")
            task_planner_ = await self._run_create_task_plan(
                request_context=request_context,
                initial_parse_result=initial_parse_result,
                node_ids=node_ids,
            )

            if task_planner_:
                mermaid_diagram = task_planner_.get_accepted_diagram(node_ids)
                await sse_stream.send_chars("__My Plan for Your Request__")
                await sse_stream.send_mermaid(mermaid_diagram)
                await sse_stream.send_chars(
                    "_Note:_ This flow shows how your query will run.\n"
                )
                await sse_stream.send_chars(
                    "Soon, you’ll be able to edit or customize the plan before execution for full transparency!"
                )
                await sse_stream.send_divider()
            else:
                await sse_stream.send_error("Unable to generate a Task Planner")

            await sse_stream.send_ui_loading("Executing the tasks...")

            result = await self.run_tasks(
                node_ids,
                task_planner_,
                sse_stream=sse_stream,
                request_context=request_context,
            )

        except Exception as e:
            logger.error(f"Error in conversation step: {str(e)}")
            raise
        finally:
            pass

    async def run(self, request_context: RequestContext):
        """
        Main entry point for orchestration with SSE streaming.

        Args:
            request_context: Request context containing conversation and state
        """
        sse_stream = request_context.sse_stream
        try:
            await sse_stream.send_ui_loading("Starting conversation...")

            # Core work
            await asyncio.wait_for(
                self._run_conversation_step(request_context, sse_stream),
                timeout=300.0,
            )

            await sse_stream.send_event("complete", {"status": "completed"})
            logger.info("Orchestration completed successfully")

        except asyncio.TimeoutError:
            msg = "Uhh... request timed out (5 mins) while processing your query."
            logger.warning(msg)
            await sse_stream.send_error(msg)

        except asyncio.CancelledError:
            logger.info("Orchestration cancelled before shutdown or client abort.")
            await sse_stream.send_error(
                f"Oh no... orchestration server while processing your query."
            )

        except Exception as e:
            logger.exception(f"Unhandled orchestrator error: {e}")
            await sse_stream.send_error(
                f"Hmm... something went wrong while processing your query."
            )

        finally:
            await sse_stream.close()
