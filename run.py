#!/usr/bin/env python3
"""The Sanctuary — Protocol Testing Lab for Agent Economies."""
import argparse
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Load .env file if present (so ANTHROPIC_API_KEY doesn't need to be set manually)
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())


def load_config(path: str) -> dict:
    import yaml
    with open(path) as f:
        return yaml.safe_load(f)


async def run_simulation(config: dict, port: int = 0, restore: bool = False):
    from core.engine import SimulationEngine
    import uvicorn
    import dashboard.app as dash_app
    from dashboard.app import app, set_engine, _CHECKPOINT_PATH
    import json

    engine = SimulationEngine(config)

    if restore and _CHECKPOINT_PATH.exists():
        try:
            checkpoint_data = json.loads(_CHECKPOINT_PATH.read_text())
            engine.restore_from_checkpoint(checkpoint_data)
            engine._initialize_threads()
            print(f"  Resuming from checkpoint at day {engine.day}")
            _CHECKPOINT_PATH.unlink()
        except Exception as e:
            print(f"  Checkpoint restore failed: {e} — starting fresh")

    set_engine(engine)

    dashboard_port = port or config.get("dashboard", {}).get("port", 8090)
    server_config = uvicorn.Config(
        app, host="0.0.0.0", port=dashboard_port,
        log_level="warning", access_log=False,
    )
    server = uvicorn.Server(server_config)
    protocol = config.get("protocol", {}).get("system", "no_protocol")
    print(f"\n  The Sanctuary — {protocol} protocol")
    print(f"  Dashboard: http://localhost:{dashboard_port}\n")

    async def run_engine():
        await asyncio.sleep(1.5)
        task = asyncio.current_task()
        dash_app._engine_task = task
        try:
            await engine.run()
        except RuntimeError as e:
            print(str(e))
            sys.exit(1)

    await asyncio.gather(server.serve(), run_engine())


def main():
    parser = argparse.ArgumentParser(description="The Sanctuary")
    parser.add_argument("--config", "-c", default=str(Path(__file__).parent / "experiments/no_protocol.yaml"))
    parser.add_argument("--port", "-p", type=int, default=0)
    parser.add_argument("--days", "-d", type=int, default=0)
    parser.add_argument("--speed", "-s", type=float, default=0)
    parser.add_argument("--protocol",
                        choices=["no_protocol", "credit_bureau", "peer_ratings",
                                 "anonymity", "mandatory_audit", "custom"])
    parser.add_argument("--restore", action="store_true", help="Resume from checkpoint.json if present")
    args = parser.parse_args()

    if args.protocol:
        args.config = str(Path(__file__).parent / f"experiments/{args.protocol}.yaml")

    config = load_config(args.config)
    config.setdefault("simulation", {})

    if args.days:
        config["simulation"]["max_days"] = args.days
    if args.speed:
        config["simulation"]["tick_interval_seconds"] = args.speed

    config.setdefault("llm", {})
    config["llm"]["enabled"] = True
    config["llm"].setdefault("provider", "anthropic")
    config["llm"].setdefault("model", "claude-haiku-4-5-20251001")

    try:
        asyncio.run(run_simulation(config, args.port, restore=args.restore))
    except KeyboardInterrupt:
        print("\nThe Sanctuary closed.")


if __name__ == "__main__":
    main()
