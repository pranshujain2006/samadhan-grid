"""AI Coalition Composer.

Most societal challenges cannot be solved by one university or one discipline.
This composes the whole problem-solving ecosystem - institutions, named faculty,
labs, student disciplines, startups, manufacturers, CSR funders, NGOs, the
Panchayat and the responsible government department - and says what each one is for.
Humans then approve, modify or reject the proposal.
"""
from __future__ import annotations

from typing import Any

from . import groq_client

# What a project typically needs from a non-academic partner, by domain.
_RESOURCE_NEEDS = {
    "water_resources": ["iot_sensors", "manufacturing", "field_deployment", "funding",
                        "community_mobilisation", "data_platform"],
    "sanitation": ["manufacturing", "field_deployment", "funding", "community_mobilisation"],
    "waste_management": ["manufacturing", "logistics", "funding", "community_mobilisation"],
    "healthcare": ["medical_devices", "data_platform", "funding", "field_deployment"],
    "education": ["data_platform", "content", "funding", "community_mobilisation"],
    "agriculture": ["iot_sensors", "remote_sensing", "market_linkage", "funding",
                    "community_mobilisation"],
    "environment": ["remote_sensing", "lab_testing", "funding"],
    "energy": ["manufacturing", "field_deployment", "funding", "maintenance_network"],
    "transportation": ["engineering_services", "funding", "field_deployment"],
    "employment": ["skilling", "market_linkage", "funding"],
    "women_child_welfare": ["community_mobilisation", "funding", "data_platform"],
    "rural_livelihood": ["market_linkage", "skilling", "funding", "community_mobilisation"],
    "disaster_resilience": ["remote_sensing", "data_platform", "field_deployment", "funding"],
}

_ROLE_TEXT = {
    "iot_sensors": "supply and calibrate low-cost field sensors",
    "manufacturing": "manufacture the hardware at village-affordable unit cost",
    "field_deployment": "install, commission and maintain units in the field",
    "funding": "fund the prototype and pilot stages",
    "community_mobilisation": "mobilise the community, run training and collect feedback",
    "data_platform": "host the data pipeline, dashboards and APIs",
    "remote_sensing": "provide satellite / GIS analysis",
    "market_linkage": "connect outputs to real buyers and markets",
    "skilling": "train local youth to operate and repair the solution",
    "lab_testing": "run certified laboratory testing",
    "maintenance_network": "run the long-term repair and spares network",
    "medical_devices": "supply and certify medical hardware",
    "engineering_services": "provide detailed engineering and structural design",
    "content": "produce localised learning content",
}

_STUDENT_DISCIPLINES = {
    "water_resources": ["Civil Engineering", "Computer Science", "Electronics & IoT",
                        "Environmental Science", "Social Work", "Management"],
    "agriculture": ["Agricultural Engineering", "Data Science", "Electronics & IoT",
                    "Economics", "Social Work"],
    "healthcare": ["Biomedical Engineering", "Public Health", "Computer Science",
                   "Statistics", "Social Work"],
    "education": ["Computer Science", "Education", "Psychology", "Design"],
    "energy": ["Electrical Engineering", "Renewable Energy", "Economics"],
    "waste_management": ["Environmental Engineering", "Mechanical Engineering",
                         "Operations Research", "Social Work"],
}


def _need_list(dna: dict[str, Any]) -> list[str]:
    needs: list[str] = []
    for d in [dna.get("primary_domain")] + (dna.get("secondary_domains") or []):
        for n in _RESOURCE_NEEDS.get(d, []):
            if n not in needs:
                needs.append(n)
    if not needs:
        needs = ["funding", "field_deployment", "community_mobilisation"]
    return needs[:7]


