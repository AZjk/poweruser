import os
import re
import stat
import tempfile
import shutil
import argparse  # For parsing command-line arguments
import sys  # For exiting the script
import importlib.util  # For loading settings.py
import time  # For progress bar timing and timestamps

# Default configuration values
DEFAULT_CONFIG = {
    # Path to raw data folder containing scan folders
    "input_folder": "/gdata/dm/8ID/8IDI/2025-2/tempus202507d/data",
    # Output folder for launch_timepix_converter
    "converter_output_dir": "/home/beams10/8IDIUSER/Documents/Miaoqi/2025_0811_timepix_reanalysis/converted_datasets",
    # Output directory for boost_corr_dev results
    "correlation_results_dir": "/home/beams10/8IDIUSER/Documents/Miaoqi/2025_0811_timepix_reanalysis/cluster_results",
    # Directory where generated .sh job scripts will be saved
    "job_script_dir": "/home/beams10/8IDIUSER/Documents/Miaoqi/2025_0811_timepix_reanalysis/jobs",
    # Path to qmap file (h5/hdf) for boost_corr_dev
    "qmap": "/gdata/dm/8ID/8IDI/2025-2/tempus202507b/data/timepix_Sq90_Dq9_lin.hdf",
    # Run acquisition time in seconds for launch_timepix_converter (if <= 0, calculated as 1e6 * tbin)
    "tac": -1,
    # Length of virtual frame in intensity export mode (time bin) for launch_timepix_converter
    "tbin": 997e-9,
    # Create a subfolder in correlation_results_dir using substring of raw_folder
    "create_result_subfolder": True,
    # Limit the number of job scripts to create (None = process all found folders)
    "limit": None,
}


def load_settings_from_python(settings_file="settings.py"):
    """
    Load settings from a Python file containing a SETTINGS dictionary.
    If the file doesn't exist or has errors, use the original defaults.
    """
    if not os.path.exists(settings_file):
        print(
            f"Settings file '{settings_file}' not found. Using default configuration."
        )
        return DEFAULT_CONFIG.copy()

    try:
        # Load the Python module dynamically
        spec = importlib.util.spec_from_file_location("settings", settings_file)
        settings_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(settings_module)

        # Get the SETTINGS dictionary from the module
        if hasattr(settings_module, "SETTINGS"):
            user_settings = settings_module.SETTINGS
        else:
            print(
                f"Warning: No 'SETTINGS' dictionary found in {settings_file}. Using default configuration."
            )
            return DEFAULT_CONFIG.copy()

        # Create a copy of default config and update with user settings
        updated_config = DEFAULT_CONFIG.copy()
        for key, value in user_settings.items():
            if key in DEFAULT_CONFIG:
                updated_config[key] = value
                print(f"Updated {key}: {value}")
            else:
                print(f"Warning: Unknown setting '{key}' in {settings_file}, ignoring.")

        print(f"Successfully loaded settings from '{settings_file}'.")
        return updated_config

    except Exception as e:
        print(f"Error loading '{settings_file}': {e}")
        print("Using default configuration.")
        return DEFAULT_CONFIG.copy()


# Load settings at module level
CURRENT_CONFIG = load_settings_from_python()

# The helper functions 'find_scan_folders' and 'create_job_script'
# remain unchanged as they are already well-defined.


def print_progress_bar(current, total, start_time, bar_length=50):
    """
    Print a progress bar using only native Python libraries.
    """
    if total == 0:
        return

    percent = float(current) / total
    filled_length = int(bar_length * percent)
    bar = "#" * filled_length + "-" * (bar_length - filled_length)

    # Calculate elapsed time and estimate remaining time
    elapsed_time = time.time() - start_time
    if current > 0:
        estimated_total_time = elapsed_time / current * total
        remaining_time = estimated_total_time - elapsed_time
        remaining_str = f"{int(remaining_time//60):02d}:{int(remaining_time%60):02d}"
    else:
        remaining_str = "--:--"

    # Format elapsed time
    elapsed_str = f"{int(elapsed_time//60):02d}:{int(elapsed_time%60):02d}"

    # Print progress bar (using \r to overwrite the same line)
    progress_line = f"\rProgress: [{bar}] {current}/{total} ({percent:.1%}) | Elapsed: {elapsed_str} | ETA: {remaining_str}"
    print(progress_line, end="", flush=True)


def find_scan_folders(input_folder, scan_index):
    """
    Finds and sorts subfolders that match a specific scan index pattern.
    """
    if not os.path.isdir(input_folder):
        print(f"Error: Input folder not found: {input_folder}", file=sys.stderr)
        return []
    pattern = re.compile(f"^[a-zA-Z]+{scan_index:04d}_")
    try:
        with os.scandir(input_folder) as it:
            matched_folders = [
                entry.path
                for entry in it
                if entry.is_dir() and pattern.match(entry.name)
            ]
            return sorted(matched_folders)
    except OSError as e:
        print(f"Error scanning directory {input_folder}: {e}", file=sys.stderr)
        return []


