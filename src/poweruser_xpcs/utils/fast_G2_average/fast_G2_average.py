"""
Optimized script for efficiently averaging data from HDF5 files using a
shared memory-based map-reduce strategy with a real-time progress bar.

This script leverages Python's `multiprocessing.shared_memory` to allow worker
processes to write their results directly into pre-allocated RAM blocks,
completely avoiding disk I/O and IPC bottlenecks for large data transfer.

"""

import h5py
import numpy as np
import tqdm
import shutil
import os
import time
import traceback
import argparse
import multiprocessing
from multiprocessing import shared_memory
import logging
import glob

# Import the key mapping and file writing utility from the user's custom module.
from apply_qmap import keymap, apply_new_G2_to_file

# --- Globals for Worker Processes ---
# These will be initialized by the pool's initializer function. This is the
# correct way to share non-picklable objects like locks with a process pool
# when using 'spawn' or 'forkserver' start methods.
g_progress_counter = None
g_progress_lock = None


def init_worker(counter, lock, level):
    """Initializer function for each worker process in the pool."""
    global g_progress_counter, g_progress_lock
    g_progress_counter = counter
    g_progress_lock = lock

    # Configure logging for each worker process
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_physical_core_count():
    """
    Determines the number of physical CPU cores. This is more reliable for
    CPU-bound tasks than using the logical core count from os.cpu_count().
    """
    try:
        import psutil

        return psutil.cpu_count(logical=False)
    except (ImportError, AttributeError):
        try:
            with open("/proc/cpuinfo") as f:
                core_ids = set()
                for line in f:
                    if "core id" in line:
                        core_ids.add(line.strip().split(":")[-1])
                if core_ids:
                    return len(core_ids)
        except:
            return os.cpu_count() // 2
    return os.cpu_count()


def find_first_valid_file_and_dims(
    flist, avg_window, avg_qindex, avg_blmin, avg_blmax, processing_dtype
):
    """Reads files sequentially until it finds one that is valid to get data shapes."""
    logging.info(
        "Searching for a valid file to determine array shapes for memory allocation..."
    )
    for fname in flist:
        try:
            with h5py.File(fname, "r", libver="latest") as fhdl:
                g2_data = fhdl[keymap["g2"]]
                idx_q = avg_qindex if avg_qindex < g2_data.shape[1] else 0
                g2_baseline = np.mean(g2_data[-avg_window:, idx_q])

                if avg_blmin <= g2_baseline <= avg_blmax:
                    logging.info(f"Found valid file: {os.path.basename(fname)}")
                    shapes = {}
                    dtypes = {}
                    for skey in ["G2", "saxs1d", "saxs1d_segments", "saxs2d"]:
                        dset = fhdl[keymap[skey]]
                        shapes[skey] = dset.shape
                        # FIX: Create a numpy.dtype object instance, not just a class
                        dtypes[skey] = np.dtype(processing_dtype)
                    return fname, shapes, dtypes
        except Exception:
            continue
    return None, None, None


def worker_process_chunk(args_tuple):
    """
    The "map" function. Processes a chunk of files, writes the sum directly
    into a dedicated shared memory block, and updates a shared progress counter.
    """
    flist_chunk, worker_args, worker_id, shm_metas = args_tuple
    avg_window, avg_qindex, avg_blmin, avg_blmax, h5_cache_size_mb, verbose = (
        worker_args
    )

    logger = logging.getLogger(f"Worker-{worker_id:02d}")

    logger.debug(f"Started. Processing {len(flist_chunk)} files.")

    # Attach to the existing shared memory blocks
    shm_blocks = {
        key: shared_memory.SharedMemory(name=meta["name"])
        for key, meta in shm_metas.items()
    }

    # Create numpy arrays that are views into the shared memory
    shm_arrays = {
        key: np.ndarray(meta["shape"], dtype=meta["dtype"], buffer=shm.buf)
        for (key, shm), meta in zip(shm_blocks.items(), shm_metas.values())
    }
    # Initialize this worker's memory block to zero
    for arr in shm_arrays.values():
        arr[:] = 0.0

    local_valid_files = 0
    first_valid_file_in_chunk = None
    skipped_files_in_chunk = []
    h5_cache_size_bytes = h5_cache_size_mb * 1024**2

    for i, fname in enumerate(flist_chunk):
        file_basename = os.path.basename(fname)
        try:
            with h5py.File(
                fname, "r", rdcc_nbytes=h5_cache_size_bytes, libver="latest"
            ) as fhdl:
                g2_data = fhdl[keymap["g2"]]
                idx_q = avg_qindex if avg_qindex < g2_data.shape[1] else 0
                g2_baseline = np.mean(g2_data[-avg_window:, idx_q])

                if avg_blmin <= g2_baseline <= avg_blmax:
                    if first_valid_file_in_chunk is None:
                        first_valid_file_in_chunk = fname

                    for skey, shm_arr in shm_arrays.items():
                        # NumPy correctly handles casting from file dtype to accumulator dtype
                        shm_arr += fhdl[keymap[skey]][()]
                    local_valid_files += 1
                else:
                    skipped_files_in_chunk.append((file_basename, g2_baseline))
        except Exception:
            skipped_files_in_chunk.append((file_basename, -1.0))

        # Increment the shared counter using the global variables
        with g_progress_lock:
            g_progress_counter.value += 1

    # Close the shared memory attachments, but don't unlink
    for shm in shm_blocks.values():
        shm.close()

    logger.debug("Finished chunk. Returning metadata.")

    return (
        local_valid_files,
        first_valid_file_in_chunk,
        skipped_files_in_chunk,
        worker_id,
    )


