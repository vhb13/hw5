"""Append-only audit trail: output/audit_trail.json.

One entry per agent-loop step (a tool call, a delegation, or an agent finishing).
The file is read, appended to and rewritten, so earlier entries always survive
restarts. If the file is ever unreadable it is moved aside (never deleted) and a
new log is started.

No passwords or customer details are logged: sensitive argument fields are
redacted, some tools' results are not logged at all, and text is truncated.
"""

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import PROJECT_ROOT

AUDIT_PATH = PROJECT_ROOT / "output" / "audit_trail.json"
MESSAGES_PATH = PROJECT_ROOT / "output" / "agent_messages.json"  # what agents said, for the dashboard
SUMMARY_LIMIT = 140
REDACTED_ARGS = {"body", "subject", "requester", "email", "password"}
# Results of these tools contain customer details, so only "ok" is logged.
QUIET_RESULT_TOOLS = {"get_ticket", "save_customer_draft"}

_lock = threading.Lock()


def _clip(text: str) -> str:
    return text if len(text) <= SUMMARY_LIMIT else text[: SUMMARY_LIMIT - 1] + "…"


def summarize_args(args: dict[str, Any]) -> str:
    parts = [f"{k}=<redacted>" if k in REDACTED_ARGS else f"{k}={v}" for k, v in args.items()]
    return _clip(", ".join(parts))


def summarize_result(tool: str, result: Any) -> str:
    if tool in QUIET_RESULT_TOOLS:
        return "ok"
    return _clip(str(result).replace("\n", " "))


def _append(path: Path, entry: dict) -> None:
    with _lock:
        path.parent.mkdir(exist_ok=True)
        entries: list = []
        if path.exists():
            try:
                entries = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                path.replace(path.with_name(f"{path.stem}.unreadable-{stamp}.json"))
                entries = []
        entries.append(entry)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_step(
    *,
    agent: str,
    ticket_id: int,
    status: str,  # in_progress | delegated | finished | needs_human_approval | error
    tool: str | None = None,
    summary: str = "",
) -> None:
    _append(
        AUDIT_PATH,
        {
            "time": _now(),
            "ticket_id": ticket_id,
            "agent": agent,
            "tool": tool,
            "summary": _clip(summary),
            "status": status,
        },
    )


ORG_WORDS = {"club", "co", "inc", "llc", "properties", "gifts", "print", "shop", "society", "association", "team"}


def _name_variants(name: str) -> set[str]:
    """The full name, plus first and last name when it looks like a person (two words,
    no organization word), because agents often write just the first name."""
    variants = {name}
    words = name.split()
    if len(words) == 2 and not any(w.lower().strip(".,") in ORG_WORDS for w in words):
        variants |= {w for w in words if len(w) >= 3}
    return variants


def scrub(text: str, names: set[str]) -> str:
    """Replace customer names with a placeholder."""
    variants = set().union(*(_name_variants(n) for n in names)) if names else set()
    for name in sorted(variants, key=len, reverse=True):
        text = re.sub(r"\b" + re.escape(name) + r"\b", "[customer]", text, flags=re.I)
    return text


def log_message(
    *,
    agent: str,
    ticket_id: int,
    status: str,
    said: dict[str, Any],
    tools_used: list[str],
    names: set[str],
) -> None:
    """Save what an agent said when it finished (for the dashboard feed).

    Text is capped and customer names are replaced. This is separate from the
    audit trail, which never holds agent text.
    """

    def clean(value: Any) -> Any:
        if isinstance(value, str):
            return scrub(value, names)[:600]
        if isinstance(value, list):
            return [clean(v) for v in value[:8]]
        return value

    _append(
        MESSAGES_PATH,
        {
            "time": _now(),
            "ticket_id": ticket_id,
            "agent": agent,
            "status": status,
            "said": {k: clean(v) for k, v in said.items()},
            "tools_used": tools_used,
        },
    )


def read_recent(path: Path, limit: int, ticket_id: int | None = None) -> list[dict]:
    """Most recent `limit` entries (oldest first), optionally for one ticket."""
    if not path.exists():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if ticket_id is not None:
        entries = [e for e in entries if e.get("ticket_id") == ticket_id]
    return entries[-limit:]
