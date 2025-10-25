"""WebSocket endpoint helpers for fundraise live updates."""

from __future__ import annotations

from fastapi import WebSocket, WebSocketDisconnect

from .service import FundraiseTracker


async def handle_fundraise_websocket(websocket: WebSocket, tracker: FundraiseTracker) -> None:
    await websocket.accept()
    queue = tracker.subscribe()
    try:
        await websocket.send_json(await tracker.status())
        while True:
            snapshot = await queue.get()
            await websocket.send_json(snapshot)
    except WebSocketDisconnect:
        pass
    finally:
        tracker.unsubscribe(queue)


__all__ = ["handle_fundraise_websocket"]
