import subprocess
import json
import os
import sys

CLI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aegis_cli.py")


class CLIError(Exception):
    pass


def run_cli(args, password=None, vault_path=None):
    cmd = [CLI_PATH]
    if password:
        cmd.extend(["-p", password])
    if vault_path:
        cmd.append(vault_path)
    cmd.extend(args)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        try:
            error_data = json.loads(result.stdout)
            if "error" in error_data:
                error_msg = error_data["error"]
        except json.JSONDecodeError:
            pass
        raise CLIError(error_msg)

    return result.stdout


def get_entries(vault_path, password, group=None):
    args = ["--json"]
    if group:
        args.extend(["-g", group])

    output = run_cli(args, password, vault_path)
    return json.loads(output)


def get_entry(uuid, vault_path, password):
    args = ["-u", uuid, "--json"]
    output = run_cli(args, password, vault_path)
    return json.loads(output)


def get_otp(uuid, vault_path, password):
    entry = get_entry(uuid, vault_path, password)
    return entry.get("otp")


def validate_password(vault_path, password):
    try:
        get_entries(vault_path, password)
        return True
    except CLIError:
        return False
