"""Pydantic I/O for every agent node."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["low", "med", "high", "critical"]


class EvidenceClaim(BaseModel):
    claim: str
    source: str
    ref: str

    @field_validator("source", "ref", "claim")
    @classmethod
    def _nonempty(cls, value: str) -> str:
        if not value or not str(value).strip():
            raise ValueError("evidence fields must be non-empty")
        return value


class TriageOutput(BaseModel):
    playbook_confirmed: bool
    severity: Severity
    scope: dict[str, Any] = Field(default_factory=dict)
    revenue_at_risk_per_hour: float = 0.0
    summary: str


class DiagnosisOutput(BaseModel):
    root_cause: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceClaim]
    hypotheses_rejected: list[str] = Field(default_factory=list)

    @field_validator("evidence")
    @classmethod
    def _need_evidence(cls, value: list[EvidenceClaim]) -> list[EvidenceClaim]:
        if not value:
            raise ValueError("diagnostician must cite at least one evidence claim")
        return value


class ProposalDraft(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    rationale: str
    expected_effect: str = ""


class RemediatorOutput(BaseModel):
    proposals: list[ProposalDraft]


class VerifierOutput(BaseModel):
    resolved: bool
    observation: str
    next_step: str
