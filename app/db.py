"""MongoDB access layer + the Evidence-to-Impact ledger."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import MONGODB_DB, MONGODB_URI

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def now() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


async def connect() -> AsyncIOMotorDatabase:
    """Connect and verify. Fails fast with a readable message rather than hanging."""
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(
            MONGODB_URI,
            uuidRepresentation="standard",
            serverSelectionTimeoutMS=8000,   # do not hang a serverless request
            connectTimeoutMS=8000,
        )
        _db = _client[MONGODB_DB]
        await _db.command("ping")            # prove the connection really works
        await _ensure_indexes(_db)
    return _db


async def close() -> None:
    global _client, _db
    if _client is not None:
        _client.close()
    _client, _db = None, None


def db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect() first.")
    return _db


async def _ensure_indexes(database: AsyncIOMotorDatabase) -> None:
    await database.challenges.create_index("challenge_id", unique=True)
    await database.challenges.create_index([("location.district", 1), ("status", 1)])
    await database.challenges.create_index("dna.primary_domain")
    await database.challenges.create_index("created_at")
    await database.institutions.create_index("institution_id", unique=True)
    await database.partners.create_index("partner_id", unique=True)
    await database.projects.create_index("project_id", unique=True)
    await database.projects.create_index("challenge_id")
    await database.constellations.create_index("constellation_id", unique=True)
    await database.ledger.create_index([("subject_id", 1), ("at", 1)])
    await database.solution_memory.create_index("solution_id", unique=True)
    await database.feedback.create_index("challenge_id")
    await database.reviews.create_index("at")


# ------------------------------------------------------------------ the ledger

async def ledger(subject_id: str, subject_type: str, event: str,
                 actor: str, actor_role: str, detail: dict[str, Any] | None = None,
                 evidence: list[str] | None = None) -> None:
    """Append-only Evidence-to-Impact Ledger entry. Never updated, never deleted."""
    await db().ledger.insert_one({
        "entry_id": new_id("LG"),
        "subject_id": subject_id,
        "subject_type": subject_type,
        "event": event,
        "actor": actor,
        "actor_role": actor_role,
        "detail": detail or {},
        "evidence": evidence or [],
        "at": now(),
    })


async def ledger_for(subject_id: str) -> list[dict[str, Any]]:
    cur = db().ledger.find({"subject_id": subject_id}, {"_id": 0}).sort("at", 1)
    return await cur.to_list(length=500)


def clean(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip Mongo's _id so documents are JSON-serialisable."""
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc
