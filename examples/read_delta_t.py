import h5py

def get_delta_t(fname, debug=False):
    """
    Get the time interval between frames in seconds.
    Parameters
    ----------
    fname : str
        The name of the HDF5 file.
    Returns
    -------
    delta_t : float
        The time interval between frames in seconds.
    """
    with h5py.File(fname, "r") as f:
        stride_frame = f["/xpcs/multitau/config/stride_frame"][()]
        avg_frame =  f["/xpcs/multitau/config/avg_frame"][()]
        frame_time = f["/entry/instrument/detector_1/frame_time"][()]
    delta_t = frame_time * avg_frame * stride_frame
    if debug:
        print(f"stride_frame: {stride_frame} frame")
        print(f"avg_frame: {avg_frame} frame")
        print(f"frame_time: {frame_time} seconds")
        print(f"delta_t: {delta_t} seconds")
    return delta_t


if __name__ == "__main__":
    print(get_delta_t("../test_datasets/A0029_CPMV_a0007_f100000_r00001_results.hdf", debug=True))