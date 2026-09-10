"""University / HEI Matching Engine.

Reasons across the Innovation Knowledge Graph rather than matching category labels.
A rural water-monitoring challenge needs civil engineering + hydrology + electronics +
IoT + data analytics + community engagement; we look for institutions that between
them actually hold those capabilities - and we always show our working.
"""
from __future__ import annotations

from typing import Any

from . import groq_client, similarity

WEIGHTS = {
    "expertise_coverage": 32,
    "faculty_specialisation": 20,
    "lab_infrastructure": 15,
    "track_record": 13,
    "geographic_feasibility": 12,
    "incubation_industry": 8,
}


def _norm_tokens(items: list[str]) -> set[str]:
    out: set[str] = set()
    for it in items or []:
        for tok in str(it).lower().replace("&", " ").replace("/", " ").split():
            tok = tok.strip(",.()-")
            if len(tok) > 2 and tok not in {"and", "the", "for", "with", "engineering"}:
                out.add(tok)
    return out


def _overlap(required: list[str], offered: list[str]) -> tuple[float, list[str]]:
    """Fraction of required capabilities that the institution demonstrably holds."""
    if not required:
        return 0.5, []
    off_tokens = _norm_tokens(offered)
    off_text = " ".join(str(o).lower() for o in offered or [])
    matched: list[str] = []
    for req in required:
        rl = str(req).lower()
        if rl in off_text:
            matched.append(req)
            continue
        rt = _norm_tokens([req])
        if rt and len(rt & off_tokens) / len(rt) >= 0.5:
            matched.append(req)
    return len(matched) / len(required), matched


def score_institution(dna: dict[str, Any], location: dict[str, Any],
                      inst: dict[str, Any]) -> dict[str, Any]:
    required = dna.get("required_expertise") or []
    domain = dna.get("primary_domain")
    all_domains = {domain, *(dna.get("secondary_domains") or [])}
    factors: list[dict[str, Any]] = []

    def add(key: str, norm: float, reason: str, evidence: list[str] | None = None) -> None:
        norm = max(0.0, min(1.0, float(norm)))
        factors.append({
            "factor": key.replace("_", " ").title(),
            "key": key,
            "weight": WEIGHTS[key],
            "contribution": round(norm * WEIGHTS[key], 2),
            "reason": reason,
            "evidence": evidence or [],
        })

    # 1. expertise coverage across departments + research areas
    capabilities = (inst.get("departments") or []) + (inst.get("research_areas") or [])
    cov, matched = _overlap(required, capabilities)
    missing = [r for r in required if r not in matched]
    add("expertise_coverage", cov,
        f"Covers {len(matched)} of {len(required)} required disciplines."
        + (f" Gap: {', '.join(missing)}." if missing else " Full coverage."),
        matched)

    # 2. named faculty whose specialisation matches
    faculty = inst.get("faculty") or []
    relevant = []
    for f in faculty:
        spec = (f.get("specialisation") or []) + (f.get("research_interests") or [])
        c, m = _overlap(required, spec)
        if c > 0 or any(d in (f.get("domains") or []) for d in all_domains):
            relevant.append({"name": f.get("name"), "designation": f.get("designation"),
                             "department": f.get("department"),
                             "matched": m, "publications": f.get("publications", 0),
                             "patents": f.get("patents", 0)})
    relevant.sort(key=lambda r: (-len(r["matched"]), -r["publications"]))
    top = relevant[:3]
    add("faculty_specialisation", min(1.0, len(relevant) / 3),
        f"{len(relevant)} faculty member(s) work in relevant areas"
        + (f", led by {top[0]['name']} ({top[0]['department']})." if top else "."),
        [f"{r['name']} - {r['department']}" for r in top])

    # 3. laboratories & equipment
    labs = inst.get("laboratories") or []
    lab_hits = [l for l in labs
                if any(d.replace("_", " ") in str(l.get("focus", "")).lower()
                       for d in all_domains if d)
                or _overlap(required, [l.get("focus", "")] + (l.get("equipment") or []))[0] > 0]
    add("lab_infrastructure", min(1.0, len(lab_hits) / 2),
        f"{len(lab_hits)} relevant laboratory/centre available."
        if lab_hits else "No directly relevant laboratory listed.",
        [l.get("name") for l in lab_hits[:3]])

    # 4. track record on similar problems
    past = inst.get("past_projects") or []
    similar = [p for p in past if p.get("domain") in all_domains]
    add("track_record", min(1.0, len(similar) / 2),
        f"{len(similar)} previous project(s) in this domain"
        + (f", including \"{similar[0].get('title')}\"." if similar else "."),
        [p.get("title") for p in similar[:2]])

    # 5. geographic feasibility - can they actually reach the field site?
    dist_km = None
    geo_reason = "Distance unknown."
    if location.get("lat") and inst.get("lat"):
        dist_km = similarity.haversine_km(location["lat"], location["lon"],
                                          inst["lat"], inst["lon"])
        if dist_km <= 40:
            geo, geo_reason = 1.0, f"Only {dist_km:.0f} km from the site - easy field access."
        elif dist_km <= 100:
            geo, geo_reason = 0.8, f"{dist_km:.0f} km away - day-trip field access."
        elif dist_km <= 200:
            geo, geo_reason = 0.55, f"{dist_km:.0f} km away - workable with planning."
        else:
            geo, geo_reason = 0.3, f"{dist_km:.0f} km away - field visits will be costly."
    else:
        geo = 0.5
    if location.get("district") in (inst.get("districts_served") or []):
        geo = max(geo, 0.9)
        geo_reason += " Institution already works in this district."
    inst_state = inst.get("state", "Jharkhand")
    if inst_state != location.get("state", "Jharkhand"):
        geo = min(geo, 0.35)
        geo_reason = (f"Based in {inst_state}, not {location.get('state', 'Jharkhand')}. "
                      "Strong on paper, but a local partner would be needed for field visits "
                      "and day-to-day maintenance.")
    add("geographic_feasibility", geo, geo_reason,
        [f"{dist_km:.0f} km"] if dist_km is not None else [])

    # 6. incubation, industry linkage, ability to carry it beyond a report
    inc = 0.0
    bits = []
    if inst.get("incubation_centre"):
        inc += 0.5; bits.append("Incubation centre")
    if inst.get("industry_partners"):
        inc += 0.3; bits.append(f"{len(inst['industry_partners'])} industry partners")
    if inst.get("patents", 0) > 0:
        inc += 0.2; bits.append(f"{inst['patents']} patents")
    add("incubation_industry", inc,
        "Can carry a prototype towards deployment: " + ", ".join(bits) + "."
        if bits else "No incubation or industry linkage listed.", bits)

    score = round(sum(f["contribution"] for f in factors), 1)
    ranked = sorted(factors, key=lambda f: -f["contribution"])

    return {
        "institution_id": inst.get("institution_id"),
        "name": inst.get("name"),
        "type": inst.get("type"),
        "district": inst.get("district"),
        "match_score": score,
        "factors": factors,
        "strengths": [f["factor"] for f in ranked[:2]],
        "gaps": [f["factor"] for f in ranked if f["contribution"] < f["weight"] * 0.35][:2],
        "recommended_faculty": top,
        "matched_expertise": matched,
        "missing_expertise": missing,
        "distance_km": round(dist_km, 1) if dist_km is not None else None,
        "explanation": (
            f"{inst.get('name')} scores {score}/100. "
            f"Strongest on {ranked[0]['factor'].lower()} ({ranked[0]['reason']}) "
            f"and {ranked[1]['factor'].lower()}. "
            + (f"Weakest on {ranked[-1]['factor'].lower()}: {ranked[-1]['reason']}"
               if ranked[-1]["contribution"] < ranked[-1]["weight"] * 0.4 else "")
        ),
    }


