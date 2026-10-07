from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_committed_validation_csv_uses_lf_only():
    data = (ROOT / "artifacts" / "test_results.csv").read_bytes()

    assert b"\r" not in data
    assert data.endswith(b"\n")
