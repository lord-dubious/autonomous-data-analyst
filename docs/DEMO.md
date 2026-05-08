# Demo Guide

This guide gives a safe way to evaluate **Autonomous Data Analyst** locally. The commands favor help screens, mock/dry-run paths, or clearly labeled local execution so the demo stays honest.

## Quick Orientation

Start with the CLI help and README sections before running any external-service path.

```bash
data-analyst --help
```
```bash
uvicorn api.main:app --reload
```
```bash
streamlit run app/streamlit_app.py
```

If a command needs live services or credentials, run the help command first and configure only the services you actually intend to test.

## Portfolio Walkthrough

Use this sequence in an interview or portfolio review:

1. Open the README and explain the problem the project solves in one sentence.
2. Open [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) and walk through the data flow.
3. Show the relevant model fields or tests that label mock, fallback, degraded, or warning states.
4. Run the local test suite or the project CI page to show the implementation is maintained.
5. Explain one tradeoff or limitation from the README instead of overselling the project.

## Suggested Demo Script

- **Problem**: CSV and DuckDB data-analysis assistant with FastAPI, Streamlit, Pydantic AI, and safe degraded metadata for failed loads/queries/analysis.
- **Engineering signal**: the project models external-service failure instead of hiding it.
- **Safety signal**: generated or assisted outputs are explicitly marked for human review.
- **Portfolio signal**: the Git history includes focused maintenance PRs, CI fixes, and docs polish.

## Screenshots And Videos

The README screenshot is generated from the real Streamlit surface, not a mock image:

```bash
streamlit run app/streamlit_app.py --server.headless true --server.port 8070
```

It shows the upload sidebar, controls area, and welcome flow that reviewers see before loading a CSV. If you add a video later, capture it from the same local app with sanitized sample data and include the exact command/config used to produce it.

## Demo Boundaries

- Analysis quality depends on dataset cleanliness and schema inference.
- Gemini/Pydantic AI paths need API configuration.
- Generated insights should be checked against the underlying data.
