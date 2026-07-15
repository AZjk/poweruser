========================================
XPCS Power User CLI - User Guide
========================================

.. contents:: Table of Contents
   :depth: 3
   :local:

Introduction
============

The XPCS Power User Tools provides a comprehensive command-line interface (CLI) for analyzing and processing X-ray Photon Correlation Spectroscopy (XPCS) data. This guide covers all available commands, their options, and practical usage examples.

Installation
============

The CLI is installed as part of the ``poweruser_xpcs`` package. After installation, the ``xpcs-poweruser`` command becomes available in your terminal.

.. code-block:: bash

   pip install poweruser_xpcs

Verify the installation:

.. code-block:: bash

   xpcs-poweruser --version

Getting Help
============

Display general help information:

.. code-block:: bash

   xpcs-poweruser --help

Get help for a specific command:

.. code-block:: bash

   xpcs-poweruser COMMAND --help

For example:

.. code-block:: bash

   xpcs-poweruser convert-legacy --help

Available Commands
==================

The CLI provides the following commands:

- ``convert-legacy`` - Convert legacy XPCS datasets to NeXus format
- ``nexus-to-csv`` - Convert HDF5/NeXus files to CSV format
- ``export-nexus`` - Extract intensity, g2, q-values, and time-delays into a compact NeXus file
- ``g2-average`` - Run G2 averaging analysis
- ``fast-g2-average`` - Run fast G2 averaging analysis
- ``link-files`` - Create symbolic links from multiple sources
- ``run-script`` - Run Python scripts from the utils directory
- ``list-utils`` - List all available utility scripts

Command Reference
=================

convert-legacy
--------------

Convert legacy XPCS datasets to the new NeXus format. This command processes legacy XPCS data by searching for subfolders containing paired data files and metadata files, then converts them to the new format.

**Syntax:**

.. code-block:: bash

   xpcs-poweruser convert-legacy SOURCE_FOLDER DEST_FOLDER [OPTIONS]

**Required Arguments:**

- ``SOURCE_FOLDER`` - Source folder containing legacy datasets
- ``DEST_FOLDER`` - Destination folder for converted datasets

**Options:**

- ``--workers N`` - Number of parallel worker processes (default: 1)
- ``--ftype {.bin,.imm,.h5}`` - File type/extension of raw data files (default: .bin)
- ``--copy-data`` - Copy data files instead of creating symbolic links

**Examples:**

Basic conversion with default settings:

.. code-block:: bash

   xpcs-poweruser convert-legacy /data/legacy /data/converted

Convert using 4 parallel workers:

.. code-block:: bash

   xpcs-poweruser convert-legacy /data/legacy /data/converted --workers 4

Convert IMM files and copy data instead of linking:

.. code-block:: bash

   xpcs-poweruser convert-legacy /data/legacy /data/converted --ftype .imm --copy-data

**Notes:**

- By default, the command creates symbolic links to preserve disk space
- Use ``--copy-data`` if you need independent copies of the data files
- The ``--workers`` option can significantly speed up processing of large datasets

nexus-to-csv
------------

Convert HDF5/NeXus files to CSV format. This command extracts G2, SAXS, and metadata information from HDF5 files and saves them as separate CSV files.

**Syntax:**

.. code-block:: bash

   xpcs-poweruser nexus-to-csv -i INPUT_DIR -o OUTPUT_DIR [OPTIONS]

**Required Arguments:**

- ``-i, --input INPUT_DIR`` - Path to the folder with HDF5 files
- ``-o, --output OUTPUT_DIR`` - Path to save CSV files

**Options:**

- ``-f, --filter SUBSTRING`` - Optional substring filter for filenames

**Examples:**

Convert all HDF5 files in a directory:

.. code-block:: bash

   xpcs-poweruser nexus-to-csv -i /data/hdf5_files -o /data/csv_output

Convert only files containing "sample1" in the filename:

.. code-block:: bash

   xpcs-poweruser nexus-to-csv -i /data/hdf5_files -o /data/csv_output -f sample1

**Output:**

The command creates separate CSV files for:

