"""
Simple job store backed by Redis.
Jobs have status: pending | running | done | failed
"""
import json
import redis
from .config import settings

_redis: redis.Redis | None = None
JOB_TTL = 3600  # 1 hour


def _r() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def create_job(job_id: str, meta: dict | None = None) -> dict:
    job = {"id": job_id, "status": "pending", "result": None, "error": None, "meta": meta or {}}
    _r().setex(f"job:{job_id}", JOB_TTL, json.dumps(job))
    return job


def set_running(job_id: str):
    job = get_job(job_id)
    if job:
        job["status"] = "running"
        _r().setex(f"job:{job_id}", JOB_TTL, json.dumps(job))


def set_done(job_id: str, result: dict):
    job = get_job(job_id)
    if job:
        job["status"] = "done"
        job["result"] = result
        _r().setex(f"job:{job_id}", JOB_TTL, json.dumps(job))


def set_failed(job_id: str, error: str):
    job = get_job(job_id)
    if job:
        job["status"] = "failed"
        job["error"] = error
        _r().setex(f"job:{job_id}", JOB_TTL, json.dumps(job))


def get_job(job_id: str) -> dict | None:
    raw = _r().get(f"job:{job_id}")
    if raw:
        return json.loads(raw)
    return None
