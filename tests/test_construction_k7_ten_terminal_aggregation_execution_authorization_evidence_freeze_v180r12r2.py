import inspect
import os
from pathlib import Path
import subprocess

import pytest

from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_evidence_freeze_v180r12r2
    as evidence,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_execution_authorization_v180r12r2
    as authorization,
)
from acfqp import (
    construction_k7_ten_terminal_aggregation_protocol_v180r12r2 as protocol,
)


def _wrapper_raw() -> bytes:
    return Path(evidence.__file__).read_bytes()


def _replace_redacted_literals(raw: bytes) -> bytes:
    result = raw
    spans = evidence._local_literal_spans(raw)  # noqa: SLF001
    for name, (start, end, _canonical) in sorted(
        spans.items(),
        key=lambda item: item[1][0],
        reverse=True,
    ):
        replacement = (
            b'"1111111111111111111111111111111111111111111111111111111111111111"'
            if name in evidence._STRING_REDACTED_CONSTANTS  # noqa: SLF001
            else b"123456"
        )
        result = result[:start] + replacement + result[end:]
    return result


def _zero_redacted_literals(raw: bytes) -> bytes:
    result = raw
    spans = evidence._local_literal_spans(raw)  # noqa: SLF001
    for name, (start, end, _canonical) in sorted(
        spans.items(),
        key=lambda item: item[1][0],
        reverse=True,
    ):
        replacement = (
            b'"0000000000000000000000000000000000000000000000000000000000000000"'
            if name in evidence._STRING_REDACTED_CONSTANTS  # noqa: SLF001
            else b"0"
        )
        result = result[:start] + replacement + result[end:]
    return result


def _git(repository_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        (evidence.GIT_EXECUTABLE, "-C", str(repository_root), *arguments),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=evidence._git_environment(),  # noqa: SLF001
    )
    return completed.stdout.strip()


def _initialize_git_repository(repository_root: Path) -> None:
    repository_root.mkdir(parents=True)
    _git(repository_root, "init", "--initial-branch=main")
    _git(repository_root, "config", "user.name", "V180r12r2 Test")
    _git(repository_root, "config", "user.email", "v180r12r2@example.invalid")


def test_v180r12r2_authorization_evidence_stays_closed_until_prereg_freeze() -> None:
    build_signature = inspect.signature(
        evidence.build_ten_terminal_aggregation_authorization_evidence_v180r12r2
    )
    candidate_parameter = build_signature.parameters["candidate_only"]
    assert candidate_parameter.default is inspect.Parameter.empty
    assert candidate_parameter.kind is inspect.Parameter.KEYWORD_ONLY
    signature = inspect.signature(
        evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2
    )
    parameter = signature.parameters["source_boundary_commit"]
    assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2()

    if evidence.EXPECTED_AUTHORIZATION_EVIDENCE_ID != "0" * 64:
        source_boundary_commit = os.environ["ACFQP_V180R12R2_PREREG_COMMIT"]
        frozen = (
            evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2(
                source_boundary_commit
            )
        )
        document = frozen.to_document()
        assert document["authorization_self_source_bound_by_this_evidence"] is True
        assert document[
            "authorization_evidence_verification_required_as_first_action_inside_"
            "runner_main_after_prelaunch_dispatch"
        ] is True
        assert document[
            "authorization_evidence_verification_required_before_scientific_"
            "output_inspection_or_creation_inside_runner"
        ] is True
        assert document[
            "authorization_evidence_verification_is_process_first_action"
        ] is False
        assert document["prelaunch_contract"] == (
            protocol.prelaunch_contract_v180r12r2()
        )
        assert document["v180r12r2_outcome_bytes_accessed"] is False
        assert document["official_execution_allowed"] is False
    else:
        evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2.cache_clear()
        with pytest.raises(
            evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
            match="authorization evidence is not frozen",
        ):
            evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2(
                "0" * 40
            )


def test_v180r12r2_authorization_has_one_exclusion_and_binds_wrapper_normalized() -> None:
    assert evidence.SOURCE_FACT_EXCLUSIONS == (
        "src/acfqp/construction_k7_ten_terminal_aggregation_execution_"
        "authorization_v180r12r2.py",
    )
    assert authorization._SOURCE_FACT_EXCLUSIONS == evidence.SOURCE_FACT_EXCLUSIONS  # noqa: SLF001
    assert authorization._AUTHORIZATION_EVIDENCE_RELATIVE_PATH not in (  # noqa: SLF001
        authorization._SOURCE_FACT_EXCLUSIONS  # noqa: SLF001
    )
    facts = {
        row["relative_path"]: row
        for row in authorization._source_facts()  # noqa: SLF001
    }
    assert facts[authorization._AUTHORIZATION_EVIDENCE_RELATIVE_PATH] == (  # noqa: SLF001
        evidence._normalized_evidence_source_fact()  # noqa: SLF001
    )
    assert len(evidence.EXECUTION_CHAIN_RELATIVE_PATHS) == 8
    assert "scripts/bootstrap_v180r12r2_ten_terminal_aggregation.py" in (
        evidence.EXECUTION_CHAIN_RELATIVE_PATHS
    )
    assert (
        "scripts/launch_v180r12r2_ten_terminal_aggregation_prelaunch.py"
        in evidence.EXECUTION_CHAIN_RELATIVE_PATHS
    )
    assert (
        "scripts/materialize_v180r12r2_ten_terminal_aggregation_prelaunch.py"
        in evidence.EXECUTION_CHAIN_RELATIVE_PATHS
    )


