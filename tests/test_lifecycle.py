# Purpose: Verify project-scoped lifecycle commands and propagation of startup failures.
import shutil
import subprocess
from pathlib import Path

BASH = (
    shutil.which("bash")
    if not Path("C:/Program Files/Git/bin/bash.exe").exists()
    else "C:/Program Files/Git/bin/bash.exe"
)


def invoke(action: str, service: str = "", failure: bool = False):
    script = 'docker() { printf "DOCKER %s\\n" "$*"; '
    if failure:
        script += 'if [[ "$*" == *" up "* ]]; then return 42; fi; '
    script += "}; export -f docker; bash scripts/lifecycle.sh " + action + " " + service
    return subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=15)


def test_scoped_service_stop_and_clean():
    stop = invoke("stop", "perception")
    assert stop.returncode == 0 and "stop perception" in stop.stdout
    clean = invoke("clean", "simulation")
    assert clean.returncode == 0 and "rm -f simulation" in clean.stdout
    assert "down" not in clean.stdout and "--volumes" not in clean.stdout


def test_root_start_uses_bounded_health_wait_and_preserves_data():
    result = invoke("build-and-run")
    assert result.returncode == 0
    assert "-p skill-to-bot down" in result.stdout
    assert "--wait --wait-timeout 240" in result.stdout
    assert "--volumes" not in result.stdout


def test_startup_failure_is_not_reported_as_success():
    result = invoke("build-and-run", "web", failure=True)
    assert result.returncode == 42
    assert "skill-to-bot: http" not in result.stdout


def test_invalid_service_and_action():
    assert invoke("stop", "unrelated").returncode == 2
    assert invoke("unknown").returncode == 2
