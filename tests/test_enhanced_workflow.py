#!/usr/bin/env python3
"""
Test script to verify the enhanced workflow functionality.
Tests the new image format support and incremental folder management.
"""

import contextlib
import io
import os
import sys
import tempfile
import shutil
from unittest.mock import patch
from zipfile import ZipFile
import json
import subprocess

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_multiple_image_formats():
    """Test that grouper.py now supports multiple image formats"""
    print("=" * 60)
    print("TEST 1: Multiple Image Format Support")
    print("=" * 60)

    test_dir = tempfile.mkdtemp(prefix="focusstack_formats_test_")
    print(f"Created test directory: {test_dir}")

    try:
        # Create test files with different extensions
        test_files = [
            "IMG_001.jpg",
            "IMG_002.JPEG",
            "IMG_003.tiff",
            "IMG_004.TIF",
            "IMG_005.png",
            "IMG_006.bmp",
            "IMG_007.HEIC",
        ]

        # Create dummy files (they won't have proper EXIF but will test format detection)
        for filename in test_files:
            filepath = os.path.join(test_dir, filename)
            with open(filepath, 'w') as f:
                f.write("dummy content")

        print(f"Created {len(test_files)} test files with different formats")

        result = subprocess.run(
            [sys.executable, "-m", "src.grouper", test_dir],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )

        assert "image files" in result.stdout.lower(), (
            f"Grouper did not detect image formats properly. Output: {result.stdout} Error: {result.stderr}"
        )
        print("✅ Grouper successfully detected multiple image formats")

    except Exception as e:
        raise AssertionError(f"Multiple image formats test failed: {e}") from e
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_arw_files_are_accepted():
    """Test that ARW files are accepted as valid source input."""
    temp_dir = tempfile.mkdtemp(prefix="arw_support_test_")
    try:
        arw_file = os.path.join(temp_dir, "IMG_0001.ARW")
        with open(arw_file, "wb") as f:
            f.write(b"fake")

        sys.path.insert(0, ROOT_DIR)
        from src.grouper import read_jpg

        with patch("src.grouper.piexif.load", return_value={"0th": {306: b"2024:01:01 12:00:00"}}):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                names, dates = read_jpg(temp_dir)

        assert names == ["IMG_0001.ARW"], f"Expected ARW file to be accepted, got {names}"
        assert len(dates) == 1, "Expected one timestamp from the ARW file"
        print("✅ ARW files are accepted as source input")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_mixed_types_are_rejected():
    """Test that mixed source file types cause a clear failure."""
    temp_dir = tempfile.mkdtemp(prefix="mixed_type_test_")
    try:
        arw_file = os.path.join(temp_dir, "IMG_0001.ARW")
        jpg_file = os.path.join(temp_dir, "IMG_0002.JPG")
        with open(arw_file, "wb") as f:
            f.write(b"fake")
        with open(jpg_file, "wb") as f:
            f.write(b"fake")

        sys.path.insert(0, ROOT_DIR)
        from src.grouper import read_jpg

        with patch("src.grouper.piexif.load", return_value={"0th": {306: b"2024:01:01 12:00:00"}}):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                try:
                    read_jpg(temp_dir)
                    assert False, "Expected SystemExit when mixed file types are present"
                except SystemExit as e:
                    assert e.code == 1, f"Unexpected exit code: {e.code}"

        output = buf.getvalue()
        assert "Mixed source image types" in output, f"Unexpected output: {output}"
        assert ".arw" in output and ".jpg" in output, f"Expected both extensions in output: {output}"
        print("✅ Mixed source file types are rejected with a clear error")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_folder_increment_logic():
    """Test the incremental folder creation and decision logic"""
    print("\n" + "=" * 60)
    print("TEST 2: Incremental Folder Management")
    print("=" * 60)

    test_base_dir = tempfile.mkdtemp(prefix="focusstack_increment_test_")
    print(f"Created test base directory: {test_base_dir}")

    try:
        sys.path.insert(0, ROOT_DIR)
        from src.folder_manager import determine_workflow_action, create_folder_if_needed

        # Test 1: No folders exist - should create first folder
        action, folder_path = determine_workflow_action(
            test_base_dir, "!newstack", "fs"
        )
        expected_folder = os.path.join(test_base_dir, "!newstack")

        print(f"Test 1 - No folders exist:")
        print(f"  Action: {action}")
        print(f"  Folder: {folder_path}")
        print(f"  Expected: {expected_folder}")

        assert action == "run_fetcher" and folder_path == expected_folder, (
            f"Expected run_fetcher on {expected_folder}, got {action} / {folder_path}"
        )
        print("✅ Test 1 passed")

        create_folder_if_needed(folder_path)

        # Test 2: Empty folder exists - should use same folder
        action, folder_path = determine_workflow_action(
            test_base_dir, "!newstack", "fs"
        )

        print(f"\nTest 2 - Empty folder exists:")
        print(f"  Action: {action}")
        print(f"  Folder: {folder_path}")

        assert action == "run_fetcher" and folder_path == expected_folder, (
            f"Expected run_fetcher on {expected_folder}, got {action} / {folder_path}"
        )
        print("✅ Test 2 passed")

        # Test 3: Add some dummy image files to simulate "ready for grouper"
        dummy_image = os.path.join(folder_path, "test.jpg")
        with open(dummy_image, 'w') as f:
            f.write("dummy")

        action, folder_path = determine_workflow_action(
            test_base_dir, "!newstack", "fs"
        )

        print(f"\nTest 3 - Folder with images (ready for grouper):")
        print(f"  Action: {action}")
        print(f"  Folder: {folder_path}")

        assert action == "run_grouper" and folder_path == expected_folder, (
            f"Expected run_grouper on {expected_folder}, got {action} / {folder_path}"
        )
        print("✅ Test 3 passed")

        # Test 4: Add "fs" folder to simulate completed processing
        fs_folder = os.path.join(folder_path, "fs")
        os.makedirs(fs_folder)

        action, folder_path = determine_workflow_action(
            test_base_dir, "!newstack", "fs"
        )
        expected_next_folder = os.path.join(test_base_dir, "!newstack_1")

        print(f"\nTest 4 - Completed folder (should create next increment):")
        print(f"  Action: {action}")
        print(f"  Folder: {folder_path}")
        print(f"  Expected: {expected_next_folder}")

        assert action == "run_fetcher" and folder_path == expected_next_folder, (
            f"Expected run_fetcher on {expected_next_folder}, got {action} / {folder_path}"
        )
        print("✅ Test 4 passed")

        print("✅ All incremental folder tests passed!")

    except Exception as e:
        raise AssertionError(f"Folder increment logic test failed: {e}") from e
    finally:
        shutil.rmtree(test_base_dir, ignore_errors=True)


