# convert_legacy_datasets API Reference

::: poweruser_xpcs.utils.convert_legacy_datasets

## Module Overview

This module provides functions for converting legacy XPCS datasets to the new NeXus format.

## Functions

### process_folder

::: poweruser_xpcs.utils.convert_legacy_datasets.process_folder

### process_subfolder

::: poweruser_xpcs.utils.convert_legacy_datasets.process_subfolder

### copy_dataset_safe

::: poweruser_xpcs.utils.convert_legacy_datasets.copy_dataset_safe

### walk_subfolders

::: poweruser_xpcs.utils.convert_legacy_datasets.walk_subfolders

### worker_process_subfolder

::: poweruser_xpcs.utils.convert_legacy_datasets.worker_process_subfolder

## Constants

### FIELD_MAPPING

Dictionary mapping legacy HDF5 paths to NeXus paths with optional scaling factors.

```python
FIELD_MAPPING = {
    "/measurement/instrument/detector/exposure_period": (
        "/entry/instrument/detector_1/frame_time",
        1.0,
    ),
    "/measurement/instrument/detector/distance": (
        "/entry/instrument/detector_1/distance",
        0.001,  # mm to m
    ),
    # ... more mappings
}
```

### MAX_DEPTH

Maximum recursion depth for directory traversal.

```python
MAX_DEPTH = 5
```

### META_TEMPLATE

Path to the metadata template file.

```python
META_TEMPLATE = SCRIPT_DIR / "sample_metadata.hdf"
```

## Usage Example

```python
from poweruser_xpcs.utils.convert_legacy_datasets import process_folder

# Basic usage
process_folder(
    source_folder="/data/legacy",
    dest_folder="/data/converted"
)

# With parallel processing
process_folder(
    source_folder="/data/legacy",
    dest_folder="/data/converted",
    max_workers=8,
    ftype=".imm",
    copy_data=True
)
