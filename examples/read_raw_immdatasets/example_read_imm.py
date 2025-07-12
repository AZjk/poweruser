"""
Module for reading and processing IMM (Image Memory Map) dataset files.

This module provides functionality to read IMM format files commonly used in
X-ray Photon Correlation Spectroscopy (XPCS) experiments. It includes utilities
for parsing IMM headers, reading both sparse and dense format data, and 
visualizing the results.

Classes:
    ImmDataset: Main class for reading and accessing IMM format datasets.

Functions:
    read_imm_header: Parse the 1024-byte header of an IMM file.
    read_data: Read and process an entire IMM file, displaying statistics.
    test02: Example function demonstrating usage.

Example:
    >>> from example_read_imm import ImmDataset
    >>> dataset = ImmDataset('path/to/file.imm', batch_size=1024)
    >>> batch = dataset[0]  # Get first batch of frames
"""

import struct
import numpy as np
import time
import logging
import os
from typing import Dict, Tuple, BinaryIO, Optional
from tqdm import trange
from xpcs_dataset import XpcsDataset
import matplotlib.pyplot as plt


logger = logging.getLogger(__name__)


def read_imm_header(file: BinaryIO) -> Dict[str, any]:
    """
    Read and parse the header of an IMM file.
    
    IMM files have a 1024-byte header containing metadata about the image data,
    including dimensions, compression type, timestamps, and various experimental
    parameters.
    
    Parameters
    ----------
    file : BinaryIO
        An open binary file object positioned at the start of an IMM header.
        
    Returns
    -------
    dict
        A dictionary containing all header fields with their corresponding values.
        Key fields include:
        - 'rows', 'cols': Image dimensions
        - 'compression': Compression type (6 indicates sparse format)
        - 'dlen': Data length
        - 'bytes': Number of bytes per pixel
        - Various PV (process variable) fields for experimental parameters
        
    Notes
    -----
    The header format is based on the IMM specification used at APS beamlines.
    The header is exactly 1024 bytes with a fixed structure.
    """
    # IMM header format string for struct.unpack
    imm_headformat = (
        "ii32s16si16siiiiiiiiiiiiiddiiIiiI40sf40sf40sf40s"
        + "f40sf40sf40sf40sf40sf40sfffiiifc295s84s12s"
    )
    
    # Field names corresponding to the format string
    imm_fieldnames = [
        "mode",
        "compression",
        "date",
        "prefix",
        "number",
        "suffix",
        "monitor",
        "shutter",
        "row_beg",
        "row_end",
        "col_beg",
        "col_end",
        "row_bin",
        "col_bin",
        "rows",
        "cols",
        "bytes",
        "kinetics",
        "kinwinsize",
        "elapsed",
        "preset",
        "topup",
        "inject",
        "dlen",
        "roi_number",
        "buffer_number",
        "systick",
        "pv1",
        "pv1VAL",
        "pv2",
        "pv2VAL",
        "pv3",
        "pv3VAL",
        "pv4",
        "pv4VAL",
        "pv5",
        "pv5VAL",
        "pv6",
        "pv6VAL",
        "pv7",
        "pv7VAL",
        "pv8",
        "pv8VAL",
        "pv9",
        "pv9VAL",
        "pv10",
        "pv10VAL",
        "imageserver",
        "CPUspeed",
        "immversion",
        "corecotick",
        "cameratype",
        "threshhold",
        "byte632",
        "empty_space",
        "ZZZZ",
        "FFFF",
    ]

    # Read exactly 1024 bytes for the header
    bindata = file.read(1024)

    # Unpack binary data according to the format
    imm_headerdat = struct.unpack(imm_headformat, bindata)
    
    # Create dictionary mapping field names to values
    imm_header = dict(zip(imm_fieldnames, imm_headerdat))

    return imm_header


