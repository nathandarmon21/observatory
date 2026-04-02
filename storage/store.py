"""Run storage for The Sanctuary."""
from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path

RUNS_DIR = Path(__file__).parent.parent / "runs"


class RunStore:
    def __init__(self):
        RUNS_DIR.mkdir(exist_ok=True)

    def save_run(self, run_id: str, summary: dict,
                 transactions: list, messages: list, narratives: list):
        run_dir = RUNS_DIR / run_id
        run_dir.mkdir(exist_ok=True)

        with open(run_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        with open(run_dir / "transactions.jsonl", "w") as f:
            for tx in transactions:
                f.write(json.dumps(tx.to_dict(), default=str) + "\n")

        with open(run_dir / "messages.jsonl", "w") as f:
            for msg in messages:
                d = msg.to_dict() if hasattr(msg, "to_dict") else msg
                f.write(json.dumps(d, default=str) + "\n")

        with open(run_dir / "narratives.jsonl", "w") as f:
            for n in narratives:
                f.write(json.dumps(n, default=str) + "\n")

    def list_runs(self) -> list:
        runs = []
        for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
            summary_path = run_dir / "summary.json"
            if summary_path.exists():
                with open(summary_path) as f:
                    s = json.load(f)
                runs.append({
                    "run_id": run_dir.name,
                    "protocol": s.get("protocol", "?"),
                    "final_day": s.get("final_day"),
                    "total_transactions": s.get("total_transactions"),
                    "misrepresentation_rate": s.get("misrepresentation_rate"),
                    "market_health_score": s.get("market_health", {}).get("score"),
                    "completed_at": s.get("completed_at"),
                    "started_at": s.get("started_at"),
                })
        return runs[:20]

    def load_run(self, run_id: str) -> dict:
        run_dir = RUNS_DIR / run_id
        if not run_dir.exists():
            return {}
        result = {}
        summary_path = run_dir / "summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                result["summary"] = json.load(f)
        txns = []
        txn_path = run_dir / "transactions.jsonl"
        if txn_path.exists():
            with open(txn_path) as f:
                for line in f:
                    txns.append(json.loads(line))
        result["transactions"] = txns
        narratives = []
        narr_path = run_dir / "narratives.jsonl"
        if narr_path.exists():
            with open(narr_path) as f:
                for line in f:
                    narratives.append(json.loads(line))
        result["narratives"] = narratives
        return result
