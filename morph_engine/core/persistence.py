"""Atomic versioned JSON snapshots for single-writer, trusted local use."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .msv import AuditLog, MinimalStateVector, canonical, CHANNELS, finite
from .zygote import MorphZygote


def state(agent):
    return {"version": 1, "msv": asdict(agent.msv), "style": agent.renderer.style,
            "growth_enabled": agent.growth_enabled,
            "organs": {k: v.snapshot() for k, v in agent.mounted_organs.items()},
            "audit": agent.audit.events}


def save(agent, path):
    path = Path(path)
    body = state(agent)
    envelope = {"state": body, "sha256": hashlib.sha256(canonical(body)).hexdigest()}
    encoded = canonical(envelope)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def load(path):
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    body = envelope["state"]
    if hashlib.sha256(canonical(body)).hexdigest() != envelope["sha256"]:
        raise ValueError("Snapshot checksum mismatch")
    if body["version"] != 1:
        raise ValueError("Unsupported snapshot version")
    audit = AuditLog(body["audit"])
    msv = MinimalStateVector(**body["msv"])
    if set(msv.gradients) != set(CHANNELS):
        raise ValueError("Invalid gradient channels")
    for field in ("reserve", "reserve_cap", "budget_per_turn", "now"):
        finite(getattr(msv, field), field)
    if msv.reserve > msv.reserve_cap:
        raise ValueError("Reserve exceeds cap")
    for value in msv.gradients.values():
        finite(value, "gradient")
    for value in (msv.current_turn, msv.session):
        if type(value) is not int or value < 0:
            raise ValueError("Invalid time counters")
    agent = MorphZygote(msv.seed_id, body["style"], body["growth_enabled"])
    if set(body["organs"]) - set(agent.ame.by_id):
        raise ValueError("Snapshot requests unknown organ")
    agent.msv, agent.audit = msv, audit
    for organ_id, snapshot in body["organs"].items():
        if not 0 <= snapshot["born"] <= snapshot["last_used"] <= msv.current_turn:
            raise ValueError("Invalid organ age")
        agent.mounted_organs[organ_id] = agent.ame.instantiate(organ_id, msv.current_turn, snapshot)
    return agent
