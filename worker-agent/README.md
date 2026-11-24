# AlphaAI Worker Agent (hardware reporting only)

This agent sends periodic hardware inventory heartbeats to an AlphaAI API instance.

## Security scope

The current agent:
- reports OS, CPU logical core count, RAM and NVIDIA GPU name/VRAM when nvidia-smi is available;
- authenticates with a one-time worker token created by a platform administrator;
- requires HTTPS by default;
- stops when the server rejects or revokes the credential;
- does not download model weights, execute remote jobs, open inbound ports, install drivers, or accept commands.

Do not run it on a machine unless you own it or have explicit authorization to report its hardware inventory.

## Setup

1. In the AlphaAI Control Center, register a worker and copy the one-time token into a secure local secret store.
2. On the worker machine, install Python 3.10 or later.
3. Configure environment variables:

   - ALPHAAI_API_URL: HTTPS base URL of the deployed AlphaAI API (no trailing slash required).
   - ALPHAAI_WORKER_TOKEN: the worker token shown once at creation.
   - ALPHAAI_HEARTBEAT_SECONDS: optional interval from 15 to 300 seconds; defaults to 30.

4. Run:

   ```bash
   python worker-agent/agent.py
   ```

On Linux, RAM is detected from /proc/meminfo. On other platforms, install psutil in the worker's Python environment. NVIDIA GPU discovery requires the vendor-provided nvidia-smi command to be installed and available on PATH.

For local development only, plain HTTP can be explicitly enabled with ALPHAAI_ALLOW_INSECURE_HTTP=1. Never use that option on a public network.

## Current limitations

This is a heartbeat/inventory agent only. The worker is not yet eligible for inference or training workloads. Workload execution must wait for signed job envelopes, mutual authentication, isolation, resource limits, artifact verification, cancellation, telemetry, and a security review.

## Automated tests

Run the agent's isolated unit tests without a running AlphaAI server:

```bash
python -m unittest -v
```

The tests mock the NVIDIA utility and HTTP endpoint; they do not send network requests or require a GPU.

## Optional local NVIDIA benchmark

The opt-in `gpu_benchmark.py` script runs a bounded, single-GPU FP32 matrix multiplication benchmark. It is a basic hardware signal, not a model-serving performance score.

Requirements: NVIDIA GPU, working NVIDIA driver and `nvidia-smi`, plus a CUDA-enabled PyTorch installation compatible with that driver. The script does not install dependencies or contact the AlphaAI server.

Preview usage (no benchmark runs):

```bash
python gpu_benchmark.py --help
```

Explicitly run a bounded benchmark locally:

```bash
python gpu_benchmark.py --run --matrix-size 1024 --repetitions 20
```

The defaults are 1024×1024 FP32 matrices and 20 repetitions; allowed bounds are 256–2048 and 1–100 repetitions. Running this uses GPU resources and may increase power draw and temperature. Run only on a machine you own or are authorized to use, while monitoring its thermals. Results are printed locally as JSON and are not uploaded.
