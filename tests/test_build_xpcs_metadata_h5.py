from pathlib import Path

import h5py
import numpy as np
import pytest

from poweruser_xpcs.aps28id_converter.build_xpcs_metadata_h5 import (
    find_spec_file,
    get_scan_number,
    parse_spec_ad_detector_block,
    get_h5_ndattribute_value,
    build_field_updates,
    compute_detector_distance,
    UNRESOLVED_FIELDS,
    NDATTRIBUTE_FIELDS,
    build_output_h5,
    build_metadata_h5,
    build_split_output,
    main,
)

SPEC_FIXTURE_TEXT = """#F test.spec
#E 1700000000
#D Mon Jan 1 00:00:00 2024

#S 1  ascan  foo 0 1  5 1
#D Mon Jan 1 00:00:01 2024
#P0 0 0
#UXML <group name="attenuator_set" NX_class="NXcollection">
#UXML   <dataset name="transmission" type="float">1.0</dataset>
#UXML </group>
#UXML <group name="ad_detector" NX_class="NXdetector">
#UXML   <dataset name="x_pixel_size" type="float" units="mm">0.075</dataset>
#UXML   <dataset name="y_pixel_size" type="float" units="mm">0.075</dataset>
#UXML   <dataset name="Exposure_time" type="float" units="second">1.00</dataset>
#UXML   <dataset name="Exposure_period" type="float" units="second">1.00</dataset>
#UXML   <dataset name="beam_center_x" type="int">442</dataset>
#UXML   <dataset name="beam_center_y" type="int">291</dataset>
#UXML </group>

#S 2  ascan  foo 1 2  5 1
#D Mon Jan 1 00:00:02 2024
#P0 1 1
#UXML <group name="ad_detector" NX_class="NXdetector">
#UXML   <dataset name="x_pixel_size" type="float" units="mm">0.075</dataset>
#UXML   <dataset name="y_pixel_size" type="float" units="mm">0.075</dataset>
#UXML   <dataset name="Exposure_time" type="float" units="second">0.20</dataset>
#UXML   <dataset name="Exposure_period" type="float" units="second">0.20</dataset>
#UXML   <dataset name="beam_center_x" type="int">500</dataset>
#UXML   <dataset name="beam_center_y" type="int">300</dataset>
#UXML </group>
"""


def make_raw_h5(path, scan_number=1, spec_name="test.spec", n_frames=3):
    with h5py.File(path, "w") as f:
        nd = f.create_group("entry/instrument/NDAttributes")
        nd.create_dataset("SCANNUM", data=np.full(n_frames, scan_number, dtype=float))
        nd.create_dataset(
            "SPECFileName",
            data=[f"/remote/path/{spec_name}".encode() for _ in range(n_frames)],
        )
        nd.create_dataset("Energy", data=np.full(n_frames, 8.86497478))
        nd.create_dataset("Exposure_time", data=np.linspace(0.9, 1.1, n_frames))
        nd.create_dataset("Slit_B1_hgap", data=np.linspace(0.099, 0.101, n_frames))
        nd.create_dataset("Slit_B1_hcen", data=np.linspace(-0.96, -0.94, n_frames))
        nd.create_dataset("Slit_B1_vgap", data=np.linspace(0.04, 0.06, n_frames))
        nd.create_dataset("Slit_B1_vcen", data=np.linspace(1.4, 1.6, n_frames))
        nd.create_dataset("SR_current", data=np.linspace(101.9, 102.1, n_frames))
        nd.create_dataset("I0", data=np.linspace(19900.0, 20100.0, n_frames))
        nd.create_dataset("ID_gap_USID", data=np.linspace(17.4, 17.6, n_frames))
        nd.create_dataset("ID_E_USID", data=np.linspace(8.9, 9.1, n_frames))
        nd.create_dataset("ID_gap_DSID", data=np.linspace(13.4, 13.6, n_frames))
        nd.create_dataset("ID_E_DSID", data=np.linspace(14.9, 15.1, n_frames))
        nd.create_dataset("28IDB_huber_delr", data=np.linspace(2.9, 3.1, n_frames))
        nd.create_dataset("28IDB_huber_nu", data=np.linspace(-0.1, 0.1, n_frames))
        f.create_dataset(
            "entry/data/data",
            data=np.zeros((n_frames, 4, 4), dtype="uint32"),
            chunks=(1, 4, 4),
            compression="gzip",
        )
    return path


