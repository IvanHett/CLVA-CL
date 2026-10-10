"""Automated system tests for the pipeline, logging and API.

    python -m pytest
"""
import pytest

from src import config
from src.api import create_app
from src.chatbot import Chatbot
from src.data_loader import load_dataset
from src.preprocessing import normalise, stemmed, tokenise
from src.storage import InteractionLogger


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture(scope="module")
def bot(dataset):
    return Chatbot(dataset)


def test_normalise_and_tokenise():
    assert normalise("  What's the DEADLINE?! ") == "whats the deadline"
    assert tokenise("Tell me about CS5002.") == ["tell", "me", "about", "cs5002"]
    assert stemmed("Deadlines for classes") == "deadline for class"


def test_exact_match(bot):
    reply = bot.ask("How do I submit my assignment?")
    assert (reply.intent, reply.stage) == ("assignment_submission", "exact")


def test_keyword_match(bot):
    reply = bot.ask("is plagiarism a big deal")
    assert (reply.intent, reply.stage) == ("academic_misconduct", "keyword")


def test_longer_keyword_rule_wins(bot):
    assert bot.ask("is there a late submission rule").intent == "late_submission"


def test_module_lookup_by_code_and_name(bot):
    by_code = bot.ask("tell me about 5cs045")
    assert by_code.intent == "module_info" and "Full Stack Development" in by_code.answer
    by_name = bot.ask("what is big data like")
    assert "6CS030" in by_name.answer


def test_topic_keyword_beats_module_mention(bot):
    assert bot.ask("can I get an extension on 5CS045?").intent == "extension_request"
    assert bot.ask("what's covered in the full stack development module").intent == "module_info"


def test_module_list_comes_from_modules_csv(bot, dataset):
    answer = bot.ask("what modules do I study").answer
    assert all(m.module_id in answer for m in dataset.modules)


def test_enhanced_handles_what_baseline_cannot(bot):
    query = "thanks for your help"
    assert bot.ask(query, config.MODE_BASELINE).stage == "fallback"
    enhanced = bot.ask(query, config.MODE_ENHANCED)
    assert enhanced.intent == "thanks" and enhanced.stage in ("classifier", "retrieval")


@pytest.mark.parametrize("query", ["what is the capital of France", "asdfghjkl", "   ", "?!"])
def test_unknown_query_falls_back(bot, query):
    reply = bot.ask(query)
    assert not reply.matched
    assert reply.answer == config.FALLBACK_RESPONSE


def test_every_intent_has_training_queries(dataset):
    assert set(dataset.answers) == {intent for _, intent in dataset.queries}


def test_logging_and_unanswered_frequency(dataset, tmp_path):
    logger = InteractionLogger(tmp_path)
    bot = Chatbot(dataset, logger)
    assert bot.ask("when is my assignment due").query_id == 1
    bot.ask("What is the capital of France?")
    bot.ask("what is the capital of france")

    unanswered = logger.unanswered()
    assert len(unanswered) == 1
    assert unanswered[0]["query_text"] == "what is the capital of france"
    assert unanswered[0]["frequency_count"] == 2
    assert len((tmp_path / "queries_log.csv").read_text(encoding="utf-8").splitlines()) == 4

    # A new logger over the same files carries on numbering where the last stopped.
    assert Chatbot(dataset, InteractionLogger(tmp_path)).ask("hello").query_id == 4


@pytest.fixture
def client(dataset, tmp_path):
    app = create_app(Chatbot(dataset, InteractionLogger(tmp_path)))
    return app.test_client()


def test_api_ask(client):
    response = client.post("/ask", json={"query": "when is my assignment due"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["intent"] == "assignment_deadline" and body["matched"] is True


def test_api_rejects_bad_requests(client):
    assert client.post("/ask", json={}).status_code == 400
    assert client.post("/ask", json={"query": "   "}).status_code == 400
    assert client.post("/ask", json={"query": "hi", "mode": "turbo"}).status_code == 400
    assert client.post("/ask", json={"query": "x" * 501}).status_code == 400


def test_api_unanswered_and_modules(client, dataset):
    client.post("/ask", json={"query": "who won the world cup in 1966"})
    assert client.get("/admin/unanswered").get_json()[0]["frequency_count"] == 1
    assert len(client.get("/modules").get_json()) == len(dataset.modules)
    assert client.get("/").status_code == 200
