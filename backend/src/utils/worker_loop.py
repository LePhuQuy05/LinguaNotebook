"""Persistent event loop for worker processes.

The async engine's connection pool binds to the loop that was running
when its connections were created. Creating a loop per task call and
closing it afterwards leaves pooled asyncpg connections pointing at a
dead loop — the next task crashes with "proactor.send on None" on
Windows (proactor_events.py `self._loop._proactor.send`).

One loop, created once per process, never closed. Every worker module
(parse, embed, lesson) shares this single loop through this helper —
the modules all run in the same process and must share one loop anyway.
"""

import asyncio

_worker_loop = None


def get_event_loop() -> asyncio.AbstractEventLoop:
    global _worker_loop
    if _worker_loop is None:
        _worker_loop = asyncio.new_event_loop()
    return _worker_loop
