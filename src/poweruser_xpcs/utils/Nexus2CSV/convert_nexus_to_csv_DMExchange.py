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
        - <basename>_g2.csv : Contains the compiled g2 data.
        - <basename>_g2err.csv : Contains the compiled g2 error data.
        - <basename>_saxs.csv : Contains the SAXS intensity profile.
        
    """
    try:
        with h5py.File(fn, "r") as hf:
            g2 = hf["exchange"]["norm-0-g2"][:]
            g2err = hf["exchange"]["norm-0-stderr"][:]
            t_el = hf["exchange"]["tau"][:]
            saxs_1d = hf["exchange"]["partition-mean-total"][:]
            saxs_1d_seg = hf["exchange"]["partition-mean-partial"][:]
            t0 = hf["entry"]["instrument"]["detector_1"]["acquire_period"][()]
            ql_dyn = hf["xpcs"]["dqlist"][:]
            ql_sta = hf["xpcs"]["sqlist"][:]
            start_time = hf["entry"]["start_time"][()]

        g2_compiled = np.zeros((g2.shape[0] + 1, g2.shape[1] + 1))
        g2_compiled[1:, 0] = t_el * t0
        g2_compiled[1:, 1:] = g2
        g2_compiled[0, 1:] = ql_dyn
        
        g2err_compiled = np.zeros((g2err.shape[0] + 1, g2err.shape[1] + 1))
        g2err_compiled[1:, 0] = t_el * t0
        g2err_compiled[1:, 1:] = g2err
        g2err_compiled[0, 1:] = ql_dyn

        temp_saxs = np.zeros((saxs_1d_seg.shape[0] + 2, saxs_1d_seg.shape[1]))
        temp_saxs[0, :] = ql_sta
        temp_saxs[1, :] = saxs_1d
        temp_saxs[2:, :] = saxs_1d_seg
        saxs_1d_compiled = np.transpose(temp_saxs)

        base_name = os.path.splitext(os.path.basename(fn))[0]
        fn_csv_g2 = os.path.join(out_path, base_name + "_g2.csv")
        fn_csv_g2err = os.path.join(out_path, base_name + "_g2err.csv")
        fn_csv_saxs = os.path.join(out_path, base_name + "_saxs.csv")

        np.savetxt(fn_csv_g2, g2_compiled, delimiter=",")
        np.savetxt(fn_csv_g2err, g2err_compiled, delimiter=",")
        np.savetxt(fn_csv_saxs, saxs_1d_compiled, delimiter=",")

        print(f"Successfully wrote: {fn_csv_g2}, {fn_csv_g2err}, {fn_csv_saxs}")

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
