"""
Folder management utility for incremental folder creation and detection.
Handles finding the next available folder and determining workflow state.
"""

import os
import re
from typing import Tuple, List, Optional


def has_image_files(folder_path: str) -> bool:
    """
    Check if folder contains any image files.

    Args:
        folder_path: Path to check for image files

    Returns:
        True if folder contains image files, False otherwise
    """
    image_extensions = {'.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.png', '.heic'}

    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return False

    for file in os.listdir(folder_path):
        if os.path.isfile(os.path.join(folder_path, file)):
            _, ext = os.path.splitext(file)
            if ext.lower() in image_extensions:
                return True
    return False


def find_subfolders_with_images(folder_path: str, folder_grouped: str) -> List[str]:
    """
    Find immediate subfolders inside a folder that contain image files.

    Args:
        folder_path: Parent folder to inspect
        folder_grouped: Folder name to ignore (typically "fs")

    Returns:
        Sorted list of subfolder names that contain image files and are not the grouped folder
    """
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return []

    subfolders: List[str] = []
    for entry in sorted(os.listdir(folder_path)):
        entry_path = os.path.join(folder_path, entry)
        if not os.path.isdir(entry_path):
            continue
        if entry == folder_grouped:
            continue
        if has_image_files(entry_path):
            subfolders.append(entry)

    return subfolders


def find_root_image_files(folder_path: str) -> List[str]:
    """Return image files located directly in the given folder."""
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return []

    image_extensions = {'.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.png', '.heic'}
    root_images: List[str] = []
    for entry in sorted(os.listdir(folder_path)):
        entry_path = os.path.join(folder_path, entry)
        if not os.path.isfile(entry_path):
            continue
        _, ext = os.path.splitext(entry)
        if ext.lower() in image_extensions:
            root_images.append(entry)

    return root_images


def find_existing_folders(
    path_all_storing: str, folder_current_pattern: str
) -> List[Tuple[str, int]]:
    """
    Find all existing folders that match the pattern.

    Args:
        path_all_storing: Base directory to search in
        folder_current_pattern: Base pattern for folder names (without increment)

    Returns:
        List of tuples (folder_name, increment_number) sorted by increment
    """
    if not os.path.exists(path_all_storing):
        return []

    folders = []
    # Remove leading slash if present for pattern matching
    pattern = folder_current_pattern.lstrip('/')

    # Match folders like "!newstack", "!newstack_1", "!newstack_2", etc.
    regex_pattern = rf"^{re.escape(pattern)}(?:_(\d+))?$"

    for item in os.listdir(path_all_storing):
        item_path = os.path.join(path_all_storing, item)
        if os.path.isdir(item_path):
            match = re.match(regex_pattern, item)
            if match:
                increment = int(match.group(1)) if match.group(1) else 0
                folders.append((item, increment))

    return sorted(folders, key=lambda x: x[1])


def get_folder_state(folder_path: str, folder_grouped: str) -> str:
    """
    Determine the state of a folder for workflow decision.

    Args:
        folder_path: Path to the folder to check
        folder_grouped: Name of the grouped folder (e.g., "fs")

    Returns:
        "completed" - folder has been processed (grouped folder exists)
        "ready_for_grouper" - folder has images but no grouped folder
        "empty" - folder is empty or has no images
        "not_exists" - folder doesn't exist
    """
    if not os.path.exists(folder_path):
        return "not_exists"

    if not os.path.isdir(folder_path):
        return "not_exists"

    grouped_path = os.path.join(folder_path, folder_grouped)
    has_grouped_folder = os.path.exists(grouped_path) and os.path.isdir(grouped_path)
    has_images = has_image_files(folder_path)

    if has_grouped_folder:
        return "completed"
    elif has_images:
        return "ready_for_grouper"
    else:
        return "empty"


def determine_workflow_action(
    path_all_storing: str, folder_current_pattern: str, folder_grouped: str
) -> Tuple[str, str]:
    """
    Determine what action to take based on existing folders.

    Args:
        path_all_storing: Base directory for all storage
        folder_current_pattern: Pattern for current folder names
        folder_grouped: Name of grouped folder

    Returns:
        Tuple of (action, folder_path) where action is:
        - "run_fetcher": Run fetcher to create new photos in returned folder
        - "run_grouper": Run grouper on existing photos in returned folder
        - "error": Something went wrong
    """
    # Ensure the base storage directory exists
    if not os.path.exists(path_all_storing):
        try:
            os.makedirs(path_all_storing)
            print(f"Created storage directory: {path_all_storing}")
        except Exception as e:
            return "error", f"Cannot create storage directory: {e}"

    # Find existing folders
    existing_folders = find_existing_folders(
        path_all_storing, folder_current_pattern.lstrip('/')
    )

    if not existing_folders:
        # No folders exist, create the first one
        pattern = folder_current_pattern.lstrip('/')
        folder_name = pattern
        folder_path = os.path.join(path_all_storing, folder_name)
        return "run_fetcher", folder_path

    # Check the highest numbered folder
    last_folder_name, last_increment = existing_folders[-1]
    last_folder_path = os.path.join(path_all_storing, last_folder_name)

    state = get_folder_state(last_folder_path, folder_grouped)

    if state == "completed":
        # Last folder is completed, create next one
        pattern = folder_current_pattern.lstrip('/')
        next_increment = last_increment + 1
        next_folder_name = f"{pattern}_{next_increment}"
        next_folder_path = os.path.join(path_all_storing, next_folder_name)
        return "run_fetcher", next_folder_path

    elif state == "ready_for_grouper":
        # Last folder has images but no grouped folder, run grouper
        return "run_grouper", last_folder_path

    elif state == "empty":
        # Last folder is empty, use it for fetcher
        return "run_fetcher", last_folder_path

    else:
        return "error", f"Cannot determine state of folder: {last_folder_path}"


def create_folder_if_needed(folder_path: str) -> bool:
    """
    Create folder if it doesn't exist.

    Args:
        folder_path: Path to create

    Returns:
        True if successful, False otherwise
    """
    if os.path.exists(folder_path):
        return True

    try:
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")
        return True
    except Exception as e:
        print(f"Error creating folder {folder_path}: {e}")
        return False
