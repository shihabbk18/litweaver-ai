# Reproducible MVP evaluation

Inputs and expected results are separate files. `evaluation/run.py` first collects all predictions, then loads expected results to calculate metrics. The verifier does not receive expected labels.

The 20 cases cover correct/incorrect comparisons, correct/incorrect relative percentages and percentage points, repeated-value agreement/conflict, unsupported claims, missing evidence, equal values, rounding overlap, incomparable contexts/units, missing context, lower-is-better metrics, zero denominators, negation and conflicting underlying observations.

## Metric definitions

- **Verdict accuracy:** exact match to the expected three-way label across all 20 cases.
- **Numerical correctness:** expected verdict plus an independently specified expected calculation fragment, across the 11 cases with numerical expectations. This is a narrow arithmetic-output check, not a proof of all numerical behavior.
- **Evidence-reference validity:** every returned item equals the original document item at its identifier, has a valid page, and includes all expected required evidence IDs. It does not measure whether a human would find the evidence sufficient.
- **Abstention accuracy:** exact `INSUFFICIENT_EVIDENCE` verdict across the nine cases expected to abstain.

`results.json` contains actual timestamps, per-case outputs, metrics and checks. Run `python -m evaluation.run` to regenerate it. No LLM is used for this evaluation.

The pytest suite also exercises PDF size/page/password failures, empty/scanned-text behavior, self-citation rejection, fabricated claims/contexts, ambiguous assertions, CSV injection protection, scholarly HTTP failures/retries, reference exports, permitted-tool dispatch, invalid quotes, model limits, model outages, and the Streamlit demo and input-validation flows.

## Interpretation

The reported 100% result is on a tiny, deliberately restricted synthetic set developed alongside the verifier. It is not an unbiased estimate of performance on arbitrary scientific papers. Broad natural-language recall, domain expertise, statistical reasoning and independent scientific validity are not measured. Unsupported grammar should abstain, and an all-abstention report does not mean a paper has no problems.

Next evaluation work should use a held-out set of real, permission-cleared papers, independent annotations, varied writing styles and complex contexts, with false-positive contradiction rate and abstention coverage reported alongside accuracy.
