"""Cost of the model calls, from the token counts saved with each prediction.

    python evaluation/cost.py evaluation/data/predictions/gpt-oss-120b --input-price 0.09 --output-price 0.47

Prices are per million tokens, in the currency of the provider's price list.
The cost per article is projected to the 1,066 articles of the year.
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("predictions", type=Path)
    parser.add_argument("--input-price", type=float, required=True, help="price per million input tokens")
    parser.add_argument("--output-price", type=float, required=True, help="price per million output tokens")
    parser.add_argument("--year", type=int, default=1066, help="articles in the year")
    args = parser.parse_args()

    rows = []
    for path in sorted(args.predictions.glob("*.json")):
        usage = json.loads(path.read_text(encoding="utf-8")).get("usage") or {}
        if usage.get("prompt_tokens"):
            rows.append((usage["prompt_tokens"], usage.get("completion_tokens", 0)))
    if not rows:
        raise SystemExit("No token counts saved yet: only predictions made after this change record them.")

    tokens_in = sum(r[0] for r in rows) / len(rows)
    tokens_out = sum(r[1] for r in rows) / len(rows)
    per_article = (tokens_in * args.input_price + tokens_out * args.output_price) / 1_000_000
    print(f"{len(rows)} articles with token counts")
    print(f"Mean tokens per article: {tokens_in:.0f} input, {tokens_out:.0f} output")
    print(f"Cost per article: {per_article:.5f}")
    print(f"Projected cost for {args.year} articles: {per_article * args.year:.2f}")


if __name__ == "__main__":
    main()
