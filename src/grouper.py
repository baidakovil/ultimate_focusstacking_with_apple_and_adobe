## ultimate_focusstacking_with_apple_and_adobe — Utility to reallocate photos taken for focus stacking into folders.
# Copyright (C) 2023 Ilia Baidakov <baidakovil@gmail.com>
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with this
# program.  If not, see <https://www.gnu.org/licenses/>.
"""This is the only file needed to run ultimate_focusstacking_with_apple_and_adobe. Check settings before using."""

import operator
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import piexif

#  Name of the future root folder where stacks will be located
FOLDER_NAME_ROOT = 'fs'

#  Maximum time interval between stacked photos
MAX_TIME_DELTA = timedelta(seconds=2)

#  Min quantity of file to create separate folder
MIN_STACK_LEN = 5

#  If stack larger than this, program will print warning message, but create stack
LENGTH_STACK_WARNING = 10

#  Datetime format used in cameras exif
TIMESTAMP_FORMAT_EXIF = '%Y:%m:%d %H:%M:%S'


def _normalize_extension(ext: str) -> str:
    """Normalize equivalent file extensions to a common representation."""
    ext = ext.lower()
    if ext in {'.jpg', '.jpeg'}:
        return '.jpg'
    if ext in {'.tif', '.tiff'}:
        return '.tiff'
    return ext


