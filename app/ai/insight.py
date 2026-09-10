"""Government Insight Engine, Predictive Problem Intelligence, Project Risk Engine."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from . import groq_client

_SEASONAL = {
    "water_resources": ("Mar-Jun", "pre-monsoon groundwater drawdown"),
    "agriculture": ("Jun-Jul, Oct-Nov", "sowing and harvest windows"),
    "healthcare": ("Jun-Sep", "monsoon waterborne disease season"),
    "disaster_resilience": ("Jun-Sep", "monsoon flooding"),
    "energy": ("Apr-Jun", "peak summer load"),
    "education": ("Jun-Jul", "academic session start"),
}


def aggregate(challenges: list[dict[str, Any]]) -> dict[str, Any]:
    dom = Counter()
    dist = Counter()
    status = Counter()
    dom_by_dist: dict[str, Counter] = defaultdict(Counter)
    vulnerable = Counter()

    for c in challenges:
        d = c.get("dna", {})
        loc = c.get("location", {})
        pd = d.get("primary_domain")
        district = loc.get("district")
        if pd:
            dom[pd] += 1
        if district:
            dist[district] += 1
        if pd and district:
            dom_by_dist[district][pd] += 1
        status[c.get("status", "unknown")] += 1
        for g in d.get("vulnerable_groups") or []:
            vulnerable[g] += 1

    hotspots = []
    for district, counter in dom_by_dist.items():
        top_dom, n = counter.most_common(1)[0]
        if n >= 3:
            hotspots.append({"district": district, "domain": top_dom, "count": n,
                             "share_pct": round(100 * n / sum(counter.values()), 1)})
    hotspots.sort(key=lambda h: -h["count"])

    return {
        "total": len(challenges),
        "by_domain": dom.most_common(),
        "by_district": dist.most_common(),
        "by_status": status.most_common(),
        "vulnerable_groups": vulnerable.most_common(),
        "hotspots": hotspots[:8],
    }


POLICY_SYSTEM = """You are the Government Insight Engine of SAMADHAN GRID, briefing the
Jharkhand state planning department.

You are given aggregate statistics from real citizen reports. Find the SYSTEMIC pattern
that individual project managers cannot see - the thing that suggests a programme or
policy change rather than 30 separate fixes.

Be rigorous. Only claim what the numbers support. Say plainly when the sample is too
small to conclude anything.