def test_v180r12r2_auth_and_wrapper_normalizers_are_independent_and_equal() -> None:
    raw = _wrapper_raw()
    auth_normalized = (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r2(
            raw
        )
    )
    wrapper_normalized = evidence.normalize_own_source_v180r12r2(raw)
    assert auth_normalized == wrapper_normalized
    assert auth_normalized != raw
    assert tuple(evidence.POST_PREREG_REDACTED_CONSTANTS) == tuple(
        authorization.AUTHORIZATION_EVIDENCE_POST_PREREG_REDACTED_CONSTANTS
    )


def test_v180r12r2_only_allowlisted_literal_values_are_redacted() -> None:
    raw = _wrapper_raw()
    changed_literals = _replace_redacted_literals(raw)
    expected = evidence.normalize_own_source_v180r12r2(raw)
    assert evidence.normalize_own_source_v180r12r2(changed_literals) == expected
    assert (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r2(
            changed_literals
        )
        == expected
    )

    changed_logic = raw.replace(
        b"No V180r12r2 outcome is read",
        b"No V180r12r2 outcome byte is read",
        1,
    )
    assert changed_logic != raw
    assert evidence.normalize_own_source_v180r12r2(changed_logic) != expected
    assert (
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r2(
            changed_logic
        )
        != expected
    )


def test_v180r12r2_redaction_rejects_expression_and_duplicate_anchor() -> None:
    raw = _wrapper_raw()
    spans = evidence._local_literal_spans(raw)  # noqa: SLF001
    start, end, _replacement = spans["EXPECTED_AUTHORIZATION_ID"]
    expression = raw[:start] + b'"0" * 64' + raw[end:]
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="string anchor is not a literal",
    ):
        evidence.normalize_own_source_v180r12r2(expression)
    with pytest.raises(
        authorization.TenTerminalAggregationExecutionAuthorizationV180R12R2Error,
        match="string anchor is not a literal",
    ):
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r2(
            expression
        )

    duplicate = raw + (
        b'\nEXPECTED_AUTHORIZATION_ID = "22222222222222222222222222222222'
        b'22222222222222222222222222222222"\n'
    )
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="duplicated",
    ):
        evidence.normalize_own_source_v180r12r2(duplicate)


def test_v180r12r2_redaction_rejects_adjacent_string_literal_escape() -> None:
    raw = _wrapper_raw()
    spans = evidence._local_literal_spans(raw)  # noqa: SLF001
    start, end, _replacement = spans["EXPECTED_AUTHORIZATION_ID"]
    adjacent = raw[:start] + (b'"' + b"0" * 32 + b'" "' + b"0" * 32 + b'"') + raw[end:]
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="exactly one lexical literal token",
    ):
        evidence.normalize_own_source_v180r12r2(adjacent)
    with pytest.raises(
        authorization.TenTerminalAggregationExecutionAuthorizationV180R12R2Error,
        match="exactly one lexical literal token",
    ):
        authorization.normalize_authorization_evidence_wrapper_source_v180r12r2(
            adjacent
        )