def rank_institutions(dna: dict[str, Any], location: dict[str, Any],
                      institutions: list[dict[str, Any]], top_n: int = 5
                      ) -> list[dict[str, Any]]:
    scored = [score_institution(dna, location, i) for i in institutions]
    scored.sort(key=lambda s: -s["match_score"])
    return scored[:top_n]


def consortium_gap(dna: dict[str, Any], picks: list[dict[str, Any]]) -> dict[str, Any]:
    """What does a multi-institution consortium cover, and what is still missing?"""
    required = set(dna.get("required_expertise") or [])
    covered: set[str] = set()
    for p in picks:
        covered |= set(p.get("matched_expertise") or [])
    missing = sorted(required - covered)
    return {
        "required": sorted(required),
        "covered": sorted(covered),
        "still_missing": missing,
        "coverage_pct": round(100 * len(covered) / max(1, len(required)), 1),
        "advice": ("Consortium covers every required discipline."
                   if not missing else
                   f"Consortium still lacks: {', '.join(missing)}. "
                   "Add an industry or startup partner for these."),
    }


async def explain_allocation(dna: dict[str, Any], match: dict[str, Any]) -> str:
    """Plain-language justification the officer can paste into an allocation order."""
    fallback = match["explanation"]
    text = await groq_client.text_call(
        "You justify a government decision to allocate a societal challenge to a "
        "university. Write 3 short sentences in plain English for an official record. "
        "Reference only the evidence given. No marketing language.",
        f"Challenge: {dna.get('title')} ({dna.get('primary_domain')})\n"
        f"Required expertise: {', '.join(dna.get('required_expertise') or [])}\n"
        f"Institution: {match['name']}, score {match['match_score']}/100\n"
        "Factor evidence:\n" + "\n".join(
            f"- {f['factor']}: {f['contribution']}/{f['weight']} - {f['reason']}"
            for f in match["factors"]),
        temperature=0.2, max_tokens=280)
    return text or fallback
