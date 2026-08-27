"""FastAPI + uvicorn live view: the static page and the WebSocket stream.

The server runs in a daemon thread beside the sim loop. On connect the
client gets the static track message once, then a dynamic message every
~150 ms. The web thread only reads engine state; all pacing lives here,
never in the engine.
"""

import asyncio
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from cocoracer.engine import RaceEngine
from cocoracer.web.protocol import build_dynamic_message, build_static_message

INDEX_PATH = Path(__file__).with_name("index.html")
_DYNAMIC_INTERVAL = 0.15
_START_TIMEOUT = 10.0


def create_app(engine: RaceEngine) -> FastAPI:
    """Build the live view app for one engine."""
    app = FastAPI()

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(INDEX_PATH)

    @app.websocket("/ws")
    async def stream(websocket: WebSocket) -> None:
        await websocket.accept()
        await websocket.send_text(build_static_message(engine.track))
        try:
            while True:
                await websocket.send_text(
                    build_dynamic_message(
                        engine.snapshot(),
                        engine.phase,
                        engine.countdown,
                        engine.last_scans,
                    )
                )
                await asyncio.sleep(_DYNAMIC_INTERVAL)
        except WebSocketDisconnect:
            pass

    return app


class WebServer:
    """The live view app, served in a daemon thread."""

    def __init__(
        self, engine: RaceEngine, host: str = "127.0.0.1", port: int = 8000
    ) -> None:
        self._host = host
        self._port = port
        self._server = uvicorn.Server(
            uvicorn.Config(
                create_app(engine), host=host, port=port, log_level="warning"
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
