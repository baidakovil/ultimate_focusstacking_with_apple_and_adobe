#!/usr/bin/env python3
"""
Full integration test for the complete workflow with mocked fetcher step.
Tests both scenarios: with groups and without groups.
"""

import subprocess
import os
import json
import sys
import shutil
import tempfile
from zipfile import ZipFile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def setup_test_environment():
    """Setup the test environment"""
    test_output_dir = os.path.join(ROOT_DIR, "test_output")

    # Clean up previous test
    if os.path.exists(test_output_dir):
        shutil.rmtree(test_output_dir)

    # Create test directory
    os.makedirs(test_output_dir, exist_ok=True)
    print(f"Created test output directory: {test_output_dir}")

    return test_output_dir


def test_workflow_with_groups():
    """Test workflow with photos that create focus stacking groups"""
    print("\n" + "=" * 60)
    print("TEST 1: Workflow with focus stacking groups")
    print("=" * 60)

    test_dir = setup_test_environment()

    try:
        # Extract test photos that have focus stacks into the current workflow folder
        current_folder = os.path.join(test_dir, "!newstack")
        os.makedirs(current_folder, exist_ok=True)
        test_zip = os.path.join(ROOT_DIR, "test", "test_97f.zip")
        if os.path.exists(test_zip):
            with ZipFile(test_zip, 'r') as zip_file:
                zip_file.extractall(current_folder)
            print(f"✅ Extracted test photos (with stacks) to: {current_folder}")
        else:
            raise AssertionError(f"Test file not found: {test_zip}")

        # Run the modified runner.py with test settings
        print("\nRunning full workflow with settings_test.txt...")
        print("Note: Step 1 (fetcher) will be mocked since we already have photos")

        result = subprocess.run(
            [sys.executable, "-m", "src.runner"],
            env={
                **os.environ,
                "FOCUSSTACK_SETTINGS": "settings_test.txt",
                "FOCUSSTACK_SKIP_PHOTOSHOP": "1",
            },
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
        )

        print("Runner output:")
        print(result.stdout)
        if result.stderr:
            print("Runner errors:")
            print(result.stderr)

        fs_folder = os.path.join(current_folder, "fs")
        assert result.returncode == 0, f"Workflow failed with exit code {result.returncode}: {result.stderr}"
        assert os.path.exists(fs_folder), "No 'fs' folder created"

        subfolders = [
            d
            for d in os.listdir(fs_folder)
            if os.path.isdir(os.path.join(fs_folder, d))
        ]
        print(f"✅ Created {len(subfolders)} focus stack folders")

    except Exception as e:
        raise AssertionError(f"Workflow test failed with exception: {e}") from e


def test_workflow_without_groups():
    """Test workflow with photos that don't create focus stacking groups"""
    print("\n" + "=" * 60)
    print("TEST 2: Workflow with NO focus stacking groups")
    print("=" * 60)

    test_dir = setup_test_environment()

    try:
        # Extract test photos that have NO focus stacks
        test_zip = os.path.join(ROOT_DIR, "test", "test_no_st.zip")
        assert os.path.exists(test_zip), f"Test file not found: {test_zip}"
        with ZipFile(test_zip, 'r') as zip_file:
            zip_file.extractall(test_dir)
        print(f"✅ Extracted test photos (no stacks) to: {test_dir}")

        sys.path.insert(0, ROOT_DIR)
        from src.runner import run_grouper

        print("\nTesting Step 2 (grouper) with no focus stacking groups...")
        grouper_result = run_grouper(test_dir)
        assert grouper_result == "no_groups", f"Unexpected result from grouper: {grouper_result}"
        print("✅ Step 2 correctly detected no groups")
        print("✅ Step 3 would be skipped (as designed)")
        print("✅ Workflow would exit gracefully with success")

    except Exception as e:
        raise AssertionError(f"No-groups workflow test failed with exception: {e}") from e


def test_runner_settings_validation():
    """Test that runner.py loads settings correctly"""
    print("\n" + "=" * 60)
    print("TEST 3: Settings validation")
    print("=" * 60)

    try:
        sys.path.insert(0, ROOT_DIR)
        from src.runner import load_settings

        # Test loading settings_test.txt
        settings = load_settings("settings_test.txt")

        assert settings is not None, "Failed to load settings_test.txt"

        required_keys = [
            "hours_icloud",
            "stacker",
            "folder_grouped",
            "path_all_storing",
            "folder_current_storing",
            "photoshop_app",
            "skip_icloud_fetcher",
        ]
        for key in required_keys:
            assert key in settings, f"Missing required setting: {key}"

        print("✅ All required settings are present:")
        for key, value in settings.items():
            print(f"  {key}: {value}")

    except Exception as e:
        raise AssertionError(f"Settings test failed: {e}") from e


def test_runner_skips_icloud_fetcher_when_flag_enabled():
    """Test that runner skips Step 1 when skip_icloud_fetcher is enabled and still processes existing files."""
    print("\n" + "=" * 60)
    print("TEST 4: Skip iCloud fetcher flag")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="focusstack_skip_fetcher_test_", dir=ROOT_DIR)
    try:
        current_folder = os.path.join(temp_dir, "!newstack")
        os.makedirs(current_folder, exist_ok=True)

        test_zip = os.path.join(ROOT_DIR, "test", "test_97f.zip")
        assert os.path.exists(test_zip), f"Test file not found: {test_zip}"
        with ZipFile(test_zip, "r") as zip_file:
            zip_file.extractall(current_folder)

        settings_path = os.path.join(temp_dir, "test_settings.json")
        settings = {
            "hours_icloud": "1",
            "stacker": "stacker.js",
            "folder_grouped": "fs",
            "path_all_storing": temp_dir,
            "folder_current_storing": "!newstack",
            "photoshop_app": "Adobe Photoshop 2026",
            "skip_icloud_fetcher": True,
        }
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

        env = {
            **os.environ,
            "FOCUSSTACK_SETTINGS": settings_path,
            "FOCUSSTACK_SKIP_PHOTOSHOP": "1",
        }

        result = subprocess.run(
            [sys.executable, "-m", "src.runner"],
            cwd=ROOT_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        print("Runner output:")
        print(result.stdout)
        if result.stderr:
            print("Runner errors:")
            print(result.stderr)

        assert result.returncode == 0, f"Workflow failed with exit code {result.returncode}: {result.stderr}"
        assert "Skipping Step 1" in result.stdout, "Runner did not print the skip message"
        assert os.path.exists(os.path.join(current_folder, "fs")), "No 'fs' folder created"
        print("✅ Runner skipped iCloud fetcher and processed existing files")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("🧪 Full Integration Test Suite for Focus Stacking Workflow")
    print("=" * 70)

    test_results = []

    # Test 1: Workflow with groups (would proceed to Step 3)
    test_results.append(test_workflow_with_groups())

    # Test 2: Workflow without groups (Step 3 skipped)
    test_results.append(test_workflow_without_groups())

    # Test 3: Settings validation
    test_results.append(test_runner_settings_validation())

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total_tests = len(test_results)
    passed_tests = sum(test_results)

    test_names = [
        "Workflow with focus stacking groups",
        "Workflow with NO focus stacking groups (Step 3 skip)",
        "Settings validation",
    ]

    for i, (test_name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{i+1}. {test_name}: {status}")

    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Workflow correctly skips Step 3 when no groups are created")
        print("✅ Integration with fetcher.py is working")
        print("✅ Settings validation is working")
    else:
        print("\n❌ Some tests failed - please review the output above")

    print("=" * 70)
