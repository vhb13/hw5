"""The five-agent Campus Customs team (PydanticAI).

All five agents use the same model (config.build_model) and read shop facts only
through the MCP server. Each agent only sees the MCP tools it needs. Agents ask
each other for help with `ask_specialist`; the Boss owns the final outcome.
"""

from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UsageLimitExceeded
from pydantic_ai.mcp import MCPServerStdio

import audit
from config import (
    MAX_AGENT_RUNS,
    MAX_DELEGATION_DEPTH,
    PROJECT_ROOT,
    PROMPTS_DIR,
    USAGE_LIMITS,
    build_model,
    mcp_command,
)
from models import (
    AgentDeps,
    BossDecision,
    RunState,
    SpecialistFinding,
    SpecialistName,
)

SPECIALISTS = ("inventory", "accounting", "facilities", "customer_service")

# Which MCP tools each agent may use.
ALLOWED_TOOLS: dict[str, set[str]] = {
    "boss": {"get_ticket", "list_open_tickets", "update_ticket_status"},
    "inventory": {"get_ticket", "get_inventory_status", "get_vendor_status", "estimate_restock"},
    "accounting": {"get_ticket", "get_accounting_status", "get_vendor_status", "propose_payment"},
    "facilities": {"get_ticket", "get_facilities_status"},
    "customer_service": {"get_ticket", "get_inventory_status", "save_customer_draft"},
}


def safe_error(exc: Exception) -> str:
    """A short message with no keys, provider response bodies or customer text.
    Used for the audit trail and API errors."""
    if isinstance(exc, UsageLimitExceeded):
        return "The agents hit their step or token limit before finishing."
    if isinstance(exc, ModelHTTPError):
        return f"The model service rejected a request (HTTP {exc.status_code})."
    return f"The agent team failed ({type(exc).__name__})."


async def _log_mcp_call(ctx: RunContext[AgentDeps], call_tool, name: str, tool_args: dict[str, Any]):
    """Audit every MCP tool call (runs inside the MCP client, so nothing is skipped)."""
    result = await call_tool(name, tool_args, None)
    ctx.deps.tools_used.append(name)
    if name == "get_ticket" and isinstance(result, dict) and result.get("requester"):
        ctx.deps.state.private_names.add(result["requester"])
    audit.log_step(
        agent=ctx.deps.agent_name,
        ticket_id=ctx.deps.state.ticket_id,
        status="in_progress",
        tool=name,
        summary=f"args: {audit.summarize_args(tool_args)} | result: "
        f"{audit.summarize_result(name, result)}",
    )
    return result


_command, _args = mcp_command()
mcp_server = MCPServerStdio(
    _command,
    _args,
    cwd=PROJECT_ROOT,
    process_tool_call=_log_mcp_call,
    timeout=30,
)


def _toolset_for(agent_name: str):
    allowed = ALLOWED_TOOLS[agent_name]
    return mcp_server.filtered(lambda ctx, tool_def: tool_def.name in allowed)


def _prompt(agent_name: str) -> str:
    return (PROMPTS_DIR / f"{agent_name}.md").read_text(encoding="utf-8")


_model = build_model()  # one model configuration, shared by all five agents


def _make_specialist(name: str) -> Agent[AgentDeps, SpecialistFinding]:
    return Agent(
        _model,
        system_prompt=_prompt(name),
        toolsets=[_toolset_for(name)],
        deps_type=AgentDeps,
        output_type=SpecialistFinding,
        retries=2,
    )


specialist_agents: dict[str, Agent[AgentDeps, SpecialistFinding]] = {
    name: _make_specialist(name) for name in SPECIALISTS
}

boss_agent: Agent[AgentDeps, BossDecision] = Agent(
    _model,
    system_prompt=_prompt("boss"),
    toolsets=[_toolset_for("boss")],
    deps_type=AgentDeps,
    output_type=BossDecision,
    retries=2,
)