Return ONLY JSON:
{
  "headline": "one sentence a minister could read",
  "systemic_findings": [
    {"finding":"...", "evidence":"the specific numbers behind it",
     "implication":"what this means for policy",
     "confidence":"high|medium|low"}
  ],
  "recommended_missions": [
    {"name":"...", "districts":["..."], "outcome":"measurable outcome with a number",
     "why_now":"..."}
  ],
  "budget_signal": "where money is likely being wasted or under-applied",
  "data_gaps": ["what the state should start measuring"]
}"""


async def policy_insights(challenges: list[dict[str, Any]]) -> dict[str, Any]:
    agg = aggregate(challenges)
    if agg["total"] < 3:
        return {"headline": "Not enough reports yet to identify a systemic pattern.",
                "systemic_findings": [], "recommended_missions": [],
                "budget_signal": "n/a", "data_gaps": ["More citizen reports needed."],
                "aggregate": agg, "source": "insufficient_data"}

    user = (
        f"Total validated/active citizen reports: {agg['total']}\n"
        f"By domain: {agg['by_domain']}\n"
        f"By district: {agg['by_district']}\n"
        f"By status: {agg['by_status']}\n"
        f"Vulnerable groups affected: {agg['vulnerable_groups']}\n"
        f"District hotspots: {agg['hotspots']}\n\n"
        "Produce the policy brief.")

    raw = await groq_client.json_call(POLICY_SYSTEM, user, temperature=0.3)

    if not raw:
        top_dom = agg["by_domain"][0] if agg["by_domain"] else ("unknown", 0)
        raw = {
            "headline": f"{top_dom[1]} of {agg['total']} reports concentrate in "
                        f"{str(top_dom[0]).replace('_', ' ')}.",
            "systemic_findings": [{
                "finding": f"{str(top_dom[0]).replace('_', ' ').title()} dominates citizen reporting.",
                "evidence": f"{top_dom[1]}/{agg['total']} reports.",
                "implication": "A domain-wide programme may beat isolated projects.",
                "confidence": "medium" if agg["total"] >= 10 else "low"}],
            "recommended_missions": [{
                "name": f"{str(top_dom[0]).replace('_', ' ').title()} Mission",
                "districts": [d for d, _ in agg["by_district"][:3]],
                "outcome": "Reduce reports in this domain by 40% within 18 months.",
                "why_now": "Concentration of independent reports."}],
            "budget_signal": "Insufficient funding data.",
            "data_gaps": ["Baseline measurement in affected villages."],
        }
    raw["aggregate"] = agg
    raw["source"] = "groq" if groq_client.available() else "fallback"
    return raw


def predict(challenges: list[dict[str, Any]]) -> dict[str, Any]:
    """Decision support, not a guaranteed forecast."""
    month = datetime.now(timezone.utc).month
    by_dd: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for c in challenges:
        d = c.get("dna", {})
        district = c.get("location", {}).get("district")
        dom = d.get("primary_domain")
        if district and dom:
            by_dd[(district, dom)].append(c)

    predictions = []
    for (district, dom), items in by_dd.items():
        seasonal_count = sum(1 for i in items
                             if i.get("dna", {}).get("frequency") in ("seasonal", "recurring"))
        if seasonal_count < 2:
            continue
        window, driver = _SEASONAL.get(dom, ("unknown", "recurring pattern"))
        risk = min(95, 35 + seasonal_count * 12)
        upcoming = (dom == "water_resources" and month in (1, 2, 3, 4, 5)) or \
                   (dom in ("healthcare", "disaster_resilience") and month in (4, 5, 6, 7)) or \
                   (dom == "energy" and month in (2, 3, 4))
        predictions.append({
            "district": district,
            "domain": dom,
            "recurring_reports": seasonal_count,
            "expected_window": window,
            "driver": driver,
            "risk_pct": risk,
            "imminent": upcoming,
            "note": (f"{seasonal_count} recurring/seasonal reports in {district} for "
                     f"{dom.replace('_', ' ')}. Expect a rise around {window} due to {driver}."),
            "suggested_action": "Pre-position resources and start a mission before the window.",
        })

    predictions.sort(key=lambda p: (-int(p["imminent"]), -p["risk_pct"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "predictions": predictions[:10],
        "disclaimer": ("Decision-support only. These are patterns in citizen reporting, "
                       "not guaranteed forecasts. Verify before committing budget."),
    }


def project_risk(project: dict[str, Any]) -> dict[str, Any]:
    """Detect delay and risk patterns in a running project."""
    flags: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    milestones = project.get("milestones", [])
    overdue = []
    for m in milestones:
        due = m.get("due")
        if isinstance(due, datetime) and m.get("status") != "approved":
            d = due if due.tzinfo else due.replace(tzinfo=timezone.utc)
            if d < now:
                overdue.append(m)
    if overdue:
        flags.append({"risk": "Overdue milestones", "severity": "high",
                      "detail": f"{len(overdue)} milestone(s) past due: "
                                + ", ".join(m.get("name", "?") for m in overdue[:3]),
                      "action": "Escalate to the faculty mentor and reset the plan."})

    missing_evidence = [m for m in milestones
                        if m.get("status") == "submitted" and not m.get("evidence")]
    if missing_evidence:
        flags.append({"risk": "Milestone claimed without evidence", "severity": "high",
                      "detail": f"{len(missing_evidence)} milestone(s) marked done with no "
                                "uploaded deliverable.",
                      "action": "Block approval until evidence is uploaded."})

    r = project.get("readiness", {})
    trl, crl = r.get("trl", 1), r.get("crl", 1)
    if trl - crl >= 3:
        flags.append({"risk": "Community left behind", "severity": "medium",
                      "detail": f"TRL {trl} but CRL {crl}. Technology is racing ahead of "
                                "the people meant to use it.",
                      "action": "Run a community design session before the next milestone."})

    funding = project.get("funding", {})
    if funding.get("released", 0) > 0 and not project.get("impact_contract", {}).get("metrics"):
        flags.append({"risk": "Money released without an Impact Contract", "severity": "high",
                      "detail": "Funds have moved but success was never defined.",
                      "action": "Freeze the next tranche until the contract is signed."})

    if project.get("stage") in ("deployment", "impact_monitoring") and \
            not project.get("community_feedback_count"):
        flags.append({"risk": "Deployed without community validation", "severity": "high",
                      "detail": "Project reports deployment but no community feedback exists.",
                      "action": "Run community validation before declaring success."})

    score = sum({"high": 30, "medium": 15, "low": 5}[f["severity"]] for f in flags)
    return {
        "risk_score": min(100, score),
        "level": "high" if score >= 45 else "medium" if score >= 20 else "low",
        "flags": flags,
        "healthy": not flags,
    }
