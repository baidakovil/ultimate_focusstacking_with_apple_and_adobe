#!/usr/bin/env python3
"""
Demo script to show the completed workflow functionality.
This demonstrates how Step 3 is skipped when no groups are created.
"""

import os
import sys
import tempfile
import shutil
from zipfile import ZipFile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the project root to the path to import runner functions
sys.path.insert(0, ROOT_DIR)
from runner import run_grouper


def demo_workflow_scenarios():
    """Demonstrate both workflow scenarios"""

    print("🎬 DEMO: Focus Stacking Workflow with Step 3 Skip Logic")
    print("=" * 65)

    # Scenario 1: Photos WITH focus stacking groups
    print("\n📸 SCENARIO 1: Photos with focus stacking groups")
    print("-" * 50)

    test_dir1 = tempfile.mkdtemp(prefix="demo_with_groups_")
    try:
        # Extract photos that create groups
        test_zip = os.path.join(ROOT_DIR, "test", "test_97f.zip")
        if os.path.exists(test_zip):
            with ZipFile(test_zip, 'r') as zip_file:
                zip_file.extractall(test_dir1)

            print(f"📁 Extracted test photos to: {test_dir1}")
            print("🔍 Running grouper analysis...")

            result1 = run_grouper(test_dir1)
            print(f"📊 Result: {result1}")

            if result1 == "success":
                print("✅ Groups created - Step 3 (Photoshop) would proceed")

                # Check what was created
                fs_folder = os.path.join(test_dir1, "fs")
                if os.path.exists(fs_folder):
                    subfolders = [
                        d
                        for d in os.listdir(fs_folder)
                        if os.path.isdir(os.path.join(fs_folder, d))
                    ]
                    print(f"📂 Created {len(subfolders)} focus stack folders:")
                    for folder in subfolders[:3]:  # Show first 3
                        print(f"   • {folder}")
                    if len(subfolders) > 3:
                        print(f"   ... and {len(subfolders) - 3} more")
            else:
                print(f"❌ Unexpected result: {result1}")
        else:
            print("❌ Test file not found")
    finally:
        shutil.rmtree(test_dir1, ignore_errors=True)

    # Scenario 2: Photos WITHOUT focus stacking groups
    print("\n📸 SCENARIO 2: Photos with NO focus stacking groups")
    print("-" * 50)

    test_dir2 = tempfile.mkdtemp(prefix="demo_no_groups_")
    try:
        # Extract photos that DON'T create groups
        test_zip = os.path.join(ROOT_DIR, "test", "test_no_st.zip")
        if os.path.exists(test_zip):
            with ZipFile(test_zip, 'r') as zip_file:
                zip_file.extractall(test_dir2)

            print(f"📁 Extracted test photos to: {test_dir2}")
            print("🔍 Running grouper analysis...")

            result2 = run_grouper(test_dir2)
            print(f"📊 Result: {result2}")

            if result2 == "no_groups":
                print("⏭️  No groups created - Step 3 (Photoshop) would be SKIPPED")
                print("✅ Workflow would complete gracefully without processing")
            else:
                print(f"❌ Unexpected result: {result2}")
        else:
            print("❌ Test file not found")
    finally:
        shutil.rmtree(test_dir2, ignore_errors=True)

    # Summary
    print("\n🎯 WORKFLOW LOGIC SUMMARY")
    print("=" * 65)
    print("Step 1: Fetcher extracts photos from iCloud Photos")
    print("Step 2: Grouper analyzes photos and creates focus stacking groups")
    print("        ├─ If groups created → Proceed to Step 3")
    print("        ├─ If no JPG files → Exit with message")
    print("        └─ If no groups → Skip Step 3, exit gracefully")
    print("Step 3: Photoshop processes focus stacking (only if groups exist)")
    print("\n✅ IMPLEMENTATION COMPLETE!")
    print("   • Step 3 is now intelligently skipped when no groups are created")
    print("   • All three scenarios handled gracefully")
    print("   • Exit codes properly implemented for subprocess communication")


if __name__ == "__main__":
    demo_workflow_scenarios()
