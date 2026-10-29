"""Run the app's analysis on many articles and save each prediction in the app's export format.

    python evaluation/run_batch.py evaluation/data/sample
    python evaluation/run_batch.py evaluation/data/candidates
    python evaluation/run_batch.py evaluation/data/sample --model qwen2.5:7b --base-url http://127.0.0.1:11434/v1

The token is read from OVH_AI_ENDPOINTS_ACCESS_TOKEN (not needed for local Ollama).
Articles that already have a prediction are skipped, so the run can be resumed.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis import (  # noqa: E402
    APP_VERSION,
    INSTRUCTIONS,
    PROMPT_VERSION,
    prediction_warnings,
    run_model,
    safe_error,
    validate_prediction,
)
from sinc import load_article  # noqa: E402
from grammar_gender import fill as fill_grammar_gender  # noqa: E402


PREDICTIONS = Path(__file__).resolve().parent / "data" / "predictions"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("articles", type=Path, help="folder with article files")
    parser.add_argument("--model", default="gpt-oss-120b")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OVH_AI_BASE_URL", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"),
    )
    parser.add_argument("--redo", action="store_true", help="analyse again articles that already have a prediction")
    args = parser.parse_args()

    api_token = os.environ.get("OVH_AI_ENDPOINTS_ACCESS_TOKEN", "").strip()
    provider = "Local Ollama" if args.base_url.startswith("http://") else "Organisers' OVH API"
    output = PREDICTIONS / re.sub(r"[^\w.-]", "_", args.model)
    output.mkdir(parents=True, exist_ok=True)

    paths = sorted(args.articles.glob("*.json"))
    print(f"{len(paths)} articles · {args.model} · {provider}", flush=True)
    for path in paths:
        record = load_article(path)
        target = output / f"{record['id']}.json"
        if target.exists() and not args.redo:
            continue

        article_fields = record["article"]
        source_text = "\n\n".join(article_fields.values())
        try:
            result, run_metadata = run_model(
                provider, args.model, args.base_url, api_token,
                article_fields, True,
            )
            validate_prediction(result)
        except (
            requests.RequestException,
            ValueError,
            KeyError,
            TypeError,
            IndexError,
        ) as error:
            # One failed article does not stop the batch; it is retried on the next run.
            print(f"{record['id']}  {safe_error(error)}", file=sys.stderr, flush=True)
            continue

        warnings = prediction_warnings(result, source_text)
        # Gender from grammatical agreement when the model left it unknown.
        filled = fill_grammar_gender(result, source_text)
        analysis = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "app_version": APP_VERSION,
            **run_metadata,
            "prompt_version": PROMPT_VERSION,
            "prompt": INSTRUCTIONS,
            "article_id": record["id"],
            "url": record["url"],
            "published": record.get("published"),
            "source_type": record.get("source_type"),
            "sections": record.get("sections", []),
            "cc_licence": record.get("cc_licence"),
            "article": article_fields,
            "original_prediction": result,
            "validation_warnings": warnings,
        }
        target.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"{record['id']}  {len(result['people'])} people  "
            f"{len(warnings)} warnings  {filled} grammar genders  {run_metadata['elapsed_seconds']} s",
            flush=True,
        )


if __name__ == "__main__":
    main()
