"""XPCS Dataset Handler Module.

This module provides a base class for handling X-ray Photon Correlation Spectroscopy (XPCS)
datasets. It supports various data formats through subclassing and provides functionality
for frame selection, averaging, batching, and format conversion.

The XpcsDataset class is designed to be extended by format-specific implementations
that handle the actual file reading logic through the __getbatch__ method.

Example:
    Basic usage with a concrete implementation::
    
        dataset = ConcreteXpcsDataset(
            fname="data.bin",
            begin_frame=100,
            end_frame=1000,
            stride_frame=2,
            avg_frame=4,
            batch_size=64
        )
        
        # Process batches
        for i in range(len(dataset)):
            batch = dataset[i]
            # Process batch...
"""

import numpy as np
import logging
import os
from typing import Optional, Tuple, Union, Dict, Any

logger = logging.getLogger(__name__)


class XpcsDataset(object):
    """Base class for handling XPCS (X-ray Photon Correlation Spectroscopy) datasets.
    
    This class provides a framework for reading and processing raw XPCS data files,
    with support for frame selection, averaging, batching, and sparse-to-dense conversion.
    
    Attributes:
        fname (str): Path to the raw data file
        raw_size (float): Size of the raw file in MB
        det_size (tuple): Detector dimensions as (height, width)
        pixel_num (int): Total number of pixels (height * width)
        is_sparse (bool): Whether the data is stored in sparse format
        mask_crop (Optional[np.ndarray]): Mask for cropping detector area
        batch_size (int): Number of frames to process in each batch
        batch_num (int): Total number of batches
        frame_num (int): Effective number of frames after stride and averaging
        frame_num_raw (int): Total number of raw frames in the dataset
        begin_frame (int): Starting frame index
        end_frame (int): Ending frame index (inclusive)
        avg_frame (int): Number of frames to average together
        stride (int): Frame stride for subsampling
        use_loader (bool): Whether to use a data loader
        dtype (np.dtype): Data type for processed frames
        dataset_type (Optional[str]): Type of dataset (set by subclasses)
        dtype_raw (Optional[np.dtype]): Raw data type from file
    """

    def __init__(
        self,
        fname: str,
        begin_frame: int = 0,
        end_frame: int = -1,
        stride_frame: int = 1,
        avg_frame: int = 1,
        batch_size: int = 128,
        det_size: Tuple[int, int] = (512, 1024),
        use_loader: bool = False,
        dtype: np.dtype = np.uint8,
        mask_crop: Optional[np.ndarray] = None,
    ):
        """Initialize an XPCS dataset.
        
        Args:
            fname: Path to the raw data file
            begin_frame: First frame to process (0-indexed)
            end_frame: Last frame to process (-1 for all frames)
            stride_frame: Frame stride for subsampling (process every nth frame)
            avg_frame: Number of consecutive frames to average together
            batch_size: Number of frames to load and process at once
            det_size: Detector dimensions as (height, width)
            use_loader: Whether to use a data loader (implementation-specific)
            dtype: NumPy data type for processed frames
            mask_crop: Optional mask array for cropping detector area
        """
        self.fname = fname
        self.raw_size = os.path.getsize(fname) / (1024**2)  # Size in MB
        self.det_size = det_size
        self.pixel_num = self.det_size[0] * self.det_size[1]
        self.is_sparse = True

        self.mask_crop = mask_crop
        self.batch_size = batch_size
        self.batch_num = 0
        self.frame_num = 0
        self.frame_num_raw = 0
        self.begin_frame = begin_frame
        self.end_frame = end_frame
        self.avg_frame = avg_frame
        self.stride = stride_frame

        self.use_loader = use_loader
        self.dtype = dtype
        self.dataset_type = None
        self.dtype_raw = None

    def update_batch_info(self, frame_num: int) -> None:
        """Update batch processing information based on total frame count.
        
        This method calculates the effective number of frames and batches
        based on the stride and averaging parameters. It ensures that the
        end frame aligns with complete averaging groups.
        
        Args:
            frame_num: Total number of raw frames in the dataset
        """
        self.frame_num_raw = frame_num
        
        # If end_frame not specified, use all frames
        if self.end_frame <= 0:
            self.end_frame = frame_num

        # Calculate total frames to process
        total_frames = self.end_frame - self.begin_frame
        
        # Calculate effective length of one averaged unit
        effective_unit_length = self.avg_frame * self.stride
        
        # Round down to nearest complete unit
        total_frames = (total_frames // effective_unit_length) * effective_unit_length
        end_frame = self.begin_frame + total_frames
        
        if self.end_frame != end_frame:
            logger.info("end_frame is rounded to the nearest complete averaging unit")
            self.end_frame = end_frame

        # Calculate effective frame count and batch count
        self.frame_num = total_frames // effective_unit_length
        self.batch_num = (self.frame_num + self.batch_size - 1) // self.batch_size

    def update_mask_crop(self, new_mask: np.ndarray) -> None:
        """Update the cropping mask.
        
        This method is useful when the q-map orientation differs from the dataset
        orientation. After rotating the q-map, this method applies the new mask.
        If no original mask exists (no cropping), the method does nothing.
        
        Args:
            new_mask: New mask array to apply for cropping
        """
        if self.mask_crop is None:
            return
        else:
            self.mask_crop = new_mask

    def update_det_size(self, det_size: Tuple[int, int]) -> None:
        """Update detector dimensions.
        
        Args:
            det_size: New detector dimensions as (height, width)
        """
        self.det_size = det_size
        self.pixel_num = self.det_size[0] * self.det_size[1]

    def get_raw_index(self, idx: int) -> Tuple[int, int, int]:
        """Get raw frame indices for a given batch.
        
        Calculates the beginning and ending raw frame indices for a specific
        batch, taking into account stride and averaging parameters.
        
        Args:
            idx: Batch index
            
        Returns:
            Tuple containing:
                - beg: Starting raw frame index
                - end: Ending raw frame index (exclusive)
                - size: Number of frames in this batch after striding
        """
        effective_batch_length = self.stride * self.avg_frame * self.batch_size
        beg = self.begin_frame + effective_batch_length * idx
        end = min(self.end_frame, beg + effective_batch_length)
        size = (end - beg) // self.stride
        return beg, end, size

    def get_sparsity(self) -> float:
        """Calculate the sparsity of the dataset.
        
        Sparsity is defined as the fraction of non-zero pixels in a frame.
        This method reads the first frame to estimate the sparsity.
        
        Returns:
            Sparsity value between 0 and 1
        """
        # Get first frame
        first_batch = self.__getitem__(0)
        first_frame = first_batch[0] if len(first_batch.shape) > 1 else first_batch
        
        # Calculate fraction of non-zero pixels
        sparsity = (first_frame > 0).sum() / self.pixel_num
        
        # Store raw data type
        self.dtype_raw = first_frame.dtype
        
        # Reset dataset state
        self.__reset__()
        
        return sparsity

    def get_description(self) -> Dict[str, Any]:
        """Get a dictionary describing the dataset configuration.
        
        Returns:
            Dictionary containing key dataset parameters and settings
        """
        result = {}
        
        # Copy key attributes
        for key in [
            "fname",
            "frame_num_raw",
            "is_sparse",
            "frame_num",
            "det_size",
            "batch_size",
            "batch_num",
            "dataset_type",
        ]:
            result[key] = self.__dict__[key]
        
        # Add formatted frame processing info
        result["frame_info"] = (
            f"(begin, end, stride, avg) = "
            f"({self.begin_frame}, {self.end_frame}, "
            f"{self.stride}, {self.avg_frame})"
        )
        
        return result

    def describe(self) -> None:
        """Log a detailed description of the dataset.
        
        This method logs various dataset properties including dimensions,
        frame information, data types, sparsity, and file size.
        """
        # Log basic dataset info
        for key, val in self.get_description().items():
            logger.info(f"{key}: {val}")

        # Calculate valid pixel count
        if self.mask_crop is not None:
            valid_size = self.mask_crop.shape[0]
        else:
            valid_size = self.pixel_num
            
        # Log additional details
        logger.info(f"dtype: {self.dtype}")
        logger.info(f"valid_size: {valid_size}")
        logger.info(f"sparsity: {self.get_sparsity():.4f}")
        logger.info(f"raw dataset file size: {self.raw_size:.2f} MB")

    def __len__(self) -> int:
        """Return the number of batches in the dataset.
        
        Returns:
            Number of batches
        """
        return self.batch_num

    def __reset__(self) -> None:
        """Reset the dataset state.
        
        This method should be overridden by subclasses if they maintain
        internal state that needs resetting (e.g., file pointers).
        """
        return

    def __getbatch__(self, idx: int) -> np.ndarray:
        """Get a batch of raw frames.
        
        This method must be implemented by subclasses to handle the specific
        file format and data loading logic.
        
        Args:
            idx: Batch index
            
        Returns:
            Array of shape (batch_size * avg_frame, pixel_num) containing raw frames
            
        Raises:
            NotImplementedError: This method must be implemented by subclasses
        """
        raise NotImplementedError

    def __getitem__(self, idx: int) -> np.ndarray:
        """Get a batch of processed frames.
        
        This method retrieves raw frames using __getbatch__ and applies
        frame averaging if specified.
        
        Args:
            idx: Batch index
            
        Returns:
            Array of shape (batch_size, pixel_num) containing processed frames
        """
        # Get raw batch
        x = self.__getbatch__(idx)
        
        # Apply frame averaging if needed
        if self.avg_frame > 1:
            # Reshape to separate frames to be averaged
            x = x.reshape(-1, self.avg_frame, x.shape[-1])
            # Average along the frame dimension
            x = np.mean(x, axis=1)
            
        return x

    def to_rigaku_bin(self, fname: str) -> None:
        """Convert dataset to Rigaku binary format.
        
        The Rigaku format encodes sparse data as 64-bit integers where:
        - Bits 40-63: Frame number (24 bits)
        - Bits 16-39: Pixel index (24 bits)
        - Bits 0-15: Photon count (16 bits)
        
        Args:
            fname: Output filename for the Rigaku binary file
        """
        offset = 0
        
        with open(fname, "ab") as fid:
            for batch_idx in range(self.batch_num):
                # Get batch of frames
                batch_data = self.__getitem__(batch_idx)
                
                # Find non-zero pixels
                nonzero_indices = np.nonzero(batch_data)
                photon_counts = batch_data[nonzero_indices]
                
                # Extract frame and pixel indices
                frame_indices = nonzero_indices[0] + offset
                pixel_indices = nonzero_indices[1].astype(np.int64)
                
                # Update offset for next batch
                offset += batch_data.shape[0]

                # Encode data in Rigaku format
                encoded_data = np.zeros_like(photon_counts, dtype=np.int64)
                encoded_data += frame_indices.astype(np.int64) << 40  # Frame number
                encoded_data += pixel_indices << 16                    # Pixel index
                encoded_data += photon_counts                          # Photon count
                
                # Write to file
                encoded_data.tofile(fid, sep="")

    def sparse_to_dense(
        self, 
        index: Union[np.ndarray, list], 
        frame: Union[np.ndarray, list], 
        count: Union[np.ndarray, list], 
        size: int
    ) -> np.ndarray:
        """Convert sparse representation to dense array.
        
        This method reconstructs a dense frame array from sparse data
        consisting of pixel indices, frame indices, and photon counts.
        
        Args:
            index: Pixel indices where photons were detected
            frame: Frame indices corresponding to each detection
            count: Photon counts at each (frame, pixel) location
            size: Number of frames in the output array
            
        Returns:
            Dense array of shape (size, pixel_num) with photon counts
        """
        if isinstance(index, np.ndarray):
            # Initialize dense array
            dense_array = np.zeros((size, self.pixel_num), dtype=self.dtype)
            
            # Fill in photon counts at specified locations
            dense_array[frame, index] = count
            
            return dense_array
        else:
            raise TypeError("Index must be a numpy array")
