#!/bin/bash

#==============================================================================
# XPCS Dataset Processing Script
#==============================================================================
# This script automates the processing of X-ray Photon Correlation Spectroscopy
# (XPCS) datasets using the boost_corr_bin program. It processes multiple 
# datasets in parallel while managing GPU queue limits.
#
# OVERVIEW:
# - Processes data files from XPCS scans using boost_corr_bin
# - Supports processing single files or ranges of repeat measurements
# - Manages GPU job queue to prevent system overload
# - Automatically finds matching directories based on scan numbers and repeat indices
# - Configurable file extension via EXTENSION variable (default: .bin)
#
# PREREQUISITES:
# - boost_corr_bin must be installed and available in PATH
# - GPU-enabled system (CUDA-compatible) for optimal performance
# - Sufficient disk space for output results
# - Q-map file (.h5/.hdf5) for correlation analysis
#
# EXPECTED DIRECTORY STRUCTURE:
# BASE_DIR/
# ├── scan_XXXX_description_rYYYYY_timestamp/
# │   ├── scan_XXXX_description_rYYYYY_timestamp.bin  (input data)
# │   └── [other metadata files]
# ├── scan_XXXX_description_rYYYYY_timestamp/
# └── ...
#
# Where:
# - XXXX = 4-digit zero-padded scan number (e.g., 0064)
# - YYYYY = 5-digit zero-padded repeat index (e.g., 00001)
# - description = arbitrary text describing the scan
# - timestamp = optional timestamp or other identifiers
#
# Note: The input file extension is configurable via the EXTENSION variable
#
# TYPICAL WORKFLOW:
# 1. Raw XPCS data is organized in directories with specific naming patterns
# 2. This script finds the appropriate .bin files for processing
# 3. Launches boost_corr_bin jobs with GPU queue management
# 4. Results are saved to the specified output directory
#
# EXAMPLE USAGE:
#   ./process_datasets.sh 64 1 qmap_file.h5          # Process single repeat
#   ./process_datasets.sh 64 1-10 qmap_file.h5       # Process range of repeats
#   ./process_datasets.sh 1234 5-15 my_qmap.h5       # Process scans 5-15 of scan 1234
#
# OUTPUT:
# - Results are saved to OUT_DIR (default: cluster_results/)
# - Each job creates correlation functions, timing data, and analysis outputs
# - Log files and error messages are captured by nohup
#
#==============================================================================
# --- USER CONFIGURATION ---
#==============================================================================
# Please modify the paths and names in this section to match your setup.

# The base directory where your scan subdirectories are located.
# Expected structure: BASE_DIR/scan_XXXX_*_rYYYYY*/
# Example: ../data/scan_0064_some_name_r00001_timestamp/
BASE_DIR="../data"

# A temporary directory for managing a queue of running GPU jobs.
# Uses /dev/shm (RAM disk) for fast I/O when checking queue status.
# The script monitors this directory to limit concurrent GPU jobs to 6.
# Each running job creates a temporary file here that gets cleaned up automatically.
GPU_QUEUE_DIR="/dev/shm/gpu_queue"

# The name of the output directory for boost_corr_bin results.
# boost_corr_bin will create this directory if it doesn't exist.
# Results include correlation functions, timing data, and analysis outputs.
OUT_DIR="cluster_results"

# The file extension for input data files.
# This allows easy modification if different file formats are used.
# Common extensions: .bin, .h5, .hdf5, .dat
EXTENSION=".bin"

#==============================================================================

# --- Argument & Usage Validation ---
# This script requires exactly 3 arguments for proper operation
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <scan_number> <repeat_index_or_range> <qmap_name>"
    echo "  <scan_number>: A 1-4 digit number (e.g., 64)"
    echo "    - Gets padded to 4 digits (64 becomes 0064)"
    echo "    - Used to match directory names like scan_0064_*"
    echo "  <repeat_index_or_range>: A single number (e.g., 1) or a range (e.g., 1-10)"
    echo "    - Single: processes one repeat measurement"
    echo "    - Range: processes all repeats from start to end (inclusive)"
    echo "    - Gets padded to 5 digits (1 becomes 00001)"
    echo "  <qmap_name>: The name of the qmap file (must exist in current directory)"
    echo "    - Contains Q-space mapping for correlation analysis"
    echo "    - Typically .h5 or .hdf5 format"
    echo ""
    echo "Examples:"
    echo "  $0 64 1 qmap_64.h5                    # Process scan 64, repeat 1"
    echo "  $0 64 1-5 qmap_64.h5                  # Process scan 64, repeats 1-5"
    echo "  $0 1234 10-20 /path/to/qmap.h5        # Process scan 1234, repeats 10-20"
    exit 1
fi

# Assign command line arguments to descriptive variable names
scan_number="$1"        # The scan number to process (will be zero-padded)
repeat_arg="$2"         # Either single repeat index or range (e.g., "1" or "1-10")
qmap_name="$3"          # Path to the Q-map file for correlation analysis

if [[ ! "$scan_number" =~ ^[0-9]{1,4}$ ]]; then
    echo "Error: Scan number must be 1 to 4 digits." >&2
    exit 1
fi

if [[ ! "$repeat_arg" =~ ^[0-9]+(-[0-9]+)?$ ]]; then
    echo "Error: Repeat index must be a number or a range (e.g., 1 or 1-10)." >&2
    exit 1
fi

