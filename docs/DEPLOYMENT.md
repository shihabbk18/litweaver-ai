# Run and deploy LitWeaver

## Local

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

No LLM key is needed. Copy `.env.example` to `.env` only when configuring optional integrations.

## GitHub publication after authorization

Use the prepared source directory as its own repository. Do not add the parent workspace, virtual environment, `.env`, `.streamlit/secrets.toml`, temporary files, or user-uploaded papers.

```bash
git init -b main
git add .
git diff --cached --stat
git commit -m "Build LitWeaver evidence-grounded research MVP"
# Create an empty litweaver-ai repository in your GitHub account, then:
git remote add origin https://github.com/YOUR_ACCOUNT/litweaver-ai.git
git push -u origin main
```

Suggested description: **LitWeaver AI — An agentic scientific research assistant for academic discovery, evidence-grounded claim verification, numerical consistency checking, and research opportunity analysis.**

Project repository: [shihabbk18/litweaver-ai](https://github.com/shihabbk18/litweaver-ai). The owner has authorized public publication. The commands above also document how to publish an independent copy.

## Streamlit Community Cloud

1. Push the reviewed repository to your GitHub account.
2. Sign in at [Streamlit Community Cloud](https://share.streamlit.io/) with access to that repository.
3. Choose **Create app**, deploy from GitHub, select the repository and `main` branch, and set the entrypoint to `app.py`.
4. In advanced settings choose Python **3.12** to match the tested runtime. Install dependencies from `requirements.txt` automatically.
5. For basic operation no secrets are necessary. Optional secrets can be entered in the platform's secrets editor using TOML:

```toml
OPENALEX_API_KEY = "your-optional-free-key"
CROSSREF_MAILTO = "your-contact-email"
LLM_PROVIDER = "disabled"
```

For a hosted tool-capable model also set `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY`. Never commit this secrets file. A local Ollama endpoint on your PC will not be reachable as `localhost` from a cloud app.

6. Deploy, wait for the app to report ready, then open its assigned `streamlit.app` URL.
7. Verify all of the following on the **public** instance: a real topic returns publication links; CSV/Markdown/BibTeX downloads work; **Try synthetic example** finds two contradictions with PDF pages; oversized or invalid PDFs fail clearly; absent model configuration is visibly disabled.

The public deployment is complete only after those checks. See [official deployment documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).

## Container hosting

```bash
docker build -t litweaver-ai .
docker run --rm -p 8501:8501 --env-file .env litweaver-ai
# Omit --env-file .env when no optional configuration is needed.
```

The included Dockerfile serves Streamlit on port 8501. Configure the hosting platform for WebSockets and HTTPS. Keep XSRF/CORS protections enabled. Provide optional integrations through hosting secrets. The container definition has not been built here because Docker is unavailable in this workspace.

## Current blockers

- No authenticated hosting deployment has been established for this project. No public deployment URL has been generated or verified.
- No live LLM credentials/model or installed Ollama runtime were present. Tool protocol tests use clearly identified doubles; live provider interoperability remains to be checked with the chosen model.

The source, deterministic modes, sample PDF, evaluation, tests and exports can run locally while those external steps are pending.
