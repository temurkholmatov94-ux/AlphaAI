import importlib.util
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location(
    "alphaai_worker_agent",
    Path(__file__).with_name("agent.py"),
)
agent = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(agent)


class WorkerAgentTests(unittest.TestCase):
    @patch.object(agent.subprocess, "run")
    def test_detect_gpus_parses_nvidia_inventory(self, run):
        run.return_value = subprocess.CompletedProcess(
            args=["nvidia-smi"],
            returncode=0,
            stdout="NVIDIA RTX Test, 24576\nNVIDIA Another, 8192\n",
            stderr="",
        )
        self.assertEqual(
            agent.detect_gpus(),
            [
                {"name": "NVIDIA RTX Test", "vendor": "NVIDIA", "vram_mb": 24576},
                {"name": "NVIDIA Another", "vendor": "NVIDIA", "vram_mb": 8192},
            ],
        )
        self.assertEqual(run.call_args.kwargs["timeout"], 3)

    @patch.object(agent.subprocess, "run", side_effect=FileNotFoundError)
    def test_detect_gpus_is_empty_when_nvidia_smi_is_missing(self, _run):
        self.assertEqual(agent.detect_gpus(), [])

    @patch.object(agent, "available_ram_mb", return_value=(32768, 12000))
    @patch.object(agent, "detect_gpus", return_value=[])
    @patch.object(agent.platform, "processor", return_value="Test CPU")
    @patch.object(agent.platform, "platform", return_value="Linux-Test")
    @patch.object(agent.platform, "machine", return_value="x86_64")
    @patch.object(agent.os, "cpu_count", return_value=8)
    def test_build_report_contains_bounded_hardware_fields(
        self, _cpu_count, _machine, _platform, _processor, _gpus, _ram
    ):
        report = agent.build_report()
        self.assertEqual(report["cpu_logical_cores"], 8)
        self.assertEqual(report["ram_total_mb"], 32768)
        self.assertEqual(report["ram_available_mb"], 12000)
        self.assertEqual(report["gpus"], [])
        self.assertEqual(report["agent_version"], agent.VERSION)

    @patch.object(agent, "available_ram_mb", return_value=(0, 0))
    def test_build_report_fails_closed_without_ram_measurement(self, _ram):
        with self.assertRaises(RuntimeError):
            agent.build_report()

    @patch.object(agent, "build_report", return_value={"agent_version": agent.VERSION})
    @patch.object(agent.urllib.request, "urlopen")
    def test_heartbeat_uses_bearer_token_and_expected_endpoint(self, urlopen, _report):
        response = Mock()
        response.status = 200
        response.read.return_value = b'{"worker_id":"wkr_test"}'
        urlopen.return_value.__enter__.return_value = response
        agent.send_heartbeat("https://alphaai.example", "aai_worker_test")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://alphaai.example/v1/workers/heartbeat")
        self.assertEqual(request.get_header("Authorization"), "Bearer aai_worker_test")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 15)

    @patch.object(agent, "build_report", return_value={"agent_version": agent.VERSION})
    @patch.object(agent.urllib.request, "urlopen")
    def test_revoked_worker_credential_stops_agent(self, urlopen, _report):
        error = agent.urllib.error.HTTPError(
            "https://alphaai.example/v1/workers/heartbeat",
            401,
            "Unauthorized",
            hdrs=None,
            fp=None,
        )
        urlopen.side_effect = error
        with self.assertRaisesRegex(RuntimeError, "credential rejected or revoked"):
            agent.send_heartbeat("https://alphaai.example", "aai_worker_revoked")


if __name__ == "__main__":
    unittest.main()
