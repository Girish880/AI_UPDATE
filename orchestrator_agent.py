# backend/agents/orchestrator_agent.py
import logging
import asyncio
from typing import List, Dict, Any, Optional

from .executor_agent import ExecutorAgent

logger = logging.getLogger("OrchestratorAgent")


class OrchestratorAgent:
    """
    OrchestratorAgent coordinates test execution across multiple ExecutorAgents.
    """

    def __init__(self, parallelism: int = 3):
        self.parallelism = parallelism

    async def execute_tests(
        self, run_id: str, tests: List[Dict[str, Any]], parallelism: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes test cases in parallel batches using ExecutorAgents.
        :param run_id: Unique identifier for the run
        :param tests: List of test dictionaries
        :param parallelism: Number of parallel executors
        :return: List of execution results
        """
        parallelism = parallelism or self.parallelism
        logger.info(
            "Executing %d tests with parallelism=%d (run_id=%s)",
            len(tests),
            parallelism,
            run_id,
        )

        sem = asyncio.Semaphore(parallelism)

        async def _bounded_exec(test: Dict[str, Any]) -> Dict[str, Any]:
            async with sem:
                executor = ExecutorAgent(test, run_id)
                return await executor.run()

        # Run all tests concurrently with bounded parallelism
        results = await asyncio.gather(*[_bounded_exec(t) for t in tests])

        logger.info("Completed execution of %d tests", len(results))
        return results
