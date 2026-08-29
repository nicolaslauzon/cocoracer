"""Tests for the live view server: the start-message path and the gate."""

import json
import queue
import socket
import threading
import time

import numpy as np
import websockets.sync.client

from cocoracer.cli import _drain_starts
from cocoracer.config import Config
from cocoracer.controller import Controller
from cocoracer.engine import RaceEngine
from cocoracer.track import Track
from cocoracer.web.server import WebServer, handle_client_message


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Sitter(Controller):
    """Sits on the grid: zero speed, zero steer."""

    def step(
        self,
        x: float,
        y: float,
        yaw: float,
        speed: float,
        steering_angle: float,
        laser_scan: np.ndarray,
    ) -> tuple[float, float]:
        return 0.0, 0.0


def test_start_message_enqueues_a_release() -> None:
    q: queue.Queue[None] = queue.Queue()
    handle_client_message('{"type": "start"}', q)
    assert q.qsize() == 1


def test_non_start_and_garbage_messages_do_not_enqueue() -> None:
    q: queue.Queue[None] = queue.Queue()
    for message in ('{"type": "ping"}', "not json", "[1, 2]", "{}"):
        handle_client_message(message, q)
    assert q.empty()


def _sim_loop(
    engine: RaceEngine, start_queue: queue.Queue[None], stop: threading.Event
) -> None:
    """The production sim loop body, without the wall-clock pacing."""
    while not stop.is_set():
        _drain_starts(start_queue, engine)
        engine.tick()
        time.sleep(0.025)


def test_live_run_waits_for_start_message(stadium: Track, config: Config) -> None:
    engine = RaceEngine(stadium, config, [Sitter()], ["sitter"], auto_start=False)
    start_queue: queue.Queue[None] = queue.Queue()
    port = _free_port()
    server = WebServer(engine, start_queue=start_queue, port=port)
    server.start()
    stop = threading.Event()
    loop = threading.Thread(
        target=_sim_loop, args=(engine, start_queue, stop), daemon=True
    )
    loop_started = False
    try:
        with websockets.sync.client.connect(f"ws://127.0.0.1:{port}/ws") as ws:
            static = json.loads(ws.recv())
            assert static["type"] == "static"
            first = json.loads(ws.recv())
            # The field waits and the sim clock is frozen at zero.
            assert first["type"] == "dynamic"
            assert first["phase"] == "waiting"
            assert first["time"] == 0.0
            # The web thread only enqueues; the engine stays waiting...
            ws.send(json.dumps({"type": "start"}))
            deadline = time.monotonic() + 5.0
            while start_queue.empty() and time.monotonic() < deadline:
                time.sleep(0.005)
            assert not start_queue.empty()
            assert engine.phase == "waiting"
            # ...until the sim thread drains the queue and releases it.
            loop.start()
            loop_started = True
            deadline = time.monotonic() + 5.0
            while engine.phase == "waiting" and time.monotonic() < deadline:
                time.sleep(0.005)
            assert engine.phase == "racing"
            assert engine.time > 0.0
            # The next fresh dynamic message carries the release to the client.
            deadline = time.monotonic() + 5.0
            released: dict = {}
            while time.monotonic() < deadline:
                released = json.loads(ws.recv())
                if released["phase"] == "racing":
                    break
            assert released["phase"] == "racing"
    finally:
        stop.set()
        if loop_started:
            loop.join(timeout=5.0)
        server.stop()
