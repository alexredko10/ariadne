"""
Subprocess-based Docker executor for the Docker agent runner adapter.

This module is the only module in the runner package that imports ``subprocess``.
It implements the ``Callable[[dict], dict]`` executor interface expected by
``run_docker_agent_execution``.

Security invariants:
- ``subprocess.run`` is always called with list-form ``argv`` — never ``shell=True``.
- Shell commands are never built via string interpolation or string concatenation.
- All arguments are passed as list elements.
- Timeout is enforced via ``subprocess.run(timeout=...)``.
- ``subprocess.TimeoutExpired`` and ``FileNotFoundError`` are caught and
  returned as structured failure dicts — never uncaught.
"""

from __future__ import annotations

import subprocess


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_docker_subprocess(command_metadata: dict) -> dict:
    """Execute a Docker command via subprocess using list-form argv.

    Parameters
    ----------
    command_metadata
        The dict produced by ``build_docker_agent_command()`` with keys:
        container_image, container_command, workdir, volumes, environment,
        network_mode, memory_limit, cpu_count, timeout_seconds.

    Returns
    -------
    dict
        A dict with keys: exit_code (int), stdout (str), stderr (str),
        success (bool).
    """
    # --- Build argv as a list (no strings) ---
    argv = _build_docker_argv(command_metadata)

    # --- Execute ---
    timeout = command_metadata.get("timeout_seconds", 300)
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Docker execution timed out after {timeout} seconds",
            "success": False,
        }
    except FileNotFoundError:
        return {
            "exit_code": -1,
            "stdout": "",
            "stderr": "Docker executable not found. Is Docker installed and in PATH?",
            "success": False,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_docker_argv(command_metadata: dict) -> list[str]:
    """Build a list-form argv for ``docker run`` from command metadata.

    Parameters
    ----------
    command_metadata
        The dict produced by ``build_docker_agent_command()``.

    Returns
    -------
    list[str]
        List of argv elements suitable for ``subprocess.run()``.
    """
    argv: list[str] = ["docker", "run", "--rm"]

    workdir = command_metadata.get("workdir", "")
    if workdir:
        argv += ["--workdir", workdir]

    volumes = command_metadata.get("volumes", {})
    for host_path, vol_cfg in volumes.items():
        container_path = vol_cfg.get("bind", "")
        mode = vol_cfg.get("mode", "")
        bind_spec = f"{host_path}:{container_path}"
        if mode:
            bind_spec += f":{mode}"
        argv += ["--volume", bind_spec]

    environment = command_metadata.get("environment", {})
    for key, val in environment.items():
        argv += ["--env", f"{key}={val}"]

    network_mode = command_metadata.get("network_mode", "")
    if network_mode:
        argv += ["--network", network_mode]

    memory_limit = command_metadata.get("memory_limit", "")
    if memory_limit:
        argv += ["--memory", memory_limit]

    cpu_count = command_metadata.get("cpu_count", 0)
    if cpu_count:
        argv += ["--cpus", str(cpu_count)]

    container_image = command_metadata.get("container_image", "")
    argv.append(container_image)

    container_command = command_metadata.get("container_command", [])
    argv.extend(container_command)

    return argv
