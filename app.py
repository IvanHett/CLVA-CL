"""CLVA command-line interface.

    python app.py                       interactive chat
    python app.py "when is my deadline"  ask a single question
    python app.py --mode baseline        use rule-based matching only
    python app.py --unanswered           list unanswered queries for review
"""
import argparse

from src import config
from src.chatbot import Chatbot
from src.storage import InteractionLogger


def print_unanswered(logger: InteractionLogger) -> None:
    rows = logger.unanswered()
    if not rows:
        print("No unanswered queries have been recorded.")
        return
    print(f"{'Count':>5}  {'Last seen':<19}  Query")
    for row in rows:
        print(f"{row['frequency_count']:>5}  {row['last_seen']:<19}  {row['query_text']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="CLVA - Course Leader Virtual Assistant")
    parser.add_argument("question", nargs="?", help="ask one question and exit")
    parser.add_argument("--mode", choices=config.MODES, default=config.DEFAULT_MODE)
    parser.add_argument("--unanswered", action="store_true", help="list unanswered queries and exit")
    parser.add_argument("--debug", action="store_true", help="show intent, stage and timing")
    args = parser.parse_args()

    logger = InteractionLogger()
    if args.unanswered:
        print_unanswered(logger)
        return

    bot = Chatbot(logger=logger)

    def respond(question: str) -> None:
        reply = bot.ask(question, args.mode)
        print(f"CLVA: {reply.answer}")
        if args.debug:
            print(
                f"      [intent={reply.intent} stage={reply.stage} "
                f"confidence={reply.confidence} time={reply.response_time_ms}ms]"
            )

    if args.question:
        respond(args.question)
        return

    print(f"CLVA - Course Leader Virtual Assistant ({args.mode} mode). Type 'quit' to exit.")
    while True:
        try:
            question = input("You:  ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"quit", "exit"}:
            break
        if question:
            respond(question)


if __name__ == "__main__":
    main()
