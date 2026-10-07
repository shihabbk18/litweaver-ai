# Actual validation record

Final test validation completed on **7 October 2026 (Asia/Dhaka)**. Machine-readable output timestamps use UTC; the live API smoke test is `2026-10-05T20:05:31.796386+00:00` (6 October locally).

## Automated checks

- `python -m pytest -q --tb=short -p no:cacheprovider`: **56 passed in 5.41 seconds**, executed after the final fixes, including malformed LLM responses. The resumed sandbox had ownership/access issues with earlier test files; the successful final run used the approved non-sandboxed environment and disabled pytest's cache.
- `python -m evaluation.run`: **20/20** correct verdicts; **11/11** numerical verdict/calculation checks; **20/20** evidence-reference checks; **9/9** expected abstentions.
- `python -m pip check`: **No broken requirements found.**
- `python -m compileall -q litweaver app.py scripts tests`: completed successfully.

This synthetic evaluation is not a validated scientific peer-review benchmark. See `EVALUATION.md` for the metric definitions and limitations.

## Real API smoke test

Executed `python scripts/smoke.py` against live OpenAlex and Crossref services.

- Query: Machine Learning for Network Traffic Optimization.
- 10 genuine OpenAlex records; all 10 included an abstract.
- Crossref enrichment ran for the first five DOI-bearing records.
- No recorded API warnings.
- CSV, Markdown and BibTeX were generated from actual returned records in `examples/output/`.

These are retrieval observations, not validation of the publications' scientific quality. The saved JSON includes original publication URLs, provider names and workflow events.

## PDF smoke test

The included, explicitly synthetic PDF has two pages and 36 extracted source items. Its report contains 10 candidate claims: **5 SUPPORTED, 2 CONTRADICTED, 3 INSUFFICIENT_EVIDENCE**. Both intentionally planted numerical errors were detected:

1. Model B is claimed to have higher accuracy, although the reported values are 84.2% for B and 87.4% for A.
2. A change from 80.0% to 92.0% is incorrectly described as 12% relative; the calculation gives 15%, or 12 percentage points.

Both pages were rendered with Poppler and visually inspected. Text and the bordered table were legible without overlap or clipping. The exported report cites actual PDF page numbers and evidence IDs.

## Running interface

The Streamlit server was started at `http://127.0.0.1:8503`. Browser checks exercised:

- A live literature search returning **15 papers, 15 abstracts, 14 DOI-linked records**, with three search queries.
- The PDF demo returning **10 claims, 5 supported, 2 contradicted and 3 abstentions**.
- Visible source excerpts, table values, actual PDF pages and the corrected percentage-point calculation.
- Disabled generative features when no LLM is configured.
- Visible CSV, Markdown, BibTeX and JSON download controls.

The 15-record browser search and the 10-record command-line smoke test use different requested limits; they are separate actual runs. Screenshots are in `docs/screenshots/`. AppTest also exercises initial rendering, the sample investigation, input validation and clearing the session.

## Not verified / external blockers

- A live LLM provider or Ollama model was not available. Tool protocol/dispatch tests use identified doubles and are not claimed as live-model validation.
- Docker is not installed, so the included container definition was not built.
- GitHub CI **passed** for source commit `f7d297af5216a6a8aebaaecbe4a9c557213e301e`: https://github.com/shihabbk18/litweaver-ai/actions/runs/37532675854. The workflow executed pytest and the synthetic evaluation on Ubuntu with Python 3.12.
- Public GitHub publication was authorized on 7 October 2026; repository: https://github.com/shihabbk18/litweaver-ai. See the repository history for the published commit.
- Streamlit Community Cloud was opened and showed its sign-in page, including acceptance of its Terms of Service. User sign-in/terms acceptance is required before deployment can proceed; there is no verified public URL.

The test runtime was Python 3.12.14, Streamlit 1.65.0, Pydantic 2.13.5, Pandas 2.3.3, PyMuPDF 1.28.2, NumPy 2.5.3, Plotly 6.9.0 and pytest 9.1.1. Exact installed packages are in `requirements-lock.txt`.
