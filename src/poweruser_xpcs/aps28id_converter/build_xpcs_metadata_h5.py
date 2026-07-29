"""Merge a raw XPCS detector HDF5 file with its matched .spec metadata and the
APS_28ID_XPCS_metadata_template.hdf schema template into a merged, metadata-only,
or split (raw copy + separate metadata file) output."""
import argparse
import math
import re
import shutil
from collections import Counter
from pathlib import Path

import h5py

HC_KEV_ANGSTROM = 12.398419843320026


def find_spec_file(raw_h5_path):
    """Locate the .spec file matching `raw_h5_path` via its SPECFileName NDAttribute."""
    raw_h5_path = Path(raw_h5_path)
    with h5py.File(raw_h5_path, "r") as f:
        raw_path = f["entry/instrument/NDAttributes/SPECFileName"][0]
    if isinstance(raw_path, bytes):
        raw_path = raw_path.decode("utf-8")
    spec_basename = Path(raw_path).name

    candidate = raw_h5_path.parent / spec_basename
    if not candidate.is_file():
        raise FileNotFoundError(
            f"Matched spec file '{spec_basename}' (from SPECFileName attribute "
            f"in {raw_h5_path.name}) not found next to it in '{raw_h5_path.parent}'"
        )
    return candidate


def get_scan_number(raw_h5_path):
    """Return the most common SCANNUM value across frames, warning if it's not constant."""
    with h5py.File(raw_h5_path, "r") as f:
        scan_nums = f["entry/instrument/NDAttributes/SCANNUM"][()]
    counts = Counter(int(v) for v in scan_nums)
    scan_number, count = counts.most_common(1)[0]
    if count != len(scan_nums):
        print(
            f"Warning: SCANNUM is not constant across frames in {raw_h5_path} "
            f"({dict(counts)}); using most common value {scan_number}"
        )
    return scan_number


_DATASET_RE = re.compile(
    r'<dataset name="([^"]+)"(?: type="([^"]+)")?(?: units="([^"]+)")?>([^<]*)</dataset>'
)


def parse_spec_ad_detector_block(spec_path, scan_number):
    """Parse the `ad_detector` UXML dataset block for `scan_number` out of a .spec file."""
    with open(spec_path, "r") as f:
        lines = f.readlines()

    scan_header_re = re.compile(r"^#S\s+" + str(scan_number) + r"(?:\s|$)")
    next_scan_re = re.compile(r"^#S\s+\d+(?:\s|$)")

    start_idx = None
    for i, line in enumerate(lines):
        if scan_header_re.match(line):
            start_idx = i
            break
    if start_idx is None:
        raise ValueError(f"No '#S {scan_number}' scan header found in {spec_path}")

    block_start = None
    block_end = None
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        if next_scan_re.match(line):
            break
        if '<group name="ad_detector"' in line:
            block_start = i
        elif block_start is not None and "</group>" in line:
            block_end = i
            break

    if block_start is None or block_end is None:
        raise ValueError(
            f"No 'ad_detector' UXML block found for scan {scan_number} in {spec_path}"
        )

    fields = {}
    for line in lines[block_start:block_end]:
        m = _DATASET_RE.search(line)
        if not m:
            continue
        name, dtype, _units, value = m.groups()
        if dtype == "int":
            value = int(value)
        elif dtype == "float":
            value = float(value)
        fields[name] = value
    return fields


def get_h5_ndattribute_value(raw_h5_path, name):
    """Read the first-frame value of NDAttribute `name` from `raw_h5_path`."""
    with h5py.File(raw_h5_path, "r") as f:
        return float(f[f"entry/instrument/NDAttributes/{name}"][0])


def compute_detector_distance(delr_deg, d0=1.1, d1=0.75):
    """Derive detector distance from the swinging-arm angle `delr_deg` (degrees)."""
    return d1 / math.cos(math.radians(delr_deg)) + d0 - d1