def test_v180r12r2_git_boundary_blocks_coordinated_nonallowlisted_resign() -> None:
    boundary_wrapper = _zero_redacted_literals(_wrapper_raw())
    current_wrapper = _replace_redacted_literals(boundary_wrapper)
    ordinary_path = "scripts/run_v180r12r2_ten_terminal_aggregation.py"
    ordinary_raw = b"preregistered ordinary source\n"
    authorization_raw = b"preregistered authorization source\n"
    normalized = evidence.normalize_own_source_v180r12r2(boundary_wrapper)
    wrapper_fact = {
        "relative_path": evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
        "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
        "byte_count": len(normalized),
        "sha256": evidence._sha256(normalized),  # noqa: SLF001
        "redacted_constant_names": list(evidence.POST_PREREG_REDACTED_CONSTANTS),
    }
    ordinary_fact = evidence._fact_from_raw(ordinary_path, ordinary_raw)  # noqa: SLF001
    authorization_fact = evidence._fact_from_raw(  # noqa: SLF001
        evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
        authorization_raw,
    )
    bound = {
        evidence._EVIDENCE_RELATIVE_PATH: wrapper_fact,  # noqa: SLF001
        ordinary_path: ordinary_fact,
    }
    boundary = {
        evidence._EVIDENCE_RELATIVE_PATH: boundary_wrapper,  # noqa: SLF001
        ordinary_path: ordinary_raw,
        evidence._AUTHORIZATION_RELATIVE_PATH: authorization_raw,  # noqa: SLF001
    }
    current = {
        **boundary,
        evidence._EVIDENCE_RELATIVE_PATH: current_wrapper,  # noqa: SLF001
    }
    replayed = evidence._verify_source_boundary_blobs(  # noqa: SLF001
        boundary,
        current,
        bound,
        authorization_fact,
    )
    assert replayed == (ordinary_fact, wrapper_fact)

    # Reproduce the old self-signing bypass exactly: wrapper normalization is
    # unchanged (only its eight literals differ), while current auth source and
    # the dynamically re-signed expected fact move together from A to B.  The
    # immutable C_pre auth blob must still reject it.
    resigned_authorization = b"coordinated re-signed authorization source\n"
    resigned_current = {
        **current,
        evidence._AUTHORIZATION_RELATIVE_PATH: resigned_authorization,  # noqa: SLF001
    }
    resigned_authorization_fact = evidence._fact_from_raw(  # noqa: SLF001
        evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
        resigned_authorization,
    )
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="authorization source differs from frozen bytes",
    ):
        evidence._verify_source_boundary_blobs(  # noqa: SLF001
            boundary,
            resigned_current,
            bound,
            resigned_authorization_fact,
        )

    resigned_ordinary = b"coordinated re-signed ordinary source\n"
    resigned_ordinary_current = {**current, ordinary_path: resigned_ordinary}
    resigned_ordinary_bound = {
        **bound,
        ordinary_path: evidence._fact_from_raw(  # noqa: SLF001
            ordinary_path,
            resigned_ordinary,
        ),
    }
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="ordinary source differs from current bytes",
    ):
        evidence._verify_source_boundary_blobs(  # noqa: SLF001
            boundary,
            resigned_ordinary_current,
            resigned_ordinary_bound,
            authorization_fact,
        )

    attacked_wrapper = current_wrapper.replace(
        b"Cycle-safe post-prereg evidence",
        b"Coordinated post-prereg evidence",
        1,
    )
    assert attacked_wrapper != current_wrapper
    attacked_authorization = b"coordinated re-signed authorization source\n"
    attacked_normalized = evidence.normalize_own_source_v180r12r2(
        attacked_wrapper
    )
    attacked_bound = {
        **bound,
        evidence._EVIDENCE_RELATIVE_PATH: {
            **wrapper_fact,
            "byte_count": len(attacked_normalized),
            "sha256": evidence._sha256(attacked_normalized),  # noqa: SLF001
        },
    }
    attacked_current = {
        **current,
        evidence._EVIDENCE_RELATIVE_PATH: attacked_wrapper,  # noqa: SLF001
        evidence._AUTHORIZATION_RELATIVE_PATH: attacked_authorization,  # noqa: SLF001
    }
    attacked_authorization_fact = evidence._fact_from_raw(  # noqa: SLF001
        evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
        attacked_authorization,
    )
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="wrapper changed outside eight literals",
    ):
        evidence._verify_source_boundary_blobs(  # noqa: SLF001
            boundary,
            attacked_current,
            attacked_bound,
            attacked_authorization_fact,
        )


def test_v180r12r2_git_boundary_rejects_nonzero_boundary_sentinels() -> None:
    boundary_wrapper = _replace_redacted_literals(
        _zero_redacted_literals(_wrapper_raw())
    )
    normalized = evidence.normalize_own_source_v180r12r2(boundary_wrapper)
    bound = {
        evidence._EVIDENCE_RELATIVE_PATH: {  # noqa: SLF001
            "relative_path": evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
            "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
            "byte_count": len(normalized),
            "sha256": evidence._sha256(normalized),  # noqa: SLF001
            "redacted_constant_names": list(
                evidence.POST_PREREG_REDACTED_CONSTANTS
            ),
        }
    }
    authorization_raw = b"authorization\n"
    blobs = {
        evidence._EVIDENCE_RELATIVE_PATH: boundary_wrapper,  # noqa: SLF001
        evidence._AUTHORIZATION_RELATIVE_PATH: authorization_raw,  # noqa: SLF001
    }
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="did not retain all eight sentinels",
    ):
        evidence._verify_source_boundary_blobs(  # noqa: SLF001
            blobs,
            blobs,
            bound,
            evidence._fact_from_raw(  # noqa: SLF001
                evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
                authorization_raw,
            ),
        )


