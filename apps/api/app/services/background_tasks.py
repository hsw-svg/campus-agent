"""Background task manager for long-running agent operations."""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

# Agent IDs that qualify as long-running background tasks.
LONG_RUNNING_AGENTS = frozenset({"course_iteration"})


def is_long_running_agent(agent_id: str | None) -> bool:
    """Return True when the agent should be dispatched as a background task."""
    return agent_id is not None and agent_id in LONG_RUNNING_AGENTS


class BackgroundTaskManager:
    """Manage asyncio tasks keyed by AgentRun id.

    Each submitted coroutine runs as a detached ``asyncio.Task``.  The manager
    keeps a weak-feeling mapping so callers can query or cancel a task by its
    run id; completed tasks self-evict via a done callback.
    """

    def __init__(self) -> None:
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    def submit(self, run_id: UUID, coro) -> asyncio.Task[None]:
        """Schedule *coro* as a background task keyed by *run_id*."""
        task = asyncio.create_task(coro)
        self._tasks[run_id] = task
        task.add_done_callback(lambda _t, _rid=run_id: self._tasks.pop(_rid, None))
        logger.info("Background task submitted for run %s", run_id)
        return task

    def get(self, run_id: UUID) -> asyncio.Task[None] | None:
        return self._tasks.get(run_id)

    def cancel(self, run_id: UUID) -> bool:
        task = self._tasks.get(run_id)
        if task is not None and not task.done():
            task.cancel()
            logger.info("Background task cancelled for run %s", run_id)
            return True
        return False