def test_find_spec_file_finds_file_next_to_raw_fname(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, spec_name="test.spec")

    found = find_spec_file(raw_h5_path)
    assert found == spec_path


def test_find_spec_file_missing_raises(tmp_path):
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, spec_name="missing.spec")

    with pytest.raises(FileNotFoundError):
        find_spec_file(raw_h5_path)


def test_get_scan_number_reads_majority_value(tmp_path):
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1)
    assert get_scan_number(raw_h5_path) == 1


def test_parse_spec_ad_detector_block_scan_1(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    fields = parse_spec_ad_detector_block(spec_path, scan_number=1)

    assert fields["beam_center_x"] == 442
    assert fields["beam_center_y"] == 291
    assert fields["x_pixel_size"] == 0.075
    assert fields["y_pixel_size"] == 0.075
    assert fields["Exposure_time"] == 1.00
    assert fields["Exposure_period"] == 1.00


def test_parse_spec_ad_detector_block_scan_2_is_distinct(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    fields = parse_spec_ad_detector_block(spec_path, scan_number=2)

    assert fields["beam_center_x"] == 500
    assert fields["beam_center_y"] == 300
    assert fields["Exposure_time"] == 0.20


def test_parse_spec_ad_detector_block_missing_scan_raises(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    with pytest.raises(ValueError):
        parse_spec_ad_detector_block(spec_path, scan_number=99)


def test_get_h5_ndattribute_value_reads_first_element_not_mean(tmp_path):
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path)
    assert get_h5_ndattribute_value(raw_h5_path, "Energy") == pytest.approx(8.86497478)
    # Exposure_time varies per-frame (linspace 0.9..1.1); first frame is 0.9,
    # while the mean across 3 frames would be 1.0 — this distinguishes the two.
    assert get_h5_ndattribute_value(raw_h5_path, "Exposure_time") == pytest.approx(0.9)


def test_compute_detector_distance_uses_default_d0_d1():
    # At delr=0 the arm points straight down the beam axis, so distance
    # collapses to the on-axis reference distance d0.
    assert compute_detector_distance(0.0) == pytest.approx(1.1)
    # cos(60 deg) == 0.5, so d1/cos(60) == 2*d1 == 1.5
    assert compute_detector_distance(60.0) == pytest.approx(1.5 + 1.1 - 0.75)


def test_compute_detector_distance_accepts_overridden_d0_d1():
    assert compute_detector_distance(0.0, d0=2.0, d1=1.0) == pytest.approx(2.0)
    assert compute_detector_distance(60.0, d0=2.0, d1=1.0) == pytest.approx(2.0 + 1.0)


def test_ndattribute_fields_maps_output_paths_to_ndattribute_names():
    assert NDATTRIBUTE_FIELDS == {
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


def test_build_field_updates_maps_and_converts_units():
    spec_fields = {
        "beam_center_x": 442,
        "beam_center_y": 291,
        "x_pixel_size": 0.075,
        "y_pixel_size": 0.075,
        "Exposure_time": 1.00,
        "Exposure_period": 1.00,
    }
    updates = build_field_updates(
        spec_fields,
        energy=8.86497478,
        exposure_time=0.9999999,
        spec_basename="PGRL351_LSMO_HZO_LSMO_5nm_Device_1em6Torr_041126_1.spec",
    )

    assert updates["instrument/detector_1/beam_center_x"] == 442.0
    assert updates["instrument/detector_1/beam_center_y"] == 291.0
    assert updates["instrument/detector_1/beam_center_position_x"] == 0.0
    assert updates["instrument/detector_1/beam_center_position_y"] == 0.0
    assert updates["instrument/detector_1/x_pixel_size"] == pytest.approx(7.5e-5)
    assert updates["instrument/detector_1/y_pixel_size"] == pytest.approx(7.5e-5)
    assert updates["instrument/detector_1/count_time"] == pytest.approx(0.9999999)
    assert updates["instrument/detector_1/frame_time"] == pytest.approx(1.00)
    assert updates["instrument/incident_beam/incident_energy"] == pytest.approx(8.86497478)
    assert updates["instrument/monochromator/energy"] == pytest.approx(8.86497478)
    assert updates["instrument/monochromator/wavelength"] == pytest.approx(
        12.398419843320026 / 8.86497478
    )
    assert updates["instrument/bluesky/spec_file"] == (
        "PGRL351_LSMO_HZO_LSMO_5nm_Device_1em6Torr_041126_1.spec"
    )


def test_unresolved_fields_is_now_empty():
    assert UNRESOLVED_FIELDS == []


def make_template_h5(path):
    with h5py.File(path, "w") as f:
        entry = f.create_group("entry")
        entry.create_dataset("beamline", data=b"APS-8-ID-I")
        entry.create_dataset("scan_number", data=0, dtype="int64")
        det = entry.create_group("instrument/detector_1")
        det.create_dataset("beam_center_x", data=1677.5)
        det.create_dataset("beam_center_y", data=841.5)
        det.create_dataset("beam_center_position_x", data=1677.5)
        det.create_dataset("beam_center_position_y", data=841.5)
        det.create_dataset("x_pixel_size", data=7.5e-05)
        det.create_dataset("y_pixel_size", data=7.5e-05)
        det.create_dataset("count_time", data=2e-05)
        det.create_dataset("frame_time", data=2e-05)
        det.create_dataset("distance", data=9.03001335)
        det.create_dataset("flightpath_swing", data=0.0)
        det.create_dataset("flightpath_swing_vertical", data=0.0)
        entry.create_dataset("instrument/incident_beam/incident_energy", data=1.0)
        entry.create_dataset("instrument/incident_beam/ring_current", data=0.0)
        entry.create_dataset("instrument/incident_beam/incident_beam_intensity", data=0.0)
        entry.create_dataset("instrument/monochromator/energy", data=1.0)
        entry.create_dataset("instrument/monochromator/wavelength", data=1.0)
        entry.create_dataset("instrument/bluesky/spec_file", data="placeholder.dat")
        entry.create_dataset("instrument/slits_1/horizontal_gap", data=0.0)
        entry.create_dataset("instrument/slits_1/horizontal_center", data=0.0)
        entry.create_dataset("instrument/slits_1/vertical_gap", data=0.0)
        entry.create_dataset("instrument/slits_1/vertical_center", data=0.0)
        entry.create_dataset("instrument/undulator_1/gap", data=0.0)
        entry.create_dataset("instrument/undulator_1/energy", data=0.0)
        entry.create_dataset("instrument/undulator_2/gap", data=0.0)
        entry.create_dataset("instrument/undulator_2/energy", data=0.0)
        entry.create_group("sample")
        entry.create_group("user")
    return path


def test_build_output_h5_full_pipeline(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec", n_frames=3)

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_dir = tmp_path / "output"
    output_path = build_output_h5(raw_h5_path, spec_path, template_path, output_dir / "raw.h5")

    assert output_path == output_dir / "raw.h5"
    assert output_path.exists()

    with h5py.File(output_path, "r") as f:
        assert f["entry/data/data"].shape == (3, 4, 4)
        assert f["entry/data/data"].compression == "gzip"
        assert f["entry/data/data"].chunks == (1, 4, 4)
        assert "SCANNUM" in f["entry/instrument_original/NDAttributes"]
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0
        assert f["entry/instrument/detector_1/beam_center_y"][()] == 291.0
        assert f["entry/instrument/detector_1/beam_center_position_x"][()] == 0.0
        assert f["entry/instrument/detector_1/beam_center_position_y"][()] == 0.0
        assert f["entry/instrument/detector_1/x_pixel_size"][()] == pytest.approx(7.5e-5)
        # count_time now reads the first frame's Exposure_time (0.9), not the
        # 3-frame mean (which would be 1.0).
        assert f["entry/instrument/detector_1/count_time"][()] == pytest.approx(0.9)
        assert f["entry/instrument/detector_1/frame_time"][()] == pytest.approx(1.0)
        assert f["entry/instrument/incident_beam/incident_energy"][()] == pytest.approx(8.86497478)
        assert f["entry/instrument/bluesky/spec_file"][()].decode() == "test.spec"
        assert f["entry/scan_number"][()] == 1
        # All NDATTRIBUTE_FIELDS below read the first frame, not the mean.
        assert f["entry/instrument/slits_1/horizontal_gap"][()] == pytest.approx(0.099)
        assert f["entry/instrument/slits_1/horizontal_center"][()] == pytest.approx(-0.96)
        assert f["entry/instrument/slits_1/vertical_gap"][()] == pytest.approx(0.04)
        assert f["entry/instrument/slits_1/vertical_center"][()] == pytest.approx(1.4)
        assert f["entry/instrument/incident_beam/ring_current"][()] == pytest.approx(101.9)
        assert f["entry/instrument/incident_beam/incident_beam_intensity"][()] == pytest.approx(19900.0)
        assert f["entry/instrument/undulator_1/gap"][()] == pytest.approx(17.4)
        assert f["entry/instrument/undulator_1/energy"][()] == pytest.approx(8.9)
        assert f["entry/instrument/undulator_2/gap"][()] == pytest.approx(13.4)
        assert f["entry/instrument/undulator_2/energy"][()] == pytest.approx(14.9)
        assert f["entry/instrument/detector_1/flightpath_swing"][()] == pytest.approx(-0.1)
        assert f["entry/instrument/detector_1/flightpath_swing_vertical"][()] == pytest.approx(2.9)
        # Derived from the first-frame delr (2.9) via compute_detector_distance,
        # not a raw copy — no longer an untouched placeholder.
        assert f["entry/instrument/detector_1/distance"][()] == pytest.approx(
            compute_detector_distance(2.9)
        )
        # Untouched template-only group:
        assert "sample" in f["entry"]
        assert "user" in f["entry"]
        # Untouched template leaf value:
        assert f["entry/beamline"][()].decode() == "APS-8-ID-I"


def test_build_output_h5_raises_if_output_exists_and_overwrite_false(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")
    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_path = tmp_path / "out.h5"
    output_path.write_bytes(b"")

    with pytest.raises(FileExistsError):
        build_output_h5(raw_h5_path, spec_path, template_path, output_path, overwrite=False)


def test_build_output_h5_overwrites_by_default(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")
    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_path = tmp_path / "out.h5"
    output_path.write_bytes(b"not a real h5 file")

    build_output_h5(raw_h5_path, spec_path, template_path, output_path)

    with h5py.File(output_path, "r") as f:
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0


def test_build_metadata_h5_creates_metadata_only_file(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec", n_frames=3)

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    metadata_path = tmp_path / "raw_metadata.hdf"
    result = build_metadata_h5(raw_h5_path, spec_path, template_path, metadata_path)

    assert result == metadata_path
    assert metadata_path.exists()

    with h5py.File(metadata_path, "r") as f:
        assert "data" not in f["entry"]
        assert "instrument_original" not in f["entry"]
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0
        assert f["entry/scan_number"][()] == 1
        assert f["entry/instrument/slits_1/horizontal_gap"][()] == pytest.approx(0.099)
        assert f["entry/instrument/detector_1/distance"][()] == pytest.approx(
            compute_detector_distance(2.9)
        )
        # Untouched template-only group, same as the merged-file behavior:
        assert "sample" in f["entry"]


def test_build_metadata_h5_raises_if_output_exists_and_overwrite_false(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")
    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    metadata_path = tmp_path / "raw_metadata.hdf"
    metadata_path.write_bytes(b"")

    with pytest.raises(FileExistsError):
        build_metadata_h5(raw_h5_path, spec_path, template_path, metadata_path, overwrite=False)


def test_build_metadata_h5_overwrites_by_default(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")
    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    metadata_path = tmp_path / "raw_metadata.hdf"
    metadata_path.write_bytes(b"not a real h5 file")

    build_metadata_h5(raw_h5_path, spec_path, template_path, metadata_path)

    with h5py.File(metadata_path, "r") as f:
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0


def test_main_end_to_end(tmp_path, capsys):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_dir = tmp_path / "output"

    main([
        str(raw_h5_path),
        "--spec-fname", str(spec_path),
        "--output-folder", str(output_dir),
        "--template-fname", str(template_path),
        "--single-file",
    ])

    output_path = output_dir / "raw.h5"
    assert output_path.exists()
    with h5py.File(output_path, "r") as f:
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0

    captured = capsys.readouterr()
    assert "Wrote" in captured.out


def test_main_overwrites_existing_output_by_default(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "raw.h5").write_bytes(b"not a real h5 file")

    main([
        str(raw_h5_path),
        "--spec-fname", str(spec_path),
        "--output-folder", str(output_dir),
        "--template-fname", str(template_path),
        "--single-file",
    ])

    with h5py.File(output_dir / "raw.h5", "r") as f:
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0


def test_main_no_overwrite_raises_if_output_exists(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "raw.h5").write_bytes(b"not a real h5 file")

    with pytest.raises(FileExistsError):
        main([
            str(raw_h5_path),
            "--spec-fname", str(spec_path),
            "--output-folder", str(output_dir),
            "--template-fname", str(template_path),
            "--no-overwrite",
            "--single-file",
        ])


def test_main_end_to_end_auto_discovers_spec_file_when_not_given(tmp_path, capsys):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_dir = tmp_path / "output"

    main([
        str(raw_h5_path),
        "--output-folder", str(output_dir),
        "--template-fname", str(template_path),
        "--single-file",
    ])

    output_path = output_dir / "raw.h5"
    assert output_path.exists()
    with h5py.File(output_path, "r") as f:
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0


def test_build_split_output_creates_folder_with_raw_copy_and_metadata(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec", n_frames=3)

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_folder = tmp_path / "output"
    raw_copy_path, metadata_path = build_split_output(
        raw_h5_path, spec_path, template_path, output_folder
    )

    scan_folder = output_folder / "raw"
    assert raw_copy_path == scan_folder / "raw.h5"
    assert metadata_path == scan_folder / "raw_metadata.hdf"
    assert raw_copy_path.read_bytes() == raw_h5_path.read_bytes()

    with h5py.File(metadata_path, "r") as f:
        assert "data" not in f["entry"]
        assert "instrument_original" not in f["entry"]
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0


def test_build_split_output_no_overwrite_raises_if_raw_copy_exists(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)
    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")
    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_folder = tmp_path / "output"
    scan_folder = output_folder / "raw"
    scan_folder.mkdir(parents=True)
    (scan_folder / "raw.h5").write_bytes(b"")

    with pytest.raises(FileExistsError):
        build_split_output(raw_h5_path, spec_path, template_path, output_folder, overwrite=False)


def test_main_default_split_mode_creates_folder_and_two_files(tmp_path):
    spec_path = tmp_path / "test.spec"
    spec_path.write_text(SPEC_FIXTURE_TEXT)

    raw_h5_path = tmp_path / "raw.h5"
    make_raw_h5(raw_h5_path, scan_number=1, spec_name="test.spec")

    template_path = tmp_path / "sample_metadata.hdf"
    make_template_h5(template_path)

    output_dir = tmp_path / "output"

    main([
        str(raw_h5_path),
        "--spec-fname", str(spec_path),
        "--output-folder", str(output_dir),
        "--template-fname", str(template_path),
    ])

    scan_folder = output_dir / "raw"
    assert (scan_folder / "raw.h5").exists()
    assert (scan_folder / "raw_metadata.hdf").exists()
    with h5py.File(scan_folder / "raw_metadata.hdf", "r") as f:
        assert f["entry/instrument/detector_1/beam_center_x"][()] == 442.0


# --- Real production data (APS 28-ID) ---
#
# These exercise the pipeline against an actual detector HDF5/.spec pair and
# the packaged APS_28ID_XPCS_metadata_template.hdf, rather than the synthetic
# fixtures above. In particular they cover a gap the synthetic fixtures can't:
# the real detector data is bitshuffle-compressed (filter id 32008), while
# the synthetic fixture above uses plain gzip — so only real data can catch a
# regression that silently decompresses/re-encodes entry/data/data.

REAL_DATA_DIR = Path(__file__).parent / "data" / "aps28id_converter"
REAL_RAW_H5 = REAL_DATA_DIR / "PGRL351_LSMO_HZO_LSMO_5nm_Device_1em6Torr_041126_1_S001_00000.h5"
REAL_SPEC = REAL_DATA_DIR / "PGRL351_LSMO_HZO_LSMO_5nm_Device_1em6Torr_041126_1.spec"
REAL_TEMPLATE = (
    Path(__file__).parent.parent
    / "src" / "poweruser_xpcs" / "aps28id_converter" / "APS_28ID_XPCS_metadata_template.hdf"
)


def test_find_spec_file_locates_real_spec_next_to_real_raw_h5():
    assert find_spec_file(REAL_RAW_H5) == REAL_SPEC


def test_build_output_h5_preserves_compression_on_real_data(tmp_path):
    output_path = tmp_path / "merged.h5"
    build_output_h5(REAL_RAW_H5, REAL_SPEC, REAL_TEMPLATE, output_path)

    with h5py.File(REAL_RAW_H5, "r") as raw_f, h5py.File(output_path, "r") as out_f:
        raw_data = raw_f["entry/data/data"]
        out_data = out_f["entry/data/data"]
        assert out_data.shape == raw_data.shape
        assert out_data.chunks == raw_data.chunks

        raw_plist = raw_data.id.get_create_plist()
        out_plist = out_data.id.get_create_plist()
        assert raw_plist.get_nfilters() == 1
        assert out_plist.get_nfilters() == 1
        # bitshuffle (filter id 32008); a decompress/re-encode regression
        # would still pass a plain shape/value comparison, so check the raw
        # filter pipeline directly.
        assert out_plist.get_filter(0)[0] == raw_plist.get_filter(0)[0] == 32008


def test_build_output_h5_populates_real_metadata_fields(tmp_path):
    output_path = tmp_path / "merged.h5"
    build_output_h5(REAL_RAW_H5, REAL_SPEC, REAL_TEMPLATE, output_path)

    with h5py.File(output_path, "r") as f:
        assert f["entry/scan_number"][()] == 1
        assert f["entry/instrument/detector_1/beam_center_x"][()] == pytest.approx(442.0)
        assert f["entry/instrument/detector_1/beam_center_y"][()] == pytest.approx(291.0)
        assert f["entry/instrument/detector_1/beam_center_position_x"][()] == 0.0
        assert f["entry/instrument/detector_1/beam_center_position_y"][()] == 0.0
        assert f["entry/instrument/detector_1/x_pixel_size"][()] == pytest.approx(7.5e-5)
        assert f["entry/instrument/incident_beam/incident_energy"][()] == pytest.approx(
            8.86497478, rel=1e-6
        )
        energy = f["entry/instrument/incident_beam/incident_energy"][()]
        assert f["entry/instrument/monochromator/wavelength"][()] == pytest.approx(
            12.398419843320026 / energy
        )
        assert f["entry/instrument/bluesky/spec_file"][()].decode() == (
            "PGRL351_LSMO_HZO_LSMO_5nm_Device_1em6Torr_041126_1.spec"
        )
        flightpath_swing_vertical = f["entry/instrument/detector_1/flightpath_swing_vertical"][()]
        assert f["entry/instrument/detector_1/distance"][()] == pytest.approx(
            compute_detector_distance(flightpath_swing_vertical)
        )


def test_build_split_output_real_data_raw_copy_is_byte_identical(tmp_path):
    raw_copy_path, metadata_path = build_split_output(REAL_RAW_H5, REAL_SPEC, REAL_TEMPLATE, tmp_path)

    assert raw_copy_path.read_bytes() == REAL_RAW_H5.read_bytes()
    with h5py.File(metadata_path, "r") as f:
        assert "data" not in f["entry"]
        assert "instrument_original" not in f["entry"]
        assert f["entry/instrument/detector_1/beam_center_x"][()] == pytest.approx(442.0)
