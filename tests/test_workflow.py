import subprocess
import os
import json
import sys
import tempfile
import shutil
from zipfile import ZipFile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_workflow_with_sample_data():
    """Test the workflow using sample data from test files"""

    # Create a temporary directory for testing
    test_dir = tempfile.mkdtemp(prefix="focusstack_test_")
    print(f"Created test directory: {test_dir}")

    try:
        # Extract test photos
        test_zip = os.path.join(ROOT_DIR, "test", "test_97f.zip")
        assert os.path.exists(test_zip), f"Test file not found: {test_zip}"
        with ZipFile(test_zip, 'r') as zip_file:
            zip_file.extractall(test_dir)
        print(f"Extracted test photos to: {test_dir}")

        # Run grouper.py on the test data
        print("\nRunning grouper.py on test data...")
        grouper_path = os.path.join(ROOT_DIR, "src", "grouper.py")
        result = subprocess.run(
            [sys.executable, grouper_path, test_dir], capture_output=True, text=True
        )

        print("Grouper output:")
        print(result.stdout)
        if result.stderr:
            print("Grouper errors:")
            print(result.stderr)

        assert result.returncode == 0, f"Grouper test failed with exit code {result.returncode}. stderr={result.stderr}"

        fs_folder = os.path.join(test_dir, "fs")
        assert os.path.exists(fs_folder), "No 'fs' folder created"
        subfolders = [
            d
            for d in os.listdir(fs_folder)
            if os.path.isdir(os.path.join(fs_folder, d))
        ]
        print(f"Created {len(subfolders)} focus stack folders")

    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"Cleaned up test directory: {test_dir}")


if __name__ == "__main__":
    print("Testing focus stacking workflow...")
    if test_workflow_with_sample_data():
        print("\n🎉 Workflow test completed successfully!")
    else:
        print("\n❌ Workflow test failed!")
