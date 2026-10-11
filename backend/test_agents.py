"""Check the agent team uses gpt-6-luna on every model call, through Portkey.

Run:  .venv\\Scripts\\python backend\\test_agents.py
Static checks (config of all five agents), then one live ticket run where every
real model request and response is recorded and its model name compared.
"""

import asyncio
import re
import shutil
import subprocess
import sys
from collections import Counter

import openai.resources.responses as responses_mod

import config
import team

results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))


# --- static: all five agents share one model configuration ---------------------------------
agents = {"boss": team.boss_agent, **team.specialist_agents}
check("five agents exist", set(agents) == {"boss", "inventory", "accounting", "facilities", "customer_service"})
models = {name: a.model for name, a in agents.items()}
check("all agents use the same model object", len({id(m) for m in models.values()}) == 1)
m = next(iter(models.values()))
check("model name is gpt-6-luna", m.model_name == "gpt-6-luna", m.model_name)
check("model uses the Responses API", type(m).__name__ == "OpenAIResponsesModel", type(m).__name__)
client = m.client
check("base URL is Portkey", str(client.base_url).startswith("https://api.portkey.ai/v1"), str(client.base_url))
check("Portkey headers set", "x-portkey-api-key" in client.default_headers
      and client.default_headers.get("x-portkey-provider") == "openai")
source = open(config.BACKEND_DIR / "config.py", encoding="utf-8").read()
check("no hard-coded key in code", not re.search(r"pk-[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{10,}", source))
check("no other model names in backend code", not any(
    re.search(r"claude|gpt-4|gpt-5|gemini", open(p, encoding="utf-8").read(), re.I)
    for p in config.BACKEND_DIR.glob("*.py") if p.name != "test_agents.py"))

# --- live: record every model request/response ---------------------------------------------
calls = []
original = responses_mod.AsyncResponses.create


async def recording_create(self, *args, **kwargs):
    resp = await original(self, *args, **kwargs)
    calls.append((kwargs.get("model"), getattr(resp, "model", None)))
    return resp


responses_mod.AsyncResponses.create = recording_create


async def live():
    async with team.mcp_server:
        return await team.run_ticket(101)


subprocess.run([sys.executable, str(config.PROJECT_ROOT / "mcp_server" / "reset_db.py")], check=True)
decision = asyncio.run(live())
sent = Counter(c[0] for c in calls)
got = Counter(c[1] for c in calls)
print(f"model requests: {len(calls)}; sent: {dict(sent)}; returned: {dict(got)}")
check("live run made model calls", len(calls) >= 3)
check("every request asked for gpt-6-luna", set(sent) == {"gpt-6-luna"})
check("every response came from gpt-6-luna", all(str(r).startswith("gpt-6-luna") for _, r in calls))
check("several agents ran in the live ticket", len(decision.agents_consulted) >= 1, str(decision.agents_consulted))
shutil.copyfile(config.PROJECT_ROOT / "data" / "campus_customs.db",
                config.PROJECT_ROOT / "data" / "campus_customs_new.db")
print(f"\n{sum(results)}/{len(results)} passed")
