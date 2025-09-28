# backend/agents/executor_agent.py
import logging
import asyncio
from typing import Dict, Any
from backend.utils.artifact_capture import capture_artifacts


logger = logging.getLogger("ExecutorAgent")


class ExecutorAgent:
    """
    ExecutorAgent runs a single test case against the target game.
    Uses Playwright to capture artifacts (screenshot, DOM snapshot, logs).
    """

    def __init__(self, test: Dict[str, Any], run_id: str):
        self.test = test
        self.run_id = run_id

    async def run(self) -> Dict[str, Any]:
        """
        Execute the test and return result with artifacts.
        """
        test_id = self.test.get("id", "unknown")
        test_name = self.test.get("name", f"test_{test_id}")
        target_url = self.test.get("target_url", "http://localhost:8000")

        logger.info("ExecutorAgent starting test %s (%s)", test_id, target_url)

        # Run artifact capture in a thread (Playwright is blocking sync code)
        loop = asyncio.get_event_loop()
        artifacts = await loop.run_in_executor(
            None, capture_artifacts, target_url, self.run_id, test_name
        )

        result = {
            "test_id": test_id,
            "name": test_name,
            "status": "completed" if "error" not in artifacts else "failed",
            "verdict": "pending",  # AnalyzerAgent decides final verdict
            "artifacts": artifacts,
        }

        logger.info("ExecutorAgent finished test %s with status=%s", test_id, result["status"])
        return result
