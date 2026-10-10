"""Data layer: loads the CSV files that drive the chatbot."""
import csv
from dataclasses import dataclass
from pathlib import Path

from . import config
from .preprocessing import stemmed


@dataclass(frozen=True)
class KeywordRule:
    intent: str
    terms: tuple[str, ...]  # every term must appear in the query

    @property
    def weight(self) -> int:
        return sum(len(term.split()) for term in self.terms)


@dataclass(frozen=True)
class Module:
    module_id: str
    module_name: str
    description: str
    assessment: str
    year: int
    credits: int
    module_type: str  # Core or Optional


@dataclass
class Dataset:
    queries: list[tuple[str, str]]  # (query text, intent)
    answers: dict[str, str]  # intent -> response
    keyword_rules: list[KeywordRule]
    modules: list[Module]


def _read_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def _parse_rules(intent: str, spec: str) -> list[KeywordRule]:
    """'deadline|when+due' -> one rule per '|' alternative, '+' joins required terms."""
    rules = []
    for alternative in spec.split("|"):
        terms = tuple(stemmed(term) for term in alternative.split("+") if term.strip())
        if terms:
            rules.append(KeywordRule(intent, terms))
    return rules


def load_dataset(
    queries_csv: Path = config.QUERIES_CSV,
    knowledge_base_csv: Path = config.KNOWLEDGE_BASE_CSV,
    modules_csv: Path = config.MODULES_CSV,
) -> Dataset:
    queries = [(r["query"], r["intent"]) for r in _read_rows(queries_csv) if r["query"]]

    answers: dict[str, str] = {}
    keyword_rules: list[KeywordRule] = []
    for row in _read_rows(knowledge_base_csv):
        answers[row["intent"]] = row["answer"]
        keyword_rules.extend(_parse_rules(row["intent"], row["keywords"]))

    modules = [
        Module(
            r["module_id"], r["module_name"], r["description"], r["assessment"],
            int(r["year"]), int(r["credits"]), r["module_type"],
        )
        for r in _read_rows(modules_csv)
    ]

    unknown = {intent for _, intent in queries} - set(answers)
    if unknown:
        raise ValueError(f"queries.csv uses intents missing from knowledge_base.csv: {sorted(unknown)}")

    return Dataset(queries, answers, keyword_rules, modules)
