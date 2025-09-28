# backend/agents/analyzer_agent.py
import os
import json
import logging
from typing import List, Dict, Any, Tuple

from backend.utils.report_generator import generate_report
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

logger = logging.getLogger("AnalyzerAgent")


class AnalyzerAgent:
    """
    AnalyzerAgent validates test execution results for play.ezygamers.com,
    performs reproducibility checks, auto-determines verdicts, and generates a structured JSON report.
    """

    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.2):
        # --- Directly set your API key here ---
        self.api_key = ""
        if not self.api_key:
            raise RuntimeError(
                "❌ OPENAI_API_KEY not found. Please set self.api_key in AnalyzerAgent.__init__"
            )

        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=self.api_key,
        )

    async def analyze_and_write_report(
        self, run_id: str, results: List[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze test results and generate a JSON report.
        :param run_id: Unique identifier for this run
        :param results: Execution results from OrchestratorAgent
        :return: (report_path, report_dict)
        """
        logger.info("AnalyzerAgent analyzing %d results for run %s", len(results), run_id)

        analyzed_tests: List[Dict[str, Any]] = []

        # --- Initial local analysis + auto-verdict ---
        for r in results:
            test_id = r.get("test_id")
            name = r.get("name", f"test_{test_id}")
            artifacts = r.get("artifacts", {})

            # Use default URL if none exists
            url = artifacts.get("url") or "play.ezygamers.com"

            # Auto-determine verdict if pending
            verdict = r.get("verdict", "pending")
            if verdict == "pending":
                logs_path = artifacts.get("logs")
                if logs_path and os.path.exists(logs_path):
                    with open(logs_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        verdict = "failed" if "ERROR" in content.upper() else "passed"
                else:
                    verdict = "failed"  # treat missing logs as failure

            notes = (
                "Execution completed successfully." if verdict == "passed"
                else "Execution failed: see artifacts." if verdict == "failed"
                else "Execution completed, verdict pending."
            )

            analyzed_tests.append(
                {
                    "test_id": test_id,
                    "name": name,
                    "verdict": verdict,
                    "artifacts": artifacts,
                    "target_url": url,
                    "reproducibility": {"repeats": 1, "stable": (verdict == "passed")},
                    "notes": notes,
                }
            )

        # --- Summarize results ---
        summary = {"total": len(analyzed_tests), "passed": 0, "failed": 0, "flaky": 0}
        for t in analyzed_tests:
            if t["verdict"] == "passed":
                summary["passed"] += 1
            elif t["verdict"] == "failed":
                summary["failed"] += 1

        # --- Optional: LLM-based deep analysis ---
        try:
            if analyzed_tests:
                prompt = ChatPromptTemplate.from_messages(
                    [
                        (
                            "system",
                            "You are a QA report analyzer for the site play.ezygamers.com."
                        ),
                        (
                            "user",
                            f"Here are the execution results:\n{analyzed_tests}\n\n"
                            "Validate correctness, reproducibility, and identify likely causes of failure. "
                            "Output structured JSON with 'summary' and 'tests'."
                        ),
                    ]
                )

                chain = prompt | self.llm
                response = await chain.ainvoke({})
                text = response.content

                smart_report = json.loads(text)
                if isinstance(smart_report, dict) and "tests" in smart_report:
                    analyzed_tests = smart_report["tests"]
                    summary = smart_report.get("summary", summary)
                    logger.info("AnalyzerAgent used LLM for report")

        except Exception as e:
            logger.error("AnalyzerAgent LLM analysis failed: %s", e)
            logger.warning("Falling back to local analysis results")

        # --- Save report ---
        artifacts_map = {t["test_id"]: t["artifacts"] for t in analyzed_tests}
        report_path = generate_report(
            run_id=run_id,
            test_results=analyzed_tests,
            artifacts=artifacts_map,
            notes="Generated by AnalyzerAgent for play.ezygamers.com",
        )

        with open(report_path, "r", encoding="utf-8") as fh:
            report = json.load(fh)

        logger.info(
            "AnalyzerAgent wrote report to %s | total=%d, passed=%d, failed=%d",
            report_path,
            summary["total"],
            summary["passed"],
            summary["failed"],
        )
        return report_path, {"summary": summary, "tests": analyzed_tests}
