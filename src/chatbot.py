"""Application core: ties preprocessing, intent routing, response generation and logging together."""
import time
from dataclasses import asdict, dataclass

from . import config
from .data_loader import Dataset, load_dataset
from .pipeline import IntentRouter
from .responder import ResponseGenerator
from .storage import InteractionLogger


@dataclass
class Reply:
    query: str
    answer: str
    intent: str
    stage: str
    confidence: float
    matched: bool
    mode: str
    response_time_ms: float
    query_id: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class Chatbot:
    def __init__(self, dataset: Dataset | None = None, logger: InteractionLogger | None = None):
        self.dataset = dataset or load_dataset()
        self.router = IntentRouter(self.dataset)
        self.responder = ResponseGenerator(self.dataset)
        self.logger = logger

    def ask(self, query: str, mode: str = config.DEFAULT_MODE) -> Reply:
        started = time.perf_counter()
        resolution = self.router.resolve(query, mode)
        answer = self.responder.generate(resolution)
        elapsed_ms = (time.perf_counter() - started) * 1000

        reply = Reply(
            query=query, answer=answer, intent=resolution.intent, stage=resolution.stage,
            confidence=round(resolution.confidence, 3), matched=resolution.matched,
            mode=mode, response_time_ms=round(elapsed_ms, 2),
        )
        if self.logger is not None:
            reply.query_id = self.logger.record(
                query, reply.intent, answer, elapsed_ms, reply.matched, reply.stage, mode,
            )
        return reply
