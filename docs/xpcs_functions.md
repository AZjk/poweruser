# xpcs_functions

Core XPCS analysis functions module.

## Overview

This module provides essential functions for XPCS (X-ray Photon Correlation Spectroscopy) data analysis, including:
- Reading raw data frames from various detectors
- Performing multi-tau correlation analysis
- Reading Q-maps for data reduction
- SAXS analysis
- Writing results to HDF5 format

## Functions

::: poweruser_xpcs.utils.xpcs_functions
    options:
      show_source: true
      show_root_heading: true
      members:
        - Read_Frames_8IDI_Rigaku
        - Muititau_Corr
        - Read_Qmap_8IDI
        - SAXS
        - Multitau_Group_g2
        - Write_HDF_Result

## Usage Examples

### Reading Frames

```python
from poweruser_xpcs.utils.xpcs_functions import Read_Frames_8IDI_Rigaku

# Read frames from Rigaku detector
frames = Read_Frames_8IDI_Rigaku("path/to/data.bin", det_size=(1024, 1024))
```

### Multi-tau Correlation

```python
from poweruser_xpcs.utils.xpcs_functions import Muititau_Corr

# Perform multi-tau correlation
g2_result = Muititau_Corr(image_stack, delay_per_level)
```

### SAXS Analysis

```python
from poweruser_xpcs.utils.xpcs_functions import SAXS

# Perform SAXS analysis
saxs_result = SAXS(image, mask, q_list_static, qmap_static, det_size)
```

## Notes

- These functions are optimized for XPCS data from APS beamline 8-ID-I
- The functions handle various detector formats including Rigaku detectors
- Results are typically saved in HDF5 format for efficient storage and retrieval