def test_v180r12r2_real_git_empty_bridge_supports_literal_freeze_sequence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "legal-sequence"
    _initialize_git_repository(repository)
    wrapper_path = repository / evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    authorization_path = repository / evidence._AUTHORIZATION_RELATIVE_PATH  # noqa: SLF001
    wrapper_path.parent.mkdir(parents=True)
    boundary_wrapper = _zero_redacted_literals(_wrapper_raw())
    authorization_raw = b"frozen authorization source\n"
    wrapper_path.write_bytes(boundary_wrapper)
    authorization_path.write_bytes(authorization_raw)
    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "add", "--", evidence._AUTHORIZATION_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "C_pre")
    source_boundary_commit = _git(repository, "rev-parse", "HEAD^{commit}")
    source_boundary_tree = _git(repository, "rev-parse", "HEAD^{tree}")

    paths = tuple(
        sorted(
            (
                evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
                evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
            )
        )
    )
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="root, commit, tree, or HEAD changed",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=True,
        )

    _git(repository, "commit", "--allow-empty", "-m", "empty bridge")
    bridge_commit = _git(repository, "rev-parse", "HEAD^{commit}")
    assert _git(repository, "rev-parse", "HEAD^{tree}") == source_boundary_tree

    current_wrapper = _replace_redacted_literals(boundary_wrapper)
    wrapper_path.write_bytes(current_wrapper)
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="runtime freeze requires the committed wrapper literal successor",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=False,
        )
    tree, replayed_bridge, boundary_blobs, candidate_committed_wrapper = (
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=True,
        )
    )
    assert tree == source_boundary_tree
    assert replayed_bridge == bridge_commit
    assert candidate_committed_wrapper == boundary_wrapper
    normalized = evidence.normalize_own_source_v180r12r2(boundary_wrapper)
    bound_facts = {
        evidence._EVIDENCE_RELATIVE_PATH: {  # noqa: SLF001
            "relative_path": evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
            "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
            "byte_count": len(normalized),
            "sha256": evidence._sha256(normalized),  # noqa: SLF001
            "redacted_constant_names": list(
                evidence.POST_PREREG_REDACTED_CONSTANTS
            ),
        }
    }
    current_blobs = {
        evidence._AUTHORIZATION_RELATIVE_PATH: authorization_path.read_bytes(),  # noqa: SLF001
        evidence._EVIDENCE_RELATIVE_PATH: wrapper_path.read_bytes(),  # noqa: SLF001
    }
    authorization_fact = evidence._fact_from_raw(  # noqa: SLF001
        evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
        authorization_raw,
    )
    evidence._verify_source_boundary_blobs(  # noqa: SLF001
        boundary_blobs,
        current_blobs,
        bound_facts,
        authorization_fact,
    )

    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    assert _git(repository, "diff", "--cached", "--name-only") == (
        evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    )
    _git(repository, "commit", "-m", "freeze exactly eight literals")
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="candidate build is allowed only at the empty bridge HEAD",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=True,
        )
    git_labels: list[str] = []
    original_run_git = evidence._run_git  # noqa: SLF001

    def counted_run_git(*args, **kwargs):
        git_labels.append(args[1])
        return original_run_git(*args, **kwargs)

    monkeypatch.setattr(evidence, "_run_git", counted_run_git)
    tree_after, bridge_after, boundary_after, committed_wrapper_after = (
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=False,
        )
    )
    assert git_labels == [
        "root-and-revision",
        "bridge-chain",
        "literal-commit-diff",
        "post-literal-bound-history",
        "archive",
        "committed-wrapper-blob",
    ]
    assert len(git_labels) == evidence.SOURCE_BOUNDARY_GIT_PROCESS_COUNT
    monkeypatch.setattr(evidence, "_run_git", original_run_git)
    assert (tree_after, bridge_after, boundary_after, committed_wrapper_after) == (
        source_boundary_tree,
        bridge_commit,
        boundary_blobs,
        current_wrapper,
    )
    evidence._verify_source_boundary_blobs(  # noqa: SLF001
        boundary_after,
        {
            evidence._AUTHORIZATION_RELATIVE_PATH: authorization_path.read_bytes(),  # noqa: SLF001
            evidence._EVIDENCE_RELATIVE_PATH: wrapper_path.read_bytes(),  # noqa: SLF001
        },
        bound_facts,
        authorization_fact,
    )
    unbound = repository / "notes.txt"
    unbound.write_text("later unbound history is allowed\n", encoding="utf-8")
    _git(repository, "add", "--", "notes.txt")
    _git(repository, "commit", "-m", "unbound descendant")
    assert evidence._git_source_boundary_blobs(  # noqa: SLF001
        source_boundary_commit,
        paths,
        repository,
        candidate_only=False,
    )[1] == bridge_commit

    frozen_wrapper = wrapper_path.read_bytes()
    touched_wrapper = frozen_wrapper.replace(
        b"Cycle-safe post-prereg evidence",
        b"Touched post-prereg evidence",
        1,
    )
    assert touched_wrapper != frozen_wrapper
    wrapper_path.write_bytes(touched_wrapper)
    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "touch bound wrapper")
    wrapper_path.write_bytes(frozen_wrapper)
    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "revert bound wrapper")
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="history touched a bound source after literal freeze",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=False,
        )
    assert evidence.SOURCE_BOUNDARY_GIT_PROCESS_COUNT == 6


