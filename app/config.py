"""Runtime configuration for SAMADHAN GRID."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3").strip()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "samadhan_grid")

HOST = os.getenv("HOST", "127.0.0.1")   # containers must use 0.0.0.0
PORT = int(os.getenv("PORT", "8000"))

# Serverless platforms give you exactly one writable directory: /tmp.
_DEFAULT_UPLOADS = "/tmp/uploads" if os.getenv("VERCEL") else str(BASE_DIR / "uploads")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", _DEFAULT_UPLOADS))
STATIC_DIR = BASE_DIR / "static"
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Read-only filesystem (some serverless platforms). Fall back to /tmp.
    UPLOAD_DIR = Path("/tmp/uploads")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- domain model

DOMAINS = [
    "water_resources", "sanitation", "healthcare", "education", "agriculture",
    "environment", "energy", "urban_development", "rural_livelihood",
    "transportation", "employment", "women_child_welfare", "accessibility",
    "public_administration", "digital_governance", "disaster_resilience",
    "waste_management", "social_inclusion",
]

DOMAIN_LABEL = {
    "water_resources": "Water Resources", "sanitation": "Sanitation",
    "healthcare": "Healthcare", "education": "Education",
    "agriculture": "Agriculture", "environment": "Environment",
    "energy": "Energy", "urban_development": "Urban Development",
    "rural_livelihood": "Rural Livelihood", "transportation": "Transportation",
    "employment": "Employment", "women_child_welfare": "Women & Child Welfare",
    "accessibility": "Accessibility", "public_administration": "Public Administration",
    "digital_governance": "Digital Governance", "disaster_resilience": "Disaster Resilience",
    "waste_management": "Waste Management", "social_inclusion": "Social Inclusion",
}

# Challenge lifecycle (validation & governance workflow)
CHALLENGE_STATES = [
    "draft", "submitted", "ai_processed", "under_review", "community_corroborated",
    "field_verification_required", "field_verified", "validated", "rejected",
    "merged", "escalated",
]

# Project lifecycle
PROJECT_STAGES = [
    "problem_validated", "research_initiated", "concept_proposed", "proof_of_concept",
    "prototype", "lab_testing", "field_pilot", "community_validation",
    "production_readiness", "deployment", "impact_monitoring", "scale_up", "completed",
]

STAGE_LABEL = {s: s.replace("_", " ").title() for s in PROJECT_STAGES}

# How a report is routed after validation
ROUTES = ["grievance", "service_delivery", "research_challenge",
          "innovation_opportunity", "emergency", "systemic_problem"]

JHARKHAND_DISTRICTS = {
    "Ranchi": (23.3441, 85.3096), "Bokaro": (23.6693, 86.1511),
    "Chatra": (24.2065, 84.8709), "Deoghar": (24.4823, 86.6947),
    "Dhanbad": (23.7957, 86.4304), "Dumka": (24.2676, 87.2497),
    "East Singhbhum": (22.8046, 86.2029), "Garhwa": (24.1541, 83.8078),
    "Giridih": (24.1913, 86.2996), "Godda": (24.8270, 87.2130),
    "Gumla": (23.0444, 84.5381), "Hazaribagh": (23.9925, 85.3637),
    "Jamtara": (23.9615, 86.8025), "Khunti": (23.0713, 85.2783),
    "Koderma": (24.4676, 85.5940), "Latehar": (23.7440, 84.4998),
    "Lohardaga": (23.4333, 84.6833), "Pakur": (24.6360, 87.8460),
    "Palamu": (24.0333, 84.0667), "Ramgarh": (23.6307, 85.5120),
    "Sahibganj": (25.2380, 87.6460), "Seraikela-Kharsawan": (22.7000, 85.9333),
    "Simdega": (22.6167, 84.5167), "West Singhbhum": (22.5500, 85.8000),
}

LANGUAGES = {"hi": "Hindi", "en": "English", "sat": "Santhali",
             "ho": "Ho", "mun": "Mundari", "kru": "Kurukh", "bho": "Bhojpuri"}

ROLES = ["citizen", "govt_officer", "domain_expert", "university_admin",
         "faculty", "student", "industry", "csr_ngo", "platform_admin"]
