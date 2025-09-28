import os
import json
from datetime import datetime


def ensure_dir(path: str):
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)


def generate_report(run_id: str, test_results: list, artifacts: dict, notes: str = "") -> str:
    """
    Generate a structured JSON report for a test run.

    Args:
        run_id (str): Unique run identifier.
        test_results (list): List of results from AnalyzerAgent/ExecutorAgents.
        artifacts (dict): Mapping of test_name → artifact paths.
        notes (str): Optional triage notes.

    Returns:
        str: Path to the generated JSON report.
    """
    report_dir = "reports"
    ensure_dir(report_dir)

    report_data = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_tests": len(test_results),
            "passed": sum(1 for r in test_results if r.get("status") == "passed"),
            "failed": sum(1 for r in test_results if r.get("status") == "failed"),
        },
        "results": test_results,
        "artifacts": artifacts,
        "notes": notes,
    }

    report_path = os.path.join(report_dir, f"{run_id}_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    return report_path
