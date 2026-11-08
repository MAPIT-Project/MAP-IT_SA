from decimal import Decimal
import zipfile

import pytest

from app.services.cordis_import import parse_projects

HEADER = "id;title;objective;contentUpdateDate;totalCost;unrecognised\n"
ROW = "101000001;Example project;Research objective;2026-11-01T10:00:00Z;12.34;ignored\n"


def test_canonical_csv_uses_whitelisted_fields_and_exact_money(tmp_path):
    file = tmp_path / "project.csv"
    file.write_text(HEADER + ROW)
    row = parse_projects(file)[0]
    assert row["id"] == 101000001 and row["totalCost"] == Decimal("12.34")
    assert "unrecognised" not in row
    assert row["contentUpdateDate"].year == 2026


def test_duplicate_project_export_is_rejected_before_any_write(tmp_path):
    file = tmp_path / "projects.csv"
    file.write_text(HEADER + ROW + ROW)
    with pytest.raises(ValueError, match="Duplicate"):
        parse_projects(file)


def test_different_export_schema_is_not_silently_imported(tmp_path):
    file = tmp_path / "projects.csv"
    file.write_text("Project ID;Project name\n1;Example\n")
    with pytest.raises(ValueError, match="must contain"):
        parse_projects(file)


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1"])
def test_invalid_financial_values_reject_whole_export(tmp_path, value):
    file = tmp_path / "projects.csv"
    file.write_text(HEADER + ROW.replace("12.34", value))
    with pytest.raises(ValueError, match="monetary"):
        parse_projects(file)


def test_project_csv_can_be_read_without_extracting_zip_paths(tmp_path):
    file = tmp_path / "export.zip"
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("nested/project.csv", HEADER + ROW)
    assert len(parse_projects(file)) == 1
    assert not (tmp_path / "nested").exists()


def test_duplicate_csv_headers_are_not_silently_trusted(tmp_path):
    file = tmp_path / "project.csv"
    file.write_text("id;id;title;objective;contentUpdateDate\n1;2;Title;Objective;2026-11-01\n")
    with pytest.raises(ValueError, match="Duplicate CSV column"):
        parse_projects(file)


def test_live_det_outer_archive_with_nested_csv_zip(tmp_path):
    import io
    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("project.csv", HEADER + ROW)
    file = tmp_path / "det.zip"
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr("csv.zip", nested.getvalue())
        archive.writestr("documentation.zip", b"unused")
    assert parse_projects(file)[0]["id"] == 101000001
    assert not (tmp_path / "csv.zip").exists()
