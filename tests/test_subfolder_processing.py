import os

from src.folder_manager import find_root_image_files, find_subfolders_with_images
from src.grouper import build_unique_stack_path


def test_find_subfolders_with_images_ignores_fs_and_empty_dirs(tmp_path):
    base_dir = tmp_path / "!newstack"
    base_dir.mkdir()

    images_dir = base_dir / "camera_folder"
    images_dir.mkdir()
    (images_dir / "IMG_0001.JPG").write_bytes(b"fake")

    empty_dir = base_dir / "empty_folder"
    empty_dir.mkdir()

    fs_dir = base_dir / "fs"
    fs_dir.mkdir()
    (fs_dir / "already_done.JPG").write_bytes(b"fake")

    result = find_subfolders_with_images(str(base_dir), "fs")

    assert result == ["camera_folder"]


def test_find_subfolders_with_images_returns_empty_when_no_candidate_dirs(tmp_path):
    base_dir = tmp_path / "!newstack"
    base_dir.mkdir()

    (base_dir / "IMG_0001.JPG").write_bytes(b"fake")

    result = find_subfolders_with_images(str(base_dir), "fs")

    assert result == []


def test_build_unique_stack_path_avoids_existing_names(tmp_path):
    fs_dir = tmp_path / "fs"
    fs_dir.mkdir()
    existing_dir = fs_dir / "IMG_0001_to_IMG_0003"
    existing_dir.mkdir()

    result = build_unique_stack_path(str(fs_dir), "IMG_0001_to_IMG_0003")

    assert result == str(fs_dir / "IMG_0001_to_IMG_0003_1")


def test_build_unique_stack_path_skips_multiple_existing_suffixes(tmp_path):
    fs_dir = tmp_path / "fs"
    fs_dir.mkdir()
    (fs_dir / "IMG_0001_to_IMG_0003").mkdir()
    (fs_dir / "IMG_0001_to_IMG_0003_1").mkdir()
    (fs_dir / "IMG_0001_to_IMG_0003_2").mkdir()

    result = build_unique_stack_path(str(fs_dir), "IMG_0001_to_IMG_0003")

    assert result == str(fs_dir / "IMG_0001_to_IMG_0003_3")


def test_find_root_image_files_detects_only_direct_images(tmp_path):
    base_dir = tmp_path / "!newstack"
    base_dir.mkdir()
    (base_dir / "IMG_0001.JPG").write_bytes(b"fake")
    (base_dir / "NOTE.txt").write_text("ignore")
    nested_dir = base_dir / "subfolder"
    nested_dir.mkdir()
    (nested_dir / "IMG_0002.JPG").write_bytes(b"fake")

    result = find_root_image_files(str(base_dir))

    assert result == ["IMG_0001.JPG"]


def test_mixed_root_files_and_subfolders_are_both_detected(tmp_path):
    base_dir = tmp_path / "!newstack"
    base_dir.mkdir()
    (base_dir / "IMG_0001.JPG").write_bytes(b"fake")

    nested_dir = base_dir / "camera_folder"
    nested_dir.mkdir()
    (nested_dir / "IMG_0002.JPG").write_bytes(b"fake")

    result = {
        "subfolders": find_subfolders_with_images(str(base_dir), "fs"),
        "root_images": find_root_image_files(str(base_dir)),
    }

    assert result == {
        "subfolders": ["camera_folder"],
        "root_images": ["IMG_0001.JPG"],
    }


def test_no_candidate_content_returns_empty_lists(tmp_path):
    base_dir = tmp_path / "!newstack"
    base_dir.mkdir()
    (base_dir / "NOTE.txt").write_text("ignore")
    nested_dir = base_dir / "empty_folder"
    nested_dir.mkdir()

    result = {
        "subfolders": find_subfolders_with_images(str(base_dir), "fs"),
        "root_images": find_root_image_files(str(base_dir)),
    }

    assert result == {"subfolders": [], "root_images": []}
