"""Command-line interface for XPCS Power User Tools using argparse."""

import argparse
import logging
import sys
from pathlib import Path
import subprocess
import importlib.util

from . import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def convert_legacy_command(args):
    """Convert legacy XPCS datasets to the new NeXus format."""
    from .utils.convert_legacy_datasets import process_folder

    logger.info(
        f"Converting legacy datasets from {args.source_folder} to {args.dest_folder}"
    )
    logger.info(
        f"File type: {args.ftype}, Workers: {args.workers}, Copy data: {args.copy_data}"
    )

    try:
        process_folder(
            args.source_folder,
            args.dest_folder,
            max_workers=args.workers,
            ftype=args.ftype,
            copy_data=args.copy_data,
        )
        logger.info("Conversion completed successfully!")
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        sys.exit(1)


def nexus_to_csv_command(args):
    """Convert HDF5/NeXus files to CSV format."""
    from .utils.convert_nexus_to_csv import hdf2csv
    import os

    logger.info(f"Converting HDF5 files from {args.input} to CSV in {args.output}")
    if args.filter:
        logger.info(f"Using filter: {args.filter}")

    os.makedirs(args.output, exist_ok=True)

    converted_count = 0
    for filename in os.listdir(args.input):
        if (filename.endswith(".hdf") or filename.endswith(".hdf5")) and (
            args.filter in filename
        ):
            full_path = os.path.join(args.input, filename)
            try:
                hdf2csv(full_path, args.output)
                converted_count += 1
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

    logger.info(f"Converted {converted_count} files successfully!")


def export_nexus_command(args):
    """Extract intensity, g2, q-values, and time-delays into a compact NeXus file."""
    from .utils.export_nexus import export_nexus

    output = args.output or f"{Path(args.hdf_file).stem}_export.nxs"

    logger.info(f"Exporting {args.hdf_file} to {output}")

    try:
        export_nexus(args.hdf_file, output)
        logger.info("Export completed successfully!")
    except Exception as e:
        logger.error(f"Error during export: {e}")
        sys.exit(1)


def aps28id_convert_command(args):
    """Merge a raw APS 28-ID XPCS detector HDF5 file with its matched .spec metadata."""
    from .aps28id_converter.build_xpcs_metadata_h5 import run as run_aps28id_convert

    logger.info(f"Converting {args.raw_fname}")

    try:
        for path in run_aps28id_convert(args):
            logger.info(f"Wrote {path}")
        logger.info("Conversion completed successfully!")
    except Exception as e:
        logger.error(f"Error during conversion: {e}")
        sys.exit(1)


def run_script_command(args):
    """Run a Python script from the utils directory."""
    script_path = Path(args.script_path)

    if not script_path.suffix == ".py":
        logger.error("Error: Script must be a Python file (.py)")
        sys.exit(1)

    logger.info(f"Running script: {script_path}")

    # Run the script with the provided arguments
    cmd = [sys.executable, str(script_path)] + list(args.args)

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        sys.exit(result.returncode)
    except Exception as e:
        logger.error(f"Error running script: {e}")
        sys.exit(1)


def g2_average_command(args):
    """Run G2 averaging analysis on HDF5 files."""
    from pathlib import Path
    import subprocess
    import sys

    # Find the G2_average script
    package_dir = Path(__file__).parent
    g2_script = package_dir / "utils" / "G2_average" / "reaverage_master_plan.py"

    if not g2_script.exists():
        logger.error(f"Error: G2 average script not found at {g2_script}")
        sys.exit(1)

    # Use default config if not provided
    if not args.config:
        args.config = package_dir / "utils" / "G2_average" / "reaverage_info.json"

    logger.info(f"Processing {args.hdf_file} with G2 averaging")
    logger.info(f"Using config: {args.config}")

    # Run the G2 average script
    cmd = [sys.executable, str(g2_script), str(args.hdf_file)]

    if args.output:
        # Modify the command to include output directory if needed
        cmd.extend(["--output", str(args.output)])

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            logger.info("G2 averaging completed successfully!")
        else:
            logger.error("G2 averaging failed!")
            sys.exit(result.returncode)
    except Exception as e:
        logger.error(f"Error running G2 average: {e}")
        sys.exit(1)


