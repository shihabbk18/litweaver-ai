"""Streamlit entry point. Run: streamlit run app.py"""
import json
import os
from collections import Counter
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from litweaver.agent import AgentSession, LLMConfig, Provider
from litweaver.models import Paper, ToolEvent
from litweaver.pdf import extract_pdf_text
from litweaver.reports import (FIELDS, bibtex_export, critic_report, csv_export,
                               generate_comparison_matrix, generate_investigation_report,
                               observed_themes, safe_url)
from litweaver.scholarly import ScholarlyClient, investigate, verify_publication_metadata
from litweaver.verification import analyze_document, extract_scientific_claims, observations_from_evidence, verify_numerical_claim

load_dotenv()
st.set_page_config(page_title="LitWeaver AI | Research with receipts", page_icon="🔬", layout="wide")
# Static trusted styling only. Source text is always rendered as text or escaped Markdown.
st.markdown("""<style>
.block-container {max-width: 1420px; padding-top: 5rem;}
h1 {letter-spacing: -1.8px; font-weight: 760 !important;}
h2,h3 {letter-spacing: -.5px;}
[data-testid="stMetric"] {background: white; border: 1px solid #dfe7ef; border-radius: 12px; padding: 16px;}
[data-testid="stTabs"] button {font-size: 1.05rem;}
.eyebrow {font-size: .75rem; letter-spacing: .16em; color: #167D8D; font-weight: 700;}
.hero-sub {font-size: 1.08rem; color: #566780; max-width: 850px; margin-bottom: 25px;}
</style>""", unsafe_allow_html=True)


