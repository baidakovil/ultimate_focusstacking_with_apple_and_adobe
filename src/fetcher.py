#!/usr/bin/env python3
"""
iCloud Photo Fetcher

This script extracts photos from the Photos library that were added within
a specified number of hours to a specified destination folder.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


def create_applescript(destination_folder, hours, use_compressed=False):
    """Create the AppleScript code for photo extraction."""
    seconds = hours * 60 * 60
    export_method = (
        "without using originals" if use_compressed else "with using originals"
    )

    applescript = f'''
    set destinationFolder to POSIX file "{destination_folder}" as alias

    tell application "Photos"
        set thePhotos to every media item
        
        repeat with i from 1 to (count of thePhotos)
            set thePhoto to media item i
            if ((current date) - (date of thePhoto)) < {seconds} then
                export (thePhoto as list) to destinationFolder {export_method}
            end if
        end repeat
    end tell
    '''
    return applescript


def run_applescript(script):
    """Run the AppleScript using osascript command."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script], capture_output=True, text=True, check=True
        )

        print(" AppleScript executed successfully!")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing AppleScript: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ Error: osascript command not found. This script only works on macOS.")
        return False


def validate_destination(destination_path):
    """Validate and create destination folder if needed."""
    path = Path(destination_path).expanduser().resolve()

    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            print(f" Created destination folder: {path}")
        except PermissionError:
            print(f"❌ Permission denied: Cannot create folder {path}")
            return None
        except Exception as e:
            print(f"❌ Error creating folder {path}: {e}")
            return None
    elif not path.is_dir():
        print(f"❌ Error: {path} exists but is not a directory")
        return None

    if not os.access(path, os.W_OK):
        print(f"❌ Error: No write permission for folder {path}")
        return None

    return str(path)


def check_photos_app():
    """Check if Photos app is available."""
    try:
        result = subprocess.run(
            ['osascript', '-e', 'tell application "Photos" to get name'],
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        print("❌ Error: Photos app is not accessible or not found.")
        return False


def fetch_photos(destination_folder, hours, use_compressed=False):
    """Main function to fetch photos - can be called programmatically."""

    if sys.platform != "darwin":
        print("❌ This script only works on macOS.")
        return False

    print(f" Validating destination folder: {destination_folder}")
    validated_folder = validate_destination(destination_folder)
    if not validated_folder:
        return False

    print(f" Destination folder ready: {validated_folder}")

    if not check_photos_app():
        print("\n💡 Make sure:")
        print("  1. Photos app is installed")
        print("  2. You have given necessary permissions")
        print("  3. Your Photos library is accessible")
        return False

    compression_text = "compressed JPEG" if use_compressed else "original quality"
    print(f"\n Starting photo extraction...")
    print(f" Looking for photos from last {hours} hours")
    print(f" Export format: {compression_text}")
    print(f" Destination: {validated_folder}")

    applescript = create_applescript(validated_folder, hours, use_compressed)

    if run_applescript(applescript):
        print("\n Photo extraction completed")
        return True
    else:
        print("\n❌ Photo extraction failed.")
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Extract photos from Photos library added within specified hours"
    )

    parser.add_argument(
        "destination", help="Destination folder path where photos will be exported"
    )

    parser.add_argument(
        "hours",
        type=int,
        help="Number of hours to look back for photos (e.g., 24 for last day)",
    )

    parser.add_argument(
        "--compressed",
        action="store_true",
        help="Export compressed JPEG versions instead of originals",
    )

    return parser.parse_args()


def main():
    """Main function to execute the photo extraction."""
    try:
        args = parse_arguments()
    except SystemExit:
        return

    success = fetch_photos(args.destination, args.hours, args.compressed)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
