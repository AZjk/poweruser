from pathlib import Path
import shutil
import h5py
import tqdm
import os
import traceback
import concurrent.futures

META_TEMPLATE = Path(
    "/home/beams10/8IDIUSER/Documents/llps-saxpcs/reanalysis_2025_0428/sample_metadata.hdf"
)
MAX_DEPTH = 5

FIELD_MAPPING = {
    "/measurement/instrument/detector/exposure_period": "/entry/instrument/detector_1/frame_time",
    "/measurement/instrument/detector/distance": "/entry/instrument/detector_1/distance",
    "/measurement/instrument/detector/x_pixel_size": "/entry/instrument/detector_1/x_pixel_size",
    "/measurement/instrument/detector/y_pixel_size": "/entry/instrument/detector_1/y_pixel_size",
    "/measurement/instrument/detector/beam_center_x": "/entry/instrument/detector_1/beam_center_x",
    "/measurement/instrument/detector/beam_center_y": "/entry/instrument/detector_1/beam_center_y",
    "/measurement/sample/QNW_Zone1_Temperature": "/entry/sample/qnw1_temperature",
    "/measurement/sample/QNW_Zone2_Temperature": "/entry/sample/qnw2_temperature",
    "/measurement/sample/QNW_Zone3_Temperature": "/entry/sample/qnw3_temperature",
    "/measurement/sample/QNW_Zone1_Temperature_Set": "/entry/sample/qnw1_temperature_set",
    "/measurement/sample/QNW_Zone2_Temperature_Set": "/entry/sample/qnw2_temperature_set",
    "/measurement/sample/QNW_Zone3_Temperature_Set": "/entry/sample/qnw3_temperature_set",
    "/measurement/instrument/source_begin/energy": "/entry/instrument/incident_beam/incident_energy",
    "/measurement/instrument/source_begin/current": "/entry/instrument/incident_beam/ring_current",
    "/measurement/instrument/source_begin/beam_intensity_incident": "/entry/instrument/incident_beam/incident_beam_intensity",
    "/measurement/instrument/source_begin/beam_intensity_transmitted": "/entry/instrument/incident_beam/transmitted_beam_intensity",
    "/measurement/instrument/acquisition/stage_x": "/entry/instrument/detector_1/position_x",
    "/measurement/instrument/acquisition/stage_z": "/entry/instrument/detector_1/position_y",
    "/measurement/instrument/acquisition/compression": "/entry/instrument/detector_1/compression",
    "/measurement/instrument/acquisition/parent_folder": "/entry/instrument/bluesky/parent_folder",
    "/measurement/instrument/acquisition/specfile": "/entry/instrument/bluesky/spec_file",
    "/measurement/sample/thickness": "/entry/sample/thickness",
}


def copy_dataset_safe(src_group, dst_group, src_path, dst_path):
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
        dst_group.create_dataset(dst_path, data=data)
    except Exception:
        pass


def process_subfolder(subfolder_path, source_folder, dest_folder):
    """
    Process a single subfolder to convert legacy datasets.
    Parameters:
    - subfolder_path: Path to the subfolder to process.
    - source_folder: Path to the source folder.
    - dest_folder: Path to the destination folder.
    """
    try:
        bin_files = list(subfolder_path.glob("*.bin"))
        hdf_files = list(subfolder_path.glob("*.hdf"))

        if len(bin_files) != 1 or len(hdf_files) != 1:
            print(f"Skipping {subfolder_path}: requires 1 .bin and 1 .hdf file.")
            return

        relative_path = subfolder_path.relative_to(source_folder)
        save_folder = dest_folder / relative_path
        save_folder.mkdir(parents=True, exist_ok=True)

        bin_file = bin_files[0]
        rawmeta_file = hdf_files[0]

        linkname = save_folder / bin_file.name
        metaname = linkname.with_name(linkname.stem + "_metadata.hdf")

        if linkname.exists():
            if not (linkname.is_symlink() and linkname.resolve() == bin_file.resolve()):
                linkname.unlink()
                os.symlink(bin_file, linkname)
        else:
            os.symlink(bin_file, linkname)

        shutil.copy2(META_TEMPLATE, metaname)

        with h5py.File(rawmeta_file, "r") as src_hdf, h5py.File(
            metaname, "r+"
        ) as dst_hdf:
            for old_path, new_path in FIELD_MAPPING.items():
                if old_path in src_hdf:
                    copy_dataset_safe(src_hdf, dst_hdf, old_path, new_path)

            if "/measurement/sample/translation" in src_hdf:
                translation = src_hdf["/measurement/sample/translation"][()]
                if translation.shape[-1] >= 3:
                    for idx, axis in enumerate(["x", "y", "z"]):
                        dst_path = f"/entry/sample/position_{axis}"
                        if dst_path in dst_hdf:
                            del dst_hdf[dst_path]
                        dst_hdf.create_dataset(dst_path, data=translation[..., idx])

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
    subfolder_path, source_folder, dest_folder = args
    process_subfolder(Path(subfolder_path), Path(source_folder), Path(dest_folder))


def process_folder(source_folder, dest_folder, max_workers=None):
    """
    Process the folder structure and copy files.
    Parameters:
    - source_folder: The source folder path.
    - dest_folder: The destination folder path.
    - max_workers: The maximum number of worker processes to use. If None, use all available cores.
    """
    source_folder = Path(source_folder)
    dest_folder = Path(dest_folder)

    dest_folder.mkdir(parents=True, exist_ok=True)
    all_subfolders = list(walk_subfolders(source_folder, max_depth=MAX_DEPTH))
    tasks = [(subfolder, source_folder, dest_folder) for subfolder in all_subfolders]

    if max_workers == 1:
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

    parser = argparse.ArgumentParser(description="Process SAXPCS data folders.")
    parser.add_argument(
        "source_folder", type=str, help="Source folder containing data."
    )
    parser.add_argument(
        "dest_folder", type=str, help="Destination folder for processed data."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes. Set to 1 for sequential processing.",
    )

    args = parser.parse_args()
    process_folder(args.source_folder, args.dest_folder, max_workers=args.workers)