def test_settings_format():
    """Test that the new settings format is working"""
    print("\n" + "=" * 60)
    print("TEST 3: Settings Format Validation")
    print("=" * 60)

    try:
        sys.path.insert(0, ROOT_DIR)
        from src.runner import load_settings

        # Test loading current settings.txt
        settings = load_settings("settings.txt")

        assert settings, "Failed to load settings.txt"

        # Check all required new format fields
        required_fields = [
            "hours_icloud",
            "stacker",
            "folder_grouped",
            "path_all_storing",
            "folder_current_storing",
            "photoshop_app",
        ]

        print("Checking required fields:")
        all_present = True
        for field in required_fields:
            if field in settings:
                print(f"  ✅ {field}: {settings[field]}")
            else:
                print(f"  ❌ {field}: MISSING")
                all_present = False

        # Verify no old format fields are present
        old_fields = ["path_grouped", "path_iphone"]
        for field in old_fields:
            if field in settings:
                print(f"  ⚠️  Old field still present: {field}")
                all_present = False

        assert all_present, "Settings format validation failed"
        print("✅ Settings format validation passed!")

    except Exception as e:
        raise AssertionError(f"Settings format validation test failed: {e}") from e


def test_runner_integration():
    """Test that runner.py works with the new settings format"""
    print("\n" + "=" * 60)
    print("TEST 4: Runner Integration Test")
    print("=" * 60)

    try:
        # Test that runner can import and validate settings
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                """
import sys
sys.path.insert(0, '.')
from src.runner import load_settings
from src.folder_manager import determine_workflow_action

settings = load_settings('settings_test.txt')
if settings is None:
    raise SystemExit('Failed to load settings')

# Extract settings
folder_grouped = settings.get('folder_grouped')
path_all_storing = settings.get('path_all_storing')
folder_current_storing = settings.get('folder_current_storing')

# Test folder logic (using a safe test path)
import tempfile
import shutil

test_dir = tempfile.mkdtemp()
action, folder_path = determine_workflow_action(test_dir, folder_current_storing, folder_grouped)

print(f'SUCCESS: action={action}, folder_type={type(folder_path).__name__}')

shutil.rmtree(test_dir)
""",
            ],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
        )

        print("Runner integration test output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)

        assert result.returncode == 0 and "SUCCESS:" in result.stdout, (
            f"Runner integration test failed. stdout={result.stdout} stderr={result.stderr}"
        )
        print("✅ Runner integration test passed!")

    except Exception as e:
        raise AssertionError(f"Runner integration test failed: {e}") from e