def fast_g2_average_command(args):
    """Run fast G2 averaging analysis on HDF5 files."""
    from pathlib import Path
    import subprocess
    import sys

    # Find the fast_G2_average script
    package_dir = Path(__file__).parent
    g2_script = package_dir / "utils" / "fast_G2_average" / "fast_G2_average.py"

    if not g2_script.exists():
        logger.error(f"Error: Fast G2 average script not found at {g2_script}")
        sys.exit(1)

    # Use default config if not provided
    if not args.config:
        args.config = package_dir / "utils" / "fast_G2_average" / "G2average_info.json"

    logger.info(f"Processing {args.hdf_file} with fast G2 averaging")
    logger.info(f"Using config: {args.config}")

    # Run the fast G2 average script
    cmd = [sys.executable, str(g2_script), str(args.hdf_file)]

    if args.output:
        # Modify the command to include output directory if needed
        cmd.extend(["--output", str(args.output)])

    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            logger.info("Fast G2 averaging completed successfully!")
        else:
            logger.error("Fast G2 averaging failed!")
            sys.exit(result.returncode)
    except Exception as e:
        logger.error(f"Error running fast G2 average: {e}")
        sys.exit(1)


def link_files_command(args):
    """Create symbolic links for files from multiple source directories."""
    from .utils.link_and_gather_files import link_and_gather_files, setup_logging
    import time

    setup_logging()

    logger.info(
        f"Linking files from {len(args.source)} source director{'y' if len(args.source) == 1 else 'ies'}"
    )
    logger.info(f"Destination: {args.destination}")

    if args.repeat_time:
        logger.info(
            f"Repeat mode: Running every {args.repeat_time} seconds (Press Ctrl+C to stop)"
        )
        try:
            while True:
                link_and_gather_files(args.source, args.destination)
                logger.info(f"Waiting {args.repeat_time} seconds before next run...")
                time.sleep(args.repeat_time)
        except KeyboardInterrupt:
            logger.info("\nStopped by user (Ctrl+C)")
            sys.exit(0)
    else:
        link_and_gather_files(args.source, args.destination)


