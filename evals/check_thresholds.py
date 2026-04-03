"""Check if RAG evaluation quality gate passed."""

import json
import sys
from pathlib import Path


def check_thresholds() -> None:
    """Read eval results and check if quality gate passed."""
    results_path = Path("eval_results.json")
    
    if not results_path.exists():
        print("Error: eval_results.json not found. Run evaluate.py first.")
        sys.exit(1)
    
    try:
        results = json.loads(results_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading eval_results.json: {e}")
        sys.exit(1)
    
    threshold_passed = results.get("threshold_passed", False)
    
    if threshold_passed:
        print("✓ Quality gate passed!")
        sys.exit(0)
    else:
        print("QUALITY GATE FAILED: faithfulness below threshold")
        sys.exit(1)


if __name__ == "__main__":
    check_thresholds()
