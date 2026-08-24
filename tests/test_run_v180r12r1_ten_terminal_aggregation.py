from pathlib import Path


def test_v180r12r1_runner_is_one_shot_local_and_resource_bounded() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_v180r12r1_ten_terminal_aggregation.py"
    ).read_text(encoding="utf-8")
    assert "OUTPUT_ROOT.exists()" in source
    assert "os.O_EXCL" in source
    assert "resource.RLIMIT_AS" in source
    assert "verify_ten_terminal_aggregation_independently_v180r12r1" in source
    assert "git push" not in source