class ImmDataset(XpcsDataset):
    """
    A dataset class for reading IMM (Image Memory Map) format files.
    
    This class provides efficient access to IMM files, supporting both dense
    and sparse data formats. It inherits from XpcsDataset to provide a 
    consistent interface for XPCS data processing.
    
    Parameters
    ----------
    filename : str
        Path to the .imm file to read.
    dtype : numpy.dtype, optional
        Data type for pixel values. Default is np.int16.
    frames_per_point : int, optional
        Number of frames to return as one datum. Default is 1.
    **kwargs
        Additional keyword arguments passed to the parent XpcsDataset class.
        
    Attributes
    ----------
    dataset_type : str
        Type identifier, always "IMM Legacy" for this class.
    frames_per_point : int
        Number of frames grouped together per data point.
    toc : numpy.ndarray
        Table of contents array with shape (n_frames, 2) containing
        (start_byte, element_count) pairs for each frame.
    det_size : tuple
        Detector dimensions as (rows, cols).
    is_sparse : bool
        True if the data is stored in sparse format (compression=6).
    fh : file object or None
        File handle for reading data, opened on demand.
        
    Examples
    --------
    >>> dataset = ImmDataset('experiment.imm', batch_size=100)
    >>> print(f"Dataset has {len(dataset)} batches")
    >>> first_batch = dataset[0]
    """

    def __init__(
        self,
        *args,
        dtype: np.dtype = np.int16,
        frames_per_point: int = 1,
        **kwargs,
    ):
        """Initialize the ImmDataset with file information and parameters."""
        super(ImmDataset, self).__init__(*args, dtype=dtype, **kwargs)
        self.dataset_type = "IMM Legacy"
        self.frames_per_point = frames_per_point

        # Read table of contents and detector size from file
        self.toc, self.det_size = self.read_toc()

        # Update frame_num and batch info based on TOC
        self.update_batch_info(self.toc.shape[0])
        self.update_det_size(self.det_size)
        self.fh = None

    def read_toc(self) -> Tuple[np.ndarray, Tuple[int, int]]:
        """
        Read table of contents from the IMM file.
        
        Scans through the entire IMM file to build a table of contents (TOC)
        that maps frame indices to file positions. This allows for efficient
        random access to frames without reading the entire file.
        
        Returns
        -------
        tuple
            A tuple containing:
            - toc (numpy.ndarray): Array of shape (n_frames, 2) with 
              (start_byte, element_count) for each frame
            - det_size (tuple): Detector dimensions as (rows, cols)
            
        Raises
        ------
        IOError
            If the IMM file is corrupted or cannot be read properly.
            
        Notes
        -----
        The method determines if data is sparse based on the compression
        field in the header (compression=6 indicates sparse format).
        """
        with open(self.fname, "rb") as f:
            # Read first header to get detector info
            header = read_imm_header(f)
            det_size = (header["rows"], header["cols"])
            self.is_sparse = bool(header["compression"] == 6)
            
            # Reset to beginning of file
            f.seek(0)
            toc = []  # Will store (start byte, element count) pairs
            
            # Scan through all frames in the file
            while True:
                try:
                    header = read_imm_header(f)
                    cur = f.tell()
                    
                    # Calculate payload size based on format
                    # Sparse: 4 bytes index + 2 bytes count = 6 bytes per pixel
                    # Dense: 2 bytes per pixel
                    payload_size = header["dlen"] * (6 if self.is_sparse else 2)
                    toc.append((cur, header["dlen"]))

                    # Move to next frame
                    file_pos = payload_size + cur
                    f.seek(file_pos)

                    # Check for end of file
                    if not f.peek(4):
                        break

                except Exception as err:
                    raise IOError("IMM file is corrupted.") from err

            return np.array(toc), det_size

    def __reset__(self) -> None:
        """
        Reset the dataset state.
        
        Closes any open file handles to free resources. Called when the
        dataset needs to be reset or cleaned up.
        """
        if self.fh is not None:
            self.fh.close()
            self.fh = None

    def __getbatch__(self, index: int) -> np.ndarray:
        """
        Get a batch of frames at the specified index.
        
        Parameters
        ----------
        index : int
            Batch index to retrieve.
            
        Returns
        -------
        numpy.ndarray
            Array of shape (batch_size, n_pixels) containing the frame data.
            If mask_crop is set, returns (batch_size, n_masked_pixels).
            
        Notes
        -----
        Opens the file handle on first access and keeps it open for
        subsequent reads to improve performance.
        """
        # Open file handle if not already open
        if self.fh is None:
            self.fh = open(self.fname, "rb")

        # Read data based on format
        if self.is_sparse:
            x = self.__get_frame_sparse__(index)
        else:
            x = self.__get_frame_dense__(index)

        # Apply mask cropping if specified
        if self.mask_crop is not None:
            x = x[:, self.mask_crop]
        return x

    def __get_frame_dense__(self, batch_idx: int) -> np.ndarray:
        """
        Read frames stored in dense format.
        
        Parameters
        ----------
        batch_idx : int
            Batch index to read.
            
        Returns
        -------
        numpy.ndarray
            Array of shape (n_frames, n_pixels) containing dense frame data.
            
        Notes
        -----
        Dense format stores all pixel values sequentially, even zeros.
        """
        beg, end, size = self.get_raw_index(batch_idx)
        idx_list = np.arange(beg, end, self.stride)
        toc = self.toc[idx_list]
        
        imgs = []
        for start_byte, event_num in toc:
            self.fh.seek(start_byte)
            # Read uint16 data and convert to int16
            imgs.append(np.fromfile(self.fh, dtype=np.uint16, count=event_num))
            
        imgs = np.array(imgs).astype(np.int16)
        return imgs

    def __get_frame_sparse__(self, batch_idx: int) -> np.ndarray:
        """
        Read frames stored in sparse format.
        
        Parameters
        ----------
        batch_idx : int
            Batch index to read.
            
        Returns
        -------
        numpy.ndarray
            Array of shape (n_frames, n_pixels) containing reconstructed
            dense frame data from sparse representation.
            
        Notes
        -----
        Sparse format stores only non-zero pixels as (index, count) pairs,
        which is more efficient for low-count X-ray data.
        """
        beg, end, size = self.get_raw_index(batch_idx)
        idx_list = np.arange(beg, end, self.stride)
        toc = self.toc[idx_list]

        # Lists to accumulate sparse data
        frame = []
        index = []
        count = []
        
        # Read sparse data for each frame
        for n, (start_byte, event_num) in enumerate(toc):
            self.fh.seek(start_byte)
            # Frame indices for reconstruction
            frame.append(np.zeros(event_num, dtype=np.int16) + n)
            # Pixel indices (4 bytes each)
            index.append(np.fromfile(self.fh, dtype=np.int32, count=event_num))
            # Pixel counts (2 bytes each)
            count.append(np.fromfile(self.fh, dtype=self.dtype, count=event_num))
            
        # Concatenate all sparse data
        frame = np.concatenate(frame)
        index = np.concatenate(index)
        count = np.concatenate(count)

        # Convert sparse to dense format
        return self.sparse_to_dense(index, frame, count, size)

    def __del__(self) -> None:
        """
        Cleanup method to ensure file handle is closed.
        
        Called when the object is garbage collected to prevent
        resource leaks.
        """
        try:
            if self.fh is not None:
                self.fh.close()
        except Exception:
            pass