- G2 correlation functions
- SAXS data
- Metadata information

export-nexus
------------

Extract intensity, g2, q-values, and time-delays from a processed HDF5/NeXus file into a new, smaller NeXus file, along with a metadata export (JSON/TXT/XLSX).

**Syntax:**

.. code-block:: bash

   xpcs-poweruser export-nexus HDF_FILE [OPTIONS]

**Required Arguments:**

- ``HDF_FILE`` - Processed HDF5/NeXus file to extract data from

**Options:**

- ``-o, --output FILE`` - Path to the output NeXus file (default: ``<input_basename>_export.nxs``)

**Examples:**

Extract data with the default output filename:

.. code-block:: bash

   xpcs-poweruser export-nexus /data/experiment_001.hdf5

Specify a custom output path:

.. code-block:: bash

   xpcs-poweruser export-nexus /data/experiment_001.hdf5 -o /data/results/experiment_001_export.nxs

**Output:**

The command creates:

- A NeXus file containing ``intensity``, ``g2``, ``q_values``, and ``time_delays`` datasets
- Metadata files (``<output_basename>_metadata.json``, ``.txt``, and ``.xlsx``) containing fields such as start time and detector frame time

g2-average
----------

Run G2 averaging analysis on HDF5 files. This command processes HDF5 files to compute G2 averages using the configuration specified in a JSON file.

**Syntax:**

.. code-block:: bash

   xpcs-poweruser g2-average HDF_FILE [OPTIONS]

**Required Arguments:**

- ``HDF_FILE`` - HDF5 file to process

**Options:**

- ``-o, --output DIR`` - Output directory for G2 average results
- ``-c, --config FILE`` - Path to G2average_info.json config file

**Examples:**

Process a file with default configuration:

.. code-block:: bash

   xpcs-poweruser g2-average /data/experiment_001.hdf5

Specify custom output directory and config:

.. code-block:: bash

   xpcs-poweruser g2-average /data/experiment_001.hdf5 \
       -o /data/results \
       -c /path/to/custom_config.json

**Configuration:**

If no config file is specified, the default configuration is used from:
``poweruser_xpcs/utils/G2_average/reaverage_info.json``

fast-g2-average
---------------

Run fast G2 averaging analysis on HDF5 files. This command uses an optimized algorithm for faster processing compared to the standard g2-average command.

**Syntax:**

.. code-block:: bash

   xpcs-poweruser fast-g2-average HDF_FILE [OPTIONS]

**Required Arguments:**

- ``HDF_FILE`` - HDF5 file to process

**Options:**

- ``-o, --output DIR`` - Output directory for fast G2 average results
- ``-c, --config FILE`` - Path to G2average_info.json config file

**Examples:**

Process a file with the fast algorithm:

.. code-block:: bash

   xpcs-poweruser fast-g2-average /data/experiment_001.hdf5

With custom configuration:

.. code-block:: bash

   xpcs-poweruser fast-g2-average /data/experiment_001.hdf5 \
       -o /data/results \
       -c /path/to/custom_config.json

**When to Use:**

- Use ``fast-g2-average`` for large datasets where processing speed is critical
- Use ``g2-average`` for standard processing or when compatibility is needed

link-files
----------

Create symbolic links for files from multiple source directories to a single destination. This is useful for gathering files from different locations into one place without copying data.

**Syntax:**

.. code-block:: bash

   xpcs-poweruser link-files -s SOURCE [SOURCE ...] -d DESTINATION [OPTIONS]

**Required Arguments:**

- ``-s, --source SOURCE [SOURCE ...]`` - One or more source directories
- ``-d, --destination DESTINATION`` - Destination directory for symbolic links

**Options:**

- ``-r, --repeat-time N`` - Repeat linking every N seconds (continuous mode)

**Examples:**

Link files from a single source:

.. code-block:: bash

   xpcs-poweruser link-files -s /data/source1 -d /data/gathered

Link files from multiple sources:

.. code-block:: bash

   xpcs-poweruser link-files \
       -s /data/source1 /data/source2 /data/source3 \
       -d /data/gathered