def read_jpg(jpg_folder: str) -> Tuple[List[str], List[datetime]]:
    """
    Read names of image files in source folder and timestamps when they were taken.
    Args:
        jpg_folder: path to folder where image files are stored
    Returns:
        list of names & list of datetimes (synchronized pairs)
    """
    print('\nRead image files...', end='')

    # Supported image file extensions
    image_extensions = {'.arw', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.png', '.heic'}

    names = []
    for file in os.listdir(jpg_folder):
        if os.path.isfile(os.path.join(jpg_folder, file)):
            _, ext = os.path.splitext(file)
            if ext.lower() in image_extensions:
                names.append(file)

    names = sorted(names)

    if len(names) != 0:
        # Ensure source files are all the same type
        extension_set = {
            _normalize_extension(os.path.splitext(name)[1].lower()) for name in names
        }
        if len(extension_set) > 1:
            actual_exts = sorted({os.path.splitext(name)[1].lower() for name in names})
            print('\n🚨 CRITICAL ERROR 🚨')
            print('❌ Mixed source image types detected. Only one file type may be processed at a time.')
            print(f'❌ Found types: {", ".join(actual_exts)}')
            sys.exit(1)

        print(f'ok.\nGot {len(names)} image files in folder')
    else:
        print('\nNo image files in folder! Exit')
        sys.exit(1)

    # Extract timestamps with error handling
    photo_data = []
    skipped_files = []

    for name in names:
        try:
            file_path = os.path.join(jpg_folder, name)
            exif_dict = piexif.load(file_path)

            # Check if EXIF has DateTime tag
            if '0th' in exif_dict and 306 in exif_dict['0th']:
                date_bytes = exif_dict['0th'][306]
                # Proper EXIF datetime decoding
                if isinstance(date_bytes, bytes):
                    date_str = date_bytes.decode('ascii').rstrip('\x00')
                else:
                    date_str = str(date_bytes).strip()

                date_obj = datetime.strptime(date_str, TIMESTAMP_FORMAT_EXIF)
                photo_data.append((name, date_obj))
            else:
                print(f'\n⚠️  WARNING: No DateTime EXIF data in {name} - skipping file')
                skipped_files.append(name)

        except Exception as e:
            print(f'\n🚨 CRITICAL EXIF ERROR 🚨')
            print(f'❌ FAILED TO READ EXIF FROM: {name}')
            print(f'❌ ERROR: {str(e)}')
            print(f'❌ THIS FILE WILL BE SKIPPED')
            skipped_files.append(name)

    if not photo_data:
        print(f'\n🚨 CRITICAL ERROR 🚨')
        print(f'❌ NO FILES WITH VALID EXIF TIMESTAMPS FOUND!')
        print(f'❌ CANNOT PROCEED WITH FOCUS STACKING')
        sys.exit(1)

    if skipped_files:
        print(f'\n⚠️  Skipped {len(skipped_files)} files without valid EXIF timestamps')

    # Sort by timestamp to maintain name-date synchronization
    photo_data.sort(key=lambda x: x[1])
    names = [name for name, _ in photo_data]
    dates = [timestamp for _, timestamp in photo_data]

    print(
        f'Got {len(dates)} valid timestamps in image files\nFROM: {dates[0]} \nTO  : {dates[-1]}\n'
    )

    return names, dates


def get_stacks(names: List[str], dates: List[datetime]) -> List[List[str]]:
    """
    Main function, creating list of stacks (list of lists) and print statistics on size
    of stacks.
    Args:
        names: list of photo names
        dates: list of dates from photos
    Returns:
        List of stacks
    """

    def done_stack(
        stacks: List[List[str]],
        stack_stat: Dict[int, int],
        stack: List[str],
    ) -> Tuple[List[List[str]], Dict[int, int]]:
        """
        Function to send new 'closed' jpg-filenames-list (stack) to list of stacks if
        needed, and refresh statistics on stack lenghts.
        Args:
            stacks: list of stacks
            stack_stat: dict with statistics on stack sizes
            stack: current ended ('closed') stack
        Returns:
            renewed list of stacks & renewed statistics
        """
        if len(stack) >= MIN_STACK_LEN:
            stacks.append(stack)
            stack_stat[len(stack)] = stack_stat.get(len(stack), 0) + 1
            if len(stack) > LENGTH_STACK_WARNING:
                print(
                    f'Strange long stack ({len(stack)}) elements. From {stack[0]} to {stack[-1]}'
                )
        return stacks, stack_stat

    stack = []
    stacks: List[List[str]] = []
    stack_stat: Dict[int, int] = {}

    # Handle edge case: no photos to process
    if not names:
        return stacks

    stack.append(names[0])

    for i in range(1, len(dates)):
        delta = dates[i] - dates[i - 1]
        if delta <= MAX_TIME_DELTA:
            #  Dates near each other -> Add name to stack.
            stack.append(names[i])  # type: ignore
            if i == (len(dates) - 1):
                #  Finish cycle with adding stack to stacks.
                stacks, stack_stat = done_stack(stacks, stack_stat, stack)  # type: ignore
                del stack  # type: ignore
        else:
            # Dates far from each other -> Add stack to stacks
            stacks, stack_stat = done_stack(stacks, stack_stat, stack)  # type: ignore
            if i == (len(dates) - 1):
                # Finish cycle
                del stack  # type: ignore
            else:
                # Start new stack
                stack = [names[i]]

    # Handle single photo edge case - if stack still exists, process it
    if 'stack' in locals() and stack:
        stacks, stack_stat = done_stack(stacks, stack_stat, stack)

    #  Below just prettyprint
    for stacksize, stackcount in sorted(stack_stat.items(), key=operator.itemgetter(0)):
        spacer = ' ' if stacksize < 10 else ''
        print(f'Stack size {spacer}{stacksize} files: {stackcount} stacks')
    return stacks


def build_unique_stack_path(fs_folder_path: str, base_name: str) -> str:
    """Return a non-conflicting stack folder path for a given base name."""
    candidate = os.path.join(fs_folder_path, base_name)
    if not os.path.exists(candidate):
        return candidate

    suffix = 1
    while True:
        candidate = os.path.join(fs_folder_path, f"{base_name}_{suffix}")
        if not os.path.exists(candidate):
            return candidate
        suffix += 1


def get_renamed_stack_path(base_name: str, final_path: str) -> str:
    """Return the final stack folder name, or an empty string when no rename was needed."""
    if final_path.endswith(base_name):
        return ""
    return os.path.basename(final_path)


def move_stacks(stacks: List[List[str]], jpg_folder: str) -> None:
    """
    Create 'fs' folder -> all the stack-folders inside of it -> move image-files-list
    (stacks) to their final folders
    Args:
        stacks: list of stacks
        jpg_folder: folder where located files in `stacks`
    """
    if not stacks:
        print('No stacks here! Exit')
        sys.exit(2)

    # Check if 'fs' folder already exists
    fs_folder_path = os.path.join(jpg_folder, FOLDER_NAME_ROOT)
    if os.path.exists(fs_folder_path):
        print(f'\n🚨 CRITICAL ERROR 🚨')
        print(f'❌ FOLDER "{FOLDER_NAME_ROOT}" ALREADY EXISTS!')
        print(f'❌ PATH: {fs_folder_path}')
        print(f'❌ CANNOT PROCEED - THIS INDICATES PHOTOS WERE ALREADY PROCESSED')
        print(f'❌ PLEASE REMOVE THE FOLDER OR USE A DIFFERENT DIRECTORY')
        sys.exit(1)

    folder_count, file_count = 0, 0
    os.mkdir(fs_folder_path)
    print(f'\nRoot folder {FOLDER_NAME_ROOT} created')
    print('Start moving files...', end='')

    for stack in stacks:
        # Safer filename handling for folder naming
        def safe_filename_for_folder(filename):
            name, ext = os.path.splitext(filename)
            return name if name else filename

        #  Prepare folder for moving files to
        first_name = safe_filename_for_folder(stack[0])
        last_name = safe_filename_for_folder(stack[-1])
        stack_dirname = f"{first_name}_to_{last_name}"
        stack_path = os.path.join(fs_folder_path, stack_dirname)

        stack_path = build_unique_stack_path(fs_folder_path, stack_dirname)
        renamed_path = get_renamed_stack_path(stack_dirname, stack_path)
        if renamed_path:
            print(f'  Renamed stack folder to: {renamed_path}')
        os.mkdir(stack_path)
        folder_count += 1

        #  Move files from origin to new folders
        for name in stack:
            src = os.path.join(jpg_folder, name)
            dst = os.path.join(stack_path, name)

            # Check if source file exists
            if not os.path.exists(src):
                print(f'\n🚨 CRITICAL ERROR 🚨')
                print(f'❌ SOURCE FILE NOT FOUND: {name}')
                print(f'❌ PATH: {src}')
                print(f'❌ CANNOT CONTINUE FILE MOVING')
                sys.exit(1)

            # Check if destination file already exists
            if os.path.exists(dst):
                print(f'\n🚨 CRITICAL ERROR 🚨')
                print(f'❌ DESTINATION FILE ALREADY EXISTS: {name}')
                print(f'❌ PATH: {dst}')
                print(f'❌ ABORTING TO PREVENT FILE OVERWRITE')
                sys.exit(1)

            try:
                os.rename(src, dst)
                file_count += 1
            except Exception as e:
                print(f'\n🚨 CRITICAL FILE MOVE ERROR 🚨')
                print(f'❌ FAILED TO MOVE: {name}')
                print(f'❌ FROM: {src}')
                print(f'❌ TO: {dst}')
                print(f'❌ ERROR: {str(e)}')
                sys.exit(1)

    print(f'Ok:\n{folder_count} folders created\n{file_count} files moved')


def main(jpg_folder: str) -> None:
    """
    Start the process. Start!
    Args:
        jpg_folder: Path to folder with image files.
    """
    print('START\n')

    # Normalize the path to handle special characters and ensure it exists
    jpg_folder = os.path.abspath(os.path.expanduser(jpg_folder))

    if not os.path.exists(jpg_folder):
        print(f"Error: Path does not exist: {jpg_folder}")
        sys.exit(1)

    if not os.path.isdir(jpg_folder):
        print(f"Error: Path is not a directory: {jpg_folder}")
        sys.exit(1)

    names, dates = read_jpg(jpg_folder)
    stacks = get_stacks(names, dates)
    move_stacks(stacks, jpg_folder)
    print('\nFINISH')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python group_photos.py <image_folder_path>")
        print(
            "Note: If path contains special characters like '!', wrap it in single quotes"
        )
        print("Example: python group_photos.py '/path/with/special!chars'")
        sys.exit(1)
    main(sys.argv[1])
