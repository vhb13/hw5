"""Shared data types for the Campus Customs agent team."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
SpecialistName = Literal["inventory", "accounting", "facilities", "customer_service"]
TicketOutcome = Literal["resolved", "needs_human_approval", "needs_investigation"]


class SpecialistFinding(BaseModel):
    """What a specialist hands back to whoever asked (Boss or another specialist)."""

    agent: SpecialistName
    summary: str = Field(description="2-4 sentences: what was checked and what it means")
    facts: list[str] = Field(
        default_factory=list, description="Verified facts from tools, each with its source"
    )
    recommendation: str = Field(description="The next step this agent recommends")
    needs_human_approval: bool = False
    proposal_ids: list[int] = Field(default_factory=list, description="Payment proposals created")
    draft_ids: list[int] = Field(default_factory=list, description="Customer drafts saved")
    blockers: list[str] = Field(default_factory=list, description="Rules or missing info in the way")
    asked_agents: list[SpecialistName] = Field(default_factory=list)


class BossDecision(BaseModel):
    """The Boss's final outcome for one ticket."""

    ticket_id: int
    outcome: TicketOutcome
    summary: str
    agents_consulted: list[SpecialistName]
    key_facts: list[str] = Field(default_factory=list)
    contradictions_or_gaps: list[str] = Field(default_factory=list)
    proposal_ids: list[int] = Field(default_factory=list)
    draft_ids: list[int] = Field(default_factory=list)


@dataclass
class RunState:
    """Shared across one ticket run, so delegation stays bounded."""

    ticket_id: int
    agent_runs: int = 0
    consulted: list[str] = field(default_factory=list)
    private_names: set[str] = field(default_factory=set)  # customer names seen; scrubbed from messages


@dataclass
class AgentDeps:
    """Per-agent run context. Kept tiny on purpose: who is running, and for which ticket."""

    agent_name: str
    state: RunState
    stack: tuple[str, ...] = ()  # who asked whom, to stop loops (A -> B -> A)
    tools_used: list[str] = field(default_factory=list)  # for the dashboard activity feed
