# convert_legacy_datasets Module

## Overview

The `convert_legacy_datasets` module provides functionality to convert legacy XPCS datasets to the new NeXus format. It processes directory structures containing paired data files and metadata files, creating a new organized structure with converted metadata.

## Features

- Recursive directory traversal with configurable depth
- Parallel processing support for large datasets
- Flexible file type support (.bin, .imm, .h5)
- Choice between symbolic links and file copying
- Automatic unit conversions and field mapping
- Error handling with automatic cleanup

## Usage

### Command Line

```bash
# Basic usage with symbolic links (default)
python -m poweruser_xpcs.utils.convert_legacy_datasets /source/folder /dest/folder

# Copy data files instead of creating symbolic links
python -m poweruser_xpcs.utils.convert_legacy_datasets /source/folder /dest/folder --copy-data

# Process with multiple workers
python -m poweruser_xpcs.utils.convert_legacy_datasets /source/folder /dest/folder --workers 4

# Process specific file types
python -m poweruser_xpcs.utils.convert_legacy_datasets /source/folder /dest/folder --ftype .imm

# Combined options
python -m poweruser_xpcs.utils.convert_legacy_datasets /source/folder /dest/folder --copy-data --workers 8 --ftype .h5
```

### Python API

```python
from poweruser_xpcs.utils.convert_legacy_datasets import process_folder

# Basic conversion
process_folder(
    source_folder="/path/to/source",
    dest_folder="/path/to/dest"
)

# With options
process_folder(
    source_folder="/path/to/source",
    dest_folder="/path/to/dest",
    max_workers=4,
    ftype=".imm",
    copy_data=True
)
```

## Functions

### process_folder

Main entry point for processing a folder structure.

```python
def process_folder(source_folder, dest_folder, max_workers=None, ftype=".bin", copy_data=False):
    """
    Process the folder structure and copy files.
    
    Parameters
    ----------
    source_folder : str or Path
        The source folder path containing legacy datasets
    dest_folder : str or Path
        The destination folder path for converted datasets
    max_workers : int, optional
        Maximum number of worker processes. If None, use single process
    ftype : str, default=".bin"
        File type/extension of raw data files (".bin", ".imm", ".h5")
    copy_data : bool, default=False
        If True, copy data files instead of creating symbolic links
    """
```

### process_subfolder

Process a single subfolder containing a data/metadata pair.

```python
def process_subfolder(subfolder_path, source_folder, dest_folder, ftype, copy_data=False):
    """
    Process a single subfolder to convert legacy datasets.
    
    Parameters
    ----------
    subfolder_path : Path
        Path to the subfolder to process
    source_folder : Path
        Path to the source folder
    dest_folder : Path
        Path to the destination folder
    ftype : str
        File type/extension of raw data files
    copy_data : bool, default=False
        If True, copy data files instead of creating symbolic links
    """
```

### copy_dataset_safe

Safely copy HDF5 datasets with optional scaling.

```python
def copy_dataset_safe(src_group, dst_group, src_path, dst_path, scale=None):
    """
    Safely copy a dataset from src_group to dst_group, handling potential exceptions.
    
    Parameters
    ----------
    src_group : h5py.Group
        The source HDF5 group
    dst_group : h5py.Group
        The destination HDF5 group
    src_path : str
        The path to the dataset in the source group
    dst_path : str
        The path to the dataset in the destination group
    scale : float, optional
        Scaling factor to apply to the data
    """
```

### walk_subfolders

Recursively walk through subfolders up to a specified depth.

```python
def walk_subfolders(base_path, max_depth, current_depth=0):
    """
    Recursively walk through subfolders up to a specified depth.
    
    Parameters
    ----------
    base_path : Path
        The starting directory
    max_depth : int
        The maximum depth to recurse
    current_depth : int, default=0
        The current depth of recursion
        
    Yields
    ------
    Path
        Directory paths found during traversal
    """
```

## Field Mapping

The module uses a predefined field mapping to convert metadata from the legacy format to the NeXus format. Each mapping includes:
- Source path in the legacy HDF5 file
- Destination path in the NeXus format
- Optional scaling factor for unit conversion

### Key Conversions

| Legacy Field | NeXus Field | Scaling | Description |
|-------------|-------------|---------|-------------|
| `/measurement/instrument/detector/exposure_period` | `/entry/instrument/detector_1/frame_time` | 1.0 | Frame exposure time |
| `/measurement/instrument/detector/distance` | `/entry/instrument/detector_1/distance` | 0.001 | Detector distance (mm to m) |
| `/measurement/instrument/detector/x_pixel_size` | `/entry/instrument/detector_1/x_pixel_size` | 0.001 | Pixel size (mm to m) |
| `/measurement/sample/thickness` | `/entry/sample/thickness` | 0.001 | Sample thickness (mm to m) |

## Requirements

### Directory Structure

Each subfolder to be processed must contain:
- Exactly one data file of the specified type (.bin, .imm, or .h5)
- Exactly one metadata file (.hdf)

Example structure:
```
source_folder/
├── experiment_001/
│   ├── data.bin
│   └── metadata.hdf
├── experiment_002/
│   ├── data.bin
│   └── metadata.hdf
└── experiment_003/
    ├── data.bin
    └── metadata.hdf
```

### Metadata Template

The module requires a `sample_metadata.hdf` template file in the same directory as the script. This template provides the base structure for the converted metadata files.

## Error Handling

- Invalid subfolders (wrong file count) are skipped with a warning message
- Processing errors are caught and logged, with automatic cleanup of incomplete conversions
- The script continues processing other subfolders even if some fail

## Performance Considerations

- **Symbolic Links**: Default behavior creates symbolic links to save disk space
- **Parallel Processing**: Use `--workers` to process multiple subfolders simultaneously
- **Large Datasets**: The module handles large datasets efficiently using HDF5's chunked I/O

## Examples

### Example 1: Basic Conversion

```python
from poweruser_xpcs.utils.convert_legacy_datasets import process_folder

# Convert all .bin files in the source directory
process_folder(
    source_folder="/data/legacy_xpcs",
    dest_folder="/data/nexus_xpcs"
)
```

### Example 2: Parallel Processing with Copy

```python
from poweruser_xpcs.utils.convert_legacy_datasets import process_folder

# Use 8 workers to copy .imm files
process_folder(
    source_folder="/data/legacy_xpcs",
    dest_folder="/backup/nexus_xpcs",
    max_workers=8,
    ftype=".imm",
    copy_data=True  # Create copies instead of links
)
```

### Example 3: Custom Processing

```python
from poweruser_xpcs.utils.convert_legacy_datasets import (
    walk_subfolders, process_subfolder
)
from pathlib import Path

source = Path("/data/legacy")
dest = Path("/data/converted")

# Process only specific subfolders
for subfolder in walk_subfolders(source, max_depth=2):
    if "important" in subfolder.name:
        process_subfolder(subfolder, source, dest, ".bin", copy_data=False)
```

## Troubleshooting

### Common Issues

1. **"Metadata template not found"**
   - Ensure `sample_metadata.hdf` exists in the utils directory
   - Check file permissions

2. **"Skipping subfolder: requires 1 .bin and 1 .hdf file"**
   - Verify each subfolder has exactly one data file and one metadata file
   - Check file extensions match the specified `--ftype`

3. **Symbolic link errors**
   - Ensure source and destination are on the same filesystem
   - Use `--copy-data` if symbolic links aren't supported

4. **Memory issues with large files**
   - Reduce the number of workers
   - Process in smaller batches

### Debug Mode

For detailed debugging, modify the script to add verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
