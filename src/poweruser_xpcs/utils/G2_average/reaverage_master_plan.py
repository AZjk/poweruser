import h5py
import numpy as np
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import time
import random
from apply_qmap import keymap, apply_new_G2_to_file
import traceback
import argparse
import json
import glob
import re # Added for advanced filename parsing


def _check_and_fetch_single_file(
    fname, avg_window, avg_qindex, avg_blmin, avg_blmax, h5_cache_size_mb=512
):
    """
    Helper function to check G2 baseline and fetch G2 data for a single file.
    """
    try:
        with h5py.File(fname, "r", rdcc_nbytes=h5_cache_size_mb * 1024**2) as fhdl:
            g2_data = fhdl[keymap["g2"]][()]
            idx = avg_qindex if avg_qindex < g2_data.shape[1] else 0
            g2_baseline = np.mean(g2_data[-avg_window:, idx])

            if avg_blmin <= g2_baseline <= avg_blmax:
                result = {}
                for skey in ["G2", "saxs1d", "saxs1d_segments", "saxs2d"]:
                    result[skey] = fhdl[keymap[skey]][()]
                return (True, g2_baseline, result, 1, fname)
            else:
                return (False, g2_baseline, None, 0, fname)
    except Exception as e:
        return (False, None, None, 0, fname)


def fast_average_g2(
    flist,
    output_filename="averaged_results.hdf",
    avg_window=3,
    avg_qindex=0,
    avg_blmin=0.95,
    avg_blmax=1.30,
    num_workers=None,
    h5_cache_size_mb=512,
):
    """
    Averages G2 data from a list of HDF5 files, filtering by G2 baseline.
    """
    sum_result = {}
    total_valid_files = 0
    first_valid_file_path = None
    total_files = len(flist)

    if not flist:
        print("No files provided for averaging.")
        return

    print(f"Found {total_files} HDF5 files to process.")

    if num_workers is None:
        num_workers = os.cpu_count()
    num_workers = min(num_workers, len(flist))
    print(f"{num_workers} workers will be used for {len(flist)} files.")

    main_start_time = time.time()
    processed_count = 0

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_file = {
            executor.submit(
                _check_and_fetch_single_file,
                f,
                avg_window,
                avg_qindex,
                avg_blmin,
                avg_blmax,
                h5_cache_size_mb,
            ): f
            for f in flist
        }

        for future in as_completed(future_to_file):
            processed_count += 1
            progress_prefix = f"({processed_count}/{total_files})"
            fname = future_to_file[future]
            try:
                flag, g2_baseline, single_result, count, original_fname = future.result()
                
                if not flag:
                    if g2_baseline is not None:
                        print(f"{progress_prefix} Skipping {os.path.basename(original_fname)}: G2 baseline ({g2_baseline:.4f}) out of range [{avg_blmin:.2f}, {avg_blmax:.2f}]")
                    else:
                        print(f"{progress_prefix} Skipping {os.path.basename(original_fname)} due to a read error.")
                else:
                    print(f"{progress_prefix} Including {os.path.basename(original_fname)} in average.")
                    
                    for key, value in single_result.items():
                        if key not in sum_result:
                            sum_result[key] = np.zeros_like(value)
                            if first_valid_file_path is None:
                                first_valid_file_path = original_fname
                        sum_result[key] += value
                    total_valid_files += count

            except Exception as exc:
                print(f"  Error with {os.path.basename(fname)}: {exc}")
                traceback.print_exc()

    main_end_time = time.time()
    print(f"\nTotal processing time for all files: {main_end_time - main_start_time:.2f} seconds.")

    if total_valid_files > 0:
        avg_result = {key: value / total_valid_files for key, value in sum_result.items()}

        if first_valid_file_path:
            output_dir = os.path.dirname(output_filename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            shutil.copy(first_valid_file_path, output_filename)
            apply_new_G2_to_file(output_filename, avg_result)

            print(f"\nAveraged data saved to '{output_filename}' (averaged over {total_valid_files} files).")
        else:
            print("\nNo valid files found to use as a template. Cannot save averaged data.")
    else:
        print("\nNo files passed the baseline check. No averaging performed.")


def main():
    """
    Main function to run the averaging process based on a JSON configuration file.
    """
    parser = argparse.ArgumentParser(description="Average G2 data from multiple HDF files using a JSON config file.")
    parser.add_argument("config_file", help="Path to the JSON configuration file.")
    args = parser.parse_args()

    with open(args.config_file, 'r') as f:
        config = json.load(f)
    
    print("Configuration loaded:")
    print(json.dumps(config, indent=2))

    flist = []
    try:
        base_path = config["file_path"]
        header = config["file_header"]
        file_range = config["file_range"]
    except KeyError as e:
        print(f"\nError: Configuration is missing a required key: {e}")
        print("Please ensure 'file_path', 'file_header', and 'file_range' are in your config file.")
        return

    # --- UNIFIED LOGIC: Check the value of 'file_range' ---
    
    # Mode 1: Search for all files if file_range is "all"
    if isinstance(file_range, str) and file_range.lower() == 'all':
        search_pattern = os.path.join(base_path, f"{header}*.hdf")
        print(f"\nMode: File Search. 'file_range' is 'all'.")
        print(f"Searching with pattern: {search_pattern}")
        flist = glob.glob(search_pattern)
        flist.sort()

    # MODIFIED Mode 2: Search with prefix, then filter by numerical range
    elif isinstance(file_range, list) and len(file_range) == 2:
        try:
            start, end = file_range
            print(f"\nMode: Search and Filter by Range. Header='{header}', Range={start}-{end}.")
            
            # Step 1: Search for all files that start with the header prefix
            search_pattern = os.path.join(base_path, f"{header}*.hdf")
            all_matching_files = glob.glob(search_pattern)
            
            # Step 2: Filter the results by the run number in the filename
            temp_flist = []
            for f in all_matching_files:
                # Use regex to find the number after '_r' in the filename
                match = re.search(r'_r(\d+)', os.path.basename(f))
                if match:
                    file_num = int(match.group(1))
                    if start <= file_num <= end:
                        temp_flist.append(f)
            flist = sorted(temp_flist)

        except (ValueError, TypeError):
             print("\nError: 'file_range' list must contain two integers (e.g., [400, 499]).")
             return
    
    # If file_range is invalid, exit with an error
    else:
        print("\nError: 'file_range' must be the string 'all' or a list of two integers (e.g., [400, 499]).")
        return

    # --- End of unified logic ---

    output_filename = config.get("output_filename", "averaged_results.hdf")
    full_output_path = os.path.join(base_path, output_filename)

    avg_window = config.get("baseline_window", 3)
    avg_qindex = config.get("baseline_qindex", 0)
    avg_blmin = config.get("baseline_min", 0.95)
    avg_blmax = config.get("baseline_max", 1.35)
    num_workers = config.get("num_workers", 12)
    
    if flist:
        fast_average_g2(
            flist,
            output_filename=full_output_path,
            avg_window=avg_window,
            avg_qindex=avg_qindex,
            avg_blmin=avg_blmin,
            avg_blmax=avg_blmax,
            num_workers=num_workers
        )
    else:
        print("\nNo files found for the selected mode. Please check your config file.")


if __name__ == "__main__":
    main()
