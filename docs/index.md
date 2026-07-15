# XPCS Power User Tools Documentation

```{toctree}
:hidden:
:maxdepth: 1

cli_user_guide
```

Welcome to the documentation for XPCS Power User Tools, a collection of utilities for XPCS (X-ray Photon Correlation Spectroscopy) data analysis.

## Overview

This package provides tools for:
- Converting legacy XPCS datasets to the new NeXus format
- Converting HDF5/NeXus files to CSV format
- Processing and analyzing XPCS data
- G2 averaging analysis

## Installation

```bash
pip install poweruser-xpcs
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### Convert Legacy Datasets

```bash
xpcs-poweruser convert-legacy /path/to/source /path/to/dest
```

### Convert HDF5 to CSV

```bash
xpcs-poweruser nexus-to-csv -i /path/to/hdf5 -o /path/to/csv
```

## Modules

- [convert_legacy_datasets](convert_legacy_datasets.md) - Convert legacy XPCS data to NeXus format
- [convert_nexus_to_csv](convert_nexus_to_csv.md) - Extract data from HDF5 files to CSV
- [xpcs_functions](xpcs_functions.md) - Core XPCS analysis functions

## Command Line Interface

The package provides a unified CLI through the `xpcs-poweruser` command. Use `xpcs-poweruser --help` to see all available commands.