def setting(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return os.getenv(name, default)


config = LLMConfig(setting("LLM_PROVIDER", "disabled"), setting("LLM_BASE_URL", "https://api.openai.com/v1"), setting("LLM_MODEL"), setting("LLM_API_KEY"))


def client():
    return ScholarlyClient(setting("OPENALEX_API_KEY"), setting("CROSSREF_MAILTO"))


def show_trace(events):
    if events:
        st.dataframe(pd.DataFrame([e.model_dump() for e in events]), width="stretch", hide_index=True)
    else:
        st.caption("No optional model tool calls were executed.")


def run_agent(session, request):
    with st.spinner("Model is selecting and invoking bounded research tools…"):
        try:
            session.run(Provider(config), request)
        except ValueError as exc:
            st.warning(str(exc))
    for event in session.trace:
        if event.tool == "llm_provider" and event.status == "error":
            st.warning(event.summary)


with st.sidebar:
    st.markdown("### LitWeaver AI")
    st.caption("EVIDENCE-GROUNDED RESEARCH")
    st.divider()
    st.markdown("**Research engine**")
    st.success("Deterministic tools ready")
    if config.enabled:
        st.caption(f"LLM provider: {config.provider} · {config.model}")
    else:
        st.info("No LLM configured. Generative synthesis and methodological critique are disabled.")
    use_llm = st.checkbox("Enable model-assisted investigation", value=False, disabled=not config.enabled,
        help="Enabling this sends selected source text to your configured LLM endpoint. The model may invoke up to 12 permitted tools.")
    if use_llm:
        st.caption("Selected abstracts or PDF excerpts will be sent to the configured model provider. Model concerns always require human review.")
    st.divider()
    st.markdown("**How to read a verdict**")
    st.caption("SUPPORTED · Agreement with the cited reported values or arithmetic.")
    st.caption("CONTRADICTED · A demonstrable inconsistency in comparable evidence.")
    st.caption("INSUFFICIENT EVIDENCE · Missing context, unsupported grammar, or uncertainty.")
    st.divider()
    st.caption("MVP research aid · Not autonomous peer review. No misconduct judgments. No OCR or figure interpretation.")
    if st.button("Clear session results", width="stretch"):
        for key in ("literature", "lit_annotations", "opportunities", "lit_agent_trace", "document", "critic_results", "critic_concerns", "critic_trace", "critic_baseline", "metadata_check"):
            st.session_state.pop(key, None)
        st.rerun()

st.markdown('<div class="eyebrow">DISCOVER · INSPECT · VERIFY</div>', unsafe_allow_html=True)
st.title("Research with receipts.")
st.markdown('<div class="hero-sub">Explore scientific literature and inspect numerical claims. Every finding links back to a source; uncertainty stays visible.</div>', unsafe_allow_html=True)
literature_tab, critic_tab = st.tabs(["Literature Investigator", "Research Critic"])

with literature_tab:
    with st.form("investigate_form"):
        left, right = st.columns([5, 1])
        topic = left.text_input("Research topic", placeholder="Machine Learning for Network Traffic Optimization", max_chars=250)
        limit = right.selectbox("Paper limit", [10, 15, 20], index=1)
        start = st.form_submit_button("Start Investigation", type="primary")
    st.caption("Live OpenAlex discovery · Crossref DOI checks · Abstract-only analysis · CSV, Markdown and BibTeX")
    if start:
        if len(topic.strip()) < 3:
            st.error("Enter a research topic with at least three characters.")
        else:
            progress = st.progress(0, text="Preparing academic search queries")
            api = client()
            try:
                run = investigate(topic, api, limit, lambda value, text: progress.progress(value, text=text))
                annotations, opportunities, trace = {}, [], []
                if use_llm and run.papers:
                    session = AgentSession(api, literature=run)
                    run_agent(session, f"Investigate {topic}. Use tools to inspect the matrix, select precise source excerpts, and suggest research questions grounded in explicit limitations. Generate the report.")
                    annotations, opportunities, trace = session.annotations, session.opportunities, session.trace
                st.session_state.update(literature=run, lit_annotations=annotations, opportunities=opportunities, lit_agent_trace=trace)
            except Exception as exc:
                st.error(f"Investigation could not complete ({type(exc).__name__}). Check connectivity and try again.")
            finally:
                api.close()
                progress.empty()
    run = st.session_state.get("literature")
    if run:
        for warning in run.warnings:
            st.warning(warning)
        st.subheader(run.topic)
        cols = st.columns(4)
        cols[0].metric("Publications", len(run.papers))
        cols[1].metric("Available abstracts", sum(bool(p.abstract) for p in run.papers))
        cols[2].metric("DOI-linked records", sum(bool(p.doi) for p in run.papers))
        cols[3].metric("Search queries", len(run.queries))
        if not run.papers:
            st.info("No records were retrieved. Try a narrower topic or inspect the API errors above.")
        else:
            annotations = st.session_state.get("lit_annotations", {})
            opportunities = st.session_state.get("opportunities", [])
            matrix = generate_comparison_matrix(run.papers, annotations)
            overview, comparison, sources, workflow = st.tabs(["Overview", "Literature matrix", "Source library", "Tool workflow"])
            with overview:
                c1, c2 = st.columns([1.2, 1])
                with c1:
                    st.markdown("#### Publication timeline")
                    years = pd.Series([p.year for p in run.papers if p.year], dtype=int).value_counts().sort_index()
                    if not years.empty:
                        chart = px.bar(x=years.index, y=years.values, labels={"x": "Publication year", "y": "Retrieved papers"}, color_discrete_sequence=["#167D8D"])
                        chart.update_layout(height=290, margin=dict(l=5, r=5, t=5, b=5), plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(chart, width="stretch")
                with c2:
                    st.markdown("#### Recurring terms")
                    themes = observed_themes(run.papers)
                    if themes:
                        for name, ids in themes.items():
                            st.write(f"**{name}** · {len(ids)} abstracts")
                    else:
                        st.caption("No repeated terms from the configured vocabulary were found.")
                    st.caption("Term occurrence is an observation about this retrieved set, not a finding about the entire literature.")
                st.markdown("#### Possible research questions")
                if opportunities:
                    for opportunity in opportunities:
                        st.write(opportunity["question"])
                        st.caption(f"Hypothesis requiring further verification · Source: {opportunity['paper_id']}")
                        st.text(opportunity["quote"])
                else:
                    st.info("Generative research questions are disabled or none were accepted. Inspect source limitation excerpts in the matrix to guide your next search.")
            with comparison:
                st.caption("Cells contain extractive passages. Missing information is left explicit. Available abstracts are not full-paper evidence.")
                st.dataframe(matrix, width="stretch", hide_index=True, column_config={"Source URL": st.column_config.LinkColumn("Source URL")})
            with sources:
                for i, paper in enumerate(run.papers, 1):
                    with st.expander(f"{i}. {paper.title} ({paper.year or 'year unknown'})"):
                        st.write("; ".join(paper.authors) or "Authors unavailable")
                        st.caption(f"{paper.venue or 'Venue unavailable'} · {paper.provider} · Relevance {paper.score:.2f}")
                        if paper.retracted:
                            st.error("OpenAlex marks this work as retracted. Inspect the publisher record.")
                        if safe_url(paper.url):
                            st.link_button("Open publication source", safe_url(paper.url))
                        st.text(paper.abstract or "No abstract available from the retrieved metadata.")
                        for note in paper.metadata_notes:
                            st.caption(note)
            with workflow:
                st.caption("Baseline steps are deterministic. Optional model-selected calls are labelled separately.")
                show_trace(run.trace)
                st.markdown("**Model-selected tools**")
                show_trace(st.session_state.get("lit_agent_trace", []))
            downloads = st.columns(3)
            downloads[0].download_button("Download CSV matrix", csv_export(matrix), "litweaver-matrix.csv", "text/csv", width="stretch")
            downloads[1].download_button("Download research report", generate_investigation_report(run, annotations, opportunities), "litweaver-literature.md", "text/markdown", width="stretch")
            downloads[2].download_button("Download BibTeX", bibtex_export(run.papers), "litweaver-references.bib", "application/x-bibtex", width="stretch")
    else:
        st.markdown("#### From question to traceable evidence")
        a, b, c = st.columns(3)
        a.info("**01 · Discover**\n\nSearch real academic records with multiple query variants.")
        b.info("**02 · Compare**\n\nInspect methods, contributions and limitations quoted from available abstracts.")
        c.info("**03 · Take it with you**\n\nExport the literature matrix, source-grounded report and citations.")

with critic_tab:
    st.markdown("### Inspect what a paper actually reports")
    st.caption("Up to 15 MB / 60 pages · Machine-readable PDFs · No OCR · At most 80 candidate claims")
    uploaded = st.file_uploader("Upload a scientific PDF", type=["pdf"])
    ca, cb, cc = st.columns([1, 1, 2])
    analyze = ca.button("Analyze Paper", type="primary", disabled=uploaded is None)
    sample_path = Path(__file__).parent / "examples" / "numerical-audit.pdf"
    demo = cb.button("Try synthetic example", disabled=not sample_path.exists())
    if sample_path.exists():
        cc.download_button("Download sample PDF", sample_path.read_bytes(), "numerical-audit.pdf", "application/pdf")
    if analyze or demo:
        try:
            with st.spinner("Extracting page-level evidence and checking numerical claims…"):
                document = extract_pdf_text(sample_path.read_bytes() if demo else uploaded.getvalue(), "numerical-audit.pdf" if demo else uploaded.name)
                baseline = [ToolEvent(tool="extract_pdf_text", arguments={"document":document.name}, status="ok", summary=f"{document.page_count} pages; {len(document.evidence)} excerpts")]
                results = analyze_document(document, baseline)
            concerns, trace = [], []
            if use_llm and document.evidence:
                api = client()
                try:
                    session = AgentSession(api, document=document)
                    run_agent(session, "Inspect this paper's claims with the available tools. Retrieve evidence, verify numerical claims, and flag source-grounded potential methodological or interpretive concerns for human review. Generate a report.")
                    concerns, trace = session.concerns, session.trace
                    results = [verify_numerical_claim(c, document) for c in session.claims]
                finally:
                    api.close()
            st.session_state.pop("metadata_check", None)
            st.session_state.update(document=document, critic_results=results, critic_concerns=concerns, critic_trace=trace, critic_baseline=baseline)
        except ValueError as exc:
            st.error(str(exc))
    document = st.session_state.get("document")
    if document:
        results = st.session_state.get("critic_results", [])
        counts = Counter(r.verdict.value for r in results)
        st.caption(f"Analyzed: {document.name} · {document.page_count} pages · {len(document.evidence)} evidence excerpts · SHA-256 {document.sha256[:16]}…")
        for warning in document.warnings:
            st.warning(warning)
        for col, label, value in zip(st.columns(4), ["Claims inspected", "Supported", "Contradicted", "Insufficient evidence"], [len(results), counts["SUPPORTED"], counts["CONTRADICTED"], counts["INSUFFICIENT_EVIDENCE"]]):
            col.metric(label, value)
        st.info("Verdicts describe consistency of reported evidence. They do not establish experimental truth. A separate review flag identifies unresolved interpretive concerns.")
        claims_tab, evidence_tab, concerns_tab, doi_tab, trace_tab = st.tabs(["Claim findings", "Evidence explorer", "Human review", "DOI metadata check", "Workflow & limits"])
        with claims_tab:
            filter_verdict = st.multiselect("Show verdicts", ["SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"], default=["SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE"])
            if not results:
                st.warning("No supported claim patterns were identified. This is not evidence that the paper has no errors.")
            for result in results:
                if result.verdict.value not in filter_verdict:
                    continue
                label = result.verdict.value.replace("_", " ")
                with st.expander(f"{result.claim.id} · {label} · {result.claim.text[:110]}", expanded=result.verdict.value == "CONTRADICTED"):
                    st.text(result.claim.text)
                    st.write(result.explanation)
                    if result.calculation:
                        st.code(result.calculation, language=None)
                    st.caption(f"{result.method} · Human review: {'required' if result.review_required else 'not separately flagged'}")
                    for e in result.evidence:
                        st.markdown(f"**Page {e.page} · {e.kind} · `{e.id}`**")
                        st.text(e.text)
                        if e.cells:
                            display_headers = [f"{header or 'Column'} [{i+1}]" for i, header in enumerate(e.cells[0])]
                            st.dataframe(pd.DataFrame(e.cells[1:], columns=display_headers), hide_index=True)
                    for limitation in result.limitations:
                        st.caption(limitation)
        with evidence_tab:
            st.caption("Verified extraction observations: these snippets were read from the document. Their scientific assertions are not independently verified.")
            page = st.selectbox("Page", list(range(1, document.page_count+1)))
            for e in document.evidence:
                if e.page == page:
                    with st.expander(f"{e.id} · {e.section} · {e.kind}"):
                        st.text(e.text)
                        st.caption(f"Experimental context: {e.context or 'Not established'}")
                        observations = observations_from_evidence(e)
                        if observations:
                            st.dataframe(pd.DataFrame([o.model_dump() for o in observations]), hide_index=True)
            with st.expander("Confirm experimental context for selected excerpts"):
                st.caption("When the parser cannot identify a dataset/split/setting, you may explicitly confirm which excerpts belong to the same experiment. These assumptions are disclosed in the report. Select both the claim and its supporting values.")
                selected = st.multiselect("Evidence excerpts", options=[e.id for e in document.evidence], format_func=lambda eid: next(f"p.{e.page} {e.text[:95]}" for e in document.evidence if e.id == eid))
                context_label = st.text_input("Confirmed dataset, split and experimental setting", placeholder="Dataset CIFAR-10; test split; single-run baseline", max_chars=200)
                if st.button("Apply confirmed context and recheck", disabled=len(selected)<2 or not context_label.strip()):
                    for e in document.evidence:
                        if e.id in selected:
                            e.context = "user-confirmed: " + context_label.strip().lower()
                    note = f"User-confirmed context '{context_label}' applied to evidence: {', '.join(selected)}. Context equivalence is an analyst assumption."
                    document.warnings.append(note)
                    st.session_state.critic_results = [verify_numerical_claim(r.claim.model_copy(update={"context":next(e.context for e in document.evidence if e.id == r.claim.source_id)}), document) for r in results]
                    st.session_state.critic_baseline.append(ToolEvent(tool="confirm_context_and_recheck", arguments={"evidence_ids":selected, "context":context_label}, status="ok", summary=f"Rechecked {len(results)} claims using disclosed analyst context"))
                    st.rerun()
        with concerns_tab:
            concerns = st.session_state.get("critic_concerns", [])
            if not concerns:
                st.info("No model-suggested concerns. Configure a tool-capable LLM and enable model-assisted investigation to use this feature.")
            for concern in concerns:
                st.warning(concern["concern"])
                st.caption(f"Potential concern requiring human review · Page {concern['page']} · {concern['evidence_id']}")
                st.text(concern["quote"])
            flagged = [r for r in results if r.review_required]
            st.caption(f"{len(flagged)} deterministic findings also carry a human-review flag.")
        with doi_tab:
            st.caption("Independently check a DOI against Crossref. Enter the cited title and year exactly; this does not prove the reference supports the paper's claim.")
            with st.form("doi_check"):
                doi = st.text_input("Cited DOI", max_chars=200)
                cited_title = st.text_input("Title as cited in the paper", max_chars=500)
                cited_year = st.number_input("Year as cited", min_value=1500, max_value=2100, value=2024)
                check_doi = st.form_submit_button("Verify DOI metadata")
            if check_doi:
                if not doi.strip() or not cited_title.strip():
                    st.error("Enter both the DOI and cited title.")
                else:
                    api = client()
                    try:
                        from litweaver.scholarly import normalize_doi
                        registered = api.retrieve_publication_metadata(doi)
                        asserted = Paper(id="user-entered-citation", title=cited_title, year=cited_year, doi=normalize_doi(doi), url="", provider="User transcription")
                        st.session_state.metadata_check = verify_publication_metadata(asserted, registered)
                    except Exception as exc:
                        st.error(f"Metadata could not be verified: {type(exc).__name__}")
                    finally:
                        api.close()
            if st.session_state.get("metadata_check"):
                st.json(st.session_state.metadata_check)
        with trace_tab:
            st.write("Executed deterministic tool calls")
            show_trace(st.session_state.get("critic_baseline", []))
            st.caption("Text, page, item and claim counts are bounded. Tables require detectable borders; numeric table checking requires explicit model, metric-unit and context columns. Across excerpts, the verifier requires an explicit matching context or a disclosed user confirmation. Unsupported phrasing abstains.")
            st.write("Optional model-selected tool calls")
            show_trace(st.session_state.get("critic_trace", []))
        report = critic_report(document, results, st.session_state.get("critic_concerns", []))
        dl1, dl2 = st.columns(2)
        dl1.download_button("Download verification report", report, "litweaver-critique.md", "text/markdown", width="stretch")
        dl2.download_button("Download evidence & results JSON", json.dumps({"document": document.model_dump(), "results": [r.model_dump(mode="json") for r in results], "concerns": st.session_state.get("critic_concerns", []), "tool_calls": [event.model_dump() for event in st.session_state.get("critic_baseline", []) + st.session_state.get("critic_trace", [])]}, indent=2), "litweaver-evidence.json", "application/json", width="stretch")
    else:
        st.caption("Start with the synthetic example to inspect known numerical errors and source locations. It is a demonstration fixture, not a real scientific paper.")

st.divider()
st.caption("LitWeaver AI · A small, auditable research assistant. Sources first. Abstention when uncertain.")