Continuous monitoring mode (repeat every 60 seconds):

.. code-block:: bash

   xpcs-poweruser link-files \
       -s /data/source1 /data/source2 \
       -d /data/gathered \
       -r 60

**Notes:**

- In repeat mode, press Ctrl+C to stop the continuous monitoring
- Symbolic links preserve disk space while making files accessible from a central location
- Useful for real-time data collection scenarios

run-script
----------

Run a Python script from the utils directory or any custom Python script with arguments.

**Syntax:**

.. code-block:: bash

   xpcs-poweruser run-script SCRIPT_PATH [ARGS ...]

**Required Arguments:**

- ``SCRIPT_PATH`` - Path to the Python script
- ``ARGS`` - Arguments to pass to the script (optional)

**Examples:**

Run a script without arguments:

.. code-block:: bash

   xpcs-poweruser run-script /path/to/script.py

Run a script with arguments:

.. code-block:: bash

   xpcs-poweruser run-script /path/to/script.py --input data.hdf5 --output results/

Run a utility script from the package:

.. code-block:: bash

   xpcs-poweruser run-script \
       ~/.local/lib/python3.x/site-packages/poweruser_xpcs/utils/custom_script.py \
       arg1 arg2

list-utils
----------

List all available utility scripts and their descriptions. This command helps you discover what tools are available in the package.

**Syntax:**

.. code-block:: bash

   xpcs-poweruser list-utils

**Example:**

.. code-block:: bash

   xpcs-poweruser list-utils

**Output:**

The command displays:

- Main CLI commands
- Python scripts in the utils/ directory
- Subdirectories and their contents

Common Workflows
================

Workflow 1: Converting Legacy Data
-----------------------------------

Convert legacy XPCS datasets to the new format and then extract CSV data for analysis:

.. code-block:: bash

   # Step 1: Convert legacy datasets
   xpcs-poweruser convert-legacy /data/legacy /data/nexus --workers 4

   # Step 2: Extract data to CSV for external analysis
   xpcs-poweruser nexus-to-csv -i /data/nexus -o /data/csv

Workflow 2: Processing New Data
--------------------------------

Process newly acquired HDF5 files with G2 averaging:

.. code-block:: bash

   # Process with fast algorithm
   xpcs-poweruser fast-g2-average /data/new_experiment.hdf5 -o /data/results

Workflow 3: Real-time Data Gathering
-------------------------------------

Set up continuous monitoring to gather files from multiple beamline directories:

.. code-block:: bash

   # Monitor and link files every 30 seconds
   xpcs-poweruser link-files \
       -s /beamline/detector1 /beamline/detector2 \
       -d /analysis/gathered_data \
       -r 30

Workflow 4: Batch Processing
-----------------------------

Process multiple files in a batch:

