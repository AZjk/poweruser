#!/usr/bin/env python3
"""
Link and Gather Files Script

This script creates symbolic links in a destination folder for files found in
multiple source directories. It can optionally repeat this process at regular intervals.
"""

import argparse
import sys
import time
import logging
from pathlib import Path
from typing import List


def setup_logging():
    """Configure logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def gather_files_from_sources(source_dirs: List[str]) -> List[Path]:
    """
    Gather all files from the source directories.

    Args:
        source_dirs: List of source directory paths

    Returns:
        List of Path objects for all files found
    """
    all_files = []

    for source_dir in source_dirs:
        source_path = Path(source_dir).resolve()

        if not source_path.exists():
            logging.warning(f"Source directory does not exist: {source_dir}")
            continue

        if not source_path.is_dir():
            logging.warning(f"Source path is not a directory: {source_dir}")
            continue

        # Recursively find all files
        try:
            for item in source_path.rglob("*"):
                if item.is_file():
                    all_files.append(item)
        except PermissionError as e:
            logging.error(f"Permission denied accessing {source_dir}: {e}")
        except Exception as e:
            logging.error(f"Error scanning {source_dir}: {e}")

    return all_files


def create_symlinks(files: List[Path], destination: str) -> tuple:
    """
    Create symbolic links in the destination folder for files that don't already have them.

    Args:
        files: List of file paths to link
        destination: Destination directory path

    Returns:
        Tuple of (created_count, skipped_count, error_count)
    """
    dest_path = Path(destination).resolve()

    # Create destination directory if it doesn't exist
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create destination directory {destination}: {e}")
        return (0, 0, len(files))

    created_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in files:
        # Use the filename for the symlink name
        link_name = file_path.name
        link_path = dest_path / link_name

        # Check if symlink already exists
        if link_path.exists() or link_path.is_symlink():
            # Check if it's a valid symlink pointing to the same file
            if link_path.is_symlink():
                try:
                    if link_path.resolve() == file_path.resolve():
                        logging.debug(
                            f"Symlink already exists and is valid: {link_name}"
                        )
                        skipped_count += 1
                        continue
                    else:
                        logging.warning(
                            f"Symlink exists but points to different file: {link_name}"
                        )
                        # Handle naming conflict by appending a suffix
                        base_name = file_path.stem
                        extension = file_path.suffix
                        counter = 1
                        while True:
                            new_link_name = f"{base_name}_{counter}{extension}"
                            link_path = dest_path / new_link_name
                            if not link_path.exists():
                                link_name = new_link_name
                                break
                            counter += 1
                except Exception as e:
                    logging.error(f"Error checking symlink {link_name}: {e}")
                    error_count += 1
                    continue
            else:
                logging.warning(f"File already exists (not a symlink): {link_name}")
                skipped_count += 1
                continue

        # Create the symbolic link
        try:
            link_path.symlink_to(file_path)
            logging.info(f"Created symlink: {link_name} -> {file_path}")
            created_count += 1
        except FileExistsError:
            logging.warning(f"Symlink already exists: {link_name}")
            skipped_count += 1
        except PermissionError as e:
            logging.error(f"Permission denied creating symlink for {link_name}: {e}")
            error_count += 1
        except Exception as e:
            logging.error(f"Failed to create symlink for {link_name}: {e}")
            error_count += 1

    return (created_count, skipped_count, error_count)


def link_and_gather_files(source_dirs: List[str], destination: str):
    """
    Main function to gather files from sources and create symlinks in destination.

    Args:
        source_dirs: List of source directory paths
        destination: Destination directory path
    """
    logging.info(
        f"Scanning {len(source_dirs)} source director{'y' if len(source_dirs) == 1 else 'ies'}..."
    )

    # Gather all files from source directories
    files = gather_files_from_sources(source_dirs)
    logging.info(f"Found {len(files)} file(s) in source directories")

    if not files:
        logging.warning("No files found in source directories")
        return

    # Create symlinks
    logging.info(f"Creating symlinks in: {destination}")
    created, skipped, errors = create_symlinks(files, destination)

    # Summary
    logging.info(f"Summary: {created} created, {skipped} skipped, {errors} errors")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Create symbolic links in a destination folder for files from multiple source directories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --source /path/to/dir1 /path/to/dir2 --destination /output/folder
  %(prog)s --source /data/source1 --destination /data/links --repeat-time 60
        """,
    )

    parser.add_argument(
        "--source",
        nargs="+",
        required=True,
        help="One or more source directories to scan for files",
    )

    parser.add_argument(
        "--destination",
        required=True,
        help="Destination directory where symbolic links will be created",
    )

    parser.add_argument(
        "--repeat-time",
        type=int,
        metavar="SECONDS",
        help="Repeat the linking process every SECONDS seconds (runs continuously until interrupted)",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    try:
        if args.repeat_time:
            if args.repeat_time <= 0:
                logging.error("--repeat-time must be a positive integer")
                sys.exit(1)

            logging.info(f"Running in repeat mode (every {args.repeat_time} seconds)")
            logging.info("Press Ctrl+C to stop")

            try:
                while True:
                    link_and_gather_files(args.source, args.destination)
                    logging.info(
                        f"Waiting {args.repeat_time} seconds before next run..."
                    )
                    time.sleep(args.repeat_time)
            except KeyboardInterrupt:
                logging.info("\nStopped by user (Ctrl+C)")
                sys.exit(0)
        else:
            # Run once
            link_and_gather_files(args.source, args.destination)

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
