# Improve export_nexus.py and CLI docs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `export_nexus.py` to drop its undeclared `pyxpcsviewer` dependency, wire it into the CLI as `export-nexus`, and document the new command in a properly-linked `cli_user_guide.rst`.

**Architecture:** `export_nexus.py` reads processed XPCS data directly via `h5py` (matching the field paths already used by `convert_nexus_to_csv_metadata.py`), replacing the `pyxpcsviewer`-based reads. `cli.py` gets a new subcommand that follows the existing `g2-average`/`fast-g2-average` pattern (positional file + optional `-o/--output`, try/except around the call). `docs/cli_user_guide.rst` gets a new Command Reference section and is wired into the Sphinx build via a hidden toctree in `docs/index.md`.

**Tech Stack:** Python, h5py, pandas (for `.xlsx` metadata export), argparse, Sphinx + MyST.

## Global Constraints

- Remove `pyxpcsviewer` entirely — no reference to it may remain in `export_nexus.py`.
- `pandas` and `openpyxl` must be added to `pyproject.toml`'s main `dependencies` list (not an optional extra), since `export_metadata()`'s `.xlsx` output is not optional/gated behind a flag by default.
- Metadata extraction reads only `entry/start_time` and `entry/instrument/detector_1/frame_time` — no rheometer-specific or otherwise dataset-specific fields. A missing field must log a warning and be omitted, not raise.
- No changes to any other existing CLI command, utility module, or dependency.
- No new test framework or `tests/` directory — this repo has none for its CLI/utils modules today; verification here is manual, matching existing practice.

---

### Task 1: Rewrite `export_nexus.py` to use h5py instead of pyxpcsviewer

**Files:**
- Modify: `src/poweruser_xpcs/utils/export_nexus.py` (full rewrite)
- Modify: `pyproject.toml:26-31` (add `pandas`, `openpyxl` dependencies)