.. code-block:: bash

   # Create a simple bash loop
   for file in /data/hdf5/*.hdf5; do
       xpcs-poweruser fast-g2-average "$file" -o /data/results
   done

Logging and Output
==================

All commands provide detailed logging information including:

- Timestamps for each operation
- Progress updates
- Success/failure messages
- Error details when issues occur

The logging format is:

.. code-block:: text

   YYYY-MM-DD HH:MM:SS - module_name - LEVEL - message

Example output:

.. code-block:: text

   2025-01-12 14:30:25 - poweruser_xpcs.cli - INFO - Converting legacy datasets from /data/legacy to /data/nexus
   2025-01-12 14:30:25 - poweruser_xpcs.cli - INFO - File type: .bin, Workers: 4, Copy data: False
   2025-01-12 14:35:42 - poweruser_xpcs.cli - INFO - Conversion completed successfully!

Troubleshooting
===============

Common Issues and Solutions
---------------------------

**Issue: Command not found**

.. code-block:: text

   bash: xpcs-poweruser: command not found

**Solution:** Ensure the package is installed and your PATH is configured correctly:

.. code-block:: bash

   pip install --user poweruser_xpcs
   # Add ~/.local/bin to PATH if needed
   export PATH=$PATH:~/.local/bin

**Issue: Permission denied when creating links**

.. code-block:: text

   PermissionError: [Errno 13] Permission denied

**Solution:** Ensure you have write permissions to the destination directory:

.. code-block:: bash

   # Check permissions
   ls -ld /destination/path
   
   # Fix permissions if needed
   chmod u+w /destination/path

**Issue: Missing configuration file**

.. code-block:: text

   Error: G2 average script not found

**Solution:** Verify the package installation is complete:

.. code-block:: bash

   pip install --force-reinstall poweruser_xpcs

**Issue: HDF5 file not found or corrupted**

.. code-block:: text

   Error processing file.hdf5: Unable to open file

**Solution:** Verify the file exists and is a valid HDF5 file:

.. code-block:: bash

   # Check if file exists
   ls -lh /path/to/file.hdf5
   
   # Test HDF5 file integrity
   h5dump -H /path/to/file.hdf5

Performance Tips
----------------

1. **Use parallel processing** for large datasets:

   .. code-block:: bash

      xpcs-poweruser convert-legacy /data/in /data/out --workers 8

2. **Use fast-g2-average** for time-critical processing:

   .. code-block:: bash

      xpcs-poweruser fast-g2-average data.hdf5

3. **Filter files** to process only what you need:

   .. code-block:: bash

      xpcs-poweruser nexus-to-csv -i /data -o /csv -f "sample_A"

4. **Use symbolic links** instead of copying to save disk space:

   .. code-block:: bash

      # Default behavior creates links
      xpcs-poweruser convert-legacy /data/in /data/out

Advanced Usage
==============

Custom Configuration Files
--------------------------

You can create custom configuration files for G2 averaging. The JSON configuration should follow this structure:

.. code-block:: json

   {
       "parameter1": "value1",
       "parameter2": "value2"
   }

Then use it with:

.. code-block:: bash

   xpcs-poweruser g2-average data.hdf5 -c custom_config.json

Integration with Scripts
-------------------------

The CLI can be integrated into larger processing pipelines:

.. code-block:: bash

   #!/bin/bash
   # Example processing pipeline
   
   SOURCE_DIR="/beamline/raw_data"
   WORK_DIR="/scratch/processing"
   RESULTS_DIR="/results/final"
   
   # Step 1: Convert legacy data
   xpcs-poweruser convert-legacy "$SOURCE_DIR" "$WORK_DIR" --workers 8
   
   # Step 2: Process each file
   for hdf_file in "$WORK_DIR"/*.hdf5; do
       xpcs-poweruser fast-g2-average "$hdf_file" -o "$RESULTS_DIR"
   done
   
   # Step 3: Export to CSV for archival
   xpcs-poweruser nexus-to-csv -i "$WORK_DIR" -o "$RESULTS_DIR/csv"
   
   echo "Processing complete!"

Environment Variables
---------------------

You can set environment variables to customize behavior:

.. code-block:: bash

   # Set Python path if needed
   export PYTHONPATH=/custom/path:$PYTHONPATH
   
   # Run command
   xpcs-poweruser convert-legacy /data/in /data/out

Additional Resources
====================

- **Source Code:** https://github.com/AZjk/poweruser
- **Issue Tracker:** Report bugs and request features on GitHub
- **Documentation:** See the ``docs/`` directory for detailed API documentation
- **Examples:** Check the ``examples/`` directory for Jupyter notebooks and scripts

For more information on specific utilities, use:

.. code-block:: bash

   xpcs-poweruser list-utils

Version Information
===================

To check the installed version:

.. code-block:: bash

   xpcs-poweruser --version

This guide corresponds to version 0.1.0 and later of the XPCS Power User Tools.

Contributing
============

If you encounter issues or have suggestions for improvements:

1. Check existing documentation in the ``docs/`` directory
2. Review the ``list-utils`` output for available tools
3. Report issues via the project's issue tracker
4. Contribute improvements via pull requests

License
=======

Refer to the project's LICENSE file for licensing information.

Last Updated
============

This guide was last updated on January 12, 2025.