def find_folders_by_prefix(input_folder, prefix):
    """
    Finds and sorts subfolders that start with a specific prefix.
    """
    if not os.path.isdir(input_folder):
        print(f"Error: Input folder not found: {input_folder}", file=sys.stderr)
        return []
    try:
        with os.scandir(input_folder) as it:
            matched_folders = [
                entry.path
                for entry in it
                if entry.is_dir() and entry.name.startswith(prefix)
            ]
            return sorted(matched_folders)
    except OSError as e:
        print(f"Error scanning directory {input_folder}: {e}", file=sys.stderr)
        return []


def extract_subfolder_name(raw_folder):
    """
    Extract subfolder name from raw_folder path by removing the _r{repeat_id:05d} suffix.

    Example:
        Input: "/gdata/dm/8ID/8IDI/2025-2/tempus202507d/data/Fc0444_PA3_a0001_f2000000_r01822"
        Output: "Fc0444_PA3_a0001_f2000000"
    """
    folder_name = os.path.basename(raw_folder)
    # Remove the _r{repeat_id:06d} pattern from the end
    # Pattern matches _r followed by exactly 6 digits at the end of the string
    subfolder_name = re.sub(r"_r\d{5}$", "", folder_name)
    return subfolder_name


def create_job_script(
    job_index,
    raw_folder,
    converter_output_dir,
    correlation_results_dir,
    job_script_dir,
    tac,
    tbin,
    qmap,
    run_timestamp,
    create_result_subfolder=True,
    verbose=True,
):
    """
    Safely generates an executable shell script for a single job.
    """
    # Use Unix timestamp to prevent duplicates across runs
    job_filename = f"job_{job_index:06d}_{run_timestamp}.sh"
    final_job_filepath = os.path.join(job_script_dir, job_filename)
    os.makedirs(job_script_dir, exist_ok=True)

    # This logic is now inside the function, making it self-contained.
    if tac <= 0:
        tac = 1e6 * tbin

    # Handle subfolder creation logic
    if create_result_subfolder:
        subfolder_name = extract_subfolder_name(raw_folder)
        final_correlation_results_dir = os.path.join(
            correlation_results_dir, subfolder_name
        )
    else:
        final_correlation_results_dir = correlation_results_dir

    temp_dir = tempfile.mkdtemp()
    try:
        temp_job_filepath = os.path.join(temp_dir, job_filename)
        script_content = f"""#!/bin/bash
# Auto-generated job script: {job_filename}
set -e
set -u
# --- Configuration ---
RAW_FOLDER="{raw_folder}"
CONVERTER_OUTPUT_DIR="{converter_output_dir}"
CORRELATION_RESULTS_DIR="{final_correlation_results_dir}"
TAC={tac}
TBIN={tbin}
QMAP="{qmap}"
# --- Script Logic ---
echo "Starting job {job_index}..."
echo "  Raw data folder: $RAW_FOLDER"
echo "  Correlation results will be saved to: $CORRELATION_RESULTS_DIR"
mkdir -p "$CONVERTER_OUTPUT_DIR"
mkdir -p "$CORRELATION_RESULTS_DIR"
binfile=$(launch_timepix_converter -r "$RAW_FOLDER" -d "$CONVERTER_OUTPUT_DIR" -tac $TAC -tbin $TBIN)
if [ -f "$binfile" ]; then
    echo "Converter finished. Output bin file: $binfile"
    boost_corr_dev -r "$binfile" -q "$QMAP" -i 0 -w --save-G2 -o "$CORRELATION_RESULTS_DIR"
    echo "Job {job_index} completed successfully."
else
    echo "Error: Converter did not produce expected output file: '$binfile'" >&2
    exit 1
fi
"""
        with open(temp_job_filepath, "w") as f:
            f.write(script_content)
        current_permissions = os.stat(temp_job_filepath).st_mode
        os.chmod(
            temp_job_filepath,
            current_permissions | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH,
        )
        shutil.move(temp_job_filepath, final_job_filepath)
    finally:
        shutil.rmtree(temp_dir)

    if verbose:
        print(f"Successfully created and moved job script to: {final_job_filepath}")
        if create_result_subfolder:
            subfolder_name = extract_subfolder_name(raw_folder)
            print(f"  Results will be saved to subfolder: {subfolder_name}")
    return final_job_filepath


