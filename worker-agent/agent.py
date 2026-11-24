#!/usr/bin/env python3
"""AlphaAI worker heartbeat agent.

This first agent reports hardware only. It does not download models, execute jobs,
open inbound ports, or accept remote commands.
"""
from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

VERSION = "0.1.0"
STOP = False


def available_ram_mb() -> tuple[int, int]:
    """Return total and available RAM, using psutil when installed."""
    try:
        import psutil  # type: ignore[import-not-found]

        memory = psutil.virtual_memory()
        return int(memory.total // (1024 * 1024)), int(memory.available // (1024 * 1024))
    except ImportError:
        pass

    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        values: dict[str, int] = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, _, rest = line.partition(":")
            if key in {"MemTotal", "MemAvailable"}:
                values[key] = int(rest.strip().split()[0])
        total = values.get("MemTotal", 0) // 1024
        available = values.get("MemAvailable", 0) // 1024
        if total:
            return total, min(available, total)
    return 0, 0


def detect_gpus() -> list[dict]:
    """Read NVIDIA inventory if nvidia-smi is present; never installs drivers."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []

    gpus = []
    for line in result.stdout.splitlines()[:32]:
        name, separator, memory = line.rpartition(",")
        if not separator:
            continue
        try:
            vram_mb = int(memory.strip())
        except ValueError:
            continue
        gpus.append(
            {
                "name": name.strip()[:120],
                "vendor": "NVIDIA",
                "vram_mb": max(0, min(vram_mb, 2_000_000)),
            }
        )
    return gpus


def build_report() -> dict:
    total_ram, available_ram = available_ram_mb()
    if total_ram <= 0:
        raise RuntimeError(
            "Could not detect RAM. Install psutil (python -m pip install psutil) "
            "or run this agent on Linux with /proc/meminfo."
        )
    return {
        "agent_version": VERSION,
        "os": platform.platform()[:80],
        "architecture": platform.machine()[:40] or "unknown",
        "cpu_model": platform.processor()[:160] or None,
        "cpu_logical_cores": max(1, os.cpu_count() or 1),
        "ram_total_mb": total_ram,
        "ram_available_mb": available_ram,
        "gpus": detect_gpus(),
    }


def send_heartbeat(api_base_url: str, token: str) -> None:
    url = api_base_url.rstrip("/") + "/v1/workers/heartbeat"
    payload = json.dumps(build_report()).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "User-Agent": "AlphaAI-Worker/" + VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise RuntimeError("Heartbeat rejected with HTTP " + str(response.status))
            data = json.loads(response.read().decode("utf-8"))
            print("Heartbeat accepted:", data.get("worker_id", "unknown"))
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise RuntimeError("Worker credential rejected or revoked; stopping agent.") from exc
        raise RuntimeError("Heartbeat failed with HTTP " + str(exc.code)) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError("Could not reach AlphaAI API: " + str(exc.reason)) from exc


def stop_agent(_signum, _frame) -> None:
    global STOP
    STOP = True


def main() -> int:
    api_base_url = os.environ.get("ALPHAAI_API_URL", "").strip()
    token = os.environ.get("ALPHAAI_WORKER_TOKEN", "").strip()
    interval = int(os.environ.get("ALPHAAI_HEARTBEAT_SECONDS", "30"))

    if not api_base_url.startswith("https://") and not (
        api_base_url.startswith("http://") and os.environ.get("ALPHAAI_ALLOW_INSECURE_HTTP") == "1"
    ):
        print("Set ALPHAAI_API_URL to an HTTPS URL. Plain HTTP requires explicit local-only opt-in.", file=sys.stderr)
        return 2
    if not token.startswith("aai_worker_"):
        print("Set ALPHAAI_WORKER_TOKEN to the one-time worker credential.", file=sys.stderr)
        return 2
    if not 15 <= interval <= 300:
        print("ALPHAAI_HEARTBEAT_SECONDS must be between 15 and 300.", file=sys.stderr)
        return 2

    signal.signal(signal.SIGINT, stop_agent)
    signal.signal(signal.SIGTERM, stop_agent)
    print("AlphaAI worker agent", VERSION, "- hardware reporting only")
    while not STOP:
        try:
            send_heartbeat(api_base_url, token)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            if "credential rejected or revoked" in str(exc):
                return 3
        for _ in range(interval):
            if STOP:
                break
            time.sleep(1)
    print("Worker agent stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
