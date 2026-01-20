"""
APScheduler with FastAPI Integration
====================================
Demonstrates running APScheduler alongside a FastAPI application.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# Scheduler Configuration
# =============================================================================

# Configure job stores
jobstores = {
    "default": MemoryJobStore(),
}

# Configure executors
executors = {
    "default": AsyncIOExecutor(),  # For async jobs
    "threadpool": ThreadPoolExecutor(max_workers=10),  # For sync jobs
    "processpool": ProcessPoolExecutor(max_workers=3),  # For CPU-intensive jobs
}

# Configure job defaults
job_defaults = {
    "coalesce": True,  # Combine multiple missed runs into one
    "max_instances": 1,  # Prevent overlapping
    "misfire_grace_time": 30,  # Allow 30s late
}

# Create scheduler
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone="UTC",
)


# =============================================================================
# Job Functions
# =============================================================================

async def async_job(name: str = "default"):
    """Async job function."""
    logger.info(f"[{name}] Async job executed at {datetime.now()}")
    await asyncio.sleep(1)  # Simulate async work
    return {"status": "completed", "job": name}


def sync_job(name: str = "default"):
    """Sync job function (runs in thread pool)."""
    import time
    logger.info(f"[{name}] Sync job executed at {datetime.now()}")
    time.sleep(1)  # Simulate blocking work
    return {"status": "completed", "job": name}


async def heartbeat_job():
    """Periodic heartbeat."""
    logger.info(f"Heartbeat: {datetime.now()}")


async def cleanup_job():
    """Periodic cleanup task."""
    logger.info("Running cleanup...")
    # Simulate cleanup work
    await asyncio.sleep(0.5)
    logger.info("Cleanup completed")


# =============================================================================
# FastAPI Application
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - start/stop scheduler."""
    # Startup
    logger.info("Starting scheduler...")
    
    # Add default jobs
    scheduler.add_job(
        heartbeat_job,
        IntervalTrigger(seconds=30),
        id="heartbeat",
        name="Heartbeat",
        replace_existing=True,
    )
    
    scheduler.add_job(
        cleanup_job,
        CronTrigger(minute="*/5"),  # Every 5 minutes
        id="cleanup",
        name="Cleanup Task",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="APScheduler FastAPI Demo",
    lifespan=lifespan,
)


# =============================================================================
# Pydantic Models
# =============================================================================

class JobCreate(BaseModel):
    """Job creation request."""
    job_id: str
    job_type: str = "interval"  # interval, cron, date
    
    # Interval settings
    seconds: Optional[int] = None
    minutes: Optional[int] = None
    hours: Optional[int] = None
    
    # Cron settings
    cron_expression: Optional[str] = None
    
    # Date settings
    run_date: Optional[datetime] = None
    
    # Job arguments
    args: List[str] = []
    kwargs: dict = {}


class JobInfo(BaseModel):
    """Job information response."""
    id: str
    name: str
    next_run_time: Optional[datetime]
    trigger: str


class JobStatus(BaseModel):
    """Scheduler status."""
    running: bool
    job_count: int
    jobs: List[JobInfo]


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "APScheduler FastAPI Demo", "docs": "/docs"}


@app.get("/scheduler/status", response_model=JobStatus)
async def get_scheduler_status():
    """Get scheduler status and list of jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(JobInfo(
            id=job.id,
            name=job.name or job.id,
            next_run_time=job.next_run_time,
            trigger=str(job.trigger),
        ))
    
    return JobStatus(
        running=scheduler.running,
        job_count=len(jobs),
        jobs=jobs,
    )


@app.get("/scheduler/jobs")
async def list_jobs():
    """List all scheduled jobs."""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
            "func": job.func.__name__,
        })
    return {"jobs": jobs}


@app.get("/scheduler/jobs/{job_id}")
async def get_job(job_id: str):
    """Get details of a specific job."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "name": job.name,
        "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        "trigger": str(job.trigger),
        "func": job.func.__name__,
        "args": job.args,
        "kwargs": job.kwargs,
    }


@app.post("/scheduler/jobs")
async def create_job(job_data: JobCreate):
    """Create a new scheduled job."""
    # Determine trigger
    if job_data.job_type == "interval":
        trigger = IntervalTrigger(
            seconds=job_data.seconds or 0,
            minutes=job_data.minutes or 0,
            hours=job_data.hours or 0,
        )
    elif job_data.job_type == "cron":
        if job_data.cron_expression:
            trigger = CronTrigger.from_crontab(job_data.cron_expression)
        else:
            raise HTTPException(400, "cron_expression required for cron jobs")
    elif job_data.job_type == "date":
        if job_data.run_date:
            trigger = DateTrigger(run_date=job_data.run_date)
        else:
            raise HTTPException(400, "run_date required for date jobs")
    else:
        raise HTTPException(400, f"Unknown job type: {job_data.job_type}")
    
    # Add job
    try:
        job = scheduler.add_job(
            async_job,
            trigger=trigger,
            id=job_data.job_id,
            name=job_data.job_id,
            args=job_data.args or ("custom",),
            kwargs=job_data.kwargs,
            replace_existing=True,
        )
        
        return {
            "message": "Job created",
            "job_id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@app.delete("/scheduler/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a scheduled job."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    scheduler.remove_job(job_id)
    return {"message": "Job deleted", "job_id": job_id}


@app.post("/scheduler/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a scheduled job."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    scheduler.pause_job(job_id)
    return {"message": "Job paused", "job_id": job_id}


@app.post("/scheduler/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume a paused job."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    scheduler.resume_job(job_id)
    return {"message": "Job resumed", "job_id": job_id}


@app.post("/scheduler/jobs/{job_id}/run")
async def run_job_now(job_id: str):
    """Run a job immediately (in addition to its schedule)."""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Schedule to run now
    scheduler.modify_job(job_id, next_run_time=datetime.now())
    return {"message": "Job scheduled to run now", "job_id": job_id}


@app.post("/scheduler/pause")
async def pause_scheduler():
    """Pause all jobs."""
    scheduler.pause()
    return {"message": "Scheduler paused"}


@app.post("/scheduler/resume")
async def resume_scheduler():
    """Resume all jobs."""
    scheduler.resume()
    return {"message": "Scheduler resumed"}


# =============================================================================
# Schedule Ad-hoc Jobs
# =============================================================================

@app.post("/tasks/schedule")
async def schedule_task(
    delay_seconds: int = 5,
    task_name: str = "adhoc_task"
):
    """Schedule a one-time task to run after a delay."""
    run_time = datetime.now() + timedelta(seconds=delay_seconds)
    
    job = scheduler.add_job(
        async_job,
        trigger=DateTrigger(run_date=run_time),
        id=f"{task_name}_{datetime.now().timestamp()}",
        args=(task_name,),
    )
    
    return {
        "message": "Task scheduled",
        "job_id": job.id,
        "run_time": run_time.isoformat(),
    }


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
