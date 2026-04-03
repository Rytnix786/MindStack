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

- `refusal_accuracy >= 90%` is required to pass.
- If refusal accuracy falls below 90%, evaluation exits with non-zero status.

Results are written to:

- `results/latest.json`

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

## Adding New Pairs

When adding new rows to `dataset.json`:

- Use only supported categories.
- Keep refusal prompts clearly outside document scope.
- For grounded/adversarial prompts, ensure answers exist in `data/*.txt`.
- Keep `expected_grounded` strictly boolean (`true` or `false`).
- Prefer concise, single-intent questions unless testing edge behavior.
