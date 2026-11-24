#!/usr/bin/env python3
"""Opt-in local NVIDIA GPU benchmark for AlphaAI worker machines.

This script runs only when manually invoked with --run. It never contacts AlphaAI,
downloads model weights, installs packages, or executes remote work.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone


def gpu_inventory() -> list[dict]:
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    devices = []
    for line in result.stdout.splitlines()[:8]:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3:
            continue
        try:
            memory_mb = int(parts[1])
        except ValueError:
            continue
        devices.append(
            {
                "name": parts[0][:120],
                "vram_mb": max(0, min(memory_mb, 2_000_000)),
                "driver_version": parts[2][:40],
            }
        )
    return devices


def run_benchmark(matrix_size: int = 1024, repetitions: int = 20) -> dict:
    if not 256 <= matrix_size <= 2048:
        raise ValueError("matrix_size must be between 256 and 2048")
    if not 1 <= repetitions <= 100:
        raise ValueError("repetitions must be between 1 and 100")

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is not installed. Install a CUDA-enabled PyTorch build "
            "that matches your NVIDIA driver before running this benchmark."
        ) from exc

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; no GPU benchmark was executed.")

    device = torch.device("cuda:0")
    properties = torch.cuda.get_device_properties(device)
    a = torch.randn((matrix_size, matrix_size), device=device, dtype=torch.float32)
    b = torch.randn((matrix_size, matrix_size), device=device, dtype=torch.float32)

    # Warm-up kernels are excluded from the timed section.
    for _ in range(3):
        torch.mm(a, b)
    torch.cuda.synchronize()

    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(repetitions):
        torch.mm(a, b)
    end.record()
    torch.cuda.synchronize()

    total_ms = float(start.elapsed_time(end))
    average_ms = total_ms / repetitions
    operations = 2 * (matrix_size ** 3)
    tflops = (operations / (average_ms / 1000)) / 1_000_000_000_000

    return {
        "benchmark": "alphaai-fp32-matmul-v1",
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "device_name": str(properties.name)[:120],
        "device_vram_bytes": int(properties.total_memory),
        "matrix_size": matrix_size,
        "repetitions": repetitions,
        "average_latency_ms": round(average_ms, 4),
        "estimated_fp32_tflops": round(tflops, 4),
        "measurement": "single-GPU FP32 matrix multiplication; not a model-serving score",
        "torch_version": str(torch.__version__)[:40],
        "cuda_version": str(torch.version.cuda or "unknown")[:40],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="explicitly run the GPU benchmark")
    parser.add_argument("--matrix-size", type=int, default=1024)
    parser.add_argument("--repetitions", type=int, default=20)
    args = parser.parse_args()

    if not args.run:
        parser.error("No benchmark was run. Pass --run to explicitly authorize local GPU load.")

    try:
        inventory = gpu_inventory()
        if not inventory:
            raise RuntimeError("No NVIDIA GPU inventory was detected.")
        result = run_benchmark(args.matrix_size, args.repetitions)
        result["inventory"] = inventory[0]
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, subprocess.SubprocessError, RuntimeError, ValueError) as exc:
        print("Benchmark unavailable:", str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