def main():
    """
    Main function to parse command-line arguments and generate job scripts.
    """
    parser = argparse.ArgumentParser(
        description="""Finds raw data folders for a given scan index or prefix and generates executable job scripts for processing.

Priority Order (highest to lowest):
1. User input (command-line arguments) - Takes precedence over everything
2. settings.py - Used if no user input provided
3. DEFAULT_CONFIG - Used as final fallback""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # --- Search Method Arguments (mutually exclusive) ---
    search_group = parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument(
        "--scan-index",
        type=int,
        help="The scan index to search for (e.g., 444).",
    )
    search_group.add_argument(
        "--prefix",
        type=str,
        help="The prefix to search for in folder names (e.g., 'sample_A').",
    )

    # --- Path Arguments with Defaults ---
    parser.add_argument(
        "--input-folder",
        type=str,
        default=CURRENT_CONFIG["input_folder"],
        help="Path to raw data folder containing scan folders (corresponds to launch_timepix_converter --raw-folder).",
    )
    parser.add_argument(
        "--converter-output-dir",
        type=str,
        default=CURRENT_CONFIG["converter_output_dir"],
        help="Path to output data folder for launch_timepix_converter (corresponds to --out-folder).",
    )
    parser.add_argument(
        "--correlation-results-dir",
        type=str,
        default=CURRENT_CONFIG["correlation_results_dir"],
        help="Output directory for boost_corr_dev result files (corresponds to --output). Directory will be created if it doesn't exist.",
    )
    parser.add_argument(
        "--job-script-dir",
        type=str,
        default=CURRENT_CONFIG["job_script_dir"],
        help="Directory where the generated executable .sh job scripts will be saved.",
    )
    parser.add_argument(
        "--qmap",
        type=str,
        default=CURRENT_CONFIG["qmap"],
        help="Filename of the qmap file (h5/hdf) for boost_corr_dev correlation analysis (corresponds to --qmap).",
    )

    # --- Processing Parameters ---
    parser.add_argument(
        "--tac",
        type=float,
        default=CURRENT_CONFIG["tac"],
        help="Run acquisition time in seconds for launch_timepix_converter (corresponds to --acquisition_time). If <= 0, calculated as 1e6 * tbin.",
    )
    parser.add_argument(
        "--tbin",
        type=float,
        default=CURRENT_CONFIG["tbin"],
        help="Length of virtual frame in intensity export mode for launch_timepix_converter (corresponds to --time_bin).",
    )

    # --- Control Flow Arguments ---
    parser.add_argument(
        "--create-result-subfolder",
        action="store_true",
        default=CURRENT_CONFIG["create_result_subfolder"],
        help="Create a subfolder in correlation_results_dir using substring of raw_folder (removes _r{repeat_id:06d} suffix).",
    )
    parser.add_argument(
        "--no-create-result-subfolder",
        dest="create_result_subfolder",
        action="store_false",
        help="Disable creation of result subfolder (use correlation_results_dir directly).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=CURRENT_CONFIG["limit"],
        help="Limit the number of job scripts to create (e.g., 1 for testing). By default, processes all found folders.",
    )

    args = parser.parse_args()

    # --- Script Logic ---
    if args.scan_index is not None:
        # Search by scan index
        scan_folders = find_scan_folders(args.input_folder, args.scan_index)
        search_term = f"index {args.scan_index}"
    else:
        # Search by prefix
        scan_folders = find_folders_by_prefix(args.input_folder, args.prefix)
        search_term = f"prefix '{args.prefix}'"

    if not scan_folders:
        print(
            f"No scan folders found for {search_term} in {args.input_folder}. Exiting.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"Found {len(scan_folders)} scan folders for {search_term}. Preparing to create jobs..."
    )

    # Slice the list based on the --limit argument. If limit is None, this takes the whole list.
    folders_to_process = scan_folders[: args.limit]
    if args.limit is not None:
        print(
            f"Processing the first {len(folders_to_process)} folder(s) due to --limit={args.limit}."
        )

    total_jobs = len(folders_to_process)
    start_time = time.time()

    # Generate Unix timestamp for this run to ensure unique job names
    run_timestamp = int(start_time)

    print(f"\nCreating {total_jobs} job scripts...")

    for index, raw_data_folder in enumerate(folders_to_process, start=1):
        # Update progress bar
        print_progress_bar(index - 1, total_jobs, start_time)

        create_job_script(
            job_index=index,
            raw_folder=raw_data_folder,
            converter_output_dir=args.converter_output_dir,
            correlation_results_dir=args.correlation_results_dir,
            job_script_dir=args.job_script_dir,
            tac=args.tac,
            tbin=args.tbin,
            qmap=args.qmap,
            run_timestamp=run_timestamp,
            create_result_subfolder=args.create_result_subfolder,
            verbose=False,  # Suppress output to avoid interfering with progress bar
        )

    # Final progress bar update
    print_progress_bar(total_jobs, total_jobs, start_time)
    print(f"\n\nCompleted! Created {total_jobs} job scripts in {args.job_script_dir}")


if __name__ == "__main__":
    main()