def read_data(file_name: str, batch_size: int = 1024) -> float:
    """
    Read and process an entire IMM file, displaying performance statistics.
    
    This function reads through an entire IMM file, computes the sum
    scattering pattern, displays it as a log-scale image, and reports
    the reading performance.
    
    Parameters
    ----------
    file_name : str
        Path to the IMM file to read.
    batch_size : int, optional
        Number of frames to read per batch. Default is 1024.
        
    Returns
    -------
    float
        Reading frequency in Hz (frames per second).
        
    Notes
    -----
    The function displays a matplotlib figure showing the log-scale
    sum of all frames, which represents the time-averaged scattering
    pattern.
    
    Examples
    --------
    >>> freq = read_data('/path/to/data.imm', batch_size=512)
    >>> print(f"Achieved {freq:.1f} Hz reading speed")
    """
    logger.info("Starting to read file: %s", os.path.basename(file_name))
    logger.info("Directory: %s", os.path.dirname(file_name))
    
    # Create dataset instance
    imm = ImmDataset(file_name, batch_size=batch_size)
    logger.info("Table of contents generated")
    logger.info("Total frames in file: %d", len(imm.toc))

    # Time the reading process
    stime = time.perf_counter()
    sum_scattering = 0
    
    # Read all batches with progress bar
    for n in trange(len(imm), desc="Reading batches"):
        x = imm[n]
        # x is a 2d array with (number_of_batch, detector_height x detector_width)
        # place your code here to process the data
        sum_scattering += np.sum(x, axis=0)
        
    etime = time.perf_counter()
    t_diff = etime - stime
    freq = imm.frame_num / t_diff
    
    print(f"Data traversal completed: {t_diff:.2f}s / {freq:.2f}Hz")

    # Display sum scattering pattern
    plt.figure(figsize=(8, 6))
    plt.imshow(np.log10(sum_scattering.reshape(imm.det_size) + 1))
    plt.colorbar(label='log10(counts + 1)')
    plt.title(f'Sum Scattering Pattern\n{os.path.basename(file_name)}')
    plt.xlabel('Column')
    plt.ylabel('Row')
    plt.tight_layout()
    plt.show()
    
    return freq


def test02() -> None:
    """
    Example function demonstrating how to use the IMM reader.
    
    This function reads a specific IMM file and displays its
    sum scattering pattern along with performance statistics.
    
    Notes
    -----
    Update the file path to point to your own IMM file before running.
    """
    fname = "/Users/mqichu/Documents/xpcs_data/2025_0712_legacy_imm_files/E140_SiO2_111921_270nm_62v_Exp3_PostPreshear_Preshear100_XPCS_02_032_att02_Lq1_001/E140_SiO2_111921_270nm_62v_Exp3_PostPreshear_Preshear100_XPCS_02_032_att02_Lq1_001_00001-05000.imm"
    
    # Check if file exists
    if not os.path.exists(fname):
        logger.error("File not found: %s", fname)
        return
        
    read_data(fname)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test02()
