"""Impact Contract, three-axis Readiness, and Impact Intelligence.

Success is defined WITH the community BEFORE work starts, not written up afterwards.
And "it works in the lab" is separated from "people actually use it" and "it can grow".
"""
from __future__ import annotations

from typing import Any

from . import groq_client

# --------------------------------------------------------------- readiness axes

TRL = {
    1: "Basic principle observed", 2: "Concept formulated", 3: "Proof of concept",
    4: "Validated in laboratory", 5: "Validated in relevant environment",
    6: "Demonstrated in relevant environment", 7: "Prototype demonstrated in the field",
    8: "System complete and qualified", 9: "Proven in operational use",
}

CRL = {  # Community Readiness Level - our addition to TRL
    1: "Community not yet consulted", 2: "Community consulted about the problem",
    3: "Community involved in design", 4: "Community tested a prototype",
    5: "Community accepts the solution", 6: "Community uses it without hand-holding",
    7: "Community can maintain it locally", 8: "Community owns operation and upkeep",
    9: "Community demands expansion",
}

SRL = {  # Scale Readiness Level
    1: "Single site only", 2: "Cost per unit unknown", 3: "Cost per unit known",
    4: "Replicated at a second site", 5: "Supply chain identified",
    6: "Local repair network exists", 7: "Block-level rollout viable",
    8: "District-level rollout viable", 9: "State-wide rollout viable",
}

_STAGE_TRL = {
    "problem_validated": 1, "research_initiated": 2, "concept_proposed": 3,
    "proof_of_concept": 4, "prototype": 5, "lab_testing": 5, "field_pilot": 7,
    "community_validation": 7, "production_readiness": 8, "deployment": 8,
    "impact_monitoring": 9, "scale_up": 9, "completed": 9,
}


def readiness_summary(trl: int, crl: int, srl: int) -> dict[str, Any]:
    trl, crl, srl = (max(1, min(9, int(x))) for x in (trl, crl, srl))
    gap = trl - crl
    if gap >= 3:
        warning = ("Technically ahead of the community. This is the classic pattern "
                   "behind impressive demos that nobody uses. Slow down and involve users.")
    elif crl >= 6 and srl <= 3:
        warning = ("People love it but it cannot spread yet. Work on unit cost and the "
                   "local repair network before asking for scale funding.")
    elif trl >= 7 and srl >= 7 and crl >= 6:
        warning = "Balanced and ready. Strong candidate for district-level scaling."
    else:
        warning = "Progressing normally. Keep all three axes moving together."
    return {
        "trl": trl, "trl_label": TRL[trl],
        "crl": crl, "crl_label": CRL[crl],
        "srl": srl, "srl_label": SRL[srl],
        "balance_gap": gap,
        "assessment": warning,
        "scale_ready": trl >= 7 and crl >= 6 and srl >= 7,
    }


def stage_default_trl(stage: str) -> int:
    return _STAGE_TRL.get(stage, 1)


# ------------------------------------------------------------ impact contract

