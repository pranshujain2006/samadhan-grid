"""Project lifecycle: solution reuse gate, teams, milestones, funding, pilots, impact."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import PROJECT_STAGES
from ..db import clean, db, ledger, ledger_for, new_id, now
from ..ai import impact as impact_ai, insight, memory

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Stages that may not be entered without evidence of the previous gate.
_GATE_REQUIREMENTS = {
    "prototype": ("solution_memory_review",
                  "Run the Solution Memory review before building anything new."),
    "field_pilot": ("impact_contract",
                    "Sign the Impact Contract with the community before the field pilot."),
    "deployment": ("pilot_report",
                   "A completed field pilot report is required before deployment."),
    "scale_up": ("community_validation",
                 "Community validation is required before scaling."),
}


async def _get(project_id: str) -> dict[str, Any]:
    doc = await db().projects.find_one({"project_id": project_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Project not found")
    return doc


@router.get("")
async def list_projects(stage: str | None = None, district: str | None = None,
                        limit: int = 60) -> dict[str, Any]:
    q: dict[str, Any] = {}
    if stage:
        q["stage"] = {"$in": stage.split(",")}
    if district:
        q["district"] = district
    items = await db().projects.find(q, {"_id": 0}).sort("created_at", -1).limit(limit) \
        .to_list(length=limit)
    for p in items:
        p["risk"] = insight.project_risk(p)
        p["readiness_summary"] = impact_ai.readiness_summary(
            p.get("readiness", {}).get("trl", 1),
            p.get("readiness", {}).get("crl", 1),
            p.get("readiness", {}).get("srl", 1))
    return {"count": len(items), "items": items}


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    p = await _get(project_id)
    p["risk"] = insight.project_risk(p)
    r = p.get("readiness", {})
    p["readiness_summary"] = impact_ai.readiness_summary(
        r.get("trl", 1), r.get("crl", 1), r.get("srl", 1))
    p["ledger"] = await ledger_for(project_id)
    p["challenge"] = await db().challenges.find_one(
        {"challenge_id": p["challenge_id"]}, {"_id": 0})
    p["feedback"] = await db().feedback.find(
        {"challenge_id": p["challenge_id"]}, {"_id": 0}).to_list(length=100)
    return p


# --------------------------------------------------- solution memory reuse gate

@router.post("/{project_id}/solution-memory")
async def run_solution_memory(project_id: str) -> dict[str, Any]:
    """Search what already exists - and what already failed - before building."""
    d = db()
    p = await _get(project_id)
    ch = await d.challenges.find_one({"challenge_id": p["challenge_id"]}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Linked challenge not found")

    library = await d.solution_memory.find({}, {"_id": 0}).to_list(length=500)
    # Completed projects on this platform become part of the memory too.
    done = await d.projects.find(
        {"stage": {"$in": ["deployment", "impact_monitoring", "scale_up", "completed"]},
         "project_id": {"$ne": project_id}}, {"_id": 0}).to_list(length=100)
    for dp in done:
        library.append({
            "solution_id": dp["project_id"], "kind": "past_project",
            "title": dp["title"], "source": "SAMADHAN GRID completed project",
            "year": dp.get("created_at", now()).year if isinstance(
                dp.get("created_at"), datetime) else None,
            "domain": dp.get("domain"), "summary": dp.get("solution_summary", ""),
            "technologies": dp.get("technologies", []), "maturity": "deployed",
            "tags": [dp.get("domain", "")], "patented": False,
        })

    hits = memory.search(ch["dna"], library, limit=10)
    advice = await memory.advise(ch["dna"], hits)
    advice["reviewed_at"] = now()

    await d.projects.update_one({"project_id": project_id},
                                {"$set": {"solution_memory_review": advice,
                                          "updated_at": now()}})
    await ledger(project_id, "project", "solution_memory_reviewed",
                 "solution_memory_engine", "ai",
                 {"verdict": advice.get("verdict"), "searched": advice.get("searched"),
                  "failures_found": advice.get("failures_found")})
    return advice


# ------------------------------------------------------------------ team + stage

class TeamMember(BaseModel):
    name: str
    role: str                       # student | faculty_mentor | industry_mentor | community_rep
    discipline: str | None = None
    institution: str | None = None
    contribution: str | None = None


@router.post("/{project_id}/team")
async def set_team(project_id: str, members: list[TeamMember],
                   approved_by: str = "university_admin") -> dict[str, Any]:
    await _get(project_id)
    team = [{**m.model_dump(), "member_id": new_id("TM"), "joined_at": now()}
            for m in members]
    await db().projects.update_one({"project_id": project_id},
                                   {"$set": {"team": team, "updated_at": now()}})
    await ledger(project_id, "project", "multidisciplinary_team_formed", approved_by,
                 "university_admin",
                 {"size": len(team),
                  "disciplines": sorted({m.discipline for m in members if m.discipline})})
    return {"project_id": project_id, "team": team}


class StageBody(BaseModel):
    stage: str
    by: str
    note: str | None = None
    override_gate: bool = False


@router.post("/{project_id}/stage")
async def advance_stage(project_id: str, body: StageBody) -> dict[str, Any]:
    d = db()
    p = await _get(project_id)
    if body.stage not in PROJECT_STAGES:
        raise HTTPException(400, f"stage must be one of {PROJECT_STAGES}")

    gate = _GATE_REQUIREMENTS.get(body.stage)
    if gate and not body.override_gate:
        key, message = gate
        satisfied = True
        if key == "solution_memory_review":
            satisfied = bool(p.get("solution_memory_review"))
        elif key == "impact_contract":
            satisfied = bool(p.get("impact_contract", {}).get("metrics"))
        elif key == "pilot_report":
            satisfied = any(m.get("kind") == "pilot" and m.get("status") == "approved"
                            for m in p.get("milestones", []))
        elif key == "community_validation":
            satisfied = (p.get("community_feedback_count", 0) or 0) > 0
        if not satisfied:
            raise HTTPException(409, {"error": "stage_gate_blocked", "requirement": key,
                                      "message": message,
                                      "hint": "Set override_gate=true only with a recorded reason."})

    trl = max(p.get("readiness", {}).get("trl", 1), impact_ai.stage_default_trl(body.stage))
    readiness = {**p.get("readiness", {}), "trl": trl}

    await d.projects.update_one(
        {"project_id": project_id},
        {"$set": {"stage": body.stage, "readiness": readiness, "updated_at": now()},
         "$push": {"stage_history": {"stage": body.stage, "at": now(), "by": body.by,
                                     "note": body.note,
                                     "gate_overridden": body.override_gate}}})
    await ledger(project_id, "project", f"stage_advanced_{body.stage}", body.by,
                 "faculty", {"note": body.note, "gate_overridden": body.override_gate})
    return await get_project(project_id)


class ReadinessBody(BaseModel):
    trl: int = Field(ge=1, le=9)
    crl: int = Field(ge=1, le=9)
    srl: int = Field(ge=1, le=9)
    assessed_by: str
    evidence: str | None = None


@router.post("/{project_id}/readiness")
async def set_readiness(project_id: str, body: ReadinessBody) -> dict[str, Any]:
    """Three axes, deliberately separate: works / people use it / it can grow."""
    await _get(project_id)
    summary = impact_ai.readiness_summary(body.trl, body.crl, body.srl)
    await db().projects.update_one(
        {"project_id": project_id},
        {"$set": {"readiness": {"trl": body.trl, "crl": body.crl, "srl": body.srl,
                                "assessed_by": body.assessed_by, "at": now(),
                                "evidence": body.evidence},
                  "updated_at": now()}})
    await ledger(project_id, "project", "readiness_assessed", body.assessed_by, "faculty",
                 {"trl": body.trl, "crl": body.crl, "srl": body.srl,
                  "assessment": summary["assessment"]})
    return {"project_id": project_id, "readiness_summary": summary}


# ----------------------------------------------------------------- milestones

class MilestoneBody(BaseModel):
    name: str
    kind: str = "deliverable"       # deliverable | prototype | pilot | report | review
    description: str | None = None
    due_in_days: int = 30
    required_evidence: list[str] = []


@router.post("/{project_id}/milestones")
async def add_milestone(project_id: str, body: MilestoneBody,
                        created_by: str = "faculty_mentor") -> dict[str, Any]:
    await _get(project_id)
    m = {"milestone_id": new_id("MI"), "name": body.name, "kind": body.kind,
         "description": body.description,
         "due": now() + timedelta(days=body.due_in_days),
         "required_evidence": body.required_evidence or ["report"],
         "evidence": [], "status": "open", "created_by": created_by, "created_at": now()}
    await db().projects.update_one({"project_id": project_id},
                                   {"$push": {"milestones": m},
                                    "$set": {"updated_at": now()}})
    await ledger(project_id, "project", "milestone_created", created_by, "faculty",
                 {"name": body.name, "kind": body.kind})
    return clean(m)


class SubmitMilestoneBody(BaseModel):
    evidence_ids: list[str] = []
    note: str | None = None
    submitted_by: str


@router.post("/{project_id}/milestones/{milestone_id}/submit")
async def submit_milestone(project_id: str, milestone_id: str,
                           body: SubmitMilestoneBody) -> dict[str, Any]:
    """Evidence-based milestones: you cannot mark it done without uploading proof."""
    d = db()
    p = await _get(project_id)
    m = next((x for x in p.get("milestones", []) if x["milestone_id"] == milestone_id), None)
    if not m:
        raise HTTPException(404, "Milestone not found")

    evidence = []
    if body.evidence_ids:
        evidence = await d.evidence.find({"id": {"$in": body.evidence_ids}},
                                         {"_id": 0}).to_list(length=20)
    if not evidence:
        raise HTTPException(
            422, {"error": "evidence_required",
                  "message": "A milestone cannot be marked complete without evidence.",
                  "required": m.get("required_evidence", [])})

    kinds = {e["kind"] for e in evidence}
    missing = [r for r in m.get("required_evidence", [])
               if r not in kinds and r not in {"report", "code", "data"}]
    ai_check = {"evidence_count": len(evidence), "kinds": sorted(kinds),
                "missing_kinds": missing,
                "flag": ("Required evidence types missing: " + ", ".join(missing))
                        if missing else "All required evidence types present.",
                "note": "AI checks completeness only. A human reviewer approves."}

    await d.projects.update_one(
        {"project_id": project_id, "milestones.milestone_id": milestone_id},
        {"$set": {"milestones.$.status": "submitted",
                  "milestones.$.evidence": evidence,
                  "milestones.$.submitted_at": now(),
                  "milestones.$.submitted_by": body.submitted_by,
                  "milestones.$.note": body.note,
                  "milestones.$.ai_check": ai_check,
                  "updated_at": now()}})
    await ledger(project_id, "project", "milestone_evidence_submitted", body.submitted_by,
                 "student", {"milestone": m["name"], "evidence_count": len(evidence)},
                 [e["id"] for e in evidence])
    return {"milestone_id": milestone_id, "status": "submitted", "ai_check": ai_check}


class ApproveBody(BaseModel):
    approved: bool
    reviewer: str
    comments: str | None = None


@router.post("/{project_id}/milestones/{milestone_id}/review")
async def review_milestone(project_id: str, milestone_id: str,
                           body: ApproveBody) -> dict[str, Any]:
    d = db()
    await _get(project_id)
    status = "approved" if body.approved else "rework_required"
    await d.projects.update_one(
        {"project_id": project_id, "milestones.milestone_id": milestone_id},
        {"$set": {"milestones.$.status": status,
                  "milestones.$.reviewed_by": body.reviewer,
                  "milestones.$.reviewed_at": now(),
                  "milestones.$.review_comments": body.comments,
                  "updated_at": now()}})
    await ledger(project_id, "project", f"milestone_{status}", body.reviewer,
                 "faculty", {"comments": body.comments})
    return {"milestone_id": milestone_id, "status": status}


# -------------------------------------------------------------------- funding

class FundingBody(BaseModel):
    amount: float = Field(gt=0)
    source: str                 # state_fund | csr | industry | university | grant
    stage_gate: str             # which stage this tranche unlocks
    approved_by: str
    conditions: str | None = None


@router.post("/{project_id}/funding")
async def release_funding(project_id: str, body: FundingBody) -> dict[str, Any]:
    """Stage-gated funding: money follows evidence, never promises."""
    d = db()
    p = await _get(project_id)

    if body.stage_gate in ("field_pilot", "deployment", "scale_up") and \
            not p.get("impact_contract", {}).get("metrics"):
        raise HTTPException(409, {
            "error": "impact_contract_required",
            "message": ("Funding beyond prototype requires a signed Impact Contract so "
                        "success is defined before the money moves.")})

    tranche = {"tranche_id": new_id("FT"), "amount": body.amount, "source": body.source,
               "stage_gate": body.stage_gate, "approved_by": body.approved_by,
               "conditions": body.conditions, "released_at": now()}
    await d.projects.update_one(
        {"project_id": project_id},
        {"$push": {"funding.tranches": tranche},
         "$inc": {"funding.released": body.amount, "funding.committed": body.amount},
         "$set": {"updated_at": now()}})
    if p.get("mission_id"):
        await d.missions.update_one({"mission_id": p["mission_id"]},
                                    {"$inc": {"budget_released": body.amount}})
    await ledger(project_id, "project", "funding_tranche_released", body.approved_by,
                 "govt_officer", {"amount": body.amount, "source": body.source,
                                  "stage_gate": body.stage_gate})
    return clean(tranche)


# ------------------------------------------------------------- impact contract

@router.post("/{project_id}/impact-contract/suggest")
async def suggest_contract(project_id: str) -> dict[str, Any]:
    d = db()
    p = await _get(project_id)
    ch = await d.challenges.find_one({"challenge_id": p["challenge_id"]}, {"_id": 0})
    if not ch:
        raise HTTPException(404, "Linked challenge not found")
    contract = await impact_ai.suggest_contract(ch["dna"])
    return contract


class SignContractBody(BaseModel):
    metrics: list[dict[str, Any]]
    review_points: list[str] = []
    fail_condition: str | None = None
    sdg_alignment: list[str] = []
    signed_by: list[str] = Field(min_length=1)   # must include a community representative


@router.post("/{project_id}/impact-contract")
async def sign_contract(project_id: str, body: SignContractBody) -> dict[str, Any]:
    """Baseline and targets agreed with the community BEFORE building starts."""
    await _get(project_id)
    contract = {"metrics": body.metrics, "review_points": body.review_points,
                "fail_condition": body.fail_condition, "sdg_alignment": body.sdg_alignment,
                "signed_by": body.signed_by, "status": "signed", "signed_at": now()}
    await db().projects.update_one({"project_id": project_id},
                                   {"$set": {"impact_contract": contract,
                                             "updated_at": now()}})
    await ledger(project_id, "project", "impact_contract_signed",
                 ", ".join(body.signed_by), "multi_party",
                 {"metrics": [m.get("metric") for m in body.metrics],
                  "fail_condition": body.fail_condition})
    return contract


class ReadingsBody(BaseModel):
    readings: list[dict[str, Any]]     # [{metric, baseline, current, measured_by}]
    beneficiaries: int = 0
    recorded_by: str


@router.post("/{project_id}/impact")
async def record_impact(project_id: str, body: ReadingsBody) -> dict[str, Any]:
    """Measure endline against the agreed baseline. Not a status update - a measurement."""
    d = db()
    p = await _get(project_id)
    contract = p.get("impact_contract") or {}
    if not contract.get("metrics"):
        raise HTTPException(409, {"error": "no_impact_contract",
                                  "message": "Sign an Impact Contract before measuring."})

    result = impact_ai.measure(contract, body.readings)
    result["beneficiaries"] = body.beneficiaries
    result.update(impact_ai.cost_effectiveness(
        p.get("funding", {}).get("released", 0), body.beneficiaries))
    result["recorded_by"] = body.recorded_by
    result["recorded_at"] = now()

    await d.projects.update_one({"project_id": project_id},
                                {"$set": {"impact": result, "updated_at": now()}})
    await ledger(project_id, "project", "impact_measured", body.recorded_by, "faculty",
                 {"success_rate_pct": result["success_rate_pct"],
                  "overall": result["overall"], "beneficiaries": body.beneficiaries})
    return result


@router.get("/{project_id}/risk")
async def project_risk(project_id: str) -> dict[str, Any]:
    p = await _get(project_id)
    return insight.project_risk(p)
