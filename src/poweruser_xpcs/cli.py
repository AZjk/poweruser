"""Command-line interface for XPCS Power User Tools using argparse."""

import argparse
import sys
from pathlib import Path
import subprocess
import importlib.util

from . import __version__


def convert_legacy_command(args):
    """Convert legacy XPCS datasets to the new NeXus format."""
    from .utils.convert_legacy_datasets import process_folder
    
    print(f"Converting legacy datasets from {args.source_folder} to {args.dest_folder}")
    print(f"File type: {args.ftype}, Workers: {args.workers}, Copy data: {args.copy_data}")
    
    try:
        process_folder(args.source_folder, args.dest_folder, max_workers=args.workers, 
                      ftype=args.ftype, copy_data=args.copy_data)
        print("Conversion completed successfully!")
    except Exception as e:
        print(f"Error during conversion: {e}", file=sys.stderr)
        sys.exit(1)


def nexus_to_csv_command(args):
    """Convert HDF5/NeXus files to CSV format."""
    from .utils.convert_nexus_to_csv import hdf2csv
    import os
    
    print(f"Converting HDF5 files from {args.input} to CSV in {args.output}")
    if args.filter:
        print(f"Using filter: {args.filter}")
    
    os.makedirs(args.output, exist_ok=True)
    
    converted_count = 0
    for filename in os.listdir(args.input):
        if (filename.endswith('.hdf') or filename.endswith('.hdf5')) and (args.filter in filename):
            full_path = os.path.join(args.input, filename)
            try:
                hdf2csv(full_path, args.output)
                converted_count += 1
            except Exception as e:
                print(f"Error processing {filename}: {e}", file=sys.stderr)
    
    print(f"Converted {converted_count} files successfully!")


def run_script_command(args):
    """Run a Python script from the utils directory."""
    script_path = Path(args.script_path)
    
    if not script_path.suffix == '.py':
        print("Error: Script must be a Python file (.py)", file=sys.stderr)
        sys.exit(1)
    
    print(f"Running script: {script_path}")
    
    # Run the script with the provided arguments
    cmd = [sys.executable, str(script_path)] + list(args.args)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"Error running script: {e}", file=sys.stderr)
        sys.exit(1)


def g2_average_command(args):
    """Run G2 averaging analysis on HDF5 files."""
    from pathlib import Path
    import subprocess
    import sys
    
    # Find the G2_average script
    package_dir = Path(__file__).parent
    g2_script = package_dir / 'utils' / 'G2_average' / 'reaverage_master_plan.py'
    
    if not g2_script.exists():
        print(f"Error: G2 average script not found at {g2_script}", file=sys.stderr)
        sys.exit(1)
    
    # Use default config if not provided
    if not args.config:
        args.config = package_dir / 'utils' / 'G2_average' / 'reaverage_info.json'
    
    print(f"Processing {args.hdf_file} with G2 averaging")
    print(f"Using config: {args.config}")
    
    # Run the G2 average script
    cmd = [sys.executable, str(g2_script), str(args.hdf_file)]
    
    if args.output:
        # Modify the command to include output directory if needed
        cmd.extend(['--output', str(args.output)])
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            print("G2 averaging completed successfully!")
        else:
            print("G2 averaging failed!", file=sys.stderr)
            sys.exit(result.returncode)
    except Exception as e:
        print(f"Error running G2 average: {e}", file=sys.stderr)
        sys.exit(1)


def fast_g2_average_command(args):
    """Run fast G2 averaging analysis on HDF5 files."""
    from pathlib import Path
    import subprocess
    import sys
    
    # Find the fast_G2_average script
    package_dir = Path(__file__).parent
    g2_script = package_dir / 'utils' / 'fast_G2_average' / 'fast_G2_average.py'
    
    if not g2_script.exists():
        print(f"Error: Fast G2 average script not found at {g2_script}", file=sys.stderr)
        sys.exit(1)
    
    # Use default config if not provided
    if not args.config:
        args.config = package_dir / 'utils' / 'fast_G2_average' / 'G2average_info.json'
    
    print(f"Processing {args.hdf_file} with fast G2 averaging")
    print(f"Using config: {args.config}")
    
    # Run the fast G2 average script
    cmd = [sys.executable, str(g2_script), str(args.hdf_file)]
    
    if args.output:
        # Modify the command to include output directory if needed
        cmd.extend(['--output', str(args.output)])
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            print("Fast G2 averaging completed successfully!")
        else:
            print("Fast G2 averaging failed!", file=sys.stderr)
            sys.exit(result.returncode)
    except Exception as e:
        print(f"Error running fast G2 average: {e}", file=sys.stderr)
        sys.exit(1)


