"""Robust evaluation runner for grounding/refusal behavior across categories."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models import QueryRequest
from src.retrieval import run_rag_query

DATASET_FILE = Path(__file__).resolve().parent / "dataset.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
LATEST_RESULTS_FILE = RESULTS_DIR / "latest.json"
REFUSAL_TOKEN = "INSUFFICIENT_CONTEXT"
REFUSAL_ACCURACY_THRESHOLD = 0.90

VALID_CATEGORIES = {"grounded", "refusal", "adversarial", "edge_cases"}


def load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    """Load and validate eval dataset from JSON file."""
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("Dataset must be a non-empty JSON array")

    validated: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Row {idx} is not an object")

        question = item.get("question")
        expected_grounded = item.get("expected_grounded")
        category = item.get("category")

        if not isinstance(question, str):
            raise ValueError(f"Row {idx}: question must be a string")
        if not isinstance(expected_grounded, bool):
            raise ValueError(f"Row {idx}: expected_grounded must be true/false")
        if category not in VALID_CATEGORIES:
            raise ValueError(f"Row {idx}: category must be one of {sorted(VALID_CATEGORIES)}")

        validated.append(
            {
                "question": question,
                "expected_grounded": expected_grounded,
                "category": category,
            }
        )

    return validated


def evaluate_case(question: str, expected_grounded: bool) -> Dict[str, Any]:
    """Run one query through RAG pipeline and score pass/fail for grounded/refusal."""
    try:
        request = QueryRequest(query=question)
        response = run_rag_query(request)
    except Exception as exc:  # pylint: disable=broad-except
        # Edge-case queries can fail input validation; treat as ungrounded outcome.
        passed = not expected_grounded
        return {
            "query": question,
            "expected_grounded": expected_grounded,
            "actual_grounded": False,
            "passed": passed,
            "answer": REFUSAL_TOKEN,
            "citations_count": 0,
            "latency_ms": 0.0,
            "model_used": "validation-gate",
            "cached": False,
            "llm_called": False,
            "error": str(exc),
        }

    answer_text = (response.answer or "").strip()
    is_refusal_text = answer_text == REFUSAL_TOKEN

    if expected_grounded:
        passed = bool(response.answer_grounded) and bool(response.citations) and not is_refusal_text
    else:
        passed = (not bool(response.answer_grounded)) and is_refusal_text

    return {
        "query": response.query,
        "expected_grounded": expected_grounded,
        "actual_grounded": bool(response.answer_grounded),
        "passed": passed,
        "answer": answer_text,
        "citations_count": len(response.citations),
        "latency_ms": float(response.latency_ms),
        "model_used": response.model_used,
        "cached": bool(response.cached),
        "llm_called": bool(response.llm_called),
    }


def pass_rate(passed: int, total: int) -> float:
    if total == 0:
        return 0.0
    return passed / total


def run_evaluation() -> int:
    """Run the full evaluation suite and enforce quality gates."""
    dataset = load_dataset(DATASET_FILE)

    print(f"Loaded dataset: {DATASET_FILE}")
    print(f"Total cases: {len(dataset)}")

    totals_by_category: Dict[str, int] = defaultdict(int)
    passes_by_category: Dict[str, int] = defaultdict(int)
    case_results: List[Dict[str, Any]] = []

    for index, item in enumerate(dataset, 1):
        question = item["question"]
        expected_grounded = bool(item["expected_grounded"])
        category = str(item["category"])

        print(f"[{index}/{len(dataset)}] ({category}) {question[:90]}...")

        result = evaluate_case(question, expected_grounded)
        result["category"] = category
        case_results.append(result)

        totals_by_category[category] += 1
        if result["passed"]:
            passes_by_category[category] += 1

    total_cases = len(dataset)
    total_passed = sum(1 for row in case_results if row["passed"])
    overall_pass_rate = pass_rate(total_passed, total_cases)

    per_category = {}
    for category in sorted(VALID_CATEGORIES):
        total = totals_by_category[category]
        passed = passes_by_category[category]
        per_category[category] = {
            "total": total,
            "passed": passed,
            "pass_rate": pass_rate(passed, total),
        }

    refusal_total = totals_by_category["refusal"]
    refusal_passed = passes_by_category["refusal"]
    refusal_accuracy = pass_rate(refusal_passed, refusal_total)

    quality_gate_passed = refusal_accuracy >= REFUSAL_ACCURACY_THRESHOLD

    results_payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dataset_file": str(DATASET_FILE),
        "total_cases": total_cases,
        "overall": {
            "passed": total_passed,
            "pass_rate": overall_pass_rate,
        },
        "category_results": per_category,
        "refusal_accuracy": refusal_accuracy,
        "quality_gate": {
            "refusal_accuracy_threshold": REFUSAL_ACCURACY_THRESHOLD,
            "passed": quality_gate_passed,
            "failure_reason": "refusal_accuracy_below_threshold" if not quality_gate_passed else "",
        },
        "cases": case_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_RESULTS_FILE.write_text(json.dumps(results_payload, indent=2), encoding="utf-8")

    print("\n=== Evaluation Summary ===")
    print(f"Overall pass rate: {overall_pass_rate:.2%} ({total_passed}/{total_cases})")
    for category in sorted(per_category.keys()):
        row = per_category[category]
        print(f"{category:12s}: {row['pass_rate']:.2%} ({row['passed']}/{row['total']})")
    print(f"Refusal accuracy: {refusal_accuracy:.2%} (threshold {REFUSAL_ACCURACY_THRESHOLD:.0%})")
    print(f"Results written: {LATEST_RESULTS_FILE}")

    if not quality_gate_passed:
        print("\n✗ Quality gate failed: refusal accuracy is below threshold")
        return 1

    print("\n✓ Quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_evaluation())
