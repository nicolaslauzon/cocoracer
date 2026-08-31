"""FastAPI + uvicorn live view: the static page and the WebSocket stream.

The server runs in a daemon thread beside the sim loop. On connect the
client gets the static track message once, then a dynamic message every
~150 ms. Client start messages are pushed onto the start queue; the sim
loop drains it and releases the field, so the web thread never mutates
the engine. All pacing lives here, never in the engine.
"""

import asyncio
import json
import queue
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from cocoracer.engine import RaceEngine
from cocoracer.pgm import parse_pgm
from cocoracer.web.protocol import (
    build_dynamic_message,
    build_static_message,
    map_display_image,
    pgm_png_bytes,
)

INDEX_PATH = Path(__file__).with_name("index.html")
SPRITE_PATH = Path(__file__).with_name("f1-car.png")
_DYNAMIC_INTERVAL = 0.15
_START_TIMEOUT = 10.0


def handle_client_message(message: str, start_queue: queue.Queue[None]) -> None:
    """Enqueue a field release if the client message is a start request."""
    try:
        payload = json.loads(message)
    except ValueError:
        return
    if isinstance(payload, dict) and payload.get("type") == "start":
        start_queue.put(None)


def create_app(engine: RaceEngine, start_queue: queue.Queue[None]) -> FastAPI:
    """Build the live view app for one engine."""
    app = FastAPI()
    map_path = map_display_image(engine.config, engine.track.name)
    map_png = pgm_png_bytes(parse_pgm(map_path)) if map_path is not None else None

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(INDEX_PATH)

    @app.get("/f1-car.png")
    def sprite() -> FileResponse:
        return FileResponse(SPRITE_PATH)

    @app.get("/map-image")
    def map_image() -> Response:
        if map_png is None:
            return Response(status_code=404)
        return Response(content=map_png, media_type="image/png")

    @app.websocket("/ws")
    async def stream(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text(build_static_message(engine.track, engine.config))
        try:
            while True:
                try:
                    message = await asyncio.wait_for(
                        websocket.receive_text(), _DYNAMIC_INTERVAL
                    )
                except asyncio.TimeoutError:
                    message = None
                if message is not None:
                    handle_client_message(message, start_queue)
                await websocket.send_text(
                    build_dynamic_message(
                        engine.snapshot(),
                        engine.phase,
                        engine.countdown,
                        engine.last_scans,
                    )
                )
        except WebSocketDisconnect:
            pass

    return app


class WebServer:
    """The live view app, served in a daemon thread."""

    def __init__(
        self,
        engine: RaceEngine,
        start_queue: queue.Queue[None],
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        self._host = host
        self._port = port
        self._server = uvicorn.Server(
            uvicorn.Config(
                create_app(engine, start_queue),
                host=host,
                port=port,
                log_level="warning",
            )
        )
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}"

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        deadline = time.monotonic() + _START_TIMEOUT
        while not self._server.started:
            if not self._thread.is_alive() or time.monotonic() > deadline:
                raise SystemExit(
                    f"web view did not start on {self._host}:{self._port} "
                    "(is the port already in use?)"
                )
            time.sleep(0.01)

    def stop(self) -> None:
        if self._thread is None:
            return
        self._server.should_exit = True
        self._thread.join(timeout=5.0)
        self._thread = None