def fast_average_shared_memory(
    flist,
    output_filename="averaged_results.hdf",
    avg_window=3,
    avg_qindex=0,
    avg_blmin=0.95,
    avg_blmax=1.30,
    num_workers=None,
    h5_cache_size_mb=512,
    verbose=False,
    precision="single",
):
    if not flist:
        logging.warning("No files provided for averaging.")
        return

    # Determine processing precision
    processing_dtype = np.float32 if precision == "single" else np.float64
    logging.info(
        f"Using {precision} precision ({processing_dtype.__name__}) for processing."
    )

    # --- Pre-computation and Memory Allocation ---
    first_file, shapes, dtypes = find_first_valid_file_and_dims(
        flist, avg_window, avg_qindex, avg_blmin, avg_blmax, processing_dtype
    )
    if not first_file:
        logging.error("Could not find any valid files to process. Aborting.")
        return

    # --- Worker Configuration ---
    if num_workers is None:
        physical_cores = get_physical_core_count()
        logging.info(
            f"Detected {physical_cores} physical cores. Setting number of workers accordingly."
        )
        num_workers = physical_cores

    num_workers = min(num_workers, len(flist), os.cpu_count())
    logging.info(f"Using {num_workers} worker processes.")

    # --- Create a list of shared memory blocks, one for each worker ---
    all_shm_metas = []
    all_shm_blocks = []
    total_mem_gb = 0
    logging.info("Allocating shared memory blocks for worker results...")
    for i in range(num_workers):
        worker_shm_metas = {}
        worker_shm_blocks = {}
        for key in shapes:
            dtype = dtypes[key]
            shape = shapes[key]
            size = np.prod(shape) * dtype.itemsize
            total_mem_gb += size

            # Create the shared memory block
            shm = shared_memory.SharedMemory(create=True, size=size)
            worker_shm_metas[key] = {"name": shm.name, "shape": shape, "dtype": dtype}
            worker_shm_blocks[key] = shm
        all_shm_metas.append(worker_shm_metas)
        all_shm_blocks.append(worker_shm_blocks)
    logging.info(
        f"Successfully allocated {total_mem_gb / 1e9:.2f} GB of shared memory."
    )

    # --- Create Shared Progress Counter ---
    progress_counter = multiprocessing.Value("i", 0)
    progress_lock = multiprocessing.Lock()

    # --- Map Step ---
    file_chunks = np.array_split(flist, num_workers)
    worker_args = (
        avg_window,
        avg_qindex,
        avg_blmin,
        avg_blmax,
        h5_cache_size_mb,
        verbose,
    )
    # The counter and lock are no longer passed in the tasks tuple
    tasks = [
        (chunk, worker_args, i + 1, all_shm_metas[i])
        for i, chunk in enumerate(file_chunks)
        if chunk.size > 0
    ]

    final_sum_result = {}
    total_valid_files = 0
    first_valid_file_path = None
    all_skipped_files = []

    logging.info("Starting file processing (map stage)...")
    main_start_time = time.time()
    try:
        # Pass the initializer function and its arguments to the Pool
        log_level = logging.DEBUG if verbose else logging.INFO
        pool_initargs = (progress_counter, progress_lock, log_level)
        with multiprocessing.Pool(
            processes=num_workers, initializer=init_worker, initargs=pool_initargs
        ) as pool:
            # Use map_async for non-blocking execution
            result_async = pool.map_async(worker_process_chunk, tasks)

            # Monitor progress while workers are busy
            with tqdm.tqdm(total=len(flist), desc="Processing Files") as pbar:
                while not result_async.ready():
                    pbar.n = progress_counter.value
                    pbar.refresh()
                    time.sleep(0.1)  # Update UI 10 times per second

                # Final update to make sure the bar reaches 100%
                pbar.n = progress_counter.value
                pbar.refresh()

            # Now, get the results from the workers
            results = result_async.get()

        for local_count, local_first_valid, local_skipped, worker_id in results:
            logging.debug(f"Received metadata from Worker {worker_id:02d}")
            total_valid_files += local_count
            all_skipped_files.extend(local_skipped)
            if first_valid_file_path is None and local_first_valid is not None:
                first_valid_file_path = local_first_valid

        map_end_time = time.time()
        logging.info(
            f"Map stage completed in {map_end_time - main_start_time:.2f} seconds."
        )

        # --- Reduce Step (in main process from shared memory) ---
        logging.info("Starting result aggregation from shared memory (reduce stage)...")
        reduce_start_time = time.time()

        worker_results_in_ram = []
        for i in range(num_workers):
            worker_result = {
                key: np.ndarray(
                    meta["shape"],
                    dtype=meta["dtype"],
                    buffer=all_shm_blocks[i][key].buf,
                )
                for key, meta in all_shm_metas[i].items()
            }
            worker_results_in_ram.append(worker_result)

        # Sum the results from all workers
        for key in shapes:
            # Initialize the final sum with the result from the first worker's memory
            # Use a copy to avoid modifying the shared memory block directly
            sum_arr = worker_results_in_ram[0][key].copy()
            # Add the results from the remaining workers
            for i in range(1, num_workers):
                sum_arr += worker_results_in_ram[i][key]
            final_sum_result[key] = sum_arr

        logging.info(
            f"Reduce stage completed in {time.time() - reduce_start_time:.2f} seconds."
        )

        # --- Finalization and Output ---
        if total_valid_files > 0 and first_valid_file_path:
            logging.info("Calculating final average and saving to disk...")
            avg_result = {
                key: value / total_valid_files
                for key, value in final_sum_result.items()
            }

            try:
                output_dir = os.path.dirname(output_filename)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                shutil.copy(first_valid_file_path, output_filename)
                apply_new_G2_to_file(output_filename, avg_result)
                logging.info(
                    f"✅ Success! Averaged data saved to '{output_filename}', and it's ready for use."
                )
            except Exception:
                logging.exception(f"❌ Error saving output file:")
        else:
            logging.warning(
                "No files passed the baseline check. No averaging performed."
            )

        # --- Summary ---
        logging.info("--- Summary ---")
        logging.info(
            f"Total processing time: {time.time() - main_start_time:.2f} seconds."
        )
        logging.info(f"Processed {len(flist)} files in total.")
        logging.info(f"Found {total_valid_files} files that met the baseline criteria.")

        if all_skipped_files:
            logging.info(f"Skipped {len(all_skipped_files)} files.")
            for i, (fname, baseline) in enumerate(all_skipped_files[:5]):
                status = (
                    f"baseline {baseline:.4f}" if baseline != -1.0 else "read error"
                )
                logging.info(f"  - Example Skipped: {fname} ({status})")
            if len(all_skipped_files) > 5:
                logging.info("  ...")

    finally:
        # --- Crucial Cleanup Step ---
        logging.info("Cleaning up shared memory blocks...")
        for worker_blocks in all_shm_blocks:
            for shm in worker_blocks.values():
                shm.close()
                shm.unlink()  # Free the memory
        logging.info("Cleanup complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Average G2 data from HDF files using a shared-memory map-reduce strategy.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input_path",
        help="A text file with a list of input HDF files (one per line), a folder containing *_result.hdf files, OR a path prefix (e.g., /path/to/folder/my_prefix to match my_prefix* files).",
    )
    parser.add_argument(
        "-o", "--output", default="averaged_results.hdf", help="Output file name."
    )
    parser.add_argument(
        "--baseline-min",
        type=float,
        default=0.95,
        help="Minimum g2 baseline to include file.",
    )
    parser.add_argument(
        "--baseline-max",
        type=float,
        default=1.35,
        help="Maximum g2 baseline to include file.",
    )
    parser.add_argument(
        "--baseline-qindex",
        type=int,
        default=0,
        help="Q index for baseline calculation.",
    )
    parser.add_argument(
        "--baseline-window",
        type=int,
        default=3,
        help="Window size for baseline calculation.",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=None,
        help="Num worker processes (default: physical cores).",
    )
    parser.add_argument(
        "--cache-mb",
        type=int,
        default=512,
        help="HDF5 raw chunk cache per worker (in MB).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed, per-file diagnostic logging (DEBUG level).",
    )
    parser.add_argument(
        "--precision",
        type=str,
        default="single",
        choices=["single", "double"],
        help="Processing precision for accumulation (default: single).",
    )
    args = parser.parse_args()

    # --- Configure Root Logger ---
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # It's recommended to install psutil for best performance: pip install psutil
    try:
        import psutil
    except ImportError:
        logging.warning(
            "`psutil` not found. Worker count will be based on a fallback. For optimal performance, please install it using: `pip install psutil`"
        )

    # Determine if input_path is a file, directory, or prefix
    if os.path.isdir(args.input_path):
        # It's a directory - search for *_result.hdf files
        search_pattern = os.path.join(args.input_path, "*_results.hdf")
        flist = glob.glob(search_pattern)
        if not flist:
            logging.error(
                f"No '*_results.hdf' files found in directory: {args.input_path}"
            )
            return
        flist.sort()  # Sort for consistent processing order
        logging.info(
            f"Found {len(flist)} '*_results.hdf' files in directory: {args.input_path}"
        )
    elif os.path.isfile(args.input_path):
        # It's a file - read file list from it
        try:
            with open(args.input_path, "r") as f:
                flist = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            logging.exception(
                f"Error: The file list '{args.input_path}' was not found."
            )
            return
    else:
        # Check if it's a prefix pattern (e.g., /path/to/folder/my_prefix)
        # Extract directory and prefix from the path
        input_dir = os.path.dirname(args.input_path)
        prefix = os.path.basename(args.input_path)

        if os.path.isdir(input_dir) and prefix:
            # Search for files matching the prefix pattern
            search_pattern = os.path.join(input_dir, f"{prefix}*")
            flist = glob.glob(search_pattern)
            # Filter to only include files (not directories)
            flist = [f for f in flist if os.path.isfile(f)]
            if not flist:
                logging.error(
                    f"No files found matching prefix '{prefix}' in directory: {input_dir}"
                )
                return
            flist.sort()  # Sort for consistent processing order
            logging.info(
                f"Found {len(flist)} files matching prefix '{prefix}' in directory: {input_dir}"
            )
        else:
            logging.error(
                f"Input path '{args.input_path}' is not a valid file, directory, or prefix pattern."
            )
            return

    logging.info("--- Configuration ---")
    logging.info(f"Output file:           {args.output}")
    logging.info(f"Baseline range:        [{args.baseline_min}, {args.baseline_max}]")
    logging.info(f"Baseline Q-index:      {args.baseline_qindex}")
    logging.info(f"Baseline window:       {args.baseline_window}")
    logging.info(f"HDF5 cache per worker: {args.cache_mb} MB")
    logging.info(f"Processing Precision:  {args.precision}")
    logging.info(f"Verbose Logging:       {'Enabled' if args.verbose else 'Disabled'}")
    logging.info("---------------------\n")

    if flist:
        fast_average_shared_memory(
            flist,
            output_filename=args.output,
            avg_window=args.baseline_window,
            avg_qindex=args.baseline_qindex,
            avg_blmin=args.baseline_min,
            avg_blmax=args.baseline_max,
            num_workers=args.num_workers,
            h5_cache_size_mb=args.cache_mb,
            verbose=args.verbose,
            precision=args.precision,
        )


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    if multiprocessing.get_start_method(allow_none=True) != "spawn":
        multiprocessing.set_start_method("spawn", force=True)
    main()
