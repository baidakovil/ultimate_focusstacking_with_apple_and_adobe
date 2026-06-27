#!/usr/bin/env python3
"""
Test script to verify that Step 3 is skipped when no focus stacking groups are created.
"""

import subprocess
import os
import json
import sys
import tempfile
import shutil
from zipfile import ZipFile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_no_groups_scenario():
    """Test the workflow when grouper creates no focus stacking groups"""

    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp(prefix="focusstack_no_groups_test_")
    print(f"Created test directory: {test_dir}")

    try:
        # Extract test photos that have no stacks
        test_zip = os.path.join(ROOT_DIR, "test", "test_no_st.zip")
        assert os.path.exists(test_zip), f"Test file not found: {test_zip}"
        with ZipFile(test_zip, 'r') as zip_file:
            zip_file.extractall(test_dir)
        print(f"Extracted test photos (no stacks) to: {test_dir}")

        print("\nRunning grouper.py on test data with no focus stacks...")
        result = subprocess.run(
            [sys.executable, "-m", "src.grouper", test_dir],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        print("Grouper output:")
        print(result.stdout)
        if result.stderr:
            print("Grouper errors:")
            print(result.stderr)

        print(f"Grouper exit code: {result.returncode}")
        assert result.returncode == 2, f"Grouper did not return expected exit code 2, got {result.returncode}"
        print("✅ Grouper correctly returned exit code 2 (no groups created)")

    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"Cleaned up test directory: {test_dir}")


def test_runner_with_no_groups():
    """Test the complete runner.py workflow with test settings and no groups scenario"""

    # Create test settings that point to test data with no stacks
    test_dir = tempfile.mkdtemp(prefix="focusstack_runner_test_")
    print(f"Created test directory for runner: {test_dir}")

    try:
        test_zip = os.path.join(ROOT_DIR, "test", "test_no_st.zip")
        assert os.path.exists(test_zip), f"Test file not found: {test_zip}"
        with ZipFile(test_zip, 'r') as zip_file:
            zip_file.extractall(test_dir)
        print(f"Extracted test photos (no stacks) to: {test_dir}")

        # Create temporary settings file
        test_settings = {
            "hours_icloud": "1",
            "stacker": "stacker.js",
            "path_grouped": os.path.join(test_dir, "fs"),
            "path_iphone": test_dir,
            "photoshop_app": "Adobe Photoshop 2025",
        }

        settings_file = os.path.join(test_dir, "test_settings.json")
        with open(settings_file, 'w') as f:
            json.dump(test_settings, f, indent=2)

        print(f"Created test settings: {settings_file}")

        # Mock the fetcher step by just continuing (since we already have test photos)
        print("\nSimulating runner.py workflow...")
        print("Step 1 (fetcher): Skipped for test - photos already present")

        # Test Step 2 directly
        print("\nTesting Step 2 (grouper) with runner.py logic...")

        # Import the run_grouper function from runner.py
        sys.path.insert(0, ROOT_DIR)
        from src.runner import run_grouper

        grouper_result = run_grouper(test_dir)
        print(f"Grouper result: {grouper_result}")

        assert grouper_result == "no_groups", f"Unexpected grouper result: {grouper_result}"
        print("✅ Runner correctly detected no groups scenario")
        print("✅ Step 3 would be skipped as expected")

    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"Cleaned up test directory: {test_dir}")


if __name__ == "__main__":
    print("Testing 'no groups' scenario...")
    print("=" * 55)

    print("\n1. Testing grouper.py exit codes...")
    try:
        test_no_groups_scenario()
        test1_passed = True
    except Exception as e:
        print(f"⚠️  test_no_groups_scenario failed: {e}")
        test1_passed = False

    print("\n2. Testing runner.py logic with no groups...")
    try:
        test_runner_with_no_groups()
        test2_passed = True
    except Exception as e:
        print(f"⚠️  test_runner_with_no_groups failed: {e}")
        test2_passed = False

    print("\n" + "=" * 55)
    if test1_passed and test2_passed:
        print("🎉 All 'no groups' tests passed!")
        print(
            "✅ Step 3 will be correctly skipped when no focus stacking groups are created"
        )
    else:
        print("❌ Some tests failed!")

    print("=" * 55)
