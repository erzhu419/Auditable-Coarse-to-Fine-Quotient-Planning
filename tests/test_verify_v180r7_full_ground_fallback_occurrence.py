from pathlib import Path


def test_v180r7_verification_entry_is_one_shot_and_producer_free() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "verify_v180r7_full_ground_fallback_occurrence.py"
    ).read_text(encoding="utf-8")
    assert "freeze_full_ground_fallback_verification_v180r7" in source
    assert "production_terminal_finalizer" not in source
    assert "VERIFICATION.exists()" in source
    assert "os.O_EXCL" in source
    assert "git push" not in source
