from pyxpcsviewer import XpcsFile as XF
import numpy as np
import h5py
import json
import pandas as pd


def export_metadata(label, metadata, use_json=True, use_txt=True, use_xlsx=True):
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


def export_nexus(input_file, output_file):
    """
    Export a .xpcs file to a Nexus file.

    Parameters
    ----------
    input_file : str
        Path to the input .xpcs file.
    output_file : str
        Path to the output Nexus file.
    """
    # Load the .xpcs file
    dset = XF(input_file)
    metadata = dset.get_hdf_info()
    export_metadata(label=output_file.replace('.nxs',''), metadata=metadata)


    # Extract relevant data
    intensity = dset.get_intensity()
    g2 = dset.get_g2()
    q_values = dset.get_q_values()
    time_delays = dset.get_time_delays()

    # Create a Nexus file and write data
    with h5py.File(output_file, "w") as nexus_file:
        nexus_file.create_dataset("intensity", data=intensity)
        nexus_file.create_dataset("g2", data=g2)
        nexus_file.create_dataset("q_values", data=q_values)
        nexus_file.create_dataset("time_delays", data=time_delays)

    print(f"Exported {input_file} to {output_file} successfully.")


if __name__ == "__main__":
    # Example usage
    input_xpcs_file = "example.xpcs"
    output_nexus_file = "output.nxs"
    export_nexus(input_xpcs_file, output_nexus_file)
