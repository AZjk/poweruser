# API Reference

This section contains the API reference for all modules in the XPCS Power User Tools package.

## Modules

### Utils

- [`convert_legacy_datasets`](convert_legacy_datasets.md) - Functions for converting legacy XPCS datasets to NeXus format
- `convert_nexus_to_csv` - Functions for extracting data from HDF5/NeXus files to CSV format
- `xpcs_functions` - Core XPCS analysis functions

## Package Structure

```
poweruser_xpcs/
├── __init__.py
├── cli.py              # Command-line interface
└── utils/
    ├── __init__.py
    ├── convert_legacy_datasets.py
    ├── convert_nexus_to_csv.py
    ├── xpcs_functions.py
    └── sample_metadata.hdf
```

## Import Examples

```python
# Import the main processing function
from poweruser_xpcs.utils.convert_legacy_datasets import process_folder

# Import specific functions
from poweruser_xpcs.utils.convert_legacy_datasets import (
    copy_dataset_safe,
    process_subfolder,
    walk_subfolders
)

# Import HDF5 to CSV converter
from poweruser_xpcs.utils.convert_nexus_to_csv import hdf2csv

# Import XPCS analysis functions
from poweruser_xpcs.utils.xpcs_functions import (
    Read_Frames_8IDI_Rigaku,
    Muititau_Corr,
    Read_Qmap_8IDI,
    SAXS,
    Multitau_Group_g2,
    Write_HDF_Result
)