if [ -z "$qmap_name" ] || [[ "$qmap_name" =~ ^- ]]; then
    echo "Error: Qmap name cannot be empty or start with '-'. Please provide a valid qmap file name." >&2
    exit 1
fi

if [ ! -f "$qmap_name" ]; then
    echo "Error: Qmap file '$qmap_name' does not exist or is not a regular file." >&2
    exit 1
fi
# --- End Validation ---

# Parse the repeat argument to determine processing range
# If it contains a dash, it's a range (e.g., "1-10")
# Otherwise, it's a single index (e.g., "5")
if [[ "$repeat_arg" == *"-"* ]]; then
    # Extract start and end from range format "start-end"
    start_index=${repeat_arg%-*}    # Remove everything after the last dash
    end_index=${repeat_arg#*-}      # Remove everything before the first dash
else
    # Single index: process only one repeat
    start_index=$repeat_arg
    end_index=$repeat_arg
fi

# Zero-pad scan number to 4 digits for directory matching
# Example: 64 becomes "0064" to match "scan_0064_*" directories
padded_scan_number=$(printf "%04d" "$scan_number")

# --- Pre-Loop Setup ---
# Initialize the GPU queue management system
# The queue directory is used to track running boost_corr_bin processes
# Each job creates a temporary file here; we limit to 6 concurrent jobs
if [ ! -d "$GPU_QUEUE_DIR" ]; then
    echo "GPU queue directory not found. Creating $GPU_QUEUE_DIR..."
    mkdir -p "$GPU_QUEUE_DIR"
fi

echo "Starting processing of scan $scan_number, repeats $start_index to $end_index"
echo "Using qmap file: $qmap_name"
echo "Output directory: $OUT_DIR"
echo "GPU queue limit: 6 concurrent jobs"
echo "============================================================"

# --- Main Processing Loop ---
# Process each repeat index in the specified range
for ((i=start_index; i<=end_index; i++)); do
    echo "===== Processing Repeat Index: $i ====="

    # Zero-pad repeat index to 5 digits for directory matching
    # Example: 1 becomes "00001" to match "*_r00001*" directories
    padded_repeat_index=$(printf "%05d" "$i")

    # Search for matching directories using shell globbing (faster than find)
    # Expected pattern: BASE_DIR/*scan_XXXX_*_rYYYYY*/
    # Example: ../data/scan_0064_sample_name_r00001_20240131_143022/
    dir_pattern="*${padded_scan_number}_*_r${padded_repeat_index}*"
    shopt -s nullglob    # Enable nullglob to handle no matches gracefully
    matching_dirs=(${BASE_DIR}/${dir_pattern}/)
    shopt -u nullglob    # Disable nullglob after use

    # Validate that exactly one matching directory was found
    if [ ${#matching_dirs[@]} -ne 1 ]; then
        if [ ${#matching_dirs[@]} -eq 0 ]; then
            echo "Warning: No matching directory found for repeat $i (pattern: $dir_pattern). Skipping." >&2
        else
            echo "Warning: Ambiguous match for repeat $i. Found ${#matching_dirs[@]} directories. Skipping." >&2
            printf " - %s\n" "${matching_dirs[@]}" >&2
        fi
        continue
    fi
    target_dir=${matching_dirs[0]%/}    # Remove trailing slash if present

    # Construct the expected data file path using the configured extension
    # Convention: the data file has the same name as its parent directory
    # Example: scan_0064_sample_r00001_timestamp/scan_0064_sample_r00001_timestamp.bin
    dir_basename=$(basename "$target_dir")
    found_files="${target_dir}/${dir_basename}${EXTENSION}"

    # Verify the data file exists before attempting to process
    if [ ! -f "$found_files" ]; then
        echo "Warning: Directory found for repeat $i, but data file '$found_files' is missing. Skipping." >&2
        continue
    fi

    echo "Processing file: $found_files"
    echo "Using Qmap: $qmap_name"
    echo "--------------------------------------------------------"

    # GPU Queue Management: Wait if too many jobs are running
    # Check the number of files in the queue directory (each represents a running job)
    # Limit to 6 concurrent boost_corr_bin processes to prevent GPU memory overflow
    while [ $(ls "$GPU_QUEUE_DIR" | wc -l) -gt 6 ]; do
        echo "GPU queue is full (6/6 jobs running). Waiting 15 seconds..."
        sleep 15
    done

    # Launch boost_corr_bin in background with nohup for job persistence
    # boost_corr_bin parameters:
    #   -r: input raw data file (format determined by EXTENSION variable)
    #   -q: Q-map file for correlation analysis
    #   -i -2: intensity normalization method
    #   -o: output directory for results
    # The & runs it in background, allowing the script to continue
    echo "Launching boost_corr_bin for repeat $i..."
    nohup boost_corr_bin -r "$found_files" -q "$qmap_name" -i -2 -o "$OUT_DIR" &
    
    # Brief pause to prevent overwhelming the system with rapid job launches
    sleep 1
done

echo "===== All processing jobs have been launched. ====="
echo "Note: boost_corr_bin jobs are running in the background."
echo "Check the '$OUT_DIR' directory for results as they complete."
echo "Monitor system resources (GPU memory, CPU usage) during processing."
echo ""
echo "To check running jobs: ps aux | grep boost_corr_bin"
echo "To monitor GPU usage: nvidia-smi"
echo "To check queue status: ls -la $GPU_QUEUE_DIR"
