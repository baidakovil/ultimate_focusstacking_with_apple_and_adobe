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


def test_photoshop_uses_root_folder_in_subfolder_mode():
    """Test that subfolder mode passes the root folder to Photoshop."""
    temp_dir = tempfile.mkdtemp(prefix="subfolder_mode_test_", dir=ROOT_DIR)
    try:
        current_folder = os.path.join(temp_dir, "!newstack")
        os.makedirs(current_folder, exist_ok=True)

        subfolder = os.path.join(current_folder, "120MSDCF")
        os.makedirs(subfolder, exist_ok=True)
        with open(os.path.join(subfolder, "DSC00001.ARW"), "wb") as f:
            f.write(b"fake")

        settings_path = os.path.join(temp_dir, "test_settings.json")
        settings = {
            "hours_icloud": "1",
            "stacker": "stacker.js",
            "folder_grouped": "fs",
            "path_all_storing": temp_dir,
            "folder_current_storing": "!newstack",
            "photoshop_app": "Adobe Photoshop 2026",
            "process_subfolders_with_photoshop": True,
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

        assert result.returncode == 0, f"Workflow failed with exit code {result.returncode}: {result.stderr}"
        assert "Photoshop input folder: " in result.stdout
        assert f"Photoshop input folder: {current_folder}" in result.stdout
        print("✅ Subfolder mode passes the root folder to Photoshop")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_mixed_types_across_root_and_subfolders_are_rejected():
    """Test that mixed file types across root and subfolders are rejected in subfolder mode."""
    temp_dir = tempfile.mkdtemp(prefix="mixed_subfolder_types_test_", dir=ROOT_DIR)
    try:
        current_folder = os.path.join(temp_dir, "!newstack")
        os.makedirs(current_folder, exist_ok=True)

        with open(os.path.join(current_folder, "IMG_0002.JPG"), "wb") as f:
            f.write(b"fake")

        subfolder = os.path.join(current_folder, "120MSDCF")
        os.makedirs(subfolder, exist_ok=True)
        with open(os.path.join(subfolder, "DSC00001.ARW"), "wb") as f:
            f.write(b"fake")

        settings_path = os.path.join(temp_dir, "test_settings.json")
        settings = {
            "hours_icloud": "1",
            "stacker": "stacker.js",
            "folder_grouped": "fs",
            "path_all_storing": temp_dir,
            "folder_current_storing": "!newstack",
            "photoshop_app": "Adobe Photoshop 2026",
            "process_subfolders_with_photoshop": True,
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

        assert result.returncode == 1, (
            f"Expected failure for mixed types across root and subfolders, got {result.returncode}."
        )
        assert "Mixed source image types" in result.stdout or "Mixed source image types" in result.stderr
        assert ".arw" in result.stdout + result.stderr
        assert ".jpg" in result.stdout + result.stderr
        print("✅ Mixed ARW/JPG files across root and subfolders are rejected")

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
            "release_arw_crop",
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
        print("✅ Settings format is valid")

    except Exception as e:
        raise AssertionError(f"Settings format test failed: {e}") from e


def test_release_arw_crop_setting_invokes_exiftool():
    """Test that release_arw_crop setting triggers exiftool metadata rewrite."""
    print("\n" + "=" * 60)
    print("TEST 4: release_arw_crop setting")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="release_arw_crop_test_")
    try:
        current_folder = os.path.join(temp_dir, "!newstack")
        os.makedirs(current_folder, exist_ok=True)
        subfolder = os.path.join(current_folder, "120MSDCF")
        os.makedirs(subfolder, exist_ok=True)
        arw_file = os.path.join(subfolder, "DSC00001.ARW")
        with open(arw_file, "wb") as f:
            f.write(b"fake")

        from src.runner import release_arw_crop_files

        with patch("src.runner.shutil.which", return_value="/usr/bin/exiftool"), patch(
            "src.runner.subprocess.run"
        ) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="SubIFD:ImageWidth: 6000\nSubIFD:ImageHeight: 4000\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=(
                        "DefaultCropOrigin: 10 10\n"
                        "DefaultCropSize: 3000 2000\n"
                        "SonyCropTopLeft: 10 10\n"
                        "SonyCropSize: 3000 2000\n"
                    ),
                    stderr="",
                ),
                subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            ]
            result = release_arw_crop_files(current_folder)

        assert result is True, "release_arw_crop_files should return True when exiftool succeeds"
        assert mock_run.call_count == 3, "Expected exiftool to be invoked for dimensions, metadata check, and rewrite"

        first_call = mock_run.call_args_list[0][0][0]
        assert "/usr/bin/exiftool" in first_call, "First call should query exiftool for dimensions"

        second_call = mock_run.call_args_list[1][0][0]
        assert "/usr/bin/exiftool" in second_call, "Second call should query metadata tags"
        assert "-s" in second_call
        assert "-DefaultCropOrigin" in second_call

        third_call = mock_run.call_args_list[2][0][0]
        assert "/usr/bin/exiftool" in third_call, "Third call should invoke exiftool rewrite"
        assert "-overwrite_original" in third_call, "Expected metadata rewrite to use overwrite_original"
        assert "-DefaultCropOrigin=0 0" in third_call
        assert "-SonyCropTopLeft=0 0" in third_call

        print("✅ release_arw_crop setting successfully triggered exiftool metadata rewrite")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_release_arw_crop_skips_clean_arw_files():
    """Test that clean ARW files are skipped without redundant rewrite."""
    print("\n" + "=" * 60)
    print("TEST 5: release_arw_crop skip clean ARW files")
    print("=" * 60)

    temp_dir = tempfile.mkdtemp(prefix="release_arw_crop_skip_test_")
    try:
        current_folder = os.path.join(temp_dir, "!newstack")
        os.makedirs(current_folder, exist_ok=True)
        subfolder = os.path.join(current_folder, "120MSDCF")
        os.makedirs(subfolder, exist_ok=True)
        arw_file = os.path.join(subfolder, "DSC00001.ARW")
        with open(arw_file, "wb") as f:
            f.write(b"fake")

        from src.runner import release_arw_crop_files

        with patch("src.runner.shutil.which", return_value="/usr/bin/exiftool"), patch(
            "src.runner.subprocess.run"
        ) as mock_run:
            mock_run.side_effect = [
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="SubIFD:ImageWidth: 6000\nSubIFD:ImageHeight: 4000\n",
                    stderr="",
                ),
                subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout=(
                        "DefaultCropOrigin: 0 0\n"
                        "DefaultCropSize: 6000 4000\n"
                        "SonyCropTopLeft: 0 0\n"
                        "SonyCropSize: 6000 4000\n"
                    ),
                    stderr="",
                ),
            ]
            result = release_arw_crop_files(current_folder)

        assert result is True, "release_arw_crop_files should return True when ARW is already clean"
        assert mock_run.call_count == 2, "Expected only dimension and metadata checks, no rewrite"

        print("✅ release_arw_crop correctly skipped clean ARW files")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


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
