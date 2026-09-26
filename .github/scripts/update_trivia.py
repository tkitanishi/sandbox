"""Replace the trivia block in README.md with today's fact (JST).

Facts come from trivia/facts.json and rotate one per day.
Usage: python .github/scripts/update_trivia.py [YYYY-MM-DD]
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
FACTS = ROOT / "trivia" / "facts.json"
START, END = "<!-- TRIVIA:START -->", "<!-- TRIVIA:END -->"
JST = dt.timezone(dt.timedelta(hours=9))


def main():
    if len(sys.argv) > 1:
        today = dt.date.fromisoformat(sys.argv[1])
    else:
        today = dt.datetime.now(JST).date()
    facts = json.loads(FACTS.read_text(encoding="utf-8"))
    idx = today.toordinal() % len(facts)
    fact = facts[idx]

    block = (
        f"{START}\n"
        f"> **{today:%Y-%m-%d}** の一言（{idx + 1}/{len(facts)}）\n"
        f">\n"
        f"> {fact['text']}\n"
        f">\n"
        f"> — *{fact['ref']}*\n"
        f"{END}"
    )
    text = README.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + ".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        sys.exit(f"markers {START} / {END} not found in README.md")
    README.write_text(pattern.sub(lambda _: block, text), encoding="utf-8")
    print(f"{today}: fact {idx + 1}/{len(facts)}")


if __name__ == "__main__":
    main()