def test_v180r12r2_runtime_rejects_literal_commit_hidden_by_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "malicious-literal-overlay"
    _initialize_git_repository(repository)
    wrapper_path = repository / evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    authorization_path = repository / evidence._AUTHORIZATION_RELATIVE_PATH  # noqa: SLF001
    wrapper_path.parent.mkdir(parents=True)
    boundary_wrapper = _zero_redacted_literals(_wrapper_raw())
    expected_wrapper = _replace_redacted_literals(boundary_wrapper)
    malicious_wrapper = expected_wrapper.replace(b"1" * 64, b"2" * 64, 1)
    assert evidence.normalize_own_source_v180r12r2(malicious_wrapper) == (
        evidence.normalize_own_source_v180r12r2(expected_wrapper)
    )
    wrapper_path.write_bytes(boundary_wrapper)
    authorization_path.write_bytes(b"frozen authorization source\n")
    paths = tuple(
        sorted(
            (
                evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
                evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
            )
        )
    )
    _git(repository, "add", "--", *paths)
    _git(repository, "commit", "-m", "C_pre")
    source_boundary_commit = _git(repository, "rev-parse", "HEAD^{commit}")
    _git(repository, "commit", "--allow-empty", "-m", "empty bridge")
    wrapper_path.write_bytes(malicious_wrapper)
    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "malicious literal commit")

    # A clean-looking working-tree overlay must not hide the bytes actually
    # committed by the literal-freeze commit.
    wrapper_path.write_bytes(expected_wrapper)
    monkeypatch.setattr(evidence, "_ROOT", repository)
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="current wrapper bytes differ from the literal commit",
    ):
        evidence._replay_git_source_boundary(  # noqa: SLF001
            source_boundary_commit,
            {
                evidence._EVIDENCE_RELATIVE_PATH: {  # noqa: SLF001
                    "relative_path": evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
                    "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
                    "byte_count": len(
                        evidence.normalize_own_source_v180r12r2(boundary_wrapper)
                    ),
                    "sha256": evidence._sha256(  # noqa: SLF001
                        evidence.normalize_own_source_v180r12r2(boundary_wrapper)
                    ),
                    "redacted_constant_names": list(
                        evidence.POST_PREREG_REDACTED_CONSTANTS
                    ),
                }
            },
            evidence._fact_from_raw(  # noqa: SLF001
                evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
                authorization_path.read_bytes(),
            ),
            candidate_only=False,
        )


def test_v180r12r2_runtime_rejects_nonregular_literal_wrapper_mode(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "executable-literal-wrapper"
    _initialize_git_repository(repository)
    wrapper_path = repository / evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    authorization_path = repository / evidence._AUTHORIZATION_RELATIVE_PATH  # noqa: SLF001
    wrapper_path.parent.mkdir(parents=True)
    boundary_wrapper = _zero_redacted_literals(_wrapper_raw())
    wrapper_path.write_bytes(boundary_wrapper)
    authorization_path.write_bytes(b"frozen authorization source\n")
    paths = tuple(
        sorted(
            (
                evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
                evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
            )
        )
    )
    _git(repository, "add", "--", *paths)
    _git(repository, "commit", "-m", "C_pre")
    source_boundary_commit = _git(repository, "rev-parse", "HEAD^{commit}")
    _git(repository, "commit", "--allow-empty", "-m", "empty bridge")
    wrapper_path.write_bytes(_replace_redacted_literals(boundary_wrapper))
    wrapper_path.chmod(0o755)
    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "executable literal wrapper")

    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="literal commit must modify only the regular wrapper",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=False,
        )