def build_field_updates(spec_fields, energy, exposure_time, spec_basename):
    """Map parsed spec fields plus energy/exposure_time to template dataset paths, converting units."""
    wavelength_angstrom = HC_KEV_ANGSTROM / energy
    beam_center_x = float(spec_fields["beam_center_x"])
    beam_center_y = float(spec_fields["beam_center_y"])
    x_pixel_size_m = float(spec_fields["x_pixel_size"]) / 1000.0
    y_pixel_size_m = float(spec_fields["y_pixel_size"]) / 1000.0
    frame_time = float(spec_fields["Exposure_period"])

    return {
        "instrument/detector_1/beam_center_x": beam_center_x,
        "instrument/detector_1/beam_center_y": beam_center_y,
        "instrument/detector_1/beam_center_position_x": 0.0,
        "instrument/detector_1/beam_center_position_y": 0.0,
        "instrument/detector_1/x_pixel_size": x_pixel_size_m,
        "instrument/detector_1/y_pixel_size": y_pixel_size_m,
        "instrument/detector_1/count_time": exposure_time,
        "instrument/detector_1/frame_time": frame_time,
        "instrument/incident_beam/incident_energy": energy,
        "instrument/monochromator/energy": energy,
        "instrument/monochromator/wavelength": wavelength_angstrom,
        "instrument/bluesky/spec_file": spec_basename,
    }


UNRESOLVED_FIELDS = []

NDATTRIBUTE_FIELDS = {
    "instrument/slits_1/horizontal_gap": "Slit_B1_hgap",
    "instrument/slits_1/horizontal_center": "Slit_B1_hcen",
    "instrument/slits_1/vertical_gap": "Slit_B1_vgap",
    "instrument/slits_1/vertical_center": "Slit_B1_vcen",
    "instrument/incident_beam/ring_current": "SR_current",
    "instrument/incident_beam/incident_beam_intensity": "I0",
    "instrument/undulator_1/gap": "ID_gap_USID",
    "instrument/undulator_1/energy": "ID_E_USID",
    "instrument/undulator_2/gap": "ID_gap_DSID",
    "instrument/undulator_2/energy": "ID_E_DSID",
    "instrument/detector_1/flightpath_swing": "28IDB_huber_nu",
    "instrument/detector_1/flightpath_swing_vertical": "28IDB_huber_delr",
}


def populate_metadata_fields(out_f, raw_h5_path, spec_path, template_f):
    """Copy the template's entry group into `out_f`, then overwrite it with values parsed from `raw_h5_path`/`spec_path`."""
    scan_number = get_scan_number(raw_h5_path)
    spec_fields = parse_spec_ad_detector_block(spec_path, scan_number)
    energy = get_h5_ndattribute_value(raw_h5_path, "Energy")
    exposure_time = get_h5_ndattribute_value(raw_h5_path, "Exposure_time")
    field_updates = build_field_updates(
        spec_fields, energy, exposure_time, Path(spec_path).name
    )

    out_entry = out_f["entry"]

    # Copy every field from the template metadata file.
    for key in template_f["entry"].keys():
        template_f.copy(template_f["entry"][key], out_entry, name=key)

    # Overwrite template placeholders with real values parsed from spec/raw h5.
    for rel_path, value in field_updates.items():
        out_f[f"entry/{rel_path}"][...] = value

    out_f["entry/scan_number"][...] = scan_number

    for rel_path, ndattribute_name in NDATTRIBUTE_FIELDS.items():
        out_f[f"entry/{rel_path}"][...] = get_h5_ndattribute_value(
            raw_h5_path, ndattribute_name
        )

    delr = get_h5_ndattribute_value(raw_h5_path, "28IDB_huber_delr")
    out_f["entry/instrument/detector_1/distance"][...] = compute_detector_distance(delr)

    for rel_path in UNRESOLVED_FIELDS:
        print(
            f"Warning: no real-data source available for 'entry/{rel_path}'; "
            f"left as template placeholder value "
            f"{out_f['entry/' + rel_path][()]}"
        )