_BASELINE_TEMPLATES = {
    "water_resources": [
        {"metric": "Distance walked to fetch drinking water", "unit": "metres", "direction": "decrease"},
        {"metric": "Water available per household per day", "unit": "litres", "direction": "increase"},
        {"metric": "Days per year with no water at source", "unit": "days", "direction": "decrease"},
        {"metric": "Time spent collecting water per household", "unit": "minutes/day", "direction": "decrease"},
    ],
    "healthcare": [
        {"metric": "Distance to nearest functional health facility", "unit": "km", "direction": "decrease"},
        {"metric": "Average waiting time for consultation", "unit": "minutes", "direction": "decrease"},
        {"metric": "Share of pregnant women receiving 4 checkups", "unit": "%", "direction": "increase"},
    ],
    "education": [
        {"metric": "Average daily attendance", "unit": "%", "direction": "increase"},
        {"metric": "Students at grade-level reading", "unit": "%", "direction": "increase"},
        {"metric": "Annual dropout rate", "unit": "%", "direction": "decrease"},
    ],
    "agriculture": [
        {"metric": "Crop yield per acre", "unit": "quintal/acre", "direction": "increase"},
        {"metric": "Irrigation water used per acre", "unit": "litres", "direction": "decrease"},
        {"metric": "Net farmer income per season", "unit": "INR", "direction": "increase"},
    ],
    "energy": [
        {"metric": "Hours of usable power per day", "unit": "hours", "direction": "increase"},
        {"metric": "Unplanned outages per month", "unit": "count", "direction": "decrease"},
    ],
    "sanitation": [
        {"metric": "Households with a working toilet", "unit": "%", "direction": "increase"},
        {"metric": "Reported waterborne illness cases per month", "unit": "count", "direction": "decrease"},
    ],
    "waste_management": [
        {"metric": "Waste collected and processed", "unit": "%", "direction": "increase"},
        {"metric": "Open dumping sites in the ward", "unit": "count", "direction": "decrease"},
    ],
}

_GENERIC = [
    {"metric": "Households experiencing the problem", "unit": "count", "direction": "decrease"},
    {"metric": "Community satisfaction with service", "unit": "score 1-5", "direction": "increase"},
    {"metric": "Time lost per household per week", "unit": "hours", "direction": "decrease"},
]

CONTRACT_SYSTEM = """You are drafting an "Impact Contract" for SAMADHAN GRID.

Before any building starts, the project team, the community and the government agree
on what success actually means, in numbers that can be measured in a village.

Rules:
- Metrics must be measurable by a field worker with a phone and a measuring tape.
  No abstract indices.
- Baselines must be things you can go and measure TODAY, before the project starts.
- Targets must be realistic for the stated timeframe, not aspirational.
- Include at least one metric the community itself can verify without any equipment.

Return ONLY JSON:
{
  "metrics": [
    {"metric":"...", "unit":"...", "direction":"increase|decrease",
     "baseline_method":"how a field worker measures this",
     "suggested_target_change":"e.g. reduce from 3000 m to under 500 m",
     "community_verifiable": true/false}
  ],
  "review_points": ["when to measure, e.g. baseline, end of pilot, +6 months"],
  "fail_condition": "the one result that would mean this project did NOT work",
  "sdg_alignment": ["e.g. SDG 6.1"]
}"""


async def suggest_contract(dna: dict[str, Any]) -> dict[str, Any]:
    domain = dna.get("primary_domain", "")
    user = (f"Problem: {dna.get('title')}\n{dna.get('description')}\n"
            f"Domain: {domain}\nAffected: {dna.get('affected_community')} "
            f"(~{dna.get('people_affected_estimate')})\n"
            f"Expected outcome in the citizen's words: {dna.get('expected_outcome')}\n"
            f"Location: rural/semi-urban Jharkhand\n\nDraft the Impact Contract.")

    raw = await groq_client.json_call(CONTRACT_SYSTEM, user, temperature=0.25)

    if not raw:
        tmpl = _BASELINE_TEMPLATES.get(domain, _GENERIC)
        raw = {
            "metrics": [
                {**m, "baseline_method": "Field survey of a sample of households",
                 "suggested_target_change": "Set jointly with the community at baseline",
                 "community_verifiable": True} for m in tmpl],
            "review_points": ["Baseline before build", "End of field pilot",
                              "6 months after deployment"],
            "fail_condition": "No measurable improvement against baseline, or the "
                              "community stops using the solution.",
            "sdg_alignment": [],
        }
    raw["status"] = "draft"
    raw["signed_by"] = []
    raw["source"] = "groq" if groq_client.available() else "fallback"
    return raw


# --------------------------------------------------------------- measurement