def test_v180r12r2_public_candidate_build_is_relaxed_but_freeze_is_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "public-build-freeze-sequence"
    _initialize_git_repository(repository)
    wrapper_path = repository / evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    authorization_path = repository / evidence._AUTHORIZATION_RELATIVE_PATH  # noqa: SLF001
    wrapper_path.parent.mkdir(parents=True)
    boundary_wrapper = _zero_redacted_literals(_wrapper_raw())
    authorization_raw = b"frozen public authorization source\n"
    wrapper_path.write_bytes(boundary_wrapper)
    authorization_path.write_bytes(authorization_raw)
    for index, relative_path in enumerate(
        evidence.EXECUTION_CHAIN_RELATIVE_PATHS,
        start=1,
    ):
        path = repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"frozen execution source {index}\n".encode("ascii"))
    source_paths = tuple(
        sorted(
            (
                evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
                evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
                *evidence.EXECUTION_CHAIN_RELATIVE_PATHS,
            )
        )
    )
    _git(repository, "add", "--", *source_paths)
    _git(repository, "commit", "-m", "C_pre")
    source_boundary_commit = _git(repository, "rev-parse", "HEAD^{commit}")
    _git(repository, "commit", "--allow-empty", "-m", "empty bridge")
    wrapper_path.write_bytes(_replace_redacted_literals(boundary_wrapper))

    normalized = evidence.normalize_own_source_v180r12r2(boundary_wrapper)
    source_facts = []
    for relative_path in sorted(
        (evidence._EVIDENCE_RELATIVE_PATH, *evidence.EXECUTION_CHAIN_RELATIVE_PATHS)  # noqa: SLF001
    ):
        if relative_path == evidence._EVIDENCE_RELATIVE_PATH:  # noqa: SLF001
            fact = {
                "relative_path": relative_path,
                "binding_kind": "POST_PREREG_LITERAL_REDACTED_SOURCE_V1",
                "byte_count": len(normalized),
                "sha256": evidence._sha256(normalized),  # noqa: SLF001
                "redacted_constant_names": list(
                    evidence.POST_PREREG_REDACTED_CONSTANTS
                ),
            }
        else:
            fact = evidence._fact_from_raw(  # noqa: SLF001
                relative_path,
                (repository / relative_path).read_bytes(),
            )
        source_facts.append(fact)

    protocol_id = "a" * 64
    authorization_id = "b" * 64
    slot_id = evidence.EXPECTED_AGGREGATION_EXECUTION_SLOT_ID
    authorization_canonical = evidence.canonical_json_bytes(
        {"fixture": "frozen authorization"}
    )
    authorization_document = {
        "aggregation_protocol_id": protocol_id,
        "aggregation_execution_slot": {
            "aggregation_execution_slot_id": slot_id,
        },
        "source_fact_exclusions": list(evidence.SOURCE_FACT_EXCLUSIONS),
        "authorization_self_source_bound_by_post_prereg_freeze": False,
        "authorization_evidence_wrapper_source_bound_in_authorization_closure": True,
        "authorization_evidence_wrapper_binding_kind": (
            "POST_PREREG_LITERAL_REDACTED_SOURCE_V1"
        ),
        "authorization_evidence_wrapper_redacted_constant_names": list(
            evidence.POST_PREREG_REDACTED_CONSTANTS
        ),
        "authorization_evidence_wrapper_self_source_excluded": False,
        "authorization_evidence_source_boundary_commit_required": True,
        "authorization_evidence_empty_bridge_commit_required": True,
        "authorization_evidence_empty_bridge_must_preserve_entire_tree": True,
        "authorization_evidence_bridge_then_wrapper_eight_literal_commit_sequence_required": True,
        "authorization_evidence_candidate_build_may_relax_only_literal_commit_presence": True,
        "authorization_evidence_runtime_freeze_requires_committed_wrapper_literals": True,
        "authorization_evidence_candidate_and_runtime_payload_identity_must_match": True,
        "authorization_evidence_post_literal_bound_history_touch_forbidden": True,
        "authorization_evidence_source_boundary_git_process_count": (
            evidence.SOURCE_BOUNDARY_GIT_PROCESS_COUNT
        ),
        "authorization_evidence_source_boundary_git_processes_are_preauthorization_not_campaign_actual_measurements": True,
        "prelaunch_contract": protocol.prelaunch_contract_v180r12r2(),
        "authorization_evidence_verification_is_first_action_inside_runner_main_after_prelaunch_dispatch": True,
        "authorization_evidence_verification_precedes_scientific_output_inspection_or_creation_inside_runner": True,
        "authorization_evidence_verification_is_process_first_action": False,
        "self_identity_cycle_avoided": True,
        "source_fact_file_count": len(source_facts),
        "source_fact_byte_count": sum(row["byte_count"] for row in source_facts),
        "source_facts_sha256": evidence._sha256(  # noqa: SLF001
            evidence.canonical_json_bytes(source_facts)
        ),
        "v180r12r2_outcome_bytes_accessed": False,
        "official_execution_allowed": False,
    }

    class FrozenAuthorization:
        def to_document(self) -> dict[str, object]:
            return authorization_document

    frozen_authorization = FrozenAuthorization()
    frozen_authorization.canonical_bytes = authorization_canonical
    frozen_authorization.authorization_id = authorization_id

    monkeypatch.setattr(evidence, "_ROOT", repository)
    monkeypatch.setattr(evidence, "EXPECTED_PROTOCOL_ID", protocol_id)
    monkeypatch.setattr(evidence.protocol, "EXPECTED_PROTOCOL_ID", protocol_id)
    monkeypatch.setattr(evidence, "EXPECTED_AUTHORIZATION_ID", authorization_id)
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        len(authorization_canonical),
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        evidence._sha256(authorization_canonical),  # noqa: SLF001
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT",
        len(authorization_raw),
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
        evidence._sha256(authorization_raw),  # noqa: SLF001
    )
    monkeypatch.setattr(evidence.authorization, "EXPECTED_AUTHORIZATION_ID", authorization_id)
    monkeypatch.setattr(
        evidence.authorization,
        "EXPECTED_CANONICAL_BYTE_COUNT",
        len(authorization_canonical),
    )
    monkeypatch.setattr(
        evidence.authorization,
        "EXPECTED_CANONICAL_SHA256",
        evidence._sha256(authorization_canonical),  # noqa: SLF001
    )
    monkeypatch.setattr(
        evidence.authorization,
        "freeze_ten_terminal_aggregation_execution_authorization_v180r12r2",
        lambda: frozen_authorization,
    )
    monkeypatch.setattr(
        evidence.authorization,
        "replay_authorization_source_facts_v180r12r2",
        lambda _document: tuple(source_facts),
    )

    candidate = (
        evidence.build_ten_terminal_aggregation_authorization_evidence_v180r12r2(
            source_boundary_commit,
            candidate_only=True,
        )
    )
    candidate_raw = evidence.canonical_json_bytes(candidate)
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_EVIDENCE_ID",
        candidate["authorization_evidence_id"],
    )
    monkeypatch.setattr(evidence, "EXPECTED_CANONICAL_BYTE_COUNT", len(candidate_raw))
    monkeypatch.setattr(
        evidence,
        "EXPECTED_CANONICAL_SHA256",
        evidence._sha256(candidate_raw),  # noqa: SLF001
    )
    evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2.cache_clear()
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="runtime freeze requires the committed wrapper literal successor",
    ):
        evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2(
            source_boundary_commit
        )

    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "freeze exactly eight literals")
    evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2.cache_clear()
    frozen = (
        evidence.freeze_ten_terminal_aggregation_authorization_evidence_v180r12r2(
            source_boundary_commit
        )
    )
    assert frozen.canonical_bytes == candidate_raw
    assert frozen.authorization_evidence_id == candidate["authorization_evidence_id"]


