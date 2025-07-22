# Unit Tests for poweruser_xpcs Utilities

This directory contains comprehensive unit tests for the functions in the `src/poweruser_xpcs/utils` module.

## Test Coverage

The test suite covers the following modules:

### 1. `test_xpcs_functions.py`
Tests for XPCS data processing functions:
- `Read_Frames_8IDI_Rigaku` - Reading binary frame data from Rigaku detectors
- `Muititau_Corr` - Multi-tau correlation calculations
- `Read_Qmap_8IDI` - Reading Q-map data from HDF5 files
- `SAXS` - SAXS intensity calculations
- `Multitau_Group_g2` - Grouping g2 correlation data
- `Write_HDF_Result` - Writing results to HDF5 format

### 2. `test_convert_legacy_datasets.py`
Tests for legacy dataset conversion functions:
- `copy_dataset_safe` - Safe HDF5 dataset copying with scaling
- `process_subfolder` - Processing individual data folders
- `walk_subfolders` - Recursive directory traversal
- `worker_process_subfolder` - Parallel processing worker
- `process_folder` - Main folder processing logic
- Field mapping validation

### 3. `test_convert_nexus_to_csv.py`
Tests for NeXus to CSV conversion:
- `hdf2csv` - Converting HDF5/NeXus files to CSV format
- Main function behavior with filters
- Error handling and edge cases

## Running the Tests

### Prerequisites
Make sure you have the required dependencies installed:
```bash
pip install numpy scipy h5py tqdm
```

### Run All Tests
To run all tests in the suite:

```bash
# From the project root directory
python -m unittest discover tests

# Or using the test runner script
python tests/run_tests.py
```

### Run Specific Test Module
To run tests from a specific module:

```bash
# Run only xpcs_functions tests
python tests/run_tests.py xpcs_functions

# Run only convert_legacy_datasets tests
python tests/run_tests.py convert_legacy_datasets

# Run only convert_nexus_to_csv tests
python tests/run_tests.py convert_nexus_to_csv
```

### Run with unittest directly
You can also run individual test files:

```bash
# From the project root
python -m unittest tests.test_xpcs_functions
python -m unittest tests.test_convert_legacy_datasets
python -m unittest tests.test_convert_nexus_to_csv

# Or run specific test classes
python -m unittest tests.test_xpcs_functions.TestReadFrames8IDIRigaku
python -m unittest tests.test_xpcs_functions.TestMultitauCorr
```

### Run specific test methods
To run a single test method:

```bash
python -m unittest tests.test_xpcs_functions.TestReadFrames8IDIRigaku.test_read_frames_basic
```

## Test Structure

Each test module follows the standard unittest pattern:
- `setUp()` - Creates temporary files and test fixtures
- `tearDown()` - Cleans up temporary files
- `test_*` methods - Individual test cases

The tests use:
- Mock objects to simulate external dependencies
- Temporary directories for file operations
- Numpy arrays for numerical data testing
- Assertions to verify expected behavior

## Adding New Tests

When adding new functionality to the utils module:
1. Create corresponding test methods in the appropriate test file
2. Use descriptive test method names (e.g., `test_function_with_edge_case`)
3. Include docstrings explaining what each test verifies
4. Clean up any created resources in `tearDown()`
5. Use mocks to avoid dependencies on external resources

## Continuous Integration

These tests can be integrated into CI/CD pipelines by running:
```bash
python tests/run_tests.py
```

The script returns exit code 0 on success, 1 on failure.