async def ask_specialist(
    ctx: RunContext[AgentDeps], agent: SpecialistName, question: str, known_facts: str = ""
) -> str:
    """Ask another agent for help on THIS ticket.

    Give a specific question and only the facts they need (e.g. "tee size S is
    out of stock; vendor 1 lead time is 5 days"). They can look up the ticket
    and database themselves, so do not paste records. Returns their finding.
    """
    me = ctx.deps
    ticket_id = me.state.ticket_id

    def refuse(reason: str) -> str:
        audit.log_step(
            agent=me.agent_name, ticket_id=ticket_id, status="in_progress",
            tool="ask_specialist", summary=f"refused: {reason}",
        )
        return f"Not delegated: {reason}. Work with what you have and say what is missing."

    if agent == me.agent_name:
        return refuse("you cannot ask yourself")
    if agent in me.stack:
        return refuse(f"{agent} is already waiting on this request chain (loop)")
    if len(me.stack) >= MAX_DELEGATION_DEPTH:
        return refuse(f"delegation depth limit {MAX_DELEGATION_DEPTH} reached")
    if me.state.agent_runs >= MAX_AGENT_RUNS:
        return refuse(f"limit of {MAX_AGENT_RUNS} agent runs for this ticket reached")

    audit.log_step(
        agent=me.agent_name, ticket_id=ticket_id, status="delegated",
        tool="ask_specialist", summary=f"asked {agent} (question: {len(question)} chars)",
    )
    me.tools_used.append(f"ask_specialist -> {agent}")
    result = await run_specialist(
        agent, ticket_id, me.agent_name, question, known_facts, me.state,
        me.stack + (me.agent_name,), ctx,
    )
    return result.model_dump_json()


async def run_specialist(
    name: str,
    ticket_id: int,
    asked_by: str,
    question: str,
    known_facts: str,
    state: RunState,
    stack: tuple[str, ...],
    ctx: RunContext[AgentDeps],
) -> SpecialistFinding:
    state.agent_runs += 1
    if name not in state.consulted:
        state.consulted.append(name)
    prompt = f"Ticket {ticket_id}. Asked by {asked_by}.\nQuestion: {question}"
    if known_facts:
        prompt += f"\nFacts already known: {known_facts}"
    deps = AgentDeps(agent_name=name, state=state, stack=stack)
    try:
        run = await specialist_agents[name].run(
            prompt, deps=deps, usage=ctx.usage, usage_limits=USAGE_LIMITS
        )
    except Exception as exc:
        audit.log_step(
            agent=name, ticket_id=ticket_id, status="error",
            summary=safe_error(exc),
        )
        raise
    finding = run.output
    audit.log_step(
        agent=name, ticket_id=ticket_id,
        status="needs_human_approval" if finding.needs_human_approval else "finished",
        summary=f"facts={len(finding.facts)}, blockers={len(finding.blockers)}, "
        f"proposals={finding.proposal_ids}, drafts={finding.draft_ids}",
    )
    audit.log_message(
        agent=name, ticket_id=ticket_id,
        status="needs_human_approval" if finding.needs_human_approval else "finished",
        said={
            "summary": finding.summary,
            "facts": finding.facts,
            "recommendation": finding.recommendation,
            "blockers": finding.blockers,
            "proposal_ids": finding.proposal_ids,
            "draft_ids": finding.draft_ids,
        },
        tools_used=deps.tools_used, names=state.private_names,
    )
    return finding


# Every agent (Boss included) can ask the specialists; the Boss is not askable,
# because it coordinates rather than being a helper.
boss_agent.tool(ask_specialist)
for _agent in specialist_agents.values():
    _agent.tool(ask_specialist)


async def run_ticket(ticket_id: int) -> BossDecision:
    """Run the Boss on one ticket. The Boss delegates only if it needs to."""
    state = RunState(ticket_id=ticket_id, agent_runs=1)
    deps = AgentDeps(agent_name="boss", state=state)
    try:
        result = await boss_agent.run(
            f"Handle ticket {ticket_id}.", deps=deps, usage_limits=USAGE_LIMITS
        )
    except Exception as exc:
        audit.log_step(
            agent="boss", ticket_id=ticket_id, status="error",
            summary=safe_error(exc),
        )
        raise
    decision = result.output
    decision.agents_consulted = list(state.consulted)  # includes agents a specialist asked
    audit.log_step(
        agent="boss", ticket_id=ticket_id,
        status="needs_human_approval" if decision.outcome == "needs_human_approval" else "finished",
        summary=f"outcome={decision.outcome}; consulted={decision.agents_consulted}; "
        f"proposals={decision.proposal_ids}; drafts={decision.draft_ids}",
    )
    audit.log_message(
        agent="boss", ticket_id=ticket_id,
        status="needs_human_approval" if decision.outcome == "needs_human_approval" else "finished",
        said={
            "outcome": decision.outcome,
            "summary": decision.summary,
            "key_facts": decision.key_facts,
            "contradictions_or_gaps": decision.contradictions_or_gaps,
            "agents_consulted": decision.agents_consulted,
            "proposal_ids": decision.proposal_ids,
            "draft_ids": decision.draft_ids,
        },
        tools_used=deps.tools_used, names=state.private_names,
    )
    return decision