def test_v180r12r2_git_boundary_rejects_symbolic_or_unknown_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="explicit lowercase commit ID",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            "HEAD",
            (evidence._EVIDENCE_RELATIVE_PATH,),  # noqa: SLF001
            candidate_only=False,
        )
    foreign = tmp_path / "not-a-repository"
    foreign.mkdir()
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="root-and-revision rejected",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            "1" * 40,
            (evidence._EVIDENCE_RELATIVE_PATH,),  # noqa: SLF001
            foreign,
            candidate_only=False,
        )


def test_v180r12r2_git_boundary_rejects_current_head_and_unknown_commit() -> None:
    head = evidence._run_git(  # noqa: SLF001
        ("rev-parse", "HEAD^{commit}"),
        "test-head",
    ).decode("ascii").strip()
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="root, commit, tree, or HEAD changed",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            head,
            (evidence._EVIDENCE_RELATIVE_PATH,),  # noqa: SLF001
            candidate_only=False,
        )
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="root-and-revision rejected",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            "f" * 40,
            (evidence._EVIDENCE_RELATIVE_PATH,),  # noqa: SLF001
            candidate_only=False,
        )


def test_v180r12r2_git_boundary_rejects_nonempty_bridge_and_nonancestor(
    tmp_path: Path,
) -> None:
    nonempty = tmp_path / "nonempty-bridge"
    _initialize_git_repository(nonempty)
    probe = nonempty / "src/acfqp/probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text("before = 1\n", encoding="utf-8")
    _git(nonempty, "add", "--", "src/acfqp/probe.py")
    _git(nonempty, "commit", "-m", "C_pre")
    boundary = _git(nonempty, "rev-parse", "HEAD^{commit}")
    probe.write_text("after = 2\n", encoding="utf-8")
    _git(nonempty, "add", "--", "src/acfqp/probe.py")
    _git(nonempty, "commit", "-m", "nonempty bridge")
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="empty bridge commit or tree changed",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            boundary,
            ("src/acfqp/probe.py",),
            nonempty,
            candidate_only=False,
        )

    alternative = tmp_path / "nonancestor"
    _initialize_git_repository(alternative)
    probe = alternative / "src/acfqp/probe.py"
    probe.parent.mkdir(parents=True)
    probe.write_text("root = 1\n", encoding="utf-8")
    _git(alternative, "add", "--", "src/acfqp/probe.py")
    _git(alternative, "commit", "-m", "root")
    _git(alternative, "checkout", "-b", "alternative")
    _git(alternative, "commit", "--allow-empty", "-m", "alternative boundary")
    alternative_boundary = _git(alternative, "rev-parse", "HEAD^{commit}")
    _git(alternative, "checkout", "main")
    _git(alternative, "commit", "--allow-empty", "-m", "main head")
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="first-parent bridge chain changed",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            alternative_boundary,
            ("src/acfqp/probe.py",),
            alternative,
            candidate_only=False,
        )


