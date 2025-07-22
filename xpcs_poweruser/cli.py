"""Command-line interface for XPCS Power User Tools."""

import click
import sys
from pathlib import Path
import subprocess
import importlib.util

from . import __version__


@click.group()
@click.version_option(version=__version__, prog_name="xpcs-poweruser")
def main():
    """XPCS Power User Tools - A collection of utilities for XPCS data analysis.
    
    This CLI provides access to various XPCS data processing and analysis tools.
    Use 'xpcs-poweruser COMMAND --help' for more information on a specific command.
    """
    pass


@main.command()
@click.argument('source_folder', type=click.Path(exists=True))
@click.argument('dest_folder', type=click.Path())
@click.option('--workers', default=1, type=int, help='Number of parallel worker processes')
@click.option('--ftype', default='.bin', type=click.Choice(['.bin', '.imm', '.h5']), 
              help='File type/extension of raw data files')
@click.option('--copy-data', is_flag=True, help='Copy data files instead of creating symbolic links')
def convert_legacy(source_folder, dest_folder, workers, ftype, copy_data):
    """Convert legacy XPCS datasets to the new NeXus format.
    
    This command processes legacy XPCS data by searching for subfolders containing
    paired data files and metadata files, then converts them to the new format.
    
    Example:
        xpcs-poweruser convert-legacy /path/to/source /path/to/dest --workers 4
    """
    from .utils.convert_legacy_datasets import process_folder
    
    click.echo(f"Converting legacy datasets from {source_folder} to {dest_folder}")
    click.echo(f"File type: {ftype}, Workers: {workers}, Copy data: {copy_data}")
    
    try:
        process_folder(source_folder, dest_folder, max_workers=workers, ftype=ftype, copy_data=copy_data)
        click.echo("Conversion completed successfully!")
    except Exception as e:
        click.echo(f"Error during conversion: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--input', '-i', required=True, type=click.Path(exists=True), 
              help='Path to the folder with HDF5 files')
@click.option('--output', '-o', required=True, type=click.Path(), 
              help='Path to save CSV files')
@click.option('--filter', '-f', default='', help='Optional substring filter for filenames')
def nexus_to_csv(input, output, filter):
    """Convert HDF5/NeXus files to CSV format.
    
    This command extracts G2, SAXS, and metadata information from HDF5 files
    and saves them as separate CSV files.
    
    Example:
        xpcs-poweruser nexus-to-csv -i /path/to/hdf5 -o /path/to/csv
    """
    from .utils.convert_nexus_to_csv import hdf2csv
    import os
    
    click.echo(f"Converting HDF5 files from {input} to CSV in {output}")
    if filter:
        click.echo(f"Using filter: {filter}")
    
    os.makedirs(output, exist_ok=True)
    
    converted_count = 0
    for filename in os.listdir(input):
        if (filename.endswith('.hdf') or filename.endswith('.hdf5')) and (filter in filename):
            full_path = os.path.join(input, filename)
            try:
                hdf2csv(full_path, output)
                converted_count += 1
            except Exception as e:
                click.echo(f"Error processing {filename}: {e}", err=True)
    
    click.echo(f"Converted {converted_count} files successfully!")


