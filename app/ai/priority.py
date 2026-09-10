"""Classification & Priority Engine + Evidence Confidence Score.

Deliberately NOT a black box. The AI never returns a bare "high/medium/low".
It returns a score built from weighted, individually explainable factors, and a
government officer always makes the final call.
"""
from __future__ import annotations

from typing import Any

from . import groq_client

# Factor weights sum to 100.
WEIGHTS = {
    "population_affected": 18,
    "severity": 16,
    "urgency": 14,
    "vulnerable_groups": 12,
    "independent_reports": 12,
    "health_safety_risk": 10,
    "recurrence": 10,
    "geographic_spread": 8,
}

_HEALTH_DOMAINS = {"healthcare", "water_resources", "sanitation", "waste_management",
                   "environment", "disaster_resilience"}

_FREQ_SCORE = {"continuous": 1.0, "recurring": 0.8, "seasonal": 0.7,
               "one_time": 0.3, "unknown": 0.4}


def _band(score: float) -> str:
    if score >= 75:
        return "critical"
    if score >= 58:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def compute_priority(dna: dict[str, Any], *, independent_reports: int = 1,
                     districts_touched: int = 1) -> dict[str, Any]:
    """Returns a 0-100 priority score with a per-factor explanation."""
    factors: list[dict[str, Any]] = []

    def add(key: str, norm: float, raw: Any, reason: str) -> None:
        norm = max(0.0, min(1.0, float(norm)))
        contribution = round(norm * WEIGHTS[key], 2)
        factors.append({
            "factor": key.replace("_", " ").title(),
            "key": key,
            "weight": WEIGHTS[key],
            "observed": raw,
            "normalised": round(norm, 3),
            "contribution": contribution,
            "reason": reason,
        })

    # 1. population affected (log-ish banding, conservative when unknown)
    people = dna.get("people_affected_estimate")
    if people:
        if people >= 20000:
            norm, why = 1.0, f"About {people:,} people affected - district scale."
        elif people >= 5000:
            norm, why = 0.85, f"About {people:,} people affected - block scale."
        elif people >= 1000:
            norm, why = 0.65, f"About {people:,} people affected - multi-village scale."
        elif people >= 300:
            norm, why = 0.45, f"About {people:,} people affected - village scale."
        else:
            norm, why = 0.25, f"About {people:,} people affected - hamlet scale."
    else:
        norm, why = 0.35, "Population not stated; assumed village-scale pending verification."
    add("population_affected", norm, people, why)

    # 2. severity
    sev = int(dna.get("severity", 3))
    add("severity", (sev - 1) / 4,
        f"{sev}/5",
        f"Reported severity {sev} of 5 - {'life or livelihood threatening' if sev >= 4 else 'significant hardship' if sev == 3 else 'manageable inconvenience'}.")

    # 3. urgency
    urg = int(dna.get("urgency", 3))
    add("urgency", (urg - 1) / 4, f"{urg}/5",
        f"Reported urgency {urg} of 5 - {'needs action within days' if urg >= 4 else 'needs action this season' if urg == 3 else 'can be planned'}.")

    # 4. vulnerable groups
    groups = dna.get("vulnerable_groups") or []
    norm = min(1.0, len(groups) / 3)
    add("vulnerable_groups", norm, groups,
        f"Affects {len(groups)} vulnerable group(s): {', '.join(groups) or 'none identified'}."
        if groups else "No specific vulnerable group identified yet.")

    # 5. independent corroboration
    n = max(1, int(independent_reports))
    norm = min(1.0, (n - 1) / 5)
    add("independent_reports", norm, n,
        f"{n} independent citizen report(s) describe this problem." +
        (" Multiple independent reports strongly suggest a systemic issue." if n >= 3 else ""))

    # 6. health / safety risk
    dom = dna.get("primary_domain", "")
    all_doms = {dom, *(dna.get("secondary_domains") or [])}
    risky = all_doms & _HEALTH_DOMAINS
    emergency = bool(dna.get("is_emergency"))
    norm = 1.0 if emergency else (0.75 if risky else 0.2)
    add("health_safety_risk", norm, sorted(risky),
        "Flagged as an emergency with direct risk to life or safety." if emergency
        else f"Touches public health / safety domains: {', '.join(sorted(risky))}." if risky
        else "No direct public health or safety pathway identified.")

    # 7. recurrence
    freq = str(dna.get("frequency", "unknown"))
    norm = _FREQ_SCORE.get(freq, 0.4)
    add("recurrence", norm, freq,
        f"Problem is {freq.replace('_', ' ')} - "
        + ("it returns predictably, so a one-off repair will not fix it."
           if freq in ("seasonal", "recurring", "continuous")
           else "appears to be a single occurrence."))

    # 8. geographic spread
    d = max(1, int(districts_touched))
    norm = min(1.0, (d - 1) / 3 + 0.25)
    add("geographic_spread", norm, f"{d} district(s)",
        f"Similar reports span {d} district(s)." if d > 1
        else "Currently confined to one district.")

    score = round(sum(f["contribution"] for f in factors), 2)
    band = _band(score)
    top = sorted(factors, key=lambda f: -f["contribution"])[:3]

    return {
        "score": score,
        "band": band,
        "factors": factors,
        "top_drivers": [f["factor"] for f in top],
        "headline": (
            f"Priority {band.upper()} ({score}/100). Driven mainly by "
            + ", ".join(f["factor"].lower() for f in top) + "."
        ),
        "decided_by": "ai_recommendation",
        "note": "AI recommendation only. Final priority must be set by an authorised officer.",
    }


