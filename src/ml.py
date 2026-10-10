"""ML components: the intent classifier and the semantic retriever."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import linear_kernel
from sklearn.pipeline import make_pipeline

from .preprocessing import normalise


class IntentClassifier:
    """Logistic regression over word n-gram TF-IDF features."""

    def __init__(self, queries: list[tuple[str, str]]):
        texts = [normalise(q) for q, _ in queries]
        intents = [intent for _, intent in queries]
        self._model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True),
            LogisticRegression(C=20, max_iter=2000),
        )
        self._model.fit(texts, intents)

    def predict(self, text: str) -> tuple[str, float]:
        """Return the most likely intent and its probability."""
        probabilities = self._model.predict_proba([normalise(text)])[0]
        best = probabilities.argmax()
        return str(self._model.classes_[best]), float(probabilities[best])


class SemanticRetriever:
    """Finds the most similar known query by cosine similarity.

    Sentences are embedded as character n-gram TF-IDF vectors, which tolerates
    typos and word-form changes. A sentence-embedding model can replace the
    vectoriser here without touching the rest of the pipeline.
    """

    def __init__(self, queries: list[tuple[str, str]]):
        self._queries = [q for q, _ in queries]
        self._intents = [intent for _, intent in queries]
        self._vectoriser = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)
        self._matrix = self._vectoriser.fit_transform(normalise(q) for q in self._queries)

    def search(self, text: str) -> tuple[str, float, str]:
        """Return (intent, similarity, matched query) for the nearest known query."""
        vector = self._vectoriser.transform([normalise(text)])
        scores = linear_kernel(vector, self._matrix)[0]
        best = scores.argmax()
        return self._intents[best], float(scores[best]), self._queries[best]