@main.command()
@click.argument('script_path', type=click.Path(exists=True))
@click.argument('args', nargs=-1)
def run_script(script_path, args):
    """Run a Python script from the utils directory.
    
    This command allows you to run any Python script with custom arguments.
    
    Example:
        xpcs-poweruser run-script path/to/script.py arg1 arg2
    """
    script_path = Path(script_path)
    
    if not script_path.suffix == '.py':
        click.echo("Error: Script must be a Python file (.py)", err=True)
        sys.exit(1)
    
    click.echo(f"Running script: {script_path}")
    
    # Run the script with the provided arguments
    cmd = [sys.executable, str(script_path)] + list(args)
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        sys.exit(result.returncode)
    except Exception as e:
        click.echo(f"Error running script: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('hdf_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory for G2 average results')
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to G2average_info.json config file')
def g2_average(hdf_file, output, config):
    """Run G2 averaging analysis on HDF5 files.
    
    This command processes HDF5 files to compute G2 averages using the
    configuration specified in the JSON file.
    
    Example:
        xpcs-poweruser g2-average data.hdf -o results/
    """
    from pathlib import Path
    import subprocess
    import sys
    
    # Find the G2_average script
    package_dir = Path(__file__).parent
    g2_script = package_dir / 'utils' / 'G2_average' / 'reaverage_master_plan.py'
    
    if not g2_script.exists():
        click.echo(f"Error: G2 average script not found at {g2_script}", err=True)
        sys.exit(1)
    
    # Use default config if not provided
    if not config:
        config = package_dir / 'utils' / 'G2_average' / 'reaverage_info.json'
    
    click.echo(f"Processing {hdf_file} with G2 averaging")
    click.echo(f"Using config: {config}")
    
    # Run the G2 average script
    cmd = [sys.executable, str(g2_script), str(hdf_file)]
    
    if output:
        # Modify the command to include output directory if needed
        cmd.extend(['--output', str(output)])
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            click.echo("G2 averaging completed successfully!")
        else:
            click.echo("G2 averaging failed!", err=True)
            sys.exit(result.returncode)
    except Exception as e:
        click.echo(f"Error running G2 average: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('hdf_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory for fast G2 average results')
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to G2average_info.json config file')
def fast_g2_average(hdf_file, output, config):
    """Run fast G2 averaging analysis on HDF5 files.
    
    This command processes HDF5 files to compute G2 averages using an optimized
    algorithm for faster processing.
    
    Example:
        xpcs-poweruser fast-g2-average data.hdf -o results/
    """
    from pathlib import Path
    import subprocess
    import sys
    
    # Find the fast_G2_average script
    package_dir = Path(__file__).parent
    g2_script = package_dir / 'utils' / 'fast_G2_average' / 'fast_G2_average.py'
    
    if not g2_script.exists():
        click.echo(f"Error: Fast G2 average script not found at {g2_script}", err=True)
        sys.exit(1)
    
    # Use default config if not provided
    if not config:
        config = package_dir / 'utils' / 'fast_G2_average' / 'G2average_info.json'
    
    click.echo(f"Processing {hdf_file} with fast G2 averaging")
    click.echo(f"Using config: {config}")
    
    # Run the fast G2 average script
    cmd = [sys.executable, str(g2_script), str(hdf_file)]
    
    if output:
        # Modify the command to include output directory if needed
        cmd.extend(['--output', str(output)])
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode == 0:
            click.echo("Fast G2 averaging completed successfully!")
        else:
            click.echo("Fast G2 averaging failed!", err=True)
            sys.exit(result.returncode)
    except Exception as e:
        click.echo(f"Error running fast G2 average: {e}", err=True)
        sys.exit(1)


@main.command()
def list_utils():
    """List all available utility scripts and their descriptions."""
    from pathlib import Path
    
    package_dir = Path(__file__).parent
    utils_dir = package_dir / 'utils'
    
    click.echo("Available XPCS Power User utilities:\n")
    
    # List main utilities
    click.echo("Main Commands:")
    click.echo("  convert-legacy      - Convert legacy XPCS datasets to NeXus format")
    click.echo("  nexus-to-csv       - Convert HDF5/NeXus files to CSV format")
    click.echo("  g2-average         - Run G2 averaging analysis")
    click.echo("  fast-g2-average    - Run fast G2 averaging analysis")
    click.echo("  run-script         - Run any Python script from utils")
    
    click.echo("\nPython Scripts in utils/:")
    
    # List Python files in utils
    for py_file in sorted(utils_dir.glob('*.py')):
        if not py_file.name.startswith('__'):
            click.echo(f"  {py_file.name}")
    
    # List subdirectories
    click.echo("\nSubdirectories:")
    for subdir in sorted(utils_dir.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith('__'):
            click.echo(f"  {subdir.name}/")
            # List Python files in subdirectory
            for py_file in sorted(subdir.glob('*.py')):
                click.echo(f"    - {py_file.name}")


if __name__ == '__main__':
    main()
