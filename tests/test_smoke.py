import nima_persianguard as pg

def test_import_version_and_clean_validation():
    assert pg.__version__ == "1.1.0"
    report = pg.validate_layout([], width=300, height=200)
    assert report.ok
    assert report.checked == 0
    assert report.issues == []
