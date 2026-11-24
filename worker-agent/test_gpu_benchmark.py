import importlib.util
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "alphaai_gpu_benchmark",
    Path(__file__).with_name("gpu_benchmark.py"),
)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(benchmark)


class GPUBenchmarkTests(unittest.TestCase):
    @patch.object(benchmark.subprocess, "run")
    def test_inventory_parses_nvidia_smi(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["nvidia-smi"], returncode=0,
            stdout="NVIDIA Test GPU, 24576, 555.42\n", stderr=""
        )
        self.assertEqual(
            benchmark.gpu_inventory(),
            [{"name": "NVIDIA Test GPU", "vram_mb": 24576, "driver_version": "555.42"}],
        )

    def test_benchmark_bounds_reject_oversized_work(self):
        with self.assertRaisesRegex(ValueError, "matrix_size"):
            benchmark.run_benchmark(matrix_size=4096)
        with self.assertRaisesRegex(ValueError, "repetitions"):
            benchmark.run_benchmark(repetitions=101)

    def test_benchmark_requires_cuda(self):
        fake_torch = types.SimpleNamespace(
            cuda=types.SimpleNamespace(is_available=lambda: False)
        )
        with patch.dict(sys.modules, {"torch": fake_torch}):
            with self.assertRaisesRegex(RuntimeError, "CUDA is unavailable"):
                benchmark.run_benchmark()

    def test_cli_does_not_run_without_explicit_flag(self):
        with patch.object(sys, "argv", ["gpu_benchmark.py"]):
            with self.assertRaises(SystemExit) as raised:
                benchmark.main()
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
