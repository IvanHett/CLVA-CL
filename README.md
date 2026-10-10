# CLVA – Course Leader Virtual Assistant (early prototype)

A chat-based virtual assistant that answers routine course and university queries.
Final year project, BSc (Hons) Computer Science – Ivantha Hetti Arachchige (2502650).

This prototype implements the design in *Artefact Design and Test Plan*:

- **Client layer** – web chat interface, CLI (`app.py`) and JSON API (`POST /ask`)
- **Application core** – preprocessing → multi-stage intent router → response generator
- **ML components** – intent classifier (logistic regression) and semantic retrieval (sentence similarity)
- **Data layer** – CSV files (`queries.csv`, `knowledge_base.csv`, `modules.csv`)
- **Evaluation logging** – every query and response, plus unanswered queries with a frequency count

## Setup

```
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Running

| What | Command |
| --- | --- |
| Web chat + API (http://127.0.0.1:5000) | `.venv\Scripts\python.exe -m src.api` |
| CLI chat | `.venv\Scripts\python.exe app.py` (add `--debug` to see intent, stage and timing) |
| One question | `.venv\Scripts\python.exe app.py "when is my assignment due"` |
| Review unanswered queries | `.venv\Scripts\python.exe app.py --unanswered` |
| Automated tests | `.venv\Scripts\python.exe -m pytest` |
| Baseline vs enhanced evaluation | `.venv\Scripts\python.exe -m evaluation.evaluate` |

## How a query is answered

```
normalise + tokenise
   → exact match          query is identical to a known query          (baseline + enhanced)
   → keyword match        keyword rules / a named module               (baseline + enhanced)
   → intent classifier    probability ≥ CLASSIFIER_THRESHOLD           (enhanced only)
   → semantic retrieval   similarity ≥ RETRIEVAL_THRESHOLD             (enhanced only)
   → fallback             "I don't have an answer", query is recorded
```

The first stage that is confident enough decides the intent. **Baseline** mode stops after
the two rule-based stages; **enhanced** mode runs the full pipeline. The mode can be chosen
per request, in the web UI and on the CLI, which is what the test plan's
baseline-vs-enhanced comparison needs. Thresholds live in `src/config.py`.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /ask` | Body `{"query": "...", "mode": "enhanced" \| "baseline"}`. Returns answer, intent, stage, confidence, matched, response time and query id. |
| `GET /modules` | All modules from `modules.csv`. |
| `GET /admin/unanswered` | Unanswered queries, most frequent first. |
| `GET /health` | Status check. |

## Project layout

```
app.py                  CLI
src/preprocessing.py    normalisation, tokenisation, light stemming
src/data_loader.py      loads the CSV data
src/pipeline.py         intent router (the four stages + fallback)
src/ml.py               intent classifier and semantic retriever
src/responder.py        response generator (KB / module / fallback)
src/storage.py          query, response and unanswered-query logs
src/chatbot.py          ties the above together
src/api.py              Flask API + serves the web UI
web/                    chat interface (HTML, CSS, JS)
data/                   queries.csv, knowledge_base.csv, modules.csv
evaluation/             test_queries.csv and evaluate.py
tests/                  automated system tests
logs/                   created at runtime
```

## Editing the knowledge

- **New answer** – add a row to `data/knowledge_base.csv` (`intent,keywords,answer`) and
  several example questions for it to `data/queries.csv`.
- **Keywords** – `|` separates alternatives and `+` joins words that must all appear:
  `late submission|submit+late`. When rules for two intents match, the longer rule wins;
  a tie is treated as ambiguous and passed to the later stages.
- **Modules** – edit `data/modules.csv`. Module list and module detail answers are generated from it.
- **Unanswered queries** – review `logs/unanswered_queries.csv`, then add the missing
  intents or example questions. Restart the app to reload the data.

## Logs

The log files mirror the planned database tables (ERD, Figure 2) so they can be imported later:

- `logs/queries_log.csv` – query_id, user_input, timestamp, predicted_intent
- `logs/responses_log.csv` – response_id, response_text, related_query_id, response_time_ms, matched, stage, mode
- `logs/unanswered_queries.csv` – id, query_text, frequency_count, first_seen, last_seen

## Current limitations

- **The knowledge base is only partly verified.** The modules and most answers were
  collected from public University of Wolverhampton web pages; `data/SOURCES.md` lists
  the source and status of each. Answers on extensions, late submission, submission,
  results and resit rules are still general, because the detailed rules are in the
  regulations documents, and module assessment details are blank.
- **Semantic retrieval is lexical.** It compares character n-gram TF-IDF vectors, so it
  copes with typos and rewording that shares words, but not with true paraphrases
  ("I had the flu" → mitigating circumstances). Swapping the vectoriser in
  `SemanticRetriever` for a sentence-embedding model is the planned next step.
- **Thresholds are untuned defaults.** They should be set on a validation set that is
  separate from `evaluation/test_queries.csv`.
- **The evaluation set is small and self-written** (82 queries). It measures intent
  accuracy, not whether the answer text is correct against official documentation.
- CSV logging suits a single-user prototype; the admin endpoint has no authentication.