def measure(contract: dict[str, Any], readings: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare endline readings against the agreed baseline."""
    by_metric = {r.get("metric"): r for r in readings}
    rows: list[dict[str, Any]] = []
    achieved = 0
    counted = 0

    for m in contract.get("metrics", []):
        r = by_metric.get(m.get("metric"))
        if not r or r.get("baseline") is None or r.get("current") is None:
            rows.append({**m, "baseline": r.get("baseline") if r else None,
                         "current": r.get("current") if r else None,
                         "change_pct": None, "verdict": "not_measured"})
            continue
        base, cur = float(r["baseline"]), float(r["current"])
        counted += 1
        if base == 0:
            change = 100.0 if cur > 0 else 0.0
        else:
            change = (cur - base) / abs(base) * 100.0
        improved = change > 0 if m.get("direction") == "increase" else change < 0
        if improved:
            achieved += 1
        rows.append({**m, "baseline": base, "current": cur,
                     "change_pct": round(change, 1),
                     "improvement_pct": round(abs(change), 1),
                     "verdict": "improved" if improved else "no_improvement"})

    pct = round(100 * achieved / counted, 1) if counted else 0.0
    return {
        "rows": rows,
        "metrics_measured": counted,
        "metrics_improved": achieved,
        "success_rate_pct": pct,
        "overall": ("delivered" if pct >= 70 else
                    "partial" if pct >= 40 else
                    "not_delivered" if counted else "not_measured"),
    }


def cost_effectiveness(total_funding: float, beneficiaries: int) -> dict[str, Any]:
    if not beneficiaries:
        return {"cost_per_beneficiary": None, "note": "Beneficiary count not established."}
    cpb = round(total_funding / beneficiaries, 2)
    return {
        "cost_per_beneficiary": cpb,
        "total_funding": total_funding,
        "beneficiaries": beneficiaries,
        "note": f"INR {cpb:,.2f} spent per person benefiting.",
    }


def digital_twin(challenges: list[dict[str, Any]], projects: list[dict[str, Any]],
                 feedback: list[dict[str, Any]]) -> dict[str, Any]:
    """Live picture of one systemic problem across every project attacking it."""
    total_funding = sum(p.get("funding", {}).get("released", 0) for p in projects)
    beneficiaries = sum(p.get("impact", {}).get("beneficiaries", 0) for p in projects)
    improvements = [p.get("impact", {}).get("success_rate_pct")
                    for p in projects if p.get("impact", {}).get("success_rate_pct") is not None]
    avg_improve = round(sum(improvements) / len(improvements), 1) if improvements else 0.0

    votes = [f.get("verdict") for f in feedback]
    resolved = votes.count("fully_resolved")
    partial = votes.count("partially_resolved")
    none = votes.count("not_resolved")
    total_votes = max(1, len(votes))

    deployed = [p for p in projects if p.get("stage") in
                ("deployment", "impact_monitoring", "scale_up", "completed")]

    if projects and total_funding > 0 and avg_improve < 25:
        signal, advice = "strategy_review_needed", (
            f"{len(projects)} project(s) and INR {total_funding:,.0f} committed, but "
            f"average measured improvement is only {avg_improve}%. Reconsider the "
            "approach rather than funding more of the same.")
    elif avg_improve >= 60 and resolved / total_votes >= 0.5:
        signal, advice = "working", (
            "Measured improvement and community verdict agree. Strong case for scaling.")
    elif not projects:
        signal, advice = "unaddressed", "Reports exist but no project is attacking this yet."
    else:
        signal, advice = "in_progress", "Too early to judge. Keep monitoring."

    return {
        "open_reports": len(challenges),
        "active_projects": len(projects),
        "deployed_projects": len(deployed),
        "total_funding_released": total_funding,
        "beneficiaries": beneficiaries,
        "avg_measured_improvement_pct": avg_improve,
        "community_verdict": {
            "fully_resolved": resolved, "partially_resolved": partial,
            "not_resolved": none, "responses": len(votes),
            "resolved_pct": round(100 * resolved / total_votes, 1) if votes else 0.0,
        },
        "cost_effectiveness": cost_effectiveness(total_funding, beneficiaries),
        "signal": signal,
        "advice": advice,
    }
