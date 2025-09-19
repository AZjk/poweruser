import argparse
import os
import h5py
import numpy as np
import csv


def hdf2csv(fn, out_path):
    """
    Convert an HDF5 file into three CSV files containing G2, SAXS, and metadata information.

    Parameters
    ----------
    fn : str
        The path to the HDF5 file to convert.
    out_path : str
        The directory where the output CSV files will be saved.

    Outputs
    -------
    Creates three CSV files:
        - <basename>_g2.csv : Contains the compiled G2 data.
        - <basename>_saxs.csv : Contains the SAXS intensity profile.
        - <basename>_meta.csv : Contains extracted metadata (e.g., start time, positions).
    """
    try:
        with h5py.File(fn, "r") as hf:
            g2 = hf["xpcs"]["multitau"]["normalized_g2"][:]
            t_el = hf["xpcs"]["multitau"]["delay_list"][:]
            saxs_1d = hf["xpcs"]["temporal_mean"]["scattering_1d"][:]
            saxs_1d_seg = hf["xpcs"]["temporal_mean"]["scattering_1d_segments"][:]
            t0 = hf["entry"]["instrument"]["detector_1"]["frame_time"][()]
            ql_dyn = hf["xpcs"]["qmap"]["dynamic_v_list_dim0"][:]
            ql_sta = hf["xpcs"]["qmap"]["static_v_list_dim0"][:]
            start_time = hf["entry"]["start_time"][()]
            position_rheo_x = hf["entry"]["sample"]["position_rheo_x"][()]
            position_rheo_y = hf["entry"]["sample"]["position_rheo_y"][()]
            position_rheo_z = hf["entry"]["sample"]["position_rheo_z"][()]

        metadata_name = [
            "start_time",
            "position_rheo_x",
            "position_rheo_y",
            "position_rheo_z",
        ]
        metadata_value = [start_time, position_rheo_x, position_rheo_y, position_rheo_z]

        g2_compiled = np.zeros((g2.shape[0] + 1, g2.shape[1] + 1))
        g2_compiled[1:, 0] = t_el * t0
        g2_compiled[1:, 1:] = g2
        g2_compiled[0, 1:] = ql_dyn

        temp_saxs = np.zeros((saxs_1d_seg.shape[0] + 2, saxs_1d_seg.shape[1]))
        temp_saxs[0, :] = ql_sta
        temp_saxs[1, :] = saxs_1d
        temp_saxs[2:, :] = saxs_1d_seg
        saxs_1d_compiled = np.transpose(temp_saxs)

        base_name = os.path.splitext(os.path.basename(fn))[0]
        fn_csv_g2 = os.path.join(out_path, base_name + "_g2.csv")
        fn_csv_saxs = os.path.join(out_path, base_name + "_saxs.csv")
        fn_csv_meta = os.path.join(out_path, base_name + "_meta.csv")

        np.savetxt(fn_csv_g2, g2_compiled, delimiter=",")
        np.savetxt(fn_csv_saxs, saxs_1d_compiled, delimiter=",")

        with open(fn_csv_meta, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Metadata Names", "Metadata Values"])
            writer.writerows(zip(metadata_name, metadata_value))

        print(f"Successfully wrote: {fn_csv_g2}, {fn_csv_saxs}, {fn_csv_meta}")

    except Exception as e:
        print(f"Error processing {fn}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert HDF5 files to CSV format (no pandas)."
    )
    parser.add_argument(
        "--input", type=str, required=True, help="Path to the folder with HDF5 files."
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Path to save CSV files."
    )
    parser.add_argument(
        "--filter",
        type=str,
        required=False,
        default="",
        help="Optional substring filter for filenames.",
    )

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output
    filter_str = args.filter

    os.makedirs(output_path, exist_ok=True)

    for filename in os.listdir(input_path):
        if (filename.endswith(".hdf") or filename.endswith(".hdf5")) and (
            filter_str in filename
        ):
            full_path = os.path.join(input_path, filename)
            hdf2csv(full_path, output_path)
