# XPCS Power User Tools

A Python package providing command-line utilities for XPCS (X-ray Photon Correlation Spectroscopy) data analysis.

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/AZjk/poweruser.git
cd poweruser

# Install in development mode
pip install -e .

# Or install normally
pip install .
```

### Install with Development Dependencies

```bash
pip install -e ".[dev]"
```

## Usage

After installation, the `xpcs-poweruser` command will be available in your terminal.

### List Available Commands

```bash
xpcs-poweruser --help
xpcs-poweruser list-utils
```

### Main Commands

#### 1. Convert Legacy Datasets

Convert legacy XPCS datasets to the new NeXus format:

```bash
# Basic usage
xpcs-poweruser convert-legacy /path/to/source /path/to/dest

# With multiple workers for faster processing
xpcs-poweruser convert-legacy /path/to/source /path/to/dest --workers 4

# Copy data instead of creating symbolic links
xpcs-poweruser convert-legacy /path/to/source /path/to/dest --copy-data

# Process specific file types
xpcs-poweruser convert-legacy /path/to/source /path/to/dest --ftype .imm
```

#### 2. Convert NeXus/HDF5 to CSV

Extract G2, SAXS, and metadata from HDF5 files to CSV format:

```bash
# Basic usage
xpcs-poweruser nexus-to-csv -i /path/to/hdf5/files -o /path/to/output

# With filename filter
xpcs-poweruser nexus-to-csv -i /path/to/hdf5/files -o /path/to/output --filter "sample_A"
```

#### 3. G2 Averaging Analysis

Run G2 averaging analysis on HDF5 files:

```bash
# Standard G2 averaging
xpcs-poweruser g2-average data.hdf -o results/

# Fast G2 averaging (optimized algorithm)
xpcs-poweruser fast-g2-average data.hdf -o results/

# With custom configuration
xpcs-poweruser g2-average data.hdf -c custom_config.json
```

#### 4. Run Any Script

Run any Python script from the utils directory:

```bash
# Run a script with arguments
xpcs-poweruser run-script path/to/script.py arg1 arg2 arg3
```

## Package Structure

```
xpcs_poweruser/
├── __init__.py
├── cli.py                    # Main CLI interface
└── utils/
    ├── __init__.py
    ├── xpcs_functions.py     # Core XPCS analysis functions
    ├── convert_legacy_datasets.py
    ├── convert_nexus_to_csv.py
    ├── sample_metadata.hdf   # Template metadata file
    ├── G2_average/          # Standard G2 averaging tools
    └── fast_G2_average/     # Optimized G2 averaging tools
```

## Python API

You can also import and use the functions directly in Python:

```python
from xpcs_poweruser.utils import (
    Read_Frames_8IDI_Rigaku,
    Muititau_Corr,
    Read_Qmap_8IDI,
    SAXS,
    Multitau_Group_g2,
    Write_HDF_Result
)

# Example: Read frames from a Rigaku detector
img = Read_Frames_8IDI_Rigaku(filename, detector_size)

# Example: Perform multitau correlation
G2, IP, IF, t_el = Muititau_Corr(img, delays_per_level)
```

## Requirements

- Python >= 3.8
- numpy >= 1.20.0
- scipy >= 1.7.0
- h5py >= 3.0.0
- tqdm >= 4.60.0
- click >= 8.0.0

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black xpcs_poweruser/
```

### Type Checking

```bash
mypy xpcs_poweruser/
```

## License

MIT License - see the original repository for details.

## Contributing

Please submit issues and pull requests to the [GitHub repository](https://github.com/AZjk/poweruser).
