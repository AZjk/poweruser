from pathlib import Path
import shutil
import h5py
import tqdm
import os
import traceback
import concurrent.futures
import numpy as np

META_TEMPLATE = Path(
    "/home/beams10/8IDIUSER/Documents/llps-saxpcs/reanalysis_2025_0428/sample_metadata.hdf"
)
MAX_DEPTH = 5

FIELD_MAPPING = {
    "/measurement/instrument/detector/exposure_period": (
        "/entry/instrument/detector_1/frame_time",
        1.0,
    ),
    "/measurement/instrument/detector/distance": (
        "/entry/instrument/detector_1/distance",
        0.001,
    ),
    "/measurement/instrument/detector/x_pixel_size": (
        "/entry/instrument/detector_1/x_pixel_size",
        0.001,
    ),
    "/measurement/instrument/detector/y_pixel_size": (
        "/entry/instrument/detector_1/y_pixel_size",
        0.001,
    ),
    "/measurement/instrument/detector/beam_center_x": (
        "/entry/instrument/detector_1/beam_center_x",
        1.0,
    ),
    "/measurement/instrument/detector/beam_center_y": (
        "/entry/instrument/detector_1/beam_center_y",
        1.0,
    ),
    "/measurement/sample/QNW_Zone1_Temperature": (
        "/entry/sample/qnw1_temperature",
        1.0,
    ),
    "/measurement/sample/QNW_Zone2_Temperature": (
        "/entry/sample/qnw2_temperature",
        1.0,
    ),
    "/measurement/sample/QNW_Zone3_Temperature": (
        "/entry/sample/qnw3_temperature",
        1.0,
    ),
    "/measurement/sample/QNW_Zone1_Temperature_Set": (
        "/entry/sample/qnw1_temperature_set",
        1.0,
    ),
    "/measurement/sample/QNW_Zone2_Temperature_Set": (
        "/entry/sample/qnw2_temperature_set",
        1.0,
    ),
    "/measurement/sample/QNW_Zone3_Temperature_Set": (
        "/entry/sample/qnw3_temperature_set",
        1.0,
    ),
    "/measurement/instrument/source_begin/energy": (
        "/entry/instrument/incident_beam/incident_energy",
        1.0,
    ),
    "/measurement/instrument/source_begin/current": (
        "/entry/instrument/incident_beam/ring_current",
        1.0,
    ),
    "/measurement/instrument/source_begin/beam_intensity_incident": (
        "/entry/instrument/incident_beam/incident_beam_intensity",
        1.0,
    ),
    "/measurement/instrument/source_begin/beam_intensity_transmitted": (
        "/entry/instrument/incident_beam/transmitted_beam_intensity",
        1.0,
    ),
    "/measurement/instrument/acquisition/stage_x": (
        "/entry/instrument/detector_1/position_x",
        0.001,
    ),
    "/measurement/instrument/acquisition/stage_z": (
        "/entry/instrument/detector_1/position_y",
        0.001,
    ),
    "/measurement/instrument/acquisition/stage_zero_x": (
        "/entry/instrument/detector_1/beam_center_position_x",
        0.001,
    ),
    "/measurement/instrument/acquisition/stage_zero_z": (
        "/entry/instrument/detector_1/beam_center_position_y",
        0.001,
    ),
    "/measurement/instrument/acquisition/compression": (
        "/entry/instrument/detector_1/compression",
        1,
    ),
    "/measurement/instrument/acquisition/parent_folder": (
        "/entry/instrument/bluesky/parent_folder",
        None,
    ),
    "/measurement/instrument/acquisition/specfile": (
        "/entry/instrument/bluesky/spec_file",
        None,
    ),
    "/measurement/sample/thickness": ("/entry/sample/thickness", 0.001),
}


def copy_dataset_safe(src_group, dst_group, src_path, dst_path, scale=None):
    """
    Safely copy a dataset from src_group to dst_group, handling potential exceptions.
    Parameters:
    - src_group: The source HDF5 group.
    - dst_group: The destination HDF5 group.
    - src_path: The path to the dataset in the source group.
    - dst_path: The path to the dataset in the destination group.
    """
    try:
        data = src_group[src_path][()]
        if dst_path in dst_group:
            del dst_group[dst_path]
        if scale is not None:
            data = data * scale
        # dst_group.create_dataset(dst_path, data=data)
        if isinstance(data, np.ndarray) and data.shape == (1, 1):
            dst_group[dst_path] = data.item()
        else:
            dst_group[dst_path] = data
    except Exception:
        pass


