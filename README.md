# ultimate_focusstacking_with_apple_and_adobe

[![Pylint](https://github.com/baidakovil/ultimate_focusstacking_with_apple_and_adobe/actions/workflows/pylint.yml/badge.svg)](https://github.com/baidakovil/ultimate_focusstacking_with_apple_and_adobe/actions/workflows/pylint.yml) [![Testing](https://github.com/baidakovil/ultimate_focusstacking_with_apple_and_adobe/actions/workflows/python-pytest-flake8.yml/badge.svg)](https://github.com/baidakovil/ultimate_focusstacking_with_apple_and_adobe/actions/workflows/python-pytest-flake8.yml) [![mypy](https://github.com/baidakovil/ultimate_focusstacking_with_apple_and_adobe/actions/workflows/mypy.yml/badge.svg)](https://github.com/baidakovil/ultimate_focusstacking_with_apple_and_adobe/actions/workflows/mypy.yml)

Automated macOS focus stacking workflow that extracts recent photos, groups them into focus stacks, and processes valid stacks in Adobe Photoshop.

## What It Does

- Extracts recent photos from macOS Photos using `src/fetcher.py` when needed.
- Groups image files by timestamp into focus stacks with `src/grouper.py`.
- Runs `src/scripts/stacker.js` in Photoshop only when valid groups exist.
- Skips Photoshop automatically when no focus stacking groups are created.

## Quick Start

### Prerequisites
- macOS
- Adobe Photoshop
- Python 3.8+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Configure
Copy `settings.txt` and edit it for your environment:

```bash
cp settings.txt my_settings.txt
```

Example config:

```json
{
    "hours_icloud": "24",
    "stacker": "stacker.js",
    "folder_grouped": "fs",
    "path_all_storing": "/Volumes/External HD/Naturalist/",
    "folder_current_storing": "!newstack",
    "photoshop_app": "Adobe Photoshop 2026",
    "process_subfolders_with_photoshop": false,
    "skip_icloud_fetcher": false
}
```

### Run the workflow

```bash
python main.py
```

## Workflow Summary

1. `runner.py` loads settings and inspects `path_all_storing`.
2. It decides whether to fetch photos, group existing photos, or create a new working folder.
3. `fetcher.py` exports recent Photos library images into the current work folder when required.
4. `grouper.py` scans images, groups them into stacks, and creates an `fs` subfolder.
5. `stacker.js` runs in Photoshop only if the `fs` folder contains valid groups.

## Important Behavior

- `stacker` is resolved from `src/scripts/stacker.js` when a relative path is used.
- `folder_grouped` is the folder name created by `grouper.py` and processed by Photoshop.
- Workflow exits cleanly without Photoshop if no groups are found.
- Supported image formats: JPG, JPEG, TIFF, TIF, BMP, PNG, HEIC.
- When `process_subfolders_with_photoshop` is `true`, the workflow checks the current working folder for immediate subfolders that contain images (excluding the `fs` folder). If such subfolders exist, it also checks for image files directly in the parent folder. Root-level images are processed by grouper, and any image-bearing subfolders are passed to Photoshop so everything is handled in one run.

## Project Layout

```
main.py
settings.txt
requirements.txt
StackDealer.applescript
StackDealer.app/
src/
  runner.py
  fetcher.py
  grouper.py
  folder_manager.py
  scripts/
    stacker.js
tests/
  test_enhanced_workflow.py
  test_integration.py
  test_no_groups.py
demos/
  demo_enhanced_workflow.py
```

## Component Roles

- `main.py`: entry point, calls `src.runner.main()`.
- `src/runner.py`: orchestrates the workflow and determines the next action.
- `src/fetcher.py`: exports photos from Photos to the current working folder.
- `src/grouper.py`: groups images into focus stacks based on timestamp proximity.
- `src/folder_manager.py`: decides folder state and workflow routing.
- `src/scripts/stacker.js`: automates Photoshop stacking for grouped folders.

## Configuration Notes

Required settings:
- `hours_icloud`
- `stacker`
- `folder_grouped`
- `path_all_storing`
- `folder_current_storing`
- `photoshop_app`
- `process_subfolders_with_photoshop` (optional, defaults to `false`)
- `skip_icloud_fetcher` (optional, defaults to `false`; when `true`, the workflow skips the iCloud photo import step and proceeds with whatever files are already in the current working folder)

### Subfolder mode behavior
When `process_subfolders_with_photoshop` is `true`, the workflow keeps the existing root-file grouping behavior and additionally processes subfolders directly in Photoshop.
- If the root folder contains image files, those files are grouped by `grouper.py` into the `fs` folder.
- If the root folder contains one or more image-bearing subfolders, Photoshop is given the root folder itself (`path_all_storing/folder_current_storing`) rather than `.../fs`.
- This allows both root-level grouping and subfolder stacking to work together in the same run.

Tuning in `src/grouper.py`:
- `MAX_TIME_DELTA = timedelta(seconds=2)`
- `MIN_STACK_LEN = 5`

Change these if your capture interval differs or you need larger or smaller stacks.

## Troubleshooting

- If Photoshop does not run, `grouper.py` likely created no stacks.
- If the stacker file is missing, verify `stacker` points to a valid file and is resolved from `src/scripts/` when relative.
- If Photoshop fails, confirm `photoshop_app` matches the installed application name.
- If no images are found, check the current working folder contents and fetcher permissions.

## Testing and linting

Run the full Python test suite with pytest:

```bash
pytest tests
```

Run static checks with flake8:

```bash
python -m flake8 src tests main.py --count --select=E9,F63,F7,F82 --show-source --statistics
```

Run type checking with mypy:

```bash
python -m mypy src
```

## Minimal example

```bash
cp settings.txt my_settings.txt
python main.py
```

The workflow performs settings validation, folder analysis, optional photo fetching, grouping, and conditional Photoshop stacking.
