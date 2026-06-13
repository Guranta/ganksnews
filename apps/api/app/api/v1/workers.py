from fastapi import APIRouter

from app.schemas.workers import WorkerResponse, WorkerSummary
from app.workers.heartbeat import get_all_workers

router = APIRouter()


@router.get("", response_model=list[WorkerResponse])
async def list_workers():
    workers = await get_all_workers()
    return workers


@router.get("/summary", response_model=list[WorkerSummary])
async def workers_summary():
    workers = await get_all_workers()
    by_type: dict[str, list] = {}
    for w in workers:
        by_type.setdefault(w.worker_type, []).append(w)

    summaries = []
    for worker_type, type_workers in by_type.items():
        running = sum(1 for w in type_workers if w.status == "running")
        stopped = sum(1 for w in type_workers if w.status == "stopped")
        error = sum(1 for w in type_workers if w.status == "error")
        summaries.append(WorkerSummary(
            worker_type=worker_type,
            running=running,
            stopped=stopped,
            error=error,
            total=len(type_workers),
            workers=type_workers,
        ))
    return summaries
