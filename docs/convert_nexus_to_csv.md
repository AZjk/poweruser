# convert_nexus_to_csv

Module for converting HDF5/NeXus files to CSV format.

## Overview

This module provides functionality to extract data from HDF5 files and save them in CSV format for easier analysis in spreadsheet applications or other data analysis tools.

## Functions

::: poweruser_xpcs.utils.convert_nexus_to_csv
    options:
      show_source: true
      show_root_heading: true
      members:
        - hdf2csv

## Usage Example

```python
from poweruser_xpcs.utils.convert_nexus_to_csv import hdf2csv

# Convert an HDF5 file to CSV
hdf2csv("path/to/input.h5", "path/to/output/")
```

## Command Line Usage

```bash
xpcs-poweruser nexus-to-csv -i /path/to/input.h5 -o /path/to/output/
```

## Notes

- The function extracts specific datasets from the HDF5 file structure
- Output CSV files are named based on the dataset names in the HDF5 file
- The function handles common XPCS data structures automatically
