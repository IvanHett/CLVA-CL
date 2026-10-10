"""Intent router: the multi-stage intent resolution pipeline.

    exact match -> keyword match -> intent classifier -> semantic retrieval -> fallback

The first stage that is confident enough decides the intent. Baseline mode
stops after the two rule-based stages.
"""
from dataclasses import dataclass

from . import config
from .data_loader import Dataset, Module
from .ml import IntentClassifier, SemanticRetriever
from .preprocessing import normalise, stemmed

STAGE_EXACT = "exact"
STAGE_KEYWORD = "keyword"
STAGE_CLASSIFIER = "classifier"
STAGE_RETRIEVAL = "retrieval"
STAGE_FALLBACK = "fallback"

MODULE_INTENTS = ("module_info", "module_list")


@dataclass
class Resolution:
    intent: str
    stage: str
    confidence: float
    module: Module | None = None

    @property
    def matched(self) -> bool:
        return self.stage != STAGE_FALLBACK


class IntentRouter:
    def __init__(self, dataset: Dataset):
        self._dataset = dataset
        self._exact = {normalise(q): intent for q, intent in dataset.queries}
        self._classifier = IntentClassifier(dataset.queries)
        self._retriever = SemanticRetriever(dataset.queries)

    def resolve(self, query: str, mode: str = config.DEFAULT_MODE) -> Resolution:
        if mode not in config.MODES:
            raise ValueError(f"Unknown mode '{mode}', expected one of {config.MODES}")

        text = normalise(query)
        if not text:
            return Resolution(config.FALLBACK_INTENT, STAGE_FALLBACK, 0.0)

        module = self.find_module(text)

        resolution = self._exact_match(text) or self._keyword_match(text, module)
        if resolution is None and mode == config.MODE_ENHANCED:
            resolution = self._classify(text) or self._retrieve(text)
        if resolution is None:
            return Resolution(config.FALLBACK_INTENT, STAGE_FALLBACK, 0.0)

        resolution.module = module
        return resolution

    def find_module(self, text: str) -> Module | None:
        """Detect a module named in the query, by code (CS5002) or full name."""
        padded = f" {normalise(text)} "
        for module in self._dataset.modules:
            if f" {normalise(module.module_id)} " in padded or f" {normalise(module.module_name)} " in padded:
                return module
        return None

    def _exact_match(self, text: str) -> Resolution | None:
        intent = self._exact.get(text)
        return Resolution(intent, STAGE_EXACT, 1.0) if intent else None

    def _keyword_match(self, text: str, module: Module | None) -> Resolution | None:
        padded = f" {stemmed(text)} "
        best_weight: dict[str, int] = {}
        for rule in self._dataset.keyword_rules:
            # When a specific module is named, the generic module rules add nothing.
            if module is not None and rule.intent in MODULE_INTENTS:
                continue
            if all(f" {term} " in padded for term in rule.terms):
                best_weight[rule.intent] = max(best_weight.get(rule.intent, 0), rule.weight)
        if not best_weight:
            # A named module with no other topic ("tell me about CS5002") asks for its details.
            return Resolution("module_info", STAGE_KEYWORD, 1.0) if module is not None else None

        top = max(best_weight.values())
        winners = [intent for intent, weight in best_weight.items() if weight == top]
        # Two intents matching equally well is ambiguous: leave it to later stages.
        if len(winners) != 1:
            return None
        return Resolution(winners[0], STAGE_KEYWORD, 1.0)

    def _classify(self, text: str) -> Resolution | None:
        intent, probability = self._classifier.predict(text)
        if probability >= config.CLASSIFIER_THRESHOLD:
            return Resolution(intent, STAGE_CLASSIFIER, probability)
        return None

    def _retrieve(self, text: str) -> Resolution | None:
        intent, similarity, _ = self._retriever.search(text)
        if similarity >= config.RETRIEVAL_THRESHOLD:
            return Resolution(intent, STAGE_RETRIEVAL, similarity)
        return None
