"""FastAPI dashboard for The Sanctuary widget economy."""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file if present
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

app = FastAPI(title="The Sanctuary")

_engine = None
_connected_ws: Set[WebSocket] = set()
_engine_task = None


def set_engine(engine):
    global _engine
    _engine = engine
    engine._dashboard_broadcast = _broadcast_to_all


async def _broadcast_to_all(data: dict):
    global _connected_ws
    if not _connected_ws:
        return
    msg = json.dumps(data)
    dead = set()
    for ws in _connected_ws:
        try:
            await ws.send_text(msg)
        except Exception:
            dead.add(ws)
    _connected_ws -= dead


@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    return HTMLResponse("<h1>Loading...</h1>")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _connected_ws.add(websocket)
    if _engine:
        try:
            await websocket.send_text(json.dumps({"type": "init", **_engine._build_state()}))
        except Exception:
            pass
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            await _handle_ws_message(msg, websocket)
    except WebSocketDisconnect:
        _connected_ws.discard(websocket)
    except Exception:
        _connected_ws.discard(websocket)


async def _handle_ws_message(msg: dict, ws: WebSocket):
    cmd = msg.get("cmd")
    if not _engine:
        return
    if cmd == "pause":
        _engine.pause()
    elif cmd == "resume":
        _engine.resume()
    elif cmd == "set_speed":
        _engine.set_tick_speed(float(msg.get("seconds") or 1))
    elif cmd == "fast_forward":
        _engine.set_fast_forward(bool(msg.get("enabled", True)))
    elif cmd == "get_agent":
        agent_id = msg.get("agent_id")
        if agent_id and agent_id in _engine.agents:
            agent = _engine.agents[agent_id]
            try:
                await ws.send_text(json.dumps({
                    "type": "agent_detail",
                    "agent": agent.to_dict(),
                    "transactions": [t.to_dict() for t in _engine.transactions
                                     if t.seller_id == agent_id or t.buyer_id == agent_id],
                    "messages": [m.to_dict() for m in _engine.messages
                                 if m.sender_id == agent_id or m.recipient_id == agent_id
                                 or m.is_public][-50:],
                    "reasoning_log": agent.reasoning_log[-50:],
                    "inventory": [w.to_dict() for w in getattr(agent, "inventory", [])
                                  if not w.is_sold][:30],
                    "offers": [p.to_dict() for p in getattr(_engine, "_pending_deals", [])
                               if p.proposer_id == agent_id or p.counterparty_id == agent_id],
                }))
            except Exception:
                pass


@app.get("/api/state")
async def get_state():
    if not _engine:
        return JSONResponse({"error": "no engine"}, status_code=503)
    return JSONResponse(_engine._build_state())


@app.get("/api/messages")
async def get_messages(limit: int = 100):
    if not _engine:
        return JSONResponse({"messages": []})
    msgs = [m.to_dict() for m in _engine.messages[-limit:]]
    return JSONResponse({"messages": msgs})


@app.get("/api/analytics")
async def get_analytics():
    if not _engine:
        return JSONResponse({})
    return JSONResponse(_engine.analytics.to_dict())


@app.get("/api/narratives")
async def get_narratives():
    if not _engine:
        return JSONResponse({"narratives": []})
    return JSONResponse({"narratives": _engine.narratives})


@app.get("/api/runs")
async def get_runs():
    from storage.store import RunStore
    store = RunStore()
    return JSONResponse({"runs": store.list_runs()})


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    from storage.store import RunStore
    store = RunStore()
    data = store.load_run(run_id)
    if not data:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(data)


@app.post("/api/start")
async def start_simulation(body: dict = None):
    global _engine, _engine_task
    body = body or {}
    protocol = body.get("protocol", "no_protocol")
    max_days = int(body.get("max_days", 60))
    speed = float(body.get("speed", 1.0))
    custom_description = body.get("custom_description", "")

    import yaml
    config_path = f"experiments/{protocol}.yaml"
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        config = {
            "simulation": {"max_days": max_days, "tick_interval_seconds": speed},
            "protocol": {"system": protocol},
            "llm": {"provider": "ollama", "model": "qwen2.5:32b", "base_url": "http://localhost:11434", "temperature": 0.7, "timeout": 300},
        }

    config["simulation"]["max_days"] = max_days
    config["simulation"]["tick_interval_seconds"] = speed
    if protocol == "custom" and custom_description:
        config["protocol"]["description"] = custom_description

    # Allow overriding model from the UI
    model_name = body.get("model_name", "").strip()
    if model_name:
        config["llm"]["model"] = model_name

    if _engine_task and not _engine_task.done():
        _engine_task.cancel()
        try:
            await _engine_task
        except asyncio.CancelledError:
            pass

    from core.engine import SimulationEngine
    new_engine = SimulationEngine(config)

    # Restore from checkpoint if one exists for this protocol
    restore = body.get("restore_checkpoint", False)
    if restore and _CHECKPOINT_PATH.exists():
        try:
            checkpoint_data = json.loads(_CHECKPOINT_PATH.read_text())
            new_engine.restore_from_checkpoint(checkpoint_data)
            new_engine._initialize_threads()
            print(f"  Restored from checkpoint at day {new_engine.day}")
            _CHECKPOINT_PATH.unlink()  # consume checkpoint so next start is fresh
        except Exception as e:
            print(f"  Checkpoint restore failed: {e} — starting fresh")

    set_engine(new_engine)

    loop = asyncio.get_event_loop()
    _engine_task = loop.create_task(_run_engine_task(new_engine))

    await _broadcast_to_all({"type": "started", "protocol": protocol})
    return JSONResponse({"ok": True, "protocol": protocol, "resumed_from_day": new_engine.day})


async def _run_engine_task(engine):
    try:
        await engine.run()
    except RuntimeError as e:
        print(str(e))
    except Exception as e:
        print(f"Engine error: {e}")
        import traceback; traceback.print_exc()


_CHECKPOINT_PATH = Path(__file__).parent.parent / "checkpoint.json"


@app.post("/api/checkpoint")
async def save_checkpoint():
    if not _engine:
        return JSONResponse({"error": "no engine"}, status_code=503)
    data = _engine.to_checkpoint()
    _CHECKPOINT_PATH.write_text(json.dumps(data))
    return JSONResponse({"ok": True, "day": data["checkpoint_day"], "path": str(_CHECKPOINT_PATH)})


@app.post("/api/restart")
async def restart(body: dict = None):
    global _engine, _engine_task
    body = body or {}
    protocol = body.get("protocol", _engine.protocol_name if _engine else "no_protocol")

    if _engine_task and not _engine_task.done():
        _engine_task.cancel()
        try:
            await _engine_task
        except asyncio.CancelledError:
            pass

    return await start_simulation(body)