**Interfaces:**
- Produces: `export_nexus(input_file: str, output_file: str) -> None` — unchanged signature, now reads via h5py. Raises `KeyError` if `input_file` lacks the expected `xpcs/multitau`, `xpcs/qmap`, or `xpcs/temporal_mean` groups (i.e. isn't a processed XPCS/NeXus file).
- Produces: `export_metadata(label: str, metadata: dict, use_json=True, use_txt=True, use_xlsx=True) -> None` — unchanged.
- Consumed by: Task 2's `export_nexus_command` in `cli.py`.

- [ ] **Step 1: Add `pandas` and `openpyxl` to `pyproject.toml` dependencies**

Edit `pyproject.toml`, replacing:

```toml
dependencies = [
    "numpy>=1.20.0",
    "scipy>=1.7.0",
    "h5py>=3.0.0",
    "tqdm>=4.60.0",
]
```

with:

```toml
dependencies = [
    "numpy>=1.20.0",
    "scipy>=1.7.0",
    "h5py>=3.0.0",
    "tqdm>=4.60.0",
    "pandas>=1.3.0",
    "openpyxl>=3.0.0",
]
```

- [ ] **Step 2: Rewrite `export_nexus.py`**

Replace the entire contents of `src/poweruser_xpcs/utils/export_nexus.py` with:

```python
"""Extract intensity, g2, q-values, time-delays, and metadata from a processed XPCS/NeXus HDF5 file."""

import argparse
import json
import logging
import os

import h5py
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def export_metadata(label, metadata, use_json=True, use_txt=True, use_xlsx=True):
    """Write a metadata dict to `{label}_metadata.json/.txt/.xlsx`."""
    if use_json:
        json_filename = f"{label}_metadata.json"
        with open(json_filename, "w") as json_file:
            json.dump(metadata, json_file, indent=4)

    if use_txt:
        txt_filename = f"{label}_metadata.txt"
        with open(txt_filename, "w") as txt_file:
            for key, value in metadata.items():
                txt_file.write(f"{key} = {value}\n")

    if use_xlsx:
        xls_filename = f"{label}_metadata.xlsx"
        df = pd.DataFrame(list(metadata.items()), columns=["Key", "Value"])
        df.to_excel(xls_filename, index=False)


def _read_metadata(hf):
    """Read fields present in any XPCS/NeXus file; skip and warn on any that are missing."""
    fields = {
        "start_time": "entry/start_time",
        "frame_time": "entry/instrument/detector_1/frame_time",
    }
    metadata = {}
    for name, path in fields.items():
        try:
            value = hf[path][()]
        except KeyError:
            logger.warning(f"Metadata field '{path}' not found, skipping.")
            continue
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        metadata[name] = value
    return metadata


def export_nexus(input_file, output_file):
    """
    Extract intensity, g2, q-values, and time-delays from a processed
    XPCS/NeXus HDF5 file and write them to a new, smaller NeXus file,
    along with a metadata export (JSON/TXT/XLSX).

    Parameters
    ----------
    input_file : str
        Path to the source HDF5/NeXus file. Must contain xpcs/multitau,
        xpcs/qmap, and xpcs/temporal_mean groups (i.e. already processed).
    output_file : str
        Path to the output NeXus file to create.
    """
    with h5py.File(input_file, "r") as hf:
        metadata = _read_metadata(hf)
        g2 = hf["xpcs"]["multitau"]["normalized_g2"][:]
        delay_list = hf["xpcs"]["multitau"]["delay_list"][:]
        frame_time = hf["entry"]["instrument"]["detector_1"]["frame_time"][()]
        intensity = hf["xpcs"]["temporal_mean"]["scattering_1d"][:]
        q_values = hf["xpcs"]["qmap"]["dynamic_v_list_dim0"][:]

    time_delays = delay_list * frame_time

    label = os.path.splitext(output_file)[0]
    export_metadata(label=label, metadata=metadata)

    with h5py.File(output_file, "w") as nexus_file:
        nexus_file.create_dataset("intensity", data=intensity)
        nexus_file.create_dataset("g2", data=g2)
        nexus_file.create_dataset("q_values", data=q_values)
        nexus_file.create_dataset("time_delays", data=time_delays)

    logger.info(f"Exported {input_file} to {output_file} successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract intensity, g2, q-values, and time-delays from a processed XPCS/NeXus HDF5 file."
    )
    parser.add_argument("input_file", type=str, help="Path to the source HDF5/NeXus file.")
    parser.add_argument(
        "-o", "--output", type=str, required=True, help="Path to the output NeXus file."
    )
    args = parser.parse_args()

    export_nexus(args.input_file, args.output)
```

- [ ] **Step 3: Verify the rewrite imports cleanly and the metadata path works**

Run:

```bash
python3 -c "
from poweruser_xpcs.utils.export_nexus import _read_metadata
import h5py
with h5py.File('src/poweruser_xpcs/utils/sample_metadata.hdf', 'r') as hf:
    print(_read_metadata(hf))
"
```

Expected: prints a dict with `start_time` and `frame_time` keys (no `ModuleNotFoundError` for `pyxpcsviewer`, no traceback).

- [ ] **Step 4: Verify the missing-groups case fails cleanly (not on import/metadata)**

Run:

```bash
python3 -c "
from poweruser_xpcs.utils.export_nexus import export_nexus
export_nexus('src/poweruser_xpcs/utils/sample_metadata.hdf', '/tmp/out.nxs')
"
```

Expected: `KeyError` mentioning `"xpcs"` (this sample file has no processed `xpcs/...` groups — this confirms the h5py reads run correctly up to that point, proving the `pyxpcsviewer` removal works; it is not evidence of a bug). Metadata files (`/tmp_metadata.json`, `.txt`, `.xlsx`) will have been written before the error — delete them: `rm -f /tmp_metadata.*`.

- [ ] **Step 5: Commit**

```bash
git add src/poweruser_xpcs/utils/export_nexus.py pyproject.toml
git commit -m "refactor: rewrite export_nexus.py to use h5py instead of pyxpcsviewer"
```

---

### Task 2: Wire `export-nexus` into the CLI

**Files:**
- Modify: `src/poweruser_xpcs/cli.py`

**Interfaces:**
- Consumes: `export_nexus(input_file: str, output_file: str) -> None` from Task 1.
- Produces: `export_nexus_command(args)` — CLI handler; `xpcs-poweruser export-nexus` subcommand with `hdf_file` positional and `-o/--output` optional.

- [ ] **Step 1: Add the `export_nexus_command` handler**

In `src/poweruser_xpcs/cli.py`, replace:

```python
    logger.info(f"Converted {converted_count} files successfully!")


def run_script_command(args):
```

with:

```python
    logger.info(f"Converted {converted_count} files successfully!")


def export_nexus_command(args):
    """Extract intensity, g2, q-values, and time-delays into a compact NeXus file."""
    from .utils.export_nexus import export_nexus

    output = args.output or f"{Path(args.hdf_file).stem}_export.nxs"

    logger.info(f"Exporting {args.hdf_file} to {output}")

    try:
        export_nexus(args.hdf_file, output)
        logger.info("Export completed successfully!")
    except Exception as e:
        logger.error(f"Error during export: {e}")
        sys.exit(1)


def run_script_command(args):
```

- [ ] **Step 2: Register the `export-nexus` subparser**

In `src/poweruser_xpcs/cli.py`, replace:

```python
    nexus_parser.set_defaults(func=nexus_to_csv_command)

    # Run script command
```

with:

```python
    nexus_parser.set_defaults(func=nexus_to_csv_command)

    # Export nexus command
    export_parser = subparsers.add_parser(
        "export-nexus",
        help="Extract intensity, g2, q-values, and time-delays into a compact NeXus file",
        description="This command extracts key derived quantities (intensity, g2, q-values, "
        "time-delays) and metadata from a processed HDF5/NeXus file into a new, smaller NeXus "
        "file plus metadata exports (JSON/TXT/XLSX).",
    )
    export_parser.add_argument("hdf_file", help="HDF5/NeXus file to process")
    export_parser.add_argument(
        "-o",
        "--output",
        help="Path to the output NeXus file (default: <input_basename>_export.nxs)",
    )
    export_parser.set_defaults(func=export_nexus_command)

    # Run script command
```

- [ ] **Step 3: Add `export-nexus` to the `list-utils` output**

In `src/poweruser_xpcs/cli.py`, replace:

```python
    logger.info("  nexus-to-csv       - Convert HDF5/NeXus files to CSV format")
    logger.info("  g2-average         - Run G2 averaging analysis")
```

with:

```python
    logger.info("  nexus-to-csv       - Convert HDF5/NeXus files to CSV format")
    logger.info("  export-nexus       - Extract intensity, g2, q-values, and time-delays into a compact NeXus file")
    logger.info("  g2-average         - Run G2 averaging analysis")
```

- [ ] **Step 4: Verify CLI registration**

Run:

```bash
python3 -m poweruser_xpcs.cli --help
python3 -m poweruser_xpcs.cli export-nexus --help
python3 -m poweruser_xpcs.cli list-utils
```

Expected: `--help` lists `export-nexus` among the commands; `export-nexus --help` shows `hdf_file` and `-o/--output`; `list-utils` prints the new `export-nexus` line.

- [ ] **Step 5: Verify end-to-end failure handling (no processed sample file available)**

Run:

```bash
python3 -m poweruser_xpcs.cli export-nexus src/poweruser_xpcs/utils/sample_metadata.hdf -o /tmp/out.nxs
echo "exit code: $?"
rm -f sample_metadata_export_metadata.* /tmp/out.nxs
```

Expected: a single `logger.error` line containing `Error during export:` and mentioning `'xpcs'`, exit code `1` — not a raw Python traceback. This confirms the try/except wiring works correctly (this sample file has no processed `xpcs/...` groups, so a clean failure here is correct behavior, not a bug).

- [ ] **Step 6: If you have a fully processed HDF5/NeXus file available, verify the success path**

Run (substitute a real processed file):

```bash
python3 -m poweruser_xpcs.cli export-nexus /path/to/processed_experiment.hdf5 -o /tmp/out.nxs
python3 -c "
import h5py
with h5py.File('/tmp/out.nxs') as f:
    print(list(f.keys()))
"
```

Expected: logs `Export completed successfully!`; the printed list is `['g2', 'intensity', 'q_values', 'time_delays']`. Skip this step if no such file is available — Step 5 already validates the wiring.

- [ ] **Step 7: Commit**

```bash
git add src/poweruser_xpcs/cli.py
git commit -m "feat(cli): add export-nexus command"
```

---

### Task 3: Document `export-nexus` and wire the CLI guide into Sphinx

**Files:**
- Modify: `docs/cli_user_guide.rst`
- Modify: `docs/index.md`

**Interfaces:**
- None (documentation only).

- [ ] **Step 1: Add `export-nexus` to the Available Commands list**

In `docs/cli_user_guide.rst`, replace:

```rst
- ``nexus-to-csv`` - Convert HDF5/NeXus files to CSV format
- ``g2-average`` - Run G2 averaging analysis
```

with:

```rst
- ``nexus-to-csv`` - Convert HDF5/NeXus files to CSV format
- ``export-nexus`` - Extract intensity, g2, q-values, and time-delays into a compact NeXus file
- ``g2-average`` - Run G2 averaging analysis
```

- [ ] **Step 2: Add the `export-nexus` Command Reference section**

In `docs/cli_user_guide.rst`, replace:

```rst
g2-average
----------
```

with:

```rst
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
```

- [ ] **Step 3: Wire `cli_user_guide` into the Sphinx build**

`docs/index.md` currently links to its other pages as plain Markdown links under "## Modules" rather than a real Sphinx toctree, so none of those pages are in the build's navigation tree either. Add a hidden toctree so `cli_user_guide` is included in the Sphinx build (fixing the "document isn't included in any toctree" case for this new page) without changing the visible page content.

In `docs/index.md`, replace:

````markdown
# XPCS Power User Tools Documentation

Welcome to the documentation for XPCS Power User Tools, a collection of utilities for XPCS (X-ray Photon Correlation Spectroscopy) data analysis.
````

with:

````markdown
# XPCS Power User Tools Documentation

```{toctree}
:hidden:
:maxdepth: 1

cli_user_guide
```

Welcome to the documentation for XPCS Power User Tools, a collection of utilities for XPCS (X-ray Photon Correlation Spectroscopy) data analysis.
````

- [ ] **Step 4: Verify the docs build includes the new page**

Run:

```bash
pip install -e ".[docs]"
sphinx-build -b html docs /tmp/docs_build 2>&1 | grep -i "cli_user_guide"
```

Expected: no line reading `document isn't included in any toctree` for `cli_user_guide`. (Other warnings about `convert_legacy_datasets`, `convert_nexus_to_csv`, or `xpcs_functions` not being in a toctree are pre-existing and out of scope for this task.)

- [ ] **Step 5: Commit**

```bash
git add docs/cli_user_guide.rst docs/index.md
git commit -m "docs: document export-nexus command and wire cli_user_guide into Sphinx build"
```
