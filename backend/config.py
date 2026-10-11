"""Model, Portkey and limit settings shared by all five agents."""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent  # .../homework 5
PROMPTS_DIR = BACKEND_DIR / "prompts"

# The key lives in the shared .env one level up (see AGENTS.md); a local .env wins.
load_dotenv(PROJECT_ROOT.parent / ".env")
load_dotenv(PROJECT_ROOT / ".env", override=True)

# The assignment requires this exact model, reached through Portkey.
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
PORTKEY_PROVIDER = "openai"

# Limits for one ticket run (shared by the Boss and every specialist it calls).
MAX_AGENT_RUNS = 10  # total agent runs per ticket, delegations included
MAX_DELEGATION_DEPTH = 3  # Boss -> specialist -> specialist -> specialist
USAGE_LIMITS = UsageLimits(request_limit=40, tool_calls_limit=40, total_tokens_limit=150_000)


def build_model() -> OpenAIResponsesModel:
    """Same model settings for every agent: gpt-6-luna via Portkey.

    gpt-6-luna refuses function tools on /v1/chat/completions, so we use the
    Responses API (/v1/responses), which supports tools.
    """
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to the .env file (see AGENTS.md).")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={
            "x-portkey-api-key": api_key,
            "x-portkey-provider": PORTKEY_PROVIDER,
        },
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def mcp_command() -> tuple[str, list[str]]:
    """Start the MCP server exactly as .mcp.json does, so there is one definition."""
    cfg = json.loads((PROJECT_ROOT / ".mcp.json").read_text(encoding="utf-8"))
    server = cfg["mcpServers"]["campus-customs"]
    command = server["command"]
    if command in ("python", "python3"):
        command = sys.executable  # the same interpreter (and virtual environment) the backend runs in
    return command, list(server["args"])
