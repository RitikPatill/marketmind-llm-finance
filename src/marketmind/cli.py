"""CLI: python -m marketmind.cli TICKER QUESTION"""

import sys

from marketmind.analyst import ask


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m marketmind.cli TICKER QUESTION", file=sys.stderr)
        sys.exit(1)
    ticker = sys.argv[1].upper()
    question = " ".join(sys.argv[2:])
    for chunk in ask(ticker, question, stream=True):
        print(chunk, end="", flush=True)
    print()  # final newline


if __name__ == "__main__":
    main()