@pytest.mark.parametrize(
    ("relative_path", "content"),
    (
        ("info/grafts", b"0" * 40 + b" " + b"1" * 40 + b"\n"),
        ("shallow", b"0" * 40 + b"\n"),
        ("objects/info/alternates", b"/tmp/foreign-objects\n"),
        ("refs/replace/placeholder", b"0" * 40 + b"\n"),
        ("packed-refs", b"0" * 40 + b" refs/replace/placeholder\n"),
    ),
)
def test_v180r12r2_git_boundary_rejects_history_overlays(
    tmp_path: Path,
    relative_path: str,
    content: bytes,
) -> None:
    repository = tmp_path / "history-overlay"
    _initialize_git_repository(repository)
    wrapper_path = repository / evidence._EVIDENCE_RELATIVE_PATH  # noqa: SLF001
    authorization_path = repository / evidence._AUTHORIZATION_RELATIVE_PATH  # noqa: SLF001
    wrapper_path.parent.mkdir(parents=True)
    wrapper_path.write_bytes(_zero_redacted_literals(_wrapper_raw()))
    authorization_path.write_bytes(b"frozen authorization source\n")
    _git(repository, "add", "--", evidence._EVIDENCE_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "add", "--", evidence._AUTHORIZATION_RELATIVE_PATH)  # noqa: SLF001
    _git(repository, "commit", "-m", "C_pre")
    source_boundary_commit = _git(repository, "rev-parse", "HEAD^{commit}")
    _git(repository, "commit", "--allow-empty", "-m", "empty bridge")

    overlay = repository / ".git" / relative_path
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_bytes(content)
    paths = tuple(
        sorted(
            (
                evidence._AUTHORIZATION_RELATIVE_PATH,  # noqa: SLF001
                evidence._EVIDENCE_RELATIVE_PATH,  # noqa: SLF001
            )
        )
    )
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="history overlays are forbidden",
    ):
        evidence._git_source_boundary_blobs(  # noqa: SLF001
            source_boundary_commit,
            paths,
            repository,
            candidate_only=True,
        )


def test_v180r12r2_frozen_external_auth_anchor_rejects_coordinated_resign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_id = "1" * 64
    old_sha = "2" * 64
    monkeypatch.setattr(evidence, "EXPECTED_AUTHORIZATION_EVIDENCE_ID", "3" * 64)
    monkeypatch.setattr(evidence, "EXPECTED_CANONICAL_BYTE_COUNT", 1)
    monkeypatch.setattr(evidence, "EXPECTED_CANONICAL_SHA256", "4" * 64)
    monkeypatch.setattr(evidence, "EXPECTED_AUTHORIZATION_ID", old_id)
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_CANONICAL_BYTE_COUNT",
        2,
    )
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_CANONICAL_SHA256",
        old_sha,
    )
    monkeypatch.setattr(evidence, "EXPECTED_AUTHORIZATION_SOURCE_BYTE_COUNT", 3)
    monkeypatch.setattr(
        evidence,
        "EXPECTED_AUTHORIZATION_SOURCE_SHA256",
        "5" * 64,
    )

    # A coordinated auth implementation/source change may generate a newly
    # self-consistent identity, but it cannot replace the already frozen
    # post-prereg wrapper anchor without being rejected before replay.
    monkeypatch.setattr(authorization, "EXPECTED_AUTHORIZATION_ID", "6" * 64)
    monkeypatch.setattr(authorization, "EXPECTED_CANONICAL_BYTE_COUNT", 4)
    monkeypatch.setattr(authorization, "EXPECTED_CANONICAL_SHA256", "7" * 64)
    with pytest.raises(
        evidence.TenTerminalAggregationAuthorizationEvidenceV180R12R2Error,
        match="post-prereg authorization anchor is not frozen",
    ):
        evidence._require_post_prereg_authorization_constants()  # noqa: SLF001
