import json
import glob
import os
import re
import logging
import multiprocessing
import argparse

# Import the main processing function from your script
from fast_G2_average import fast_average_shared_memory

def run_g2_average_from_json(json_config_path):
    """
    Generates a file list based on a JSON config and runs the G2 averaging.

    Args:
        json_config_path (str): The path to the JSON configuration file.
    """
    # 1. Read and parse the JSON configuration file
    print(f"Loading configuration from: {json_config_path}")
    try:
        with open(json_config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"Error: The configuration file '{json_config_path}' was not found.")
        return

    print("Configuration loaded:")
    print(json.dumps(config, indent=4))

    # 2. Generate the list of files (flist) based on the config
    flist = []
    try:
        base_path = config["file_path"]
        header = config["file_header"]
        file_range = config["file_range"]
    except KeyError as e:
        print(f"\nError: Configuration is missing a required key: {e}")
        return

    # Use the unified logic to generate the file list
    if isinstance(file_range, str) and file_range.lower() == 'all':
        search_pattern = os.path.join(base_path, f"{header}*.hdf")
        print(f"\nMode: File Search. Searching with pattern: {search_pattern}")
        flist = sorted(glob.glob(search_pattern))
    elif isinstance(file_range, list) and len(file_range) == 2:
        start, end = file_range
        print(f"\nMode: Search and Filter by Range. Header='{header}', Range={start}-{end}.")
        search_pattern = os.path.join(base_path, f"{header}*.hdf")
        all_matching_files = glob.glob(search_pattern)
        
        temp_flist = []
        for f in all_matching_files:
            match = re.search(r'_r(\d+)', os.path.basename(f))
            if match:
                file_num = int(match.group(1))
                if start <= file_num <= end:
                    temp_flist.append(f)
        flist = sorted(temp_flist)
    else:
        print(f"\nError: 'file_range' in {json_config_path} must be the string 'all' or a list of two integers.")
        return
    
    if not flist:
        print("\nNo files found matching the specified criteria. Aborting.")
        return
    
    print(f"\nGenerated a list of {len(flist)} files to be processed.")

    # --- MODIFIED SECTION ---
    # 3. Construct the full path for the output file
    output_filename = config.get("output_filename", "averaged_results.hdf")
    # Combine the input directory with the output filename
    full_output_path = os.path.join(base_path, output_filename)
    print(f"\nOutput file will be saved to: {full_output_path}")
    # --- END OF MODIFICATION ---


    # 4. Call the main averaging function with the full output path
    print("\nCalling the G2 averaging function...")
    
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
                        
    fast_average_shared_memory(
        flist=flist,
        output_filename=full_output_path, # Use the newly constructed full path
        avg_window=config.get("baseline_window", 3),
        avg_qindex=config.get("baseline_qindex", 0),
        avg_blmin=config.get("baseline_min", 0.95),
        avg_blmax=config.get("baseline_max", 1.35),
        num_workers=config.get("num_workers", None),
        h5_cache_size_mb=config.get("cache_mb", 512),
        verbose=config.get("verbose", False),
        precision=config.get("precision", "single"),
    )

if __name__ == '__main__':
    # This part allows you to run the script from the command line
    # with the JSON file as an argument.
    
    multiprocessing.set_start_method("spawn", force=True)

    parser = argparse.ArgumentParser(
        description="A wrapper script to run G2 averaging from a JSON configuration file."
    )
    parser.add_argument(
        "config_file",
        type=str,
        help="Path to the JSON configuration file to process."
    )
    args = parser.parse_args()

    run_g2_average_from_json(args.config_file)
