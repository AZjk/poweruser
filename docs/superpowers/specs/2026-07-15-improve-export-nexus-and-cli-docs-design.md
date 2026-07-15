# Improve `export_nexus.py` and `cli_user_guide.rst`

## Context

Two untracked files existed in the repo:

- `src/poweruser_xpcs/utils/export_nexus.py` — a draft utility that reads an
  XPCS HDF5 file via `pyxpcsviewer` and writes a compact NeXus file plus
  metadata exports (JSON/TXT/XLSX). `pyxpcsviewer` is not a declared
  dependency anywhere in `pyproject.toml`, so the script fails to import for
  anyone without that package installed.
- `docs/cli_user_guide.rst` — a complete CLI reference guide, accurate
  against the current `cli.py` commands, but not wired into the Sphinx
  toctree (`docs/index.md`), so it isn't built into the docs site.

This spec covers bringing both files up to the standard of the rest of the
codebase and wiring them in properly, plus adding an `export-nexus` CLI
subcommand consistent with the other data-conversion commands.

## Goals

1. `export_nexus.py` reads data with `h5py` directly (same NeXus field
   paths already used by `convert_nexus_to_csv.py` /
   `convert_nexus_to_csv_metadata.py`), removing the undeclared
   `pyxpcsviewer` dependency.
2. `export_nexus` becomes a first-class `xpcs-poweruser export-nexus`
   subcommand, following the existing `g2-average`/`fast-g2-average`
   positional-file + optional-output pattern.
3. `docs/cli_user_guide.rst` is wired into the Sphinx build and documents
   the new `export-nexus` command.

## Non-goals

- No changes to any other existing CLI command or utility.
- No new metadata fields beyond what's safely present in every XPCS/NeXus
  file (no rheometer-specific assumptions).

## Design

### `export_nexus.py`

Data reads (mirrors `convert_nexus_to_csv_metadata.py`):

```python
with h5py.File(input_file, "r") as hf:
    g2 = hf["xpcs"]["multitau"]["normalized_g2"][:]
    delay_list = hf["xpcs"]["multitau"]["delay_list"][:]
    frame_time = hf["entry"]["instrument"]["detector_1"]["frame_time"][()]
    intensity = hf["xpcs"]["temporal_mean"]["scattering_1d"][:]
    q_values = hf["xpcs"]["qmap"]["dynamic_v_list_dim0"][:]
    time_delays = delay_list * frame_time
```

Metadata extraction ("generic + safe"): attempt to read `entry/start_time`
and `entry/instrument/detector_1/frame_time`; if a field is missing, log a
warning and omit it from the metadata dict rather than raising.

`export_metadata()` keeps its current JSON/TXT/XLSX behavior (pandas-based
`.xlsx` write). Since `pandas`/`openpyxl` aren't currently declared
dependencies, add them to `pyproject.toml`'s `dependencies` list.

Output: write `output_file` as an HDF5 file with `intensity`, `g2`,
`q_values`, `time_delays` datasets (unchanged from current behavior).

Replace `print()` calls with `logging` (module-level logger), consistent
with the rest of the CLI. Fix the docstring, which currently describes the
function backwards ("Export a .xpcs file to a Nexus file") — it actually
extracts derived quantities from an existing HDF5/NeXus file into a new,
smaller NeXus file plus metadata side-files.

Replace the hardcoded `if __name__ == "__main__":` example block with a
real `argparse` interface (`input_file` positional, `-o/--output`
optional), matching how `convert_nexus_to_csv.py` supports direct/
`run-script` invocation.

### `cli.py`

- New subparser `export-nexus`:
  - positional `hdf_file`
  - `-o, --output` (optional; default derived from input basename + `.nxs`)
- New `export_nexus_command(args)` following the existing pattern: log
  intent, call `export_nexus(...)` in a try/except, `logger.error` +
  `sys.exit(1)` on failure.
- Add `export-nexus` to `list_utils_command()`'s hardcoded "Main Commands"
  list.

### `docs/cli_user_guide.rst` / `docs/index.md`

- Add `cli_user_guide` to the toctree in `docs/index.md`.
- Add `export-nexus` to the "Available Commands" bullet list.
- Add a full Command Reference section for `export-nexus` (Syntax,
  Required Arguments, Options, Examples), matching the existing style of
  the other command sections.

## Testing

No existing test suite covers the CLI or utils modules (none found in the
repo). Verification is manual:

- `src/poweruser_xpcs/utils/sample_metadata.hdf`, the only sample data file
  in the repo, contains only `entry/...` (raw acquisition metadata) — no
  `xpcs/multitau`, `xpcs/qmap`, or `xpcs/temporal_mean` groups. It can
  exercise the metadata-only path (`entry/start_time`,
  `entry/instrument/detector_1/frame_time` extraction) but will hit a
  `KeyError` on the `xpcs` group when reading intensity/g2/q_values, since
  it holds no processed analysis results. Confirm this fails with the
  try/except in `export_nexus_command` producing a clean `logger.error` +
  exit 1, not a raw traceback.
- If a fully processed HDF5/NeXus file (with `xpcs/multitau`,
  `xpcs/qmap`, `xpcs/temporal_mean` groups) is available locally, run
  `xpcs-poweruser export-nexus <file.hdf> -o out.nxs` against it and
  confirm it produces `out.nxs` plus metadata files without error.
- Confirm the Sphinx docs build (`sphinx-build docs docs/_build`) picks up
  the new page without toctree warnings.
