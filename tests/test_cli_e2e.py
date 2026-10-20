"""
End-to-end CLI tests executing every command across every model in the catalog as a real subprocess.
"""

import sys
import os
import subprocess
import pytest
from jblpc.models import SUPPORTED_MODELS

ALL_COMMANDS = [
    "status",
    "models",
    "battery",
    "health",
    "scan",
    "diagnose",
    "battery-log",
    "noiseoff",
    "anc",
    "ambient",
    "talkthru",
    "poweroff",
    "eq",
]


@pytest.mark.cli
@pytest.mark.parametrize("model", SUPPORTED_MODELS, ids=lambda m: m.model_id)
@pytest.mark.parametrize("command", ALL_COMMANDS)
def test_cli_command_every_model(isolated_env, model, command):
    """
    Execute each CLI command across every cataloged model as an isolated subprocess.
    Ensures:
      - No raw traceback is output
      - Enforces strict timeout
      - Sane output matching model capabilities
      - Appropriate exit code (0 if supported, 1 if unsupported command on that model)
    """
    env = os.environ.copy()
    env["HOME"] = str(isolated_env["home"])
    env["XDG_CONFIG_HOME"] = str(isolated_env["config_dir"])
    env["XDG_DATA_HOME"] = str(isolated_env["data_dir"])
    env["XDG_RUNTIME_DIR"] = str(isolated_env["runtime_dir"])

    cmd = [
        sys.executable,
        "-m",
        "jblpc",
        "cli",
        "--sim",
        "--model",
        model.model_id,
        command,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )

    stdout = result.stdout
    stderr = result.stderr
    combined = stdout + stderr

    # 1. Assert no raw unhandled python traceback
    assert "Traceback (most recent call last):" not in combined, (
        f"Raw traceback found executing '{command}' on model '{model.model_id}':\n{combined}"
    )

    # 2. Check capability-based expected return codes
    if command == "anc":
        if model.has_anc:
            assert result.returncode == 0, f"Expected 0 for ANC on {model.model_id}: {combined}"
            assert "ANC enabled" in stdout
        else:
            assert result.returncode == 1, f"Expected non-zero for ANC on non-ANC model {model.model_id}"
            assert "not supported" in combined
    elif command == "ambient":
        if model.has_ambient_aware:
            assert result.returncode == 0, f"Expected 0 for Ambient Aware on {model.model_id}"
            assert "Ambient Aware enabled" in stdout
        else:
            assert result.returncode == 1, f"Expected non-zero on {model.model_id}"
            assert "not supported" in combined
    elif command == "talkthru":
        if model.has_talkthru:
            assert result.returncode == 0, f"Expected 0 for TalkThru on {model.model_id}"
            assert "TalkThru enabled" in stdout
        else:
            assert result.returncode == 1, f"Expected non-zero on {model.model_id}"
            assert "not supported" in combined
    elif command == "poweroff":
        if model.has_power_off_command:
            assert result.returncode == 0, f"Expected 0 for poweroff on {model.model_id}"
            assert "Power off command sent" in stdout
        else:
            assert result.returncode == 1, f"Expected non-zero on {model.model_id}"
            assert "not supported" in combined
    elif command == "noiseoff":
        has_noise = model.has_anc or model.has_ambient_aware or model.has_talkthru
        if has_noise:
            assert result.returncode == 0, f"Expected 0 for noiseoff on {model.model_id}: {combined}"
            assert "Noise control disabled" in stdout
        else:
            assert result.returncode == 1, f"Expected non-zero for noiseoff on {model.model_id}: {combined}"
            assert "not supported" in combined
    elif command == "eq":
        if model.eq_type.value != "none" and model.eq_band_frequencies:
            assert result.returncode == 0, f"Expected 0 for EQ on {model.model_id}: {combined}"
            assert "Equalizer" in stdout
        else:
            assert result.returncode == 1, f"Expected non-zero for EQ on {model.model_id}: {combined}"
            assert "not supported" in combined
    elif command in ("status", "battery", "models", "health", "battery-log"):
        assert result.returncode == 0, (
            f"Expected exit code 0 for '{command}' on model '{model.model_id}':\n{combined}"
        )
    elif command in ("scan", "diagnose"):
        # Simulated scan or diagnose may return 0 or 1 depending on whether bluetoothctl detects paired devices
        assert result.returncode in (0, 1)