def match_partners(dna: dict[str, Any], location: dict[str, Any],
                   partners: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score industry / startup / CSR / NGO partners against what the project needs."""
    needs = set(_need_list(dna))
    domains = {dna.get("primary_domain"), *(dna.get("secondary_domains") or [])}
    out: list[dict[str, Any]] = []

    for p in partners:
        offers = set(p.get("offers") or [])
        hit = offers & needs
        if not hit and not (set(p.get("domains") or []) & domains):
            continue
        score = 0.0
        reasons: list[str] = []

        if hit:
            score += 55 * len(hit) / max(1, len(needs))
            reasons.append("Offers " + ", ".join(
                _ROLE_TEXT.get(h, h.replace('_', ' ')) for h in sorted(hit)) + ".")
        dom_hit = set(p.get("domains") or []) & domains
        if dom_hit:
            score += 20
            reasons.append(f"Already works in {', '.join(sorted(dom_hit))}.")
        if location.get("district") in (p.get("districts_active") or []):
            score += 15
            reasons.append(f"Already active in {location.get('district')} district.")
        if p.get("past_projects"):
            score += 10
            reasons.append(f"{len(p['past_projects'])} comparable project(s) delivered.")

        out.append({
            "partner_id": p.get("partner_id"),
            "name": p.get("name"),
            "type": p.get("type"),
            "district": p.get("district"),
            "fit_score": round(min(100.0, score), 1),
            "fills_needs": sorted(hit),
            "proposed_role": "; ".join(
                _ROLE_TEXT.get(h, h.replace('_', ' ')) for h in sorted(hit)
            ) or "general support",
            "why": " ".join(reasons),
        })

    out.sort(key=lambda o: -o["fit_score"])
    return out


COALITION_SYSTEM = """You are the AI Coalition Composer of SAMADHAN GRID
(Government of Jharkhand).

You are given a validated societal challenge, the universities that matched it, and
the industry / startup / CSR / NGO partners available. Propose ONE coalition that can
actually take this from research to a working field deployment.

Principles:
- Every member must have a distinct, necessary job. No decorative members.
- Always include the community voice (Panchayat / ward / local NGO). A solution the
  village will not use is not a solution.
- Name the single accountable lead.
- Be honest about what the coalition still lacks.

Return ONLY JSON:
{
  "coalition_name": "short name",
  "lead": {"member": "name", "why_lead": "one sentence"},
  "members": [
    {"name": "...", "kind": "university|faculty|startup|industry|csr|ngo|panchayat|government",
     "role": "the specific job they do", "why": "why them specifically",
     "stage": "research|prototype|pilot|deployment|scale"}
  ],
  "student_team": [
    {"discipline": "...", "count": 1-4, "contribution": "what they build or study"}
  ],
  "missing_capability": ["what the coalition still cannot do"],
  "first_90_days": ["3-5 concrete actions"],
  "risk_note": "the single biggest risk to this coalition working"
}"""


async def compose(dna: dict[str, Any], location: dict[str, Any],
                  institution_matches: list[dict[str, Any]],
                  partner_matches: list[dict[str, Any]]) -> dict[str, Any]:
    needs = _need_list(dna)
    inst_lines = "\n".join(
        f"- {m['name']} (score {m['match_score']}/100, {m['district']}): "
        f"strengths {', '.join(m['strengths'])}; faculty "
        f"{', '.join(f['name'] for f in m.get('recommended_faculty', [])) or 'n/a'}"
        for m in institution_matches[:4]) or "- none matched"
    partner_lines = "\n".join(
        f"- {p['name']} ({p['type']}, fit {p['fit_score']}): {p['proposed_role']}"
        for p in partner_matches[:6]) or "- none available"

    user = (
        f"Challenge: {dna.get('title')}\n"
        f"Domain: {dna.get('primary_domain')} (also {', '.join(dna.get('secondary_domains') or []) or 'none'})\n"
        f"Location: {location.get('village_or_ward') or '-'}, {location.get('block') or '-'}, "
        f"{location.get('district') or '-'}, Jharkhand\n"
        f"Affected: {dna.get('affected_community')} (~{dna.get('people_affected_estimate')})\n"
        f"Required expertise: {', '.join(dna.get('required_expertise') or [])}\n"
        f"Non-academic needs: {', '.join(needs)}\n\n"
        f"Matched universities:\n{inst_lines}\n\n"
        f"Available partners:\n{partner_lines}\n\n"
        "Compose the coalition now.")

    raw = await groq_client.json_call(COALITION_SYSTEM, user, temperature=0.3)

    if not raw:
        members = []
        for m in institution_matches[:2]:
            members.append({"name": m["name"], "kind": "university",
                            "role": "Lead research and student team",
                            "why": m["explanation"][:180], "stage": "research"})
        for p in partner_matches[:3]:
            members.append({"name": p["name"], "kind": p["type"],
                            "role": p["proposed_role"], "why": p["why"],
                            "stage": "prototype"})
        members.append({
            "name": f"{location.get('panchayat_or_ulb') or 'Local'} Panchayat / Ward",
            "kind": "panchayat",
            "role": "Community mobilisation, site access and final acceptance",
            "why": "The community that reported the problem must validate the fix.",
            "stage": "pilot"})
        for dept in (dna.get("govt_departments") or [])[:1]:
            members.append({"name": dept, "kind": "government",
                            "role": "Approvals, convergence with existing schemes",
                            "why": "Owns the mandate for this domain.", "stage": "deployment"})
        raw = {
            "coalition_name": f"{dna.get('subdomain', 'Challenge').title()} Coalition",
            "lead": {"member": institution_matches[0]["name"] if institution_matches else "TBD",
                     "why_lead": "Highest capability match for the required disciplines."},
            "members": members,
            "student_team": [
                {"discipline": d, "count": 2, "contribution": "Domain workstream"}
                for d in _STUDENT_DISCIPLINES.get(dna.get("primary_domain", ""),
                                                  ["Engineering", "Computer Science",
                                                   "Social Work"])[:5]],
            "missing_capability": [],
            "first_90_days": ["Baseline survey with the community",
                              "Sign the Impact Contract",
                              "Solution Memory review before any new build"],
            "risk_note": "Coalition members may not have worked together before; "
                         "the lead must run a single shared workplan.",
        }

    raw["needs_identified"] = needs
    raw["status"] = "proposed"
    raw["approval"] = {"state": "awaiting_approval", "by": None, "at": None}
    raw["source"] = "groq" if groq_client.available() else "fallback"
    return raw
