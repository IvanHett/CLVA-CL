"""System evaluation: compares the baseline and enhanced pipelines on the test queries.

    python -m evaluation.evaluate

Reports the test plan's quantitative metrics - accuracy, failure (fallback)
rate and response time - and writes the per-query results to
evaluation/results/.
"""
import csv
import statistics
from collections import Counter
from pathlib import Path

from src import config
from src.chatbot import Chatbot

EVAL_DIR = Path(__file__).resolve().parent
TEST_QUERIES_CSV = EVAL_DIR / "test_queries.csv"
RESULTS_DIR = EVAL_DIR / "results"
OUT_OF_SCOPE = "none"  # expected_intent for questions the bot should not answer


def load_test_queries(path: Path = TEST_QUERIES_CSV) -> list[tuple[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [(row["query"], row["expected_intent"].strip()) for row in csv.DictReader(f)]


def run(bot: Chatbot, tests: list[tuple[str, str]], mode: str) -> tuple[dict, list[dict]]:
    details = []
    for query, expected in tests:
        reply = bot.ask(query, mode)
        expected_intent = config.FALLBACK_INTENT if expected == OUT_OF_SCOPE else expected
        details.append({
            "mode": mode, "query": query, "expected_intent": expected,
            "predicted_intent": reply.intent, "stage": reply.stage,
            "confidence": reply.confidence, "correct": reply.intent == expected_intent,
            "response_time_ms": reply.response_time_ms,
        })

    in_scope = [d for d in details if d["expected_intent"] != OUT_OF_SCOPE]
    out_scope = [d for d in details if d["expected_intent"] == OUT_OF_SCOPE]
    times = [d["response_time_ms"] for d in details]
    stages = Counter(d["stage"] for d in details)
    summary = {
        "mode": mode,
        "queries": len(details),
        "accuracy_pct": pct(sum(d["correct"] for d in details), len(details)),
        "in_scope_accuracy_pct": pct(sum(d["correct"] for d in in_scope), len(in_scope)),
        "out_of_scope_rejected_pct": pct(sum(d["correct"] for d in out_scope), len(out_scope)),
        # Failure rate: in-scope questions the bot gave up on.
        "failure_rate_pct": pct(sum(d["stage"] == "fallback" for d in in_scope), len(in_scope)),
        # In-scope questions that got a confident answer for the wrong intent.
        "wrong_answer_pct": pct(
            sum(not d["correct"] and d["stage"] != "fallback" for d in in_scope), len(in_scope)
        ),
        "mean_time_ms": round(statistics.mean(times), 2),
        "max_time_ms": round(max(times), 2),
        **{f"stage_{s}": stages.get(s, 0) for s in ("exact", "keyword", "classifier", "retrieval", "fallback")},
    }
    return summary, details


def pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    bot = Chatbot()  # no logger: evaluation runs must not pollute the interaction logs
    tests = load_test_queries()
    bot.ask("warm up")  # exclude one-off start-up cost from timings

    summaries, all_details = [], []
    for mode in config.MODES:
        summary, details = run(bot, tests, mode)
        summaries.append(summary)
        all_details.extend(details)

    RESULTS_DIR.mkdir(exist_ok=True)
    write_csv(RESULTS_DIR / "summary.csv", summaries)
    write_csv(RESULTS_DIR / "details.csv", all_details)

    print(f"{'Metric':<28}" + "".join(f"{s['mode']:>12}" for s in summaries))
    for key in summaries[0]:
        if key != "mode":
            print(f"{key:<28}" + "".join(f"{s[key]:>12}" for s in summaries))

    for summary in summaries:
        wrong = [d for d in all_details if d["mode"] == summary["mode"] and not d["correct"]]
        print(f"\nIncorrect in {summary['mode']} mode ({len(wrong)}):")
        for d in wrong:
            print(f"  {d['query']!r}: expected {d['expected_intent']}, got {d['predicted_intent']} ({d['stage']})")
    print(f"\nResults written to {RESULTS_DIR}")


if __name__ == "__main__":
    main()
