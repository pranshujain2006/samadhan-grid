"""Seed data for the SAMADHAN GRID prototype.

IMPORTANT / HONESTY NOTE
------------------------
Institution names below are real Jharkhand institutions, but every capability
profile, faculty record, laboratory, past project and partner organisation here is
SYNTHETIC DEMO DATA created to exercise the matching engine. Faculty names are
placeholders and do not refer to real people. In production these profiles would be
populated and verified by the institutions themselves.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .db import db

DATA_NOTE = ("Demo capability profiles. Faculty names are placeholders, not real "
             "individuals. Institutions would maintain their own verified profiles.")


DEFAULT_STATE = "Jharkhand"


def _f(name: str, dept: str, spec: list[str], domains: list[str],
       pubs: int = 0, pats: int = 0, desig: str = "Associate Professor") -> dict[str, Any]:
    return {"name": name, "designation": desig, "department": dept,
            "specialisation": spec, "research_interests": spec, "domains": domains,
            "publications": pubs, "patents": pats, "available_for_mentorship": True,
            "synthetic": True}


INSTITUTIONS: list[dict[str, Any]] = [
    {
        "institution_id": "HEI-BITMESRA", "name": "Birla Institute of Technology, Mesra",
        "type": "Deemed University", "district": "Ranchi", "lat": 23.4126, "lon": 85.4400,
        "departments": ["Civil Engineering", "Computer Science", "Electronics & Communication",
                        "Electrical Engineering", "Environmental Engineering",
                        "Remote Sensing", "Management", "Chemical Engineering"],
        "research_areas": ["Hydrology", "IoT & Sensors", "Data Science", "GIS",
                           "Water Quality", "Machine Learning", "Renewable Energy"],
        "laboratories": [
            {"name": "Remote Sensing & GIS Centre", "focus": "geospatial water resources",
             "equipment": ["GIS workstations", "Satellite data licence", "GPS survey kit"]},
            {"name": "Environmental Engineering Lab", "focus": "water quality testing",
             "equipment": ["Spectrophotometer", "TDS meters", "Microbial assay"]},
            {"name": "IoT & Embedded Systems Lab", "focus": "IoT & sensors",
             "equipment": ["LoRaWAN gateways", "Sensor prototyping bench", "3D printer"]},
        ],
        "faculty": [
            _f("Dr. A. Verma [demo]", "Civil Engineering", ["Hydrology", "Groundwater Modelling"],
               ["water_resources", "agriculture"], 42, 2, "Professor"),
            _f("Dr. S. Mahato [demo]", "Electronics & Communication", ["IoT & Sensors", "LoRaWAN"],
               ["water_resources", "energy"], 28, 3),
            _f("Dr. P. Nag [demo]", "Computer Science", ["Data Science", "Machine Learning"],
               ["water_resources", "healthcare", "agriculture"], 35, 1),
            _f("Dr. R. Toppo [demo]", "Management", ["Community Engagement", "Rural Management"],
               ["rural_livelihood", "social_inclusion"], 18, 0, "Assistant Professor"),
        ],
        "past_projects": [
            {"title": "Groundwater level monitoring pilot, Kanke block", "domain": "water_resources",
             "year": 2023, "outcome": "12 wells instrumented"},
            {"title": "Solar micro-grid feasibility study", "domain": "energy", "year": 2022,
             "outcome": "Report submitted to JREDA"},
        ],
        "incubation_centre": True, "patents": 14,
        "industry_partners": ["Tata Steel Foundation", "JUSCO"],
        "districts_served": ["Ranchi", "Khunti", "Ramgarh", "Lohardaga", "Gumla"],
        "students": 6800, "data_note": DATA_NOTE,
    },
    {
        "institution_id": "HEI-IITISM", "name": "IIT (ISM) Dhanbad",
        "type": "Institute of National Importance", "district": "Dhanbad",
        "lat": 23.8143, "lon": 86.4412,
        "departments": ["Civil Engineering", "Environmental Science & Engineering",
                        "Computer Science & Engineering", "Electrical Engineering",
                        "Mining Engineering", "Applied Geology", "Applied Geophysics"],
        "research_areas": ["Hydrogeology", "Groundwater Modelling", "Water Quality",
                           "Remote Sensing", "Machine Learning", "Mine Water Management",
                           "Environmental Engineering"],
        "laboratories": [
            {"name": "Hydrogeology Laboratory", "focus": "groundwater and aquifer studies",
             "equipment": ["Resistivity meter", "Water level loggers", "Pumping test rig"]},
            {"name": "Geoinformatics Lab", "focus": "remote sensing and GIS",
             "equipment": ["ERDAS/ArcGIS", "Drone survey kit"]},
            {"name": "Water Chemistry Lab", "focus": "water quality testing",
             "equipment": ["ICP-MS", "Ion chromatograph"]},
        ],
        "faculty": [
            _f("Dr. K. Prasad [demo]", "Applied Geology", ["Hydrogeology", "Aquifer Mapping"],
               ["water_resources", "environment"], 78, 4, "Professor"),
            _f("Dr. M. Singh [demo]", "Environmental Science & Engineering",
               ["Water Quality", "Environmental Engineering"], ["water_resources", "environment"], 55, 2, "Professor"),
            _f("Dr. N. Roy [demo]", "Computer Science & Engineering",
               ["Machine Learning", "Data Science", "Time Series Forecasting"],
               ["water_resources", "disaster_resilience"], 46, 1),
        ],
        "past_projects": [
            {"title": "Aquifer mapping for Damodar basin", "domain": "water_resources",
             "year": 2022, "outcome": "Aquifer maps for 3 blocks"},
            {"title": "Mine water treatment prototype", "domain": "environment", "year": 2021,
             "outcome": "Pilot plant commissioned"},
        ],
        "incubation_centre": True, "patents": 61,
        "industry_partners": ["Coal India", "BCCL", "Tata Steel"],
        "districts_served": ["Dhanbad", "Bokaro", "Giridih", "Ramgarh"],
        "students": 5200, "data_note": DATA_NOTE,
    },
    {
        "institution_id": "HEI-NITJSR", "name": "NIT Jamshedpur",
        "type": "Institute of National Importance", "district": "East Singhbhum",
        "lat": 22.7769, "lon": 86.1441,
        "departments": ["Civil Engineering", "Computer Science & Engineering",
                        "Electronics & Communication", "Electrical Engineering",
                        "Mechanical Engineering", "Production Engineering"],
        "research_areas": ["Structural Engineering", "IoT & Sensors", "Water Supply Systems",
                           "Renewable Energy", "Manufacturing", "Data Science"],
        "laboratories": [
            {"name": "Environmental Engineering Lab", "focus": "water supply and treatment",
             "equipment": ["Jar test apparatus", "Turbidity meters"]},
            {"name": "Embedded & IoT Lab", "focus": "IoT & sensors",
             "equipment": ["Microcontroller bench", "Sensor calibration rig"]},
            {"name": "Central Workshop", "focus": "manufacturing and fabrication",
             "equipment": ["CNC", "Welding", "Sheet metal"]},
        ],
        "faculty": [
            _f("Dr. B. Ekka [demo]", "Civil Engineering", ["Water Supply Systems", "Hydrology"],
               ["water_resources", "urban_development"], 31, 1),
            _f("Dr. V. Kumar [demo]", "Electronics & Communication", ["IoT & Sensors", "Embedded Systems"],
               ["water_resources", "agriculture", "energy"], 24, 2),
            _f("Dr. L. Hansda [demo]", "Mechanical Engineering", ["Manufacturing", "Product Design"],
               ["waste_management", "energy"], 19, 0, "Assistant Professor"),
        ],
        "past_projects": [
            {"title": "Low-cost water filter for rural households", "domain": "water_resources",
             "year": 2023, "outcome": "200 units field tested"},
        ],
        "incubation_centre": True, "patents": 22,
        "industry_partners": ["Tata Steel", "Tata Motors"],
        "districts_served": ["East Singhbhum", "Seraikela-Kharsawan", "West Singhbhum"],
        "students": 4100, "data_note": DATA_NOTE,
    },
    {
        "institution_id": "HEI-BAU", "name": "Birsa Agricultural University, Ranchi",
        "type": "State Agricultural University", "district": "Ranchi",
        "lat": 23.4300, "lon": 85.3200,
        "departments": ["Agronomy", "Soil Science", "Agricultural Engineering",
                        "Horticulture", "Agricultural Economics", "Extension Education"],
        "research_areas": ["Irrigation", "Soil Health", "Rainfed Agriculture",
                           "Watershed Management", "Agronomy", "Community Engagement"],
        "laboratories": [
            {"name": "Soil & Water Testing Lab", "focus": "soil and irrigation water quality",
             "equipment": ["Soil analysers", "Moisture probes"]},
            {"name": "Watershed Research Station", "focus": "watershed management",
             "equipment": ["Rain gauges", "Runoff plots"]},
        ],
        "faculty": [
            _f("Dr. G. Oraon [demo]", "Agricultural Engineering",
               ["Irrigation", "Watershed Management"], ["agriculture", "water_resources"], 37, 1, "Professor"),
            _f("Dr. S. Devi [demo]", "Extension Education",
               ["Community Engagement", "Farmer Training"], ["agriculture", "rural_livelihood"], 22, 0),
        ],
        "past_projects": [
            {"title": "Watershed rejuvenation, Khunti", "domain": "water_resources", "year": 2021,
             "outcome": "18 check dams, 40 ha treated"},
            {"title": "Drought-tolerant paddy trials", "domain": "agriculture", "year": 2023,
             "outcome": "3 varieties recommended"},
        ],
        "incubation_centre": True, "patents": 6,
        "industry_partners": ["NABARD"],
        "districts_served": ["Ranchi", "Khunti", "Gumla", "Simdega", "Lohardaga", "Hazaribagh"],
        "students": 2400, "data_note": DATA_NOTE,
    },
    {
        "institution_id": "HEI-CUJ", "name": "Central University of Jharkhand, Ranchi",
        "type": "Central University", "district": "Ranchi", "lat": 23.2350, "lon": 85.2100,
        "departments": ["Environmental Science", "Computer Science", "Water Engineering",
                        "Geoinformatics", "Social Work", "Tribal Studies", "Statistics"],
        "research_areas": ["Environmental Science", "GIS", "Water Quality", "Data Science",
                           "Community Engagement", "Tribal Development"],
        "laboratories": [
            {"name": "Geoinformatics Lab", "focus": "GIS and remote sensing",
             "equipment": ["QGIS cluster", "GNSS receivers"]},
            {"name": "Environmental Analysis Lab", "focus": "water and soil quality",
             "equipment": ["Water testing kits", "Atomic absorption spectrometer"]},
        ],
        "faculty": [
            _f("Dr. J. Munda [demo]", "Tribal Studies",
               ["Community Engagement", "Tribal Development", "Social Work"],
               ["social_inclusion", "rural_livelihood", "water_resources"], 26, 0),
            _f("Dr. T. Bhagat [demo]", "Environmental Science",
               ["Water Quality", "Environmental Science"], ["water_resources", "environment"], 30, 1),
        ],
        "past_projects": [
            {"title": "Tribal household water access survey", "domain": "water_resources",
             "year": 2022, "outcome": "Baseline for 60 villages"},
        ],
        "incubation_centre": False, "patents": 3,
        "industry_partners": [],
        "districts_served": ["Ranchi", "Khunti", "Gumla", "Simdega"],
        "students": 3100, "data_note": DATA_NOTE,
    },
    {
        "institution_id": "HEI-VBU", "name": "Vinoba Bhave University, Hazaribagh",
        "type": "State University", "district": "Hazaribagh", "lat": 23.9900, "lon": 85.3600,
        "departments": ["Botany", "Chemistry", "Geology", "Computer Applications",
                        "Zoology", "Economics"],
        "research_areas": ["Water Quality", "Geology", "Biodiversity", "Rural Economics"],
        "laboratories": [
            {"name": "Geology Laboratory", "focus": "rock and aquifer studies",
             "equipment": ["Petrology microscopes"]},
        ],
        "faculty": [
            _f("Dr. H. Kachhap [demo]", "Geology", ["Geology", "Groundwater"],
               ["water_resources", "environment"], 21, 0),
        ],
        "past_projects": [],
        "incubation_centre": False, "patents": 1, "industry_partners": [],
        "districts_served": ["Hazaribagh", "Koderma", "Chatra"],
        "students": 2900, "data_note": DATA_NOTE,
    },
    {
        "institution_id": "HEI-XISS", "name": "Xavier Institute of Social Service, Ranchi",
        "type": "Autonomous Institute", "district": "Ranchi", "lat": 23.3760, "lon": 85.3300,
        "departments": ["Rural Management", "Social Work", "Human Resource Management",
                        "Sustainable Development"],
        "research_areas": ["Community Engagement", "Rural Management", "Behavioural Science",
                           "Impact Assessment", "Livelihoods"],
        "laboratories": [
            {"name": "Field Action Centre", "focus": "community engagement and field studies",
             "equipment": ["Survey tablets", "Field research kits"]},
        ],
        "faculty": [
            _f("Dr. A. Kujur [demo]", "Rural Management",
               ["Community Engagement", "Impact Assessment", "Behavioural Science"],
               ["rural_livelihood", "water_resources", "women_child_welfare"], 29, 0, "Professor"),
        ],
        "past_projects": [
            {"title": "SHG water committee capacity building", "domain": "water_resources",
             "year": 2023, "outcome": "34 committees trained"},
        ],
        "incubation_centre": False, "patents": 0,
        "industry_partners": ["Tata Steel Foundation"],
        "districts_served": ["Ranchi", "Khunti", "Gumla", "West Singhbhum"],
        "students": 900, "data_note": DATA_NOTE,
    },
    {
        "institution_id": "HEI-SATIVIDISHA",
        "name": "Samrat Ashok Technological Institute (SATI), Vidisha",
        "type": "Autonomous Engineering Institute", "state": "Madhya Pradesh",
        "district": "Vidisha", "lat": 23.5205, "lon": 77.8135,
        "departments": ["Civil Engineering", "Mechanical Engineering",
                        "Electrical Engineering", "Electronics & Communication",
                        "Computer Science & Engineering", "Information Technology",
                        "Chemical Engineering", "Biomedical Engineering",
                        "Petrochemical Engineering", "Applied Sciences",
                        "Management (MBA)", "Computer Applications (MCA)"],
        "research_areas": ["IoT & Sensors", "Data Science", "Machine Learning",
                           "Renewable Energy", "Water Quality", "Environmental Engineering",
                           "Structural Engineering", "Entrepreneurship & Incubation",
                           "Product Design", "Embedded Systems"],
        "laboratories": [
            {"name": "Startup Cell & Incubation Centre",
             "focus": "entrepreneurship, prototyping and student startups",
             "equipment": ["Prototyping lab", "3D printers", "Mentoring space",
                           "Pitch and demo room"]},
            {"name": "IoT & Embedded Systems Laboratory", "focus": "IoT & sensors",
             "equipment": ["Microcontroller benches", "Sensor kits", "Wireless modules"]},
            {"name": "Environmental Engineering Laboratory",
             "focus": "water quality and environmental testing",
             "equipment": ["Water testing kits", "Turbidity meters", "pH/TDS meters"]},
            {"name": "Computer Centre", "focus": "data science and software development",
             "equipment": ["GPU workstations", "Software development lab"]},
        ],
        "faculty": [
            {"name": "Dr. Onkar Tiwari", "designation": "Professor",
             "department": "Startup Cell", "specialisation":
                 ["Entrepreneurship & Incubation", "Innovation Management",
                  "Product Design", "Technology Commercialisation"],
             "research_interests": ["Startup mentoring", "Student innovation",
                                    "Technology transfer"],
             "domains": ["employment", "rural_livelihood", "digital_governance",
                         "education"],
             "publications": 0, "patents": 0, "available_for_mentorship": True,
             "role": "Startup Cell", "source": "provided by the project team"},
            {"name": "Dr. Divya Rishi", "designation": "Professor",
             "department": "Startup Cell", "specialisation":
                 ["Entrepreneurship & Incubation", "Innovation Management",
                  "Business Development", "Startup Mentoring"],
             "research_interests": ["Incubation", "Student startups",
                                    "Industry collaboration"],
             "domains": ["employment", "rural_livelihood", "education",
                         "digital_governance"],
             "publications": 0, "patents": 0, "available_for_mentorship": True,
             "role": "Startup Cell", "source": "provided by the project team"},
        ],
        "past_projects": [],
        "incubation_centre": True, "patents": 0,
        "industry_partners": [],
        "districts_served": ["Vidisha", "Bhopal", "Raisen", "Sagar"],
        "students": 4000,
        "data_note": ("Institution and Startup Cell faculty supplied by the project team. "
                      "Departments and laboratories listed here are indicative and should be "
                      "confirmed by the institute before any real allocation."),
    },
]

PARTNERS: list[dict[str, Any]] = [
    {"partner_id": "PT-JALIOT", "name": "JalSense Technologies (demo startup)",
     "type": "startup", "district": "Ranchi",
     "offers": ["iot_sensors", "data_platform", "field_deployment"],
     "domains": ["water_resources", "agriculture"],
     "districts_active": ["Ranchi", "Khunti", "Gumla"],
     "description": "Low-power groundwater level and handpump usage sensors with LoRaWAN backhaul.",
     "past_projects": ["120 handpump sensors, Ranchi district"],
     "contact": "demo@jalsense.example", "synthetic": True},
    {"partner_id": "PT-SENSORMFG", "name": "Chhotanagpur Sensor Works (demo MSME)",
     "type": "industry", "district": "Bokaro",
     "offers": ["manufacturing", "maintenance_network", "field_deployment"],
     "domains": ["water_resources", "energy", "agriculture"],
     "districts_active": ["Bokaro", "Dhanbad", "Ramgarh", "Ranchi"],
     "description": "Contract manufacturing of ruggedised enclosures and sensor assemblies.",
     "past_projects": ["8,000 units/yr capacity"], "contact": "demo@cnsw.example", "synthetic": True},
    {"partner_id": "PT-CSRSTEEL", "name": "Steel City CSR Foundation (demo CSR)",
     "type": "csr", "district": "East Singhbhum",
     "offers": ["funding", "community_mobilisation", "skilling"],
     "domains": ["water_resources", "education", "healthcare", "rural_livelihood"],
     "districts_active": ["East Singhbhum", "Seraikela-Kharsawan", "West Singhbhum", "Ranchi"],
     "description": "CSR arm funding water, health and education pilots under Sec 135.",
     "past_projects": ["42 village water projects"], "contact": "demo@sccsr.example", "synthetic": True},
    {"partner_id": "PT-NGOGRAM", "name": "Gram Vikas Sahyog (demo NGO)",
     "type": "ngo", "district": "Khunti",
     "offers": ["community_mobilisation", "skilling", "field_deployment"],
     "domains": ["water_resources", "rural_livelihood", "women_child_welfare", "social_inclusion"],
     "districts_active": ["Khunti", "Gumla", "Simdega", "Ranchi"],
     "description": "Works with 180 tribal villages on water committees and SHGs.",
     "past_projects": ["180 village water committees"], "contact": "demo@gvs.example", "synthetic": True},
    {"partner_id": "PT-GEOSPAT", "name": "TerraView Geospatial (demo startup)",
     "type": "startup", "district": "Ranchi",
     "offers": ["remote_sensing", "data_platform"],
     "domains": ["water_resources", "agriculture", "environment", "disaster_resilience"],
     "districts_active": ["Ranchi", "Hazaribagh", "Palamu"],
     "description": "Satellite-based groundwater and cropping analytics.",
     "past_projects": ["Drought mapping for 4 districts"], "contact": "demo@terraview.example",
     "synthetic": True},
    {"partner_id": "PT-SOLARCO", "name": "Jharkhand Solar Solutions (demo MSME)",
     "type": "industry", "district": "Ranchi",
     "offers": ["manufacturing", "field_deployment", "maintenance_network"],
     "domains": ["energy", "water_resources"],
     "districts_active": ["Ranchi", "Lohardaga", "Latehar", "Gumla"],
     "description": "Solar pumping and off-grid power systems with a district technician network.",
     "past_projects": ["600 solar pumps installed"], "contact": "demo@jss.example", "synthetic": True},
    {"partner_id": "PT-HEALTHDEV", "name": "AarogyaKit Devices (demo startup)",
     "type": "startup", "district": "Ranchi",
     "offers": ["medical_devices", "data_platform", "field_deployment"],
     "domains": ["healthcare", "women_child_welfare"],
     "districts_active": ["Ranchi", "Hazaribagh", "Dumka"],
     "description": "Portable diagnostic kits for ASHA and ANM workers.",
     "past_projects": ["Field trial with 90 ASHA workers"], "contact": "demo@aarogyakit.example",
     "synthetic": True},
    {"partner_id": "PT-INCUB", "name": "Jharkhand Innovation Hub (demo incubator)",
     "type": "industry", "district": "Ranchi",
     "offers": ["funding", "skilling", "market_linkage", "data_platform"],
     "domains": ["water_resources", "agriculture", "education", "healthcare", "energy"],
     "districts_active": ["Ranchi"],
     "description": "State incubator offering seed grants, cloud credits and mentoring.",
     "past_projects": ["38 startups incubated"], "contact": "demo@jih.example", "synthetic": True},
    {"partner_id": "PT-AGRIMKT", "name": "KisanSetu Market Linkage (demo startup)",
     "type": "startup", "district": "Hazaribagh",
     "offers": ["market_linkage", "data_platform", "skilling"],
     "domains": ["agriculture", "rural_livelihood", "employment"],
     "districts_active": ["Hazaribagh", "Chatra", "Koderma", "Giridih"],
     "description": "Connects FPOs to buyers with price discovery and logistics.",
     "past_projects": ["22 FPOs onboarded"], "contact": "demo@kisansetu.example", "synthetic": True},
    {"partner_id": "PT-WASTECO", "name": "SwachhCircle Recycling (demo MSME)",
     "type": "industry", "district": "Dhanbad",
     "offers": ["manufacturing", "logistics", "field_deployment", "skilling"],
     "domains": ["waste_management", "environment", "urban_development"],
     "districts_active": ["Dhanbad", "Bokaro", "Ranchi"],
     "description": "Decentralised waste segregation and material recovery units.",
     "past_projects": ["6 ward-level MRF units"], "contact": "demo@swachhcircle.example",
     "synthetic": True},
]

SOLUTION_MEMORY: list[dict[str, Any]] = [
    {"solution_id": "SM-001", "kind": "past_project",
     "title": "IoT handpump monitoring, Ranchi district pilot",
     "source": "State university pilot (demo record)", "year": 2022, "domain": "water_resources",
     "summary": "Vibration sensors on 120 handpumps reported usage and failure to a dashboard. "
                "Detected breakdowns within 24 hours instead of weeks.",
     "technologies": ["Vibration sensor", "GSM", "Dashboard"], "maturity": "field_tested",
     "tags": ["handpump", "iot", "monitoring", "water"], "patented": False,
     "cost_note": "INR 4,200 per unit hardware.", "url": None},
    {"solution_id": "SM-002", "kind": "failure",
     "title": "Solar-powered water ATM network (discontinued)",
     "source": "District administration pilot (demo record)", "year": 2019, "domain": "water_resources",
     "summary": "24 solar water ATMs installed across 12 villages with RFID cards.",
     "technologies": ["RO", "Solar", "RFID"], "maturity": "abandoned",
     "tags": ["water atm", "ro", "solar", "purification"], "patented": False,
     "failure_reason": "Annual maintenance cost of INR 38,000 per unit exceeded what "
                       "Panchayats could pay. 19 of 24 units were non-functional within 20 months.",
     "lesson": "Design to a maintenance budget the Panchayat actually controls. "
               "Ask 'who pays for repairs in year three?' before choosing the technology.",
     "cost_note": "High recurring cost killed it, not the capital cost.", "url": None},
    {"solution_id": "SM-003", "kind": "failure",
     "title": "SMS-based water complaint line (low adoption)",
     "source": "NGO programme (demo record)", "year": 2020, "domain": "water_resources",
     "summary": "Villagers could SMS a shortcode to report a dry handpump.",
     "technologies": ["SMS", "Shortcode"], "maturity": "abandoned",
     "tags": ["sms", "complaint", "reporting", "water"], "patented": False,
     "failure_reason": "Required literate users to type in English. Uptake below 4% of "
                       "households; the women most affected by water collection used it least.",
     "lesson": "If the people worst affected cannot use the channel, the channel has failed. "
               "Voice-first beats text-first in low-literacy contexts.", "url": None},
    {"solution_id": "SM-004", "kind": "past_project",
     "title": "Community-managed rainwater recharge shafts",
     "source": "Watershed programme (demo record)", "year": 2021, "domain": "water_resources",
     "summary": "Recharge shafts near handpumps raised post-monsoon water levels by 1.8 m "
                "on average across 18 sites.",
     "technologies": ["Recharge shaft", "Check dam"], "maturity": "deployed",
     "tags": ["recharge", "groundwater", "rainwater", "watershed"], "patented": False,
     "cost_note": "INR 55,000 per shaft, no recurring cost.", "url": None},
    {"solution_id": "SM-005", "kind": "paper",
     "title": "Predicting seasonal groundwater decline using rainfall and abstraction data",
     "source": "Peer-reviewed journal (demo record)", "year": 2023, "domain": "water_resources",
     "summary": "Gradient boosting model predicted pre-monsoon water table decline with "
                "RMSE 0.7 m using rainfall, land use and pumping hours.",
     "technologies": ["Machine Learning", "Time series"], "maturity": "research",
     "tags": ["prediction", "groundwater", "ml", "forecast"], "patented": False, "url": None},
    {"solution_id": "SM-006", "kind": "patent",
     "title": "Self-cleaning low-maintenance borewell filter assembly",
     "source": "Indian patent (demo record)", "year": 2021, "domain": "water_resources",
     "summary": "Filter assembly claimed to reduce clogging maintenance to once per year.",
     "technologies": ["Mechanical filter"], "maturity": "commercial", "patented": True,
     "tags": ["filter", "borewell", "maintenance"],
     "cost_note": "Licensing required before manufacture.", "url": None},
    {"solution_id": "SM-007", "kind": "startup_product",
     "title": "Commercial LoRaWAN water level sensor (off-the-shelf)",
     "source": "Indian startup catalogue (demo record)", "year": 2024, "domain": "water_resources",
     "summary": "Battery life 3 years, IP68, INR 6,800 per node, existing dealer network.",
     "technologies": ["LoRaWAN", "Pressure sensor"], "maturity": "deployed",
     "tags": ["lorawan", "sensor", "water level"], "patented": False, "url": None},
    {"solution_id": "SM-008", "kind": "scheme",
     "title": "Jal Jeevan Mission - Har Ghar Jal",
     "source": "Government of India", "year": 2019, "domain": "water_resources",
     "summary": "National programme for functional household tap connections in rural India. "
                "Any village solution should converge with JJM rather than duplicate it.",
     "technologies": ["Piped water supply"], "maturity": "scaled",
     "tags": ["scheme", "piped water", "jjm", "convergence"], "patented": False,
     "url": "https://jaljeevanmission.gov.in/"},
    {"solution_id": "SM-009", "kind": "failure",
     "title": "Tablet-based classroom learning rollout (stalled)",
     "source": "District education pilot (demo record)", "year": 2019, "domain": "education",
     "summary": "600 tablets distributed to upper-primary schools with offline content.",
     "technologies": ["Tablets", "Offline content"], "maturity": "abandoned",
     "tags": ["tablet", "edtech", "school", "digital learning"], "patented": False,
     "failure_reason": "No teacher training budget and no charging infrastructure in "
                       "schools with 4-hour daily power. 70% of devices unused after one year.",
     "lesson": "Hardware without teacher capacity and power planning is dead weight. "
               "Budget training and electricity as part of the solution, not as an afterthought.",
     "url": None},
    {"solution_id": "SM-010", "kind": "past_project",
     "title": "ASHA worker mobile diagnostic kit trial",
     "source": "Health department pilot (demo record)", "year": 2023, "domain": "healthcare",
     "summary": "Portable haemoglobin and BP screening kits raised antenatal screening "
                "coverage from 54% to 81% in trial blocks.",
     "technologies": ["Point-of-care devices", "Android app"], "maturity": "field_tested",
     "tags": ["asha", "diagnostics", "maternal health"], "patented": False, "url": None},
    {"solution_id": "SM-011", "kind": "past_project",
     "title": "Solar irrigation pump cooperative model",
     "source": "Agriculture department (demo record)", "year": 2022, "domain": "agriculture",
     "summary": "Shared solar pumps owned by farmer groups cut diesel cost by 62% across "
                "40 farmer groups.",
     "technologies": ["Solar pump", "Cooperative ownership"], "maturity": "deployed",
     "tags": ["solar", "irrigation", "cooperative", "farmers"], "patented": False, "url": None},
    {"solution_id": "SM-012", "kind": "failure",
     "title": "Village waste segregation bins programme (abandoned)",
     "source": "Urban local body (demo record)", "year": 2020, "domain": "waste_management",
     "summary": "Colour-coded bins distributed to 3,000 households in two wards.",
     "technologies": ["Bins", "Awareness campaign"], "maturity": "abandoned",
     "tags": ["waste", "segregation", "bins"], "patented": False,
     "failure_reason": "Segregated waste was mixed again in the single collection vehicle. "
                       "Households stopped segregating within 4 months.",
     "lesson": "Do not fix one link of a chain. If downstream collection is not segregated, "
               "upstream segregation is wasted effort.", "url": None},
    {"solution_id": "SM-013", "kind": "paper",
     "title": "Community ownership and the sustainability of rural water assets",
     "source": "Development studies journal (demo record)", "year": 2020, "domain": "water_resources",
     "summary": "Across 240 villages, assets with a functioning village water committee and "
                "a collected user fee were 3.4x more likely to be working after 5 years.",
     "technologies": [], "maturity": "research",
     "tags": ["community", "ownership", "sustainability", "water committee"],
     "patented": False, "url": None},
]


# ------------------------------------------------------------------ demo cases

def _dt(days_ago: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


DEMO_REPORTS = [
    {"text": "गर्मी के मौसम में हमारे गाँव के चापाकल सूख जाते हैं। औरतों को तीन किलोमीटर दूर "
             "पानी लाने जाना पड़ता है। यह हर साल होता है और इस बार अप्रैल से ही शुरू हो गया।",
     "language": "hi", "district": "Khunti", "block": "Murhu", "panchayat_or_ulb": "Murhu",
     "village_or_ward": "Hutar", "lat": 23.0500, "lon": 85.2700, "days_ago": 26,
     "channel": "voice", "reporter": "Sunita Devi [demo]"},
    {"text": "Our handpump has not been working for two months. We have to take water from "
             "the pond which makes children sick.",
     "language": "en", "district": "Khunti", "block": "Murhu", "panchayat_or_ulb": "Murhu",
     "village_or_ward": "Bariatu", "lat": 23.0700, "lon": 85.2500, "days_ago": 21,
     "channel": "web", "reporter": "Ramesh Munda [demo]"},
    {"text": "बोरवेल का पानी बहुत नीचे चला गया है। पिछले साल 80 फीट पर पानी था, अब 140 फीट पर भी "
             "मुश्किल से आता है। खेती के लिए पानी नहीं बचा।",
     "language": "hi", "district": "Khunti", "block": "Torpa", "panchayat_or_ulb": "Torpa",
     "village_or_ward": "Kudda", "lat": 22.9800, "lon": 85.1900, "days_ago": 18,
     "channel": "csc_assisted", "reporter": "Birsa Oraon [demo]"},
    {"text": "Irrigation has failed this rabi season. The wells dried by January and we lost "
             "most of the wheat crop. About 60 farmer families are affected in our panchayat.",
     "language": "en", "district": "Khunti", "block": "Torpa", "panchayat_or_ulb": "Torpa",
     "village_or_ward": "Jaltanda", "lat": 22.9600, "lon": 85.2100, "days_ago": 14,
     "channel": "web", "reporter": "Farmer Group [demo]"},
    {"text": "Women in our village spend nearly three hours every day fetching water in summer. "
             "Girls miss school because they help carry water.",
     "language": "en", "district": "Khunti", "block": "Murhu", "panchayat_or_ulb": "Murhu",
     "village_or_ward": "Sarwada", "lat": 23.0900, "lon": 85.2300, "days_ago": 9,
     "channel": "web", "reporter": "Anganwadi Worker [demo]"},
    {"text": "गाँव में बिजली सिर्फ 4 घंटे आती है इसलिए पानी का पंप भी नहीं चल पाता।",
     "language": "hi", "district": "Khunti", "block": "Murhu", "panchayat_or_ulb": "Murhu",
     "village_or_ward": "Hutar", "lat": 23.0520, "lon": 85.2680, "days_ago": 7,
     "channel": "voice", "reporter": "Village Committee [demo]"},
    {"text": "The government school in our ward has no functional toilet for girls. Many girls "
             "stop coming to school after class 6.",
     "language": "en", "district": "Ranchi", "block": "Kanke", "panchayat_or_ulb": "Kanke",
     "village_or_ward": "Ward 12", "lat": 23.4200, "lon": 85.3200, "days_ago": 12,
     "channel": "web", "reporter": "Parent Association [demo]"},
    {"text": "Garbage is dumped in the open near our colony and nobody collects it. In the rains "
             "it flows into the drain and mosquitoes breed.",
     "language": "en", "district": "Dhanbad", "block": "Dhanbad Sadar",
     "panchayat_or_ulb": "Dhanbad Municipal Corporation", "village_or_ward": "Ward 24",
     "lat": 23.7950, "lon": 86.4300, "days_ago": 16, "channel": "web",
     "reporter": "Resident Welfare Assoc [demo]"},
]


async def seed_reference_data(force: bool = False) -> dict[str, Any]:
    """Load institutions, partners and the solution/failure library."""
    d = db()
    result: dict[str, Any] = {}

    if force:
        await d.institutions.delete_many({})
        await d.partners.delete_many({})
        await d.solution_memory.delete_many({})

    if await d.institutions.count_documents({}) == 0:
        await d.institutions.insert_many([dict(i) for i in INSTITUTIONS])
    result["institutions"] = await d.institutions.count_documents({})

    if await d.partners.count_documents({}) == 0:
        await d.partners.insert_many([dict(p) for p in PARTNERS])
    result["partners"] = await d.partners.count_documents({})

    if await d.solution_memory.count_documents({}) == 0:
        await d.solution_memory.insert_many([dict(s) for s in SOLUTION_MEMORY])
    result["solution_memory"] = await d.solution_memory.count_documents({})

    return result