def evidence_confidence(*, evidence: list[dict[str, Any]], location: dict[str, Any],
                        independent_reports: int, text_length: int,
                        assisted: bool = False, field_verified: bool = False
                        ) -> dict[str, Any]:
    """How much can we trust this report as-is? Low score != rejection."""
    factors: list[dict[str, Any]] = []
    total = 0.0

    def add(name: str, points: float, cap: float, reason: str) -> None:
        nonlocal total
        points = round(max(0.0, min(cap, points)), 2)
        total += points
        factors.append({"factor": name, "points": points, "max": cap, "reason": reason})

    has_gps = bool(location.get("lat") and location.get("lon"))
    add("GPS coordinates", 18 if has_gps else 0, 18,
        "Exact GPS captured with the report." if has_gps
        else "No GPS captured - location is text only.")

    photos = [e for e in evidence if e.get("kind") in ("image", "video")]
    add("Photo / video evidence", min(len(photos), 3) * 8, 24,
        f"{len(photos)} media file(s) attached." if photos else "No media evidence attached.")

    audio = [e for e in evidence if e.get("kind") == "audio"]
    add("Voice testimony", 8 if audio else 0, 8,
        "Citizen recorded a voice statement." if audio else "No voice statement.")

    n = max(1, independent_reports)
    add("Independent corroboration", min(n - 1, 4) * 6, 24,
        f"{n} separate citizens reported this." if n > 1
        else "Only one report so far - needs corroboration.")

    add("Description richness", min(text_length / 400, 1.0) * 8, 8,
        f"Description is {text_length} characters - "
        + ("detailed." if text_length > 250 else "brief, more detail would help."))

    add("Assisted submission", 8 if assisted else 0, 8,
        "Submitted through a CSC / Panchayat facilitator (identity traceable)."
        if assisted else "Self-submitted online.")

    add("Field verification", 10 if field_verified else 0, 10,
        "Verified on the ground by an officer." if field_verified
        else "Not yet field verified.")

    score = round(total, 1)
    if score >= 70:
        level, guidance = "high", "Sufficient evidence to proceed to allocation."
    elif score >= 45:
        level, guidance = "medium", "Proceed, but request one corroborating report or a site photo."
    else:
        level, guidance = "low", "Recommend field verification before any resource commitment."

    return {"score": score, "level": level, "factors": factors, "guidance": guidance}


async def narrate(dna: dict[str, Any], priority: dict[str, Any],
                  confidence: dict[str, Any]) -> str:
    """Optional plain-language brief for the reviewing officer."""
    fallback = (
        f"{priority['headline']} Evidence confidence is {confidence['level']} "
        f"({confidence['score']}/100). {confidence['guidance']}"
    )
    text = await groq_client.text_call(
        "You brief a busy Jharkhand government officer. Write 3 short sentences, plain "
        "English, no jargon, no bullet points. State what the problem is, why the AI "
        "scored it this way, and what the officer should check before deciding. "
        "Never claim certainty the evidence does not support.",
        f"Problem: {dna.get('title')}\nDomain: {dna.get('primary_domain')}\n"
        f"Affected: {dna.get('affected_community')} (~{dna.get('people_affected_estimate')})\n"
        f"Priority: {priority['score']}/100 ({priority['band']}), "
        f"top drivers {', '.join(priority['top_drivers'])}\n"
        f"Evidence confidence: {confidence['score']}/100 ({confidence['level']})\n"
        f"Guidance: {confidence['guidance']}",
        temperature=0.25, max_tokens=260)
    return text or fallback
