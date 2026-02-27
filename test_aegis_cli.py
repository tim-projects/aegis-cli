#!/usr/bin/env python3
"""Tests for aegis-cli"""

import json
import subprocess
import sys

VAULT = "test_vault.json"
PASSWORD = "testvault123!"


def run_cli(args):
    cmd = [sys.executable, "-m", "aegis_tui.aegis_cli", "-p", PASSWORD, VAULT] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def test_list_all():
    """Test listing all entries"""
    result = run_cli([])
    assert result.returncode == 0, f"Failed: {result.stderr}"
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 50, f"Expected 50 entries, got {len(lines)}"
    print("PASS: list all")


def test_json_output():
    """Test JSON output"""
    result = run_cli(["--json"])
    assert result.returncode == 0, f"Failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, list), "Expected list"
    assert len(data) == 50, f"Expected 50 entries, got {len(data)}"
    assert "uuid" in data[0], "Missing uuid field"
    assert "otp" in data[0], "Missing otp field"
    print("PASS: json output")


def test_uuid_filter():
    """Test UUID filtering"""
    uuid = "32ca053b-cde6-4e30-8885-287a424a709e"
    result = run_cli(["-u", uuid])
    assert result.returncode == 0, f"Failed: {result.stderr}"
    assert result.stdout.strip() == "269249", f"Unexpected OTP: {result.stdout}"
    print("PASS: uuid filter")


def test_uuid_filter_json():
    """Test UUID filtering with JSON"""
    uuid = "32ca053b-cde6-4e30-8885-287a424a709e"
    result = run_cli(["-u", uuid, "--json"])
    assert result.returncode == 0, f"Failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["uuid"] == uuid
    assert data["name"] == "Microsoft Primary"
    print("PASS: uuid filter json")


def test_group_filter():
    """Test group filtering"""
    result = run_cli(["-g", "Social Media"])
    assert result.returncode == 0, f"Failed: {result.stderr}"
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 6, f"Expected 6 entries in Social Media, got {len(lines)}"
    print("PASS: group filter")


def test_group_filter_json():
    """Test group filtering with JSON"""
    result = run_cli(["-g", "Social Media", "--json"])
    assert result.returncode == 0, f"Failed: {result.stderr}"
    data = json.loads(result.stdout)
    assert len(data) == 6, f"Expected 6 entries, got {len(data)}"
    print("PASS: group filter json")


def test_invalid_password():
    """Test invalid password"""
    result = subprocess.run(
        [sys.executable, "-m", "aegis_tui.aegis_cli", "-p", "wrongpassword", VAULT],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, "Should fail with wrong password"
    print("PASS: invalid password")


def test_invalid_uuid():
    """Test invalid UUID"""
    result = run_cli(["-u", "invalid-uuid"])
    assert result.returncode == 1, "Should fail with invalid UUID"
    print("PASS: invalid uuid")


def test_invalid_group():
    """Test invalid group"""
    result = run_cli(["-g", "NonExistentGroup"])
    assert result.returncode == 1, "Should fail with invalid group"
    print("PASS: invalid group")


if __name__ == "__main__":
    tests = [
        test_list_all,
        test_json_output,
        test_uuid_filter,
        test_uuid_filter_json,
        test_group_filter,
        test_group_filter_json,
        test_invalid_password,
        test_invalid_uuid,
        test_invalid_group,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
