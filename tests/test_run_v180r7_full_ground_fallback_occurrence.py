from pathlib import Path


def test_v180r7_entry_is_one_shot_and_local_only() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "run_v180r7_full_ground_fallback_occurrence.py"
    ).read_text(encoding="utf-8")
    assert 'SUCCESS.open("xb")' in source
    assert 'FAILURE.open("xb")' in source
    assert "already has progress or terminal" in source
    assert "git push" not in source