def list_utils_command(args):
    """List all available utility scripts and their descriptions."""
    from pathlib import Path
    
    package_dir = Path(__file__).parent
    utils_dir = package_dir / 'utils'
    
    print("Available XPCS Power User utilities:\n")
    
    # List main utilities
    print("Main Commands:")
    print("  convert-legacy      - Convert legacy XPCS datasets to NeXus format")
    print("  nexus-to-csv       - Convert HDF5/NeXus files to CSV format")
    print("  g2-average         - Run G2 averaging analysis")
    print("  fast-g2-average    - Run fast G2 averaging analysis")
    print("  run-script         - Run any Python script from utils")
    
    print("\nPython Scripts in utils/:")
    
    # List Python files in utils
    for py_file in sorted(utils_dir.glob('*.py')):
        if not py_file.name.startswith('__'):
            print(f"  {py_file.name}")
    
    # List subdirectories
    print("\nSubdirectories:")
    for subdir in sorted(utils_dir.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith('__'):
            print(f"  {subdir.name}/")
            # List Python files in subdirectory
            for py_file in sorted(subdir.glob('*.py')):
                print(f"    - {py_file.name}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='xpcs-poweruser',
        description='XPCS Power User Tools - A collection of utilities for XPCS data analysis.',
        epilog="Use 'xpcs-poweruser COMMAND --help' for more information on a specific command."
    )
    
    # Add version argument
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Convert legacy command
    convert_parser = subparsers.add_parser(
        'convert-legacy',
        help='Convert legacy XPCS datasets to the new NeXus format',
        description='This command processes legacy XPCS data by searching for subfolders containing '
                    'paired data files and metadata files, then converts them to the new format.'
    )
    convert_parser.add_argument('source_folder', type=str, help='Source folder containing legacy datasets')
    convert_parser.add_argument('dest_folder', type=str, help='Destination folder for converted datasets')
    convert_parser.add_argument('--workers', type=int, default=1, help='Number of parallel worker processes')
    convert_parser.add_argument('--ftype', choices=['.bin', '.imm', '.h5'], default='.bin',
                               help='File type/extension of raw data files')
    convert_parser.add_argument('--copy-data', action='store_true',
                               help='Copy data files instead of creating symbolic links')
    convert_parser.set_defaults(func=convert_legacy_command)
    
    # Nexus to CSV command
    nexus_parser = subparsers.add_parser(
        'nexus-to-csv',
        help='Convert HDF5/NeXus files to CSV format',
        description='This command extracts G2, SAXS, and metadata information from HDF5 files '
                    'and saves them as separate CSV files.'
    )
    nexus_parser.add_argument('-i', '--input', required=True, help='Path to the folder with HDF5 files')
    nexus_parser.add_argument('-o', '--output', required=True, help='Path to save CSV files')
    nexus_parser.add_argument('-f', '--filter', default='', help='Optional substring filter for filenames')
    nexus_parser.set_defaults(func=nexus_to_csv_command)
    
    # Run script command
    script_parser = subparsers.add_parser(
        'run-script',
        help='Run a Python script from the utils directory',
        description='This command allows you to run any Python script with custom arguments.'
    )
    script_parser.add_argument('script_path', help='Path to the Python script')
    script_parser.add_argument('args', nargs='*', help='Arguments to pass to the script')
    script_parser.set_defaults(func=run_script_command)
    
    # G2 average command
    g2_parser = subparsers.add_parser(
        'g2-average',
        help='Run G2 averaging analysis on HDF5 files',
        description='This command processes HDF5 files to compute G2 averages using the '
                    'configuration specified in the JSON file.'
    )
    g2_parser.add_argument('hdf_file', help='HDF5 file to process')
    g2_parser.add_argument('-o', '--output', help='Output directory for G2 average results')
    g2_parser.add_argument('-c', '--config', help='Path to G2average_info.json config file')
    g2_parser.set_defaults(func=g2_average_command)
    
    # Fast G2 average command
    fast_g2_parser = subparsers.add_parser(
        'fast-g2-average',
        help='Run fast G2 averaging analysis on HDF5 files',
        description='This command processes HDF5 files to compute G2 averages using an optimized '
                    'algorithm for faster processing.'
    )
    fast_g2_parser.add_argument('hdf_file', help='HDF5 file to process')
    fast_g2_parser.add_argument('-o', '--output', help='Output directory for fast G2 average results')
    fast_g2_parser.add_argument('-c', '--config', help='Path to G2average_info.json config file')
    fast_g2_parser.set_defaults(func=fast_g2_average_command)
    
    # List utils command
    list_parser = subparsers.add_parser(
        'list-utils',
        help='List all available utility scripts and their descriptions'
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


if __name__ == '__main__':
    main()
