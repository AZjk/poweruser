"""Extract intensity, g2, q-values, time-delays, and metadata from a processed XPCS/NeXus HDF5 file."""

import argparse
import json
import logging
import os

import h5py
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def export_metadata(label, metadata, use_json=True, use_txt=True, use_xlsx=True):
    """Write a metadata dict to `{label}_metadata.json/.txt/.xlsx`."""
    if use_json:
        json_filename = f"{label}_metadata.json"
        with open(json_filename, "w") as json_file:
            json.dump(metadata, json_file, indent=4)

    if use_txt:
        txt_filename = f"{label}_metadata.txt"
        with open(txt_filename, "w") as txt_file:
            for key, value in metadata.items():
                txt_file.write(f"{key} = {value}\n")

    if use_xlsx:
        xls_filename = f"{label}_metadata.xlsx"
        df = pd.DataFrame(list(metadata.items()), columns=["Key", "Value"])
        df.to_excel(xls_filename, index=False)


def _read_metadata(hf):
    """Read fields present in any XPCS/NeXus file; skip and warn on any that are missing."""
    fields = {
        "start_time": "entry/start_time",
        "frame_time": "entry/instrument/detector_1/frame_time",
    }
    metadata = {}
    for name, path in fields.items():
        try:
            value = hf[path][()]
        except KeyError:
            logger.warning(f"Metadata field '{path}' not found, skipping.")
            continue
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        metadata[name] = value
    return metadata


def export_nexus(input_file, output_file):
    """
    Extract intensity, g2, q-values, and time-delays from a processed
    XPCS/NeXus HDF5 file and write them to a new, smaller NeXus file,
    along with a metadata export (JSON/TXT/XLSX).

    Parameters
    ----------
    input_file : str
        Path to the source HDF5/NeXus file. Must contain xpcs/multitau,
        xpcs/qmap, and xpcs/temporal_mean groups (i.e. already processed).
    output_file : str
        Path to the output NeXus file to create.
    """
    with h5py.File(input_file, "r") as hf:
        metadata = _read_metadata(hf)
        g2 = hf["xpcs"]["multitau"]["normalized_g2"][:]
        delay_list = hf["xpcs"]["multitau"]["delay_list"][:]
        frame_time = hf["entry"]["instrument"]["detector_1"]["frame_time"][()]
        intensity = hf["xpcs"]["temporal_mean"]["scattering_1d"][:]
        q_values = hf["xpcs"]["qmap"]["dynamic_v_list_dim0"][:]

    time_delays = delay_list * frame_time

    label = os.path.splitext(output_file)[0]
    export_metadata(label=label, metadata=metadata)

    with h5py.File(output_file, "w") as nexus_file:
        nexus_file.create_dataset("intensity", data=intensity)
        nexus_file.create_dataset("g2", data=g2)
        nexus_file.create_dataset("q_values", data=q_values)
        nexus_file.create_dataset("time_delays", data=time_delays)

    logger.info(f"Exported {input_file} to {output_file} successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract intensity, g2, q-values, and time-delays from a processed XPCS/NeXus HDF5 file."
    )
    parser.add_argument("input_file", type=str, help="Path to the source HDF5/NeXus file.")
    parser.add_argument(
        "-o", "--output", type=str, required=True, help="Path to the output NeXus file."
    )
    args = parser.parse_args()

    export_nexus(args.input_file, args.output)