@pytest.mark.cli
def test_cli_health_json_flag(isolated_env):
    """Test health command with --json produces valid JSON."""
    env = os.environ.copy()
    env["HOME"] = str(isolated_env["home"])
    env["XDG_CONFIG_HOME"] = str(isolated_env["config_dir"])
    env["XDG_DATA_HOME"] = str(isolated_env["data_dir"])
    env["XDG_RUNTIME_DIR"] = str(isolated_env["runtime_dir"])

    import json
    result = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "--model", "tune_770nc", "health", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "device_id" in data
    assert "components" in data
    assert "single" in data["components"]
    assert "confidence" in data["components"]["single"]


@pytest.mark.cli
def test_cli_unknown_command(isolated_env):
    """Unknown command must return non-zero and no traceback."""
    env = os.environ.copy()
    env["HOME"] = str(isolated_env["home"])
    env["XDG_CONFIG_HOME"] = str(isolated_env["config_dir"])
    env["XDG_DATA_HOME"] = str(isolated_env["data_dir"])

    result = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "nonexistent_command"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "Unknown command" in result.stdout or "Unknown command" in result.stderr


@pytest.mark.cli
def test_cli_eq_preset_and_bands(isolated_env):
    """Test CLI eq command setting presets and custom band levels."""
    env = os.environ.copy()
    env["HOME"] = str(isolated_env["home"])
    env["XDG_CONFIG_HOME"] = str(isolated_env["config_dir"])
    env["XDG_DATA_HOME"] = str(isolated_env["data_dir"])

    # 1. Set preset bass
    res_bass = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "--model", "tune_770nc", "eq", "bass"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert res_bass.returncode == 0
    assert "EQ preset set to Bass Boost" in res_bass.stdout

    # 2. Set custom 10 bands
    res_custom = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "--model", "tune_770nc", "eq", "5", "4", "3", "2", "1", "0", "-1", "-2", "-3", "-4"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert res_custom.returncode == 0
    assert "Custom EQ bands applied" in res_custom.stdout

    # 3. Wrong band count should fail cleanly
    res_wrong = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "--model", "tune_770nc", "eq", "5", "4"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert res_wrong.returncode != 0
    assert "requires 10 bands" in res_wrong.stdout or "requires 10 bands" in res_wrong.stderr


@pytest.mark.cli
def test_cli_eq_json_output(isolated_env):
    """Test CLI eq command with --json outputs valid JSON representation of bands."""
    env = os.environ.copy()
    env["HOME"] = str(isolated_env["home"])
    env["XDG_CONFIG_HOME"] = str(isolated_env["config_dir"])
    env["XDG_DATA_HOME"] = str(isolated_env["data_dir"])

    import json
    res = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "--model", "tune_770nc", "eq", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["eq_type"] == "10_band"
    assert "bands" in data
    assert len(data["bands"]) == 10
    assert data["bands"][0]["freq"] == "32Hz"


@pytest.mark.cli
def test_cli_eq_save_command_and_flag(isolated_env):
    """Test CLI eq save and --save flag persist configuration to config.json."""
    import json
    env = os.environ.copy()
    env["HOME"] = str(isolated_env["home"])
    env["XDG_CONFIG_HOME"] = str(isolated_env["config_dir"])
    env["XDG_DATA_HOME"] = str(isolated_env["data_dir"])

    config_file = isolated_env["config_dir"] / "jblpc" / "config.json"

    # 1. eq save
    res_save = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "--model", "tune_770nc", "eq", "save"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert res_save.returncode == 0
    assert "Saved active EQ preset" in res_save.stdout
    assert config_file.exists()

    # 2. eq jazz --save
    res_jazz = subprocess.run(
        [sys.executable, "-m", "jblpc", "cli", "--sim", "--model", "tune_770nc", "eq", "jazz", "--save"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert res_jazz.returncode == 0
    assert "EQ preset set to Jazz" in res_jazz.stdout
    assert "saved to config.json" in res_jazz.stdout

    saved = json.loads(config_file.read_text(encoding="utf-8"))
    assert saved.get("eq_preset") == "Jazz"


