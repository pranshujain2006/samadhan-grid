"""Government command dashboard, State Innovation Map, insights, digital twin, registry."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from ..config import DOMAIN_LABEL, JHARKHAND_DISTRICTS, STAGE_LABEL
from ..db import db
from ..ai import groq_client, impact as impact_ai, insight

router = APIRouter(prefix="/api", tags=["analytics"])

_ACTIVE_STAGES = ("research_initiated", "concept_proposed", "proof_of_concept",
                  "prototype", "lab_testing", "field_pilot", "community_validation",
                  "production_readiness")
_DEPLOYED_STAGES = ("deployment", "impact_monitoring", "scale_up", "completed")


@router.get("/dashboard")
async def dashboard() -> dict[str, Any]:
    d = db()
    challenges = await d.challenges.find({}, {"_id": 0}).to_list(length=2000)
    projects = await d.projects.find({}, {"_id": 0}).to_list(length=1000)
    feedback = await d.feedback.find({}, {"_id": 0}).to_list(length=2000)
    missions = await d.missions.find({}, {"_id": 0}).to_list(length=200)
    constellations = await d.constellations.find({}, {"_id": 0}).to_list(length=200)
    institutions = await d.institutions.find({}, {"_id": 0}).to_list(length=200)
    partners = await d.partners.find({}, {"_id": 0}).to_list(length=200)
    reviews = await d.reviews.find({}, {"_id": 0}).to_list(length=2000)

    status = Counter(c.get("status") for c in challenges)
    band = Counter(c.get("priority", {}).get("band") for c in challenges)
    stage = Counter(p.get("stage") for p in projects)

    funding = sum(p.get("funding", {}).get("released", 0) for p in projects)
    beneficiaries = sum(p.get("impact", {}).get("beneficiaries", 0) for p in projects)
    measured = [p for p in projects if p.get("impact", {}).get("success_rate_pct") is not None]
    avg_improvement = round(
        sum(p["impact"]["success_rate_pct"] for p in measured) / len(measured), 1
    ) if measured else 0.0

    votes = Counter(f.get("verdict") for f in feedback)
    total_votes = sum(votes.values())

    students = sum(len(p.get("team", [])) for p in projects)
    risky = [p for p in projects if insight.project_risk(p)["level"] in ("high", "medium")]

    agg = insight.aggregate(challenges)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_status": groq_client.status(),
        "challenges": {
            "total": len(challenges),
            "validated": status.get("validated", 0),
            "under_review": status.get("under_review", 0) + status.get("ai_processed", 0),
            "rejected": status.get("rejected", 0),
            "merged": status.get("merged", 0),
            "field_verification_required": status.get("field_verification_required", 0),
            "by_status": [{"key": k, "count": v} for k, v in status.most_common() if k],
            "by_priority": [{"key": k, "count": v} for k, v in band.most_common() if k],
            "by_domain": [{"key": k, "label": DOMAIN_LABEL.get(k, k), "count": v}
                          for k, v in agg["by_domain"]],
            "by_district": [{"key": k, "count": v} for k, v in agg["by_district"]],
            "vulnerable_groups": [{"key": k, "count": v} for k, v in agg["vulnerable_groups"]],
        },
        "projects": {
            "total": len(projects),
            "active": sum(stage.get(s, 0) for s in _ACTIVE_STAGES),
            "prototypes": stage.get("prototype", 0) + stage.get("lab_testing", 0),
            "pilots": stage.get("field_pilot", 0) + stage.get("community_validation", 0),
            "deployed": sum(stage.get(s, 0) for s in _DEPLOYED_STAGES),
            "at_risk": len(risky),
            "by_stage": [{"key": k, "label": STAGE_LABEL.get(k, k), "count": v}
                         for k, v in stage.most_common() if k],
            "scale_ready": sum(
                1 for p in projects
                if impact_ai.readiness_summary(
                    p.get("readiness", {}).get("trl", 1),
                    p.get("readiness", {}).get("crl", 1),
                    p.get("readiness", {}).get("srl", 1))["scale_ready"]),
        },
        "ecosystem": {
            "institutions": len(institutions),
            "partners": len(partners),
            "faculty_available": sum(len(i.get("faculty", [])) for i in institutions),
            "team_members": students,
            "missions": len(missions),
            "constellations": len(constellations),
        },
        "impact": {
            "funding_released": funding,
            "beneficiaries": beneficiaries,
            "avg_measured_improvement_pct": avg_improvement,
            "projects_measured": len(measured),
            "cost_per_beneficiary": (round(funding / beneficiaries, 2)
                                     if beneficiaries else None),
            "community_responses": total_votes,
            "community_resolved_pct": (round(100 * votes.get("fully_resolved", 0) / total_votes, 1)
                                       if total_votes else 0.0),
            "community_verdict": [{"key": k, "count": v} for k, v in votes.most_common() if k],
        },
        "satisfaction": {
            "reviews": len(reviews),
            "average": (round(sum(r["overall"] for r in reviews) / len(reviews), 2)
                        if reviews else None),
            "happy_pct": (round(100 * sum(1 for r in reviews if r["overall"] >= 4)
                                / len(reviews), 1) if reviews else None),
            "recommend_pct": (round(
                100 * sum(1 for r in reviews if r.get("would_recommend")) /
                max(1, sum(1 for r in reviews if r.get("would_recommend") is not None)), 1)
                if any(r.get("would_recommend") is not None for r in reviews) else None),
        },
        "hotspots": agg["hotspots"],
    }


@router.get("/map")
async def innovation_map(privacy: bool = True) -> dict[str, Any]:
    """State Innovation Map. Public view fuzzes exact coordinates for citizen safety."""
    d = db()
    challenges = await d.challenges.find(
        {"status": {"$ne": "draft"}}, {"_id": 0}).to_list(length=2000)
    projects = await d.projects.find({}, {"_id": 0}).to_list(length=1000)
    proj_by_challenge = {p["challenge_id"]: p for p in projects}

    def state_of(ch: dict[str, Any]) -> str:
        p = proj_by_challenge.get(ch["challenge_id"])
        if not p:
            return "rejected" if ch.get("status") == "rejected" else "unresolved"
        s = p.get("stage")
        if s in _DEPLOYED_STAGES:
            return "deployed"
        if s in ("field_pilot", "community_validation"):
            return "field_pilot"
        if s in ("prototype", "lab_testing", "proof_of_concept"):
            return "prototype"
        return "research"

    points = []
    for ch in challenges:
        loc = ch.get("location", {})
        lat, lon = loc.get("lat"), loc.get("lon")
        if lat is None or lon is None:
            continue
        if privacy and loc.get("coords_source") == "gps":
            # ~1 km grid snap so a public map cannot pinpoint a household
            lat = round(lat, 2)
            lon = round(lon, 2)
        points.append({
            "challenge_id": ch["challenge_id"],
            "title": ch.get("dna", {}).get("title"),
            "domain": ch.get("dna", {}).get("primary_domain"),
            "domain_label": DOMAIN_LABEL.get(ch.get("dna", {}).get("primary_domain"), ""),
            "district": loc.get("district"), "block": loc.get("block"),
            "lat": lat, "lon": lon,
            "priority": ch.get("priority", {}).get("band"),
            "priority_score": ch.get("priority", {}).get("score"),
            "status": ch.get("status"),
            "progress_state": state_of(ch),
            "constellation_id": ch.get("constellation_id"),
            "project_id": ch.get("project_id"),
        })

    by_district = Counter(p["district"] for p in points if p["district"])
    districts = [{"district": name, "lat": c[0], "lon": c[1],
                  "count": by_district.get(name, 0)}
                 for name, c in JHARKHAND_DISTRICTS.items()]

    return {"points": points, "districts": districts,
            "legend": {"unresolved": "Reported, not yet addressed",
                       "research": "Research in progress",
                       "prototype": "Prototype being built",
                       "field_pilot": "Field pilot running",
                       "deployed": "Deployed solution",
                       "rejected": "Closed / routed elsewhere"},
            "privacy_note": ("Exact GPS is snapped to a ~1 km grid on the public map. "
                             "Officers see precise coordinates in the case file.")}


@router.get("/insights")
async def insights() -> dict[str, Any]:
    """Government Insight Engine: systemic patterns across thousands of reports."""
    challenges = await db().challenges.find(
        {"status": {"$nin": ["draft", "rejected"]}}, {"_id": 0}).to_list(length=2000)
    return await insight.policy_insights(challenges)


@router.get("/predictions")
async def predictions() -> dict[str, Any]:
    """Predictive problem intelligence. Decision support, not a guaranteed forecast."""
    challenges = await db().challenges.find(
        {"status": {"$nin": ["draft", "rejected"]}}, {"_id": 0}).to_list(length=2000)
    return insight.predict(challenges)


@router.get("/digital-twin/{key}")
async def digital_twin(key: str, district: str | None = None) -> dict[str, Any]:
    """Live picture of one systemic problem across every project attacking it.

    `key` is a domain (e.g. water_resources) or a constellation id.
    """
    d = db()
    if key.startswith("CN-"):
        con = await d.constellations.find_one({"constellation_id": key}, {"_id": 0})
        if not con:
            raise HTTPException(404, "Constellation not found")
        q = {"challenge_id": {"$in": con.get("challenge_ids", [])}}
        label = con.get("root_cause_hypothesis") or key
    else:
        q = {"$or": [{"dna.primary_domain": key}, {"dna.secondary_domains": key}]}
        if district:
            q = {"$and": [q, {"location.district": district}]}
        label = DOMAIN_LABEL.get(key, key)

    challenges = await d.challenges.find(q, {"_id": 0}).to_list(length=1000)
    ids = [c["challenge_id"] for c in challenges]
    projects = await d.projects.find({"challenge_id": {"$in": ids}},
                                     {"_id": 0}).to_list(length=500)
    feedback = await d.feedback.find({"challenge_id": {"$in": ids}},
                                     {"_id": 0}).to_list(length=1000)

    twin = impact_ai.digital_twin(challenges, projects, feedback)
    twin["subject"] = label
    twin["key"] = key
    twin["districts"] = sorted({c.get("location", {}).get("district")
                                for c in challenges} - {None})
    twin["severity_avg"] = round(
        sum(c.get("dna", {}).get("severity", 0) for c in challenges) / len(challenges), 2
    ) if challenges else 0
    return twin


# ------------------------------------------------------------------- registry

@router.get("/institutions")
async def institutions() -> dict[str, Any]:
    items = await db().institutions.find({}, {"_id": 0}).to_list(length=200)
    projects = await db().projects.find({}, {"_id": 0}).to_list(length=1000)

    for i in items:
        mine = [p for p in projects
                if any(x["institution_id"] == i["institution_id"]
                       for x in p.get("institutions", []))]
        deployed = [p for p in mine if p.get("stage") in _DEPLOYED_STAGES]
        pilots = [p for p in mine if p.get("stage") in
                  ("field_pilot", "community_validation", *_DEPLOYED_STAGES)]
        i["impact_profile"] = {
            "challenges_accepted": len(mine),
            "prototype_conversion_pct": round(
                100 * len([p for p in mine if p.get("stage") not in
                           ("problem_validated", "research_initiated", "concept_proposed")])
                / len(mine), 1) if mine else 0.0,
            "pilot_conversion_pct": round(100 * len(pilots) / len(mine), 1) if mine else 0.0,
            "deployments": len(deployed),
            "citizens_impacted": sum(p.get("impact", {}).get("beneficiaries", 0) for p in mine),
            "districts_supported": sorted({p.get("district") for p in mine} - {None}),
            "note": "Capability domains, not a league table ranking.",
        }
    return {"count": len(items), "items": items}


@router.get("/partners")
async def partners() -> dict[str, Any]:
    items = await db().partners.find({}, {"_id": 0}).to_list(length=200)
    projects = await db().projects.find({}, {"_id": 0}).to_list(length=1000)
    for p in items:
        mine = [x for x in projects
                if any(y["partner_id"] == p["partner_id"] for y in x.get("partners", []))]
        p["impact_profile"] = {
            "projects_supported": len(mine),
            "funding_enabled": sum(
                t["amount"] for x in mine for t in x.get("funding", {}).get("tranches", [])),
            "citizens_impacted": sum(x.get("impact", {}).get("beneficiaries", 0) for x in mine),
        }
    return {"count": len(items), "items": items}


@router.get("/solution-memory")
async def solution_library(domain: str | None = None,
                           kind: str | None = None) -> dict[str, Any]:
    q: dict[str, Any] = {}
    if domain:
        q["domain"] = domain
    if kind:
        q["kind"] = kind
    items = await db().solution_memory.find(q, {"_id": 0}).to_list(length=500)
    failures = [i for i in items if i.get("kind") == "failure"]
    return {"count": len(items), "failures": len(failures), "items": items,
            "note": ("Failure Intelligence: failed projects are kept and surfaced, "
                     "not hidden. Every failure saves the next team a year.")}


@router.get("/passport/{name}")
async def innovation_passport(name: str) -> dict[str, Any]:
    """Student Innovation Passport: verified record of real-world contribution."""
    d = db()
    projects = await d.projects.find({"team.name": name}, {"_id": 0}).to_list(length=200)
    entries = []
    for p in projects:
        me = next((m for m in p.get("team", []) if m.get("name") == name), {})
        entries.append({
            "project_id": p["project_id"], "title": p["title"], "domain": p.get("domain"),
            "district": p.get("district"), "role": me.get("role"),
            "discipline": me.get("discipline"), "contribution": me.get("contribution"),
            "stage_reached": p.get("stage"),
            "readiness": p.get("readiness"),
            "beneficiaries": p.get("impact", {}).get("beneficiaries", 0),
            "measured_improvement_pct": p.get("impact", {}).get("success_rate_pct"),
            "community_validated": (p.get("community_feedback_count", 0) or 0) > 0,
        })
    return {
        "name": name,
        "projects": entries,
        "summary": {
            "challenges_worked_on": len(entries),
            "prototypes": sum(1 for e in entries if e["stage_reached"] not in
                              ("problem_validated", "research_initiated", "concept_proposed")),
            "pilots_supported": sum(1 for e in entries if e["stage_reached"] in
                                    ("field_pilot", "community_validation", *_DEPLOYED_STAGES)),
            "deployed_solutions": sum(1 for e in entries
                                      if e["stage_reached"] in _DEPLOYED_STAGES),
            "citizens_impacted": sum(e["beneficiaries"] for e in entries),
            "community_validated_projects": sum(1 for e in entries if e["community_validated"]),
        },
        "note": "Every entry is backed by ledger evidence, not self-declared.",
    }


@router.get("/config")
async def config() -> dict[str, Any]:
    from ..config import (CHALLENGE_STATES, DOMAINS, LANGUAGES, PROJECT_STAGES, ROLES,
                          ROUTES)
    return {"domains": [{"key": k, "label": DOMAIN_LABEL[k]} for k in DOMAINS],
            "districts": sorted(JHARKHAND_DISTRICTS.keys()),
            "district_coords": JHARKHAND_DISTRICTS,
            "languages": LANGUAGES, "challenge_states": CHALLENGE_STATES,
            "project_stages": [{"key": k, "label": STAGE_LABEL[k]} for k in PROJECT_STAGES],
            "routes": ROUTES, "roles": ROLES, "ai": groq_client.status()}
