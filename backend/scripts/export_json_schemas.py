from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.schemas.agents import (
    AnalysisAgentRequest,
    AnalysisAgentResponse,
    SearchAgentRequest,
    SearchAgentResponse,
    VerifierAgentRequest,
    VerifierAgentResponse,
    WritingAgentRequest,
    WritingAgentResponse,
)
from backend.app.schemas.events import EVENT_SCHEMAS

AGENT_OUT_DIR = ROOT / "contracts" / "agents"
EVENT_OUT_DIR = ROOT / "contracts" / "events"

AGENT_SCHEMAS = {
    "search-agent-request.schema.json": SearchAgentRequest,
    "search-agent-response.schema.json": SearchAgentResponse,
    "analysis-agent-request.schema.json": AnalysisAgentRequest,
    "analysis-agent-response.schema.json": AnalysisAgentResponse,
    "writing-agent-request.schema.json": WritingAgentRequest,
    "writing-agent-response.schema.json": WritingAgentResponse,
    "verifier-agent-request.schema.json": VerifierAgentRequest,
    "verifier-agent-response.schema.json": VerifierAgentResponse,
}


def render_schema(model: type) -> str:
    payload = model.model_json_schema()
    payload["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_schemas(out_dir: Path, schemas: dict[str, type]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, model in schemas.items():
        path = out_dir / filename
        path.write_text(render_schema(model))
        print(f"wrote {path.relative_to(ROOT)}")


def check_schemas(out_dir: Path, schemas: dict[str, type]) -> list[str]:
    failures: list[str] = []
    for filename, model in schemas.items():
        path = out_dir / filename
        expected = render_schema(model)
        if not path.exists():
            failures.append(f"missing {path.relative_to(ROOT)}")
            continue
        actual = path.read_text()
        if actual != expected:
            failures.append(f"stale {path.relative_to(ROOT)}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated schemas are stale")
    args = parser.parse_args()

    if args.check:
        failures = [
            *check_schemas(AGENT_OUT_DIR, AGENT_SCHEMAS),
            *check_schemas(EVENT_OUT_DIR, EVENT_SCHEMAS),
        ]
        if failures:
            print("Schema drift detected:")
            for failure in failures:
                print(f"- {failure}")
            return 1
        print("Schema check passed.")
        return 0

    write_schemas(AGENT_OUT_DIR, AGENT_SCHEMAS)
    write_schemas(EVENT_OUT_DIR, EVENT_SCHEMAS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