def process_subfolder(subfolder_path, source_folder, dest_folder, ftype):
    """
    Process a single subfolder to convert legacy datasets.
    Parameters:
    - subfolder_path: Path to the subfolder to process.
    - source_folder: Path to the source folder.
    - dest_folder: Path to the destination folder.
    """
    try:
        raw_files = list(subfolder_path.glob(f"*{ftype}"))
        hdf_files = list(subfolder_path.glob("*.hdf"))
        if len(raw_files) != 1 or len(hdf_files) != 1:
            print(f"Skipping {subfolder_path}: requires 1 {ftype} and 1 .hdf file.")
            return

        relative_path = subfolder_path.relative_to(source_folder)
        save_folder = dest_folder / relative_path
        save_folder.mkdir(parents=True, exist_ok=True)

        raw_file = raw_files[0]
        rawmeta_file = hdf_files[0]

        linkname = save_folder / raw_file.name
        metaname = linkname.with_name(linkname.stem + "_metadata.hdf")

        if linkname.exists():
            if not (linkname.is_symlink() and linkname.resolve() == raw_file.resolve()):
                linkname.unlink()
                os.symlink(raw_file, linkname)
        else:
            os.symlink(raw_file, linkname)

        shutil.copy2(META_TEMPLATE, metaname)

        with h5py.File(rawmeta_file, "r") as src_hdf, h5py.File(
            metaname, "r+"
        ) as dst_hdf:
            for old_path, (new_path, scale) in FIELD_MAPPING.items():
                if old_path in src_hdf:
                    copy_dataset_safe(src_hdf, dst_hdf, old_path, new_path, scale)

    except Exception as e:
        print(f"Error processing {subfolder_path}: {e}")
        traceback.print_exc()
        relative_path = subfolder_path.relative_to(source_folder)
        save_folder = dest_folder / relative_path
        if save_folder.exists():
            shutil.rmtree(save_folder)


def walk_subfolders(base_path, max_depth, current_depth=0):
    """
    Recursively walk through subfolders up to a specified depth.
    Parameters:
    - base_path: The starting directory.
    - max_depth: The maximum depth to recurse.
    - current_depth: The current depth of recursion (default is 0).
    """
    if current_depth > max_depth:
        return

    for entry in base_path.iterdir():
        if entry.is_dir():
            yield entry
            yield from walk_subfolders(entry, max_depth, current_depth + 1)


def worker_process_subfolder(args):
    """
    Worker function to process a single subfolder.
    """
    subfolder_path, source_folder, dest_folder, ftype = args
    process_subfolder(
        Path(subfolder_path), Path(source_folder), Path(dest_folder), ftype
    )


def process_folder(source_folder, dest_folder, max_workers=None, ftype=".bin"):
    """
    Process the folder structure and copy files.
    Parameters:
    - source_folder: The source folder path.
    - dest_folder: The destination folder path.
    - max_workers: The maximum number of worker processes to use. If None, use all available cores.
    """
    source_folder = Path(source_folder).resolve()
    dest_folder = Path(dest_folder).resolve()

    dest_folder.mkdir(parents=True, exist_ok=True)
    all_subfolders = list(walk_subfolders(source_folder, max_depth=MAX_DEPTH))
    tasks = [
        (subfolder, source_folder, dest_folder, ftype) for subfolder in all_subfolders
    ]

    if max_workers is None or max_workers == 1:
        for task in tqdm.tqdm(tasks, desc="Processing subfolders"):
            worker_process_subfolder(task)
    else:
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers
        ) as executor:
            list(
                tqdm.tqdm(
                    executor.map(worker_process_subfolder, tasks),
                    total=len(tasks),
                    desc="Processing subfolders",
                )
            )


if __name__ == "__main__":
    import argparse

    example_text = """\
    Example:
    python convert_legacy_datasets.py /path/to/source_folder /path/to/dest_folder --workers 1 --ftype .bin
    """

    parser = argparse.ArgumentParser(
        description="Convert legacy XPCS datasets to the new nexus format",
        epilog=example_text,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source_folder", type=str, help="Source folder containing data."
    )
    parser.add_argument(
        "dest_folder", type=str, help="Destination folder for processed data."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes. Set to 1 for sequential processing.",
    )
    parser.add_argument(
        "--ftype",
        type=str,
        default=".bin",
        help="File type to process. options: [.bin, .imm, .h5]",
    )

    args = parser.parse_args()
    process_folder(
        args.source_folder, args.dest_folder, max_workers=args.workers, ftype=args.ftype
    )
