from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import verify_v180r7r1_full_ground_fallback_occurrence as runner


def test_v180r7r1_verification_entry_is_one_shot_and_producer_free() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "verify_v180r7r1_full_ground_fallback_occurrence.py"
    ).read_text(encoding="utf-8")
    assert "freeze_full_ground_fallback_verification_v180r7r1" in source
    assert "production_terminal_finalizer" not in source
    assert "v180r7r1_full_ground_fallback_failure.json" in source
    assert "v180r7r1_full_ground_fallback_verification_failure.json" in source
    assert "v180r7r1_full_ground_fallback_verification.json" in source
    assert "os.path.lexists(VERIFICATION)" in source
    assert "_write_verification_failure(error, terminal_bytes)" in source
    assert "os.O_EXCL" in source
    assert "os.fsync(descriptor)" in source
    assert "_freeze_authorization_boundary()" in source
    assert "git push" not in source


def test_verification_runner_rejects_a_symlinked_terminal(tmp_path: Path) -> None:
    target = tmp_path / "terminal.json"
    target.write_bytes(b"{}")
    linked = tmp_path / "linked.json"
    try:
        linked.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are unavailable")
    with pytest.raises(RuntimeError, match="contains a symlink"):
        runner._read_symlink_free(linked)


def test_verification_runner_checks_authorization_before_retained_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def stop() -> None:
        raise RuntimeError("authorization first")

    monkeypatch.setattr(runner, "_freeze_authorization_boundary", stop)
    monkeypatch.setattr(
        runner.os.path,
        "lexists",
        lambda _path: pytest.fail("retained path checked before authorization"),
    )
    with pytest.raises(RuntimeError, match="authorization first"):
        runner.main()


def test_authorization_boundary_requires_outcome_free_locks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document = {
        "production_outcome_accessed": False,
        "fresh_production_occurrence_count": 0,
        "outcome_free": True,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    frozen = SimpleNamespace(
        authorization_evidence_id=(
            runner.authorization_evidence.EXPECTED_AUTHORIZATION_EVIDENCE_ID
        ),
        authorization_id=runner.authorization_evidence.EXPECTED_AUTHORIZATION_ID,
        to_document=lambda: document,
    )
    monkeypatch.setattr(
        runner.authorization_evidence,
        "freeze_full_ground_fallback_execution_authorization_evidence_v180r7r1",
        lambda: frozen,
    )
    runner._freeze_authorization_boundary()
    document["production_outcome_accessed"] = True
    with pytest.raises(RuntimeError, match="evidence boundary changed"):
        runner._freeze_authorization_boundary()
