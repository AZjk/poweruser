# XPCS Power User Tools - Installation and Usage Guide

## Quick Installation

1. **Clone the repository** (if not already done):
   ```bash
   git clone https://github.com/AZjk/poweruser.git
   cd poweruser
   ```

2. **Install the package**:
   ```bash
   # For development (recommended - allows you to modify the code)
   pip install -e .
   
   # For regular installation
   pip install .
   ```

3. **Verify installation**:
   ```bash
   # Test the installation
   python test_installation.py
   
   # Check CLI availability
   xpcs-poweruser --version
   ```

## Quick Start

After installation, the `xpcs-poweruser` command will be available in your terminal.

### View available commands:
```bash
xpcs-poweruser --help
xpcs-poweruser list-utils
```

### Run the demo:
```bash
python quick_start_demo.py
```

## Common Use Cases

### 1. Convert Legacy Datasets
```bash
# Basic conversion
xpcs-poweruser convert-legacy /path/to/legacy/data /path/to/output

# With multiple workers for faster processing
xpcs-poweruser convert-legacy /path/to/legacy/data /path/to/output --workers 4

# Copy files instead of creating symbolic links
xpcs-poweruser convert-legacy /path/to/legacy/data /path/to/output --copy-data
```

### 2. Convert HDF5 to CSV
```bash
# Convert all HDF5 files in a directory
xpcs-poweruser nexus-to-csv -i /path/to/hdf5/files -o /path/to/csv/output

# Filter by filename
xpcs-poweruser nexus-to-csv -i /path/to/hdf5/files -o /path/to/csv/output --filter "sample_name"
```

### 3. G2 Analysis
```bash
# Standard G2 averaging
xpcs-poweruser g2-average /path/to/data.hdf -o /path/to/results/

# Fast G2 averaging
xpcs-poweruser fast-g2-average /path/to/data.hdf -o /path/to/results/
```

### 4. Run Custom Scripts
```bash
# Run any Python script from the utils directory
xpcs-poweruser run-script /path/to/script.py arg1 arg2
```

## Python API Usage

You can also use the functions directly in Python:

```python
# Import the functions
from xpcs_poweruser.utils import (
    Read_Frames_8IDI_Rigaku,
    Muititau_Corr,
    Read_Qmap_8IDI,
    SAXS,
    Multitau_Group_g2,
    Write_HDF_Result
)

# Example: Read detector data
detector_size = (512, 1024)  # Example size
img = Read_Frames_8IDI_Rigaku("path/to/data.bin", detector_size)

# Example: Perform correlation analysis
delays_per_level = 8
G2, IP, IF, t_el = Muititau_Corr(img, delays_per_level)
```

## Troubleshooting

### Command not found
If `xpcs-poweruser` command is not found:
1. Make sure the package is installed: `pip list | grep xpcs`
2. Check if pip's scripts directory is in your PATH
3. Try reinstalling: `pip uninstall xpcs-poweruser && pip install -e .`

### Import errors
If you get import errors:
1. Check Python version: `python --version` (requires >= 3.8)
2. Install missing dependencies: `pip install -r requirements.txt`
3. Reinstall in development mode: `pip install -e .`

### Permission errors
If you get permission errors when creating symbolic links:
- Use the `--copy-data` flag instead of symbolic links
- Make sure you have write permissions in the destination directory

## Development

### Install development dependencies:
```bash
pip install -e ".[dev]"
```

### Run tests:
```bash
pytest
```

### Format code:
```bash
black xpcs_poweruser/
```

## File Structure

```
poweruser/
├── xpcs_poweruser/          # Main package directory
│   ├── __init__.py
│   ├── cli.py              # CLI interface
│   └── utils/              # Utility modules
│       ├── xpcs_functions.py
│       ├── convert_legacy_datasets.py
│       ├── convert_nexus_to_csv.py
│       ├── G2_average/
│       └── fast_G2_average/
├── pyproject.toml          # Modern Python packaging config
├── setup.py               # Traditional packaging config
├── README_PACKAGE.md      # Detailed documentation
├── test_installation.py   # Installation test script
└── quick_start_demo.py    # Demo script
```

## Need Help?

- Check the detailed documentation: `README_PACKAGE.md`
- View command help: `xpcs-poweruser COMMAND --help`
- Report issues: https://github.com/AZjk/poweruser/issues
