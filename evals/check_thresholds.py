"""Check if RAG evaluation quality gate passed."""

import json
import sys
from pathlib import Path


def check_thresholds() -> None:
    """Read eval results and check if quality gate passed."""
    results_path = Path(__file__).resolve().parent / "eval_results.json"
    
    if not results_path.exists():
        print("Error: evals/eval_results.json not found. Run evals/evaluate.py first.")
        sys.exit(1)
    
    try:
        results = json.loads(results_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Error reading evals/eval_results.json: {exc}")
        sys.exit(1)
    
    quality_gate = results.get("quality_gate", {}) if isinstance(results, dict) else {}
    threshold_passed = bool(quality_gate.get("passed", results.get("threshold_passed", False)))
    
    if threshold_passed:
        print("✓ Quality gate passed!")
        sys.exit(0)
    else:
        failure_reason = ""
        if isinstance(quality_gate, dict):
            failure_reason = str(quality_gate.get("failure_reason", "")).strip()
        print("QUALITY GATE FAILED" + (f": {failure_reason}" if failure_reason else ""))
        sys.exit(1)


if __name__ == "__main__":
    check_thresholds()
