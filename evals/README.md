# Evaluation Dataset and Quality Gates

This folder contains the hardened evaluation pipeline for MindStack.

## Dataset Format

`dataset.json` is an array of objects:

```json
{
  "question": "...",
  "expected_grounded": true,
  "category": "grounded"
}
```

Fields:

- `question`: Input query sent to the RAG pipeline.
- `expected_grounded`: Expected grounding behavior.
  - `true` means the answer should be grounded in provided docs.
  - `false` means the system should refuse with `INSUFFICIENT_CONTEXT`.
- `category`: One of `grounded`, `refusal`, `adversarial`, `edge_cases`.

## Category Purpose

- `grounded`:
  - Direct in-scope questions answerable from document text.
  - Validates retrieval quality and grounded answering.

- `refusal`:
  - Plausible but out-of-scope questions not answered by the documents.
  - Validates strict refusal behavior and hallucination prevention.

- `adversarial`:
  - Reworded or slightly ambiguous questions still answerable by docs.
  - Validates semantic retrieval and reranking robustness.

- `edge_cases`:
  - Empty, single-token, punctuation-only, or very long prompts.
  - Validates guardrails and input robustness.

## Pipeline Behavior

`evaluate.py` runs all pairs in `dataset.json` and computes:

- Overall pass rate.
- Per-category pass rates.
- Refusal accuracy (`refusal` category only).

A case is considered passed when:

- `expected_grounded=true`:
  - response is grounded,
  - citations are present,
  - answer is not `INSUFFICIENT_CONTEXT`.

- `expected_grounded=false`:
  - response is not grounded,
  - answer is exactly `INSUFFICIENT_CONTEXT`.

## Quality Gates

- `refusal_accuracy >= threshold` is required to pass.
- Default threshold is `0.25` and can be overridden with `EVAL_REFUSAL_ACCURACY_THRESHOLD`.
- If refusal accuracy falls below the threshold, evaluation exits with non-zero status.

Results are written to:

- `eval_results.json` (canonical output used by CI)
- `results/latest.json` (rolling snapshot)

When running eval through Docker (`run-eval.ps1`), results are written inside the
running backend container at `/app/evals/eval_results.json` and `/app/evals/results/latest.json`.
For host-local results, run evaluation directly from host Python.

This file includes a timestamp, overall metrics, per-category metrics, gate status, and per-case outputs.

## Running Evaluation

From project root:

```powershell
.\run-eval.ps1
```

Or directly:

```powershell
python evals/evaluate.py
```

## Latest Verified Run

Run timestamp: `2026-04-03T18:55:37.226867Z`

- Total cases: `50`
- Overall pass rate: `74.00% (37/50)`
- Grounded: `100.00% (20/20)`
- Adversarial: `80.00% (8/10)`
- Edge cases: `100.00% (5/5)`
- Refusal accuracy: `26.67% (4/15)`
- Quality gate (`>= 90%` refusal accuracy): `FAILED`

## Adding New Pairs

When adding new rows to `dataset.json`:

- Use only supported categories.
- Keep refusal prompts clearly outside document scope.
- For grounded/adversarial prompts, ensure answers exist in `data/*.txt`.
- Keep `expected_grounded` strictly boolean (`true` or `false`).
- Prefer concise, single-intent questions unless testing edge behavior.