def list_utils_command(args):
    """List all available utility scripts and their descriptions."""
    from pathlib import Path

    package_dir = Path(__file__).parent
    utils_dir = package_dir / "utils"

    logger.info("Available XPCS Power User utilities:\n")

    # List main utilities
    logger.info("Main Commands:")
    logger.info("  convert-legacy      - Convert legacy XPCS datasets to NeXus format")
    logger.info("  nexus-to-csv       - Convert HDF5/NeXus files to CSV format")
    logger.info("  export-nexus       - Extract intensity, g2, q-values, and time-delays into a compact NeXus file")
    logger.info("  aps28id-convert    - Merge a raw APS 28-ID detector HDF5 file with its matched .spec metadata")
    logger.info("  g2-average         - Run G2 averaging analysis")
    logger.info("  fast-g2-average    - Run fast G2 averaging analysis")
    logger.info(
        "  link-files         - Create symbolic links from multiple sources to destination"
    )
    logger.info("  run-script         - Run any Python script from utils")

    logger.info("\nPython Scripts in utils/:")

    # List Python files in utils
    for py_file in sorted(utils_dir.glob("*.py")):
        if not py_file.name.startswith("__"):
            logger.info(f"  {py_file.name}")

    # List subdirectories
    logger.info("\nSubdirectories:")
    for subdir in sorted(utils_dir.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith("__"):
            logger.info(f"  {subdir.name}/")
            # List Python files in subdirectory
            for py_file in sorted(subdir.glob("*.py")):
                logger.info(f"    - {py_file.name}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="xpcs-poweruser",
        description="XPCS Power User Tools - A collection of utilities for XPCS data analysis.",
        epilog="Use 'xpcs-poweruser COMMAND --help' for more information on a specific command.",
    )

    # Add version argument
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Convert legacy command
    convert_parser = subparsers.add_parser(
        "convert-legacy",
        help="Convert legacy XPCS datasets to the new NeXus format",
        description="This command processes legacy XPCS data by searching for subfolders containing "
        "paired data files and metadata files, then converts them to the new format.",
    )
    convert_parser.add_argument(
        "source_folder", type=str, help="Source folder containing legacy datasets"
    )
    convert_parser.add_argument(
        "dest_folder", type=str, help="Destination folder for converted datasets"
    )
    convert_parser.add_argument(
        "--workers", type=int, default=1, help="Number of parallel worker processes"
    )
    convert_parser.add_argument(
        "--ftype",
        choices=[".bin", ".imm", ".h5"],
        default=".bin",
        help="File type/extension of raw data files",
    )
    convert_parser.add_argument(
        "--copy-data",
        action="store_true",
        help="Copy data files instead of creating symbolic links",
    )
    convert_parser.set_defaults(func=convert_legacy_command)

    # Nexus to CSV command
    nexus_parser = subparsers.add_parser(
        "nexus-to-csv",
        help="Convert HDF5/NeXus files to CSV format",
        description="This command extracts G2, SAXS, and metadata information from HDF5 files "
        "and saves them as separate CSV files.",
    )
    nexus_parser.add_argument(
        "-i", "--input", required=True, help="Path to the folder with HDF5 files"
    )
    nexus_parser.add_argument(
        "-o", "--output", required=True, help="Path to save CSV files"
    )
    nexus_parser.add_argument(
        "-f", "--filter", default="", help="Optional substring filter for filenames"
    )
    nexus_parser.set_defaults(func=nexus_to_csv_command)

    # Export nexus command
    export_parser = subparsers.add_parser(
        "export-nexus",
        help="Extract intensity, g2, q-values, and time-delays into a compact NeXus file",
        description="This command extracts key derived quantities (intensity, g2, q-values, "
        "time-delays) and metadata from a processed HDF5/NeXus file into a new, smaller NeXus "
        "file plus metadata exports (JSON/TXT/XLSX).",
    )
    export_parser.add_argument("hdf_file", help="HDF5/NeXus file to process")
    export_parser.add_argument(
        "-o",
        "--output",
        help="Path to the output NeXus file (default: <input_basename>_export.nxs)",
    )
    export_parser.set_defaults(func=export_nexus_command)

    # APS 28-ID convert command
    from .aps28id_converter.build_xpcs_metadata_h5 import add_arguments as add_aps28id_arguments

    aps28id_parser = subparsers.add_parser(
        "aps28id-convert",
        help="Merge a raw APS 28-ID XPCS detector HDF5 file with its matched .spec metadata",
        description="This command merges a raw APS 28-ID detector HDF5 file with its matched "
        ".spec metadata and the APS_28ID_XPCS_metadata_template.hdf schema template into a "
        "standardized XPCS metadata HDF5 file.",
    )
    add_aps28id_arguments(aps28id_parser)
    aps28id_parser.set_defaults(func=aps28id_convert_command)

    # Run script command
    script_parser = subparsers.add_parser(
        "run-script",
        help="Run a Python script from the utils directory",
        description="This command allows you to run any Python script with custom arguments.",
    )
    script_parser.add_argument("script_path", help="Path to the Python script")
    script_parser.add_argument(
        "args", nargs="*", help="Arguments to pass to the script"
    )
    script_parser.set_defaults(func=run_script_command)

    # G2 average command
    g2_parser = subparsers.add_parser(
        "g2-average",
        help="Run G2 averaging analysis on HDF5 files",
        description="This command processes HDF5 files to compute G2 averages using the "
        "configuration specified in the JSON file.",
    )
    g2_parser.add_argument("hdf_file", help="HDF5 file to process")
    g2_parser.add_argument(
        "-o", "--output", help="Output directory for G2 average results"
    )
    g2_parser.add_argument(
        "-c", "--config", help="Path to G2average_info.json config file"
    )
    g2_parser.set_defaults(func=g2_average_command)

    # Fast G2 average command
    fast_g2_parser = subparsers.add_parser(
        "fast-g2-average",
        help="Run fast G2 averaging analysis on HDF5 files",
        description="This command processes HDF5 files to compute G2 averages using an optimized "
        "algorithm for faster processing.",
    )
    fast_g2_parser.add_argument("hdf_file", help="HDF5 file to process")
    fast_g2_parser.add_argument(
        "-o", "--output", help="Output directory for fast G2 average results"
    )
    fast_g2_parser.add_argument(
        "-c", "--config", help="Path to G2average_info.json config file"
    )
    fast_g2_parser.set_defaults(func=fast_g2_average_command)

    # Link files command
    link_parser = subparsers.add_parser(
        "link-files",
        help="Create symbolic links for files from multiple source directories",
        description="This command creates symbolic links from multiple source directories "
        "to a single destination directory. Optionally supports repeat mode for continuous monitoring.",
    )
    link_parser.add_argument(
        "--source",
        "-s",
        nargs="+",
        required=True,
        help="One or more source directories to link files from",
    )
    link_parser.add_argument(
        "--destination",
        "-d",
        required=True,
        help="Destination directory for symbolic links",
    )
    link_parser.add_argument(
        "-r",
        "--repeat-time",
        type=int,
        help="Optional: Repeat linking every N seconds (continuous mode)",
    )
    link_parser.set_defaults(func=link_files_command)

    # List utils command
    list_parser = subparsers.add_parser(
        "list-utils", help="List all available utility scripts and their descriptions"
    )
    list_parser.set_defaults(func=list_utils_command)

    # Parse arguments
    args = parser.parse_args()

    # If no command is provided, print help
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Execute the command
    args.func(args)


if __name__ == "__main__":
    main()