def build_output_h5(raw_h5_path, spec_path, template_h5_path, output_h5_path, overwrite=True):
    """Write a single merged HDF5 file with raw detector data, original instrument metadata, and populated template fields."""
    raw_h5_path = Path(raw_h5_path)
    output_h5_path = Path(output_h5_path)
    if not overwrite and output_h5_path.exists():
        raise FileExistsError(f"Output file already exists: {output_h5_path}")

    output_h5_path.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(raw_h5_path, "r") as raw_f, \
            h5py.File(template_h5_path, "r") as template_f, \
            h5py.File(output_h5_path, "w") as out_f:

        out_entry = out_f.create_group("entry")

        # Copy raw detector data without decompressing.
        out_entry.create_group("data")
        raw_f.copy(raw_f["entry/data/data"], out_entry["data"], name="data")

        # Copy raw instrument metadata under a renamed group.
        raw_f.copy(raw_f["entry/instrument"], out_entry, name="instrument_original")

        populate_metadata_fields(out_f, raw_h5_path, spec_path, template_f)

    return output_h5_path


def build_metadata_h5(raw_h5_path, spec_path, template_h5_path, metadata_h5_path, overwrite=True):
    """Write a metadata-only HDF5 file (no raw detector data) with populated template fields."""
    raw_h5_path = Path(raw_h5_path)
    metadata_h5_path = Path(metadata_h5_path)
    if not overwrite and metadata_h5_path.exists():
        raise FileExistsError(f"Output file already exists: {metadata_h5_path}")

    metadata_h5_path.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(template_h5_path, "r") as template_f, \
            h5py.File(metadata_h5_path, "w") as out_f:
        out_f.create_group("entry")
        populate_metadata_fields(out_f, raw_h5_path, spec_path, template_f)

    return metadata_h5_path


def build_split_output(raw_h5_path, spec_path, template_h5_path, output_folder, overwrite=True):
    """Copy the raw HDF5 file and write a separate metadata HDF5 file into `<output_folder>/<raw-stem>/`."""
    raw_h5_path = Path(raw_h5_path)
    basename = raw_h5_path.stem
    scan_folder = Path(output_folder) / basename
    scan_folder.mkdir(parents=True, exist_ok=True)

    raw_copy_path = scan_folder / raw_h5_path.name
    if not overwrite and raw_copy_path.exists():
        raise FileExistsError(f"Output file already exists: {raw_copy_path}")
    shutil.copy2(raw_h5_path, raw_copy_path)

    metadata_h5_path = scan_folder / f"{basename}_metadata.hdf"
    build_metadata_h5(raw_h5_path, spec_path, template_h5_path, metadata_h5_path, overwrite=overwrite)

    return raw_copy_path, metadata_h5_path


def add_arguments(parser):
    """Add this tool's arguments to `parser` (a top-level parser or a subparser)."""
    parser.add_argument("raw_fname", help="Path to the raw detector .h5 file")
    parser.add_argument(
        "--spec-fname",
        default=None,
        help="Path to the .spec file (default: auto-discovered next to raw-fname "
        "using its SPECFileName attribute)",
    )
    parser.add_argument(
        "--output-folder", required=True, help="Folder to write the output .h5 file into"
    )
    parser.add_argument(
        "--template-fname",
        default=str(Path(__file__).parent / "APS_28ID_XPCS_metadata_template.hdf"),
        help="Path to the metadata schema/template file (default: %(default)s)",
    )
    parser.add_argument(
        "--no-overwrite",
        action="store_true",
        help="Refuse to overwrite an existing output file (default: overwrite)",
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="Write one merged .h5 file (default: split into a folder containing "
        "a raw .h5 copy and a separate _metadata.hdf file)",
    )
    return parser


def run(args):
    """Execute the conversion described by parsed `args`; return the written paths."""
    raw_h5_path = Path(args.raw_fname)
    spec_path = Path(args.spec_fname) if args.spec_fname else find_spec_file(raw_h5_path)

    if args.single_file:
        output_h5_path = Path(args.output_folder) / raw_h5_path.name
        build_output_h5(
            raw_h5_path, spec_path, args.template_fname, output_h5_path,
            overwrite=not args.no_overwrite,
        )
        return (output_h5_path,)
    else:
        return build_split_output(
            raw_h5_path, spec_path, args.template_fname, args.output_folder,
            overwrite=not args.no_overwrite,
        )


def main(argv=None):
    """CLI entry point: parse arguments, run the conversion, and print each written path."""
    parser = argparse.ArgumentParser(
        description="Build a standardized XPCS metadata HDF5 file from a raw "
        "detector HDF5 file and its matched .spec file."
    )
    add_arguments(parser)
    args = parser.parse_args(argv)

    for path in run(args):
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
