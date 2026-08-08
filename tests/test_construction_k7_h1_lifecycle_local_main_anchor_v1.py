from __future__ import annotations

import copy
from pathlib import Path
import shutil
import subprocess

import pytest

from acfqp import construction_k7_h1_lifecycle_preregistration_v1 as producer
from acfqp import construction_k7_h1_lifecycle_local_main_anchor_independent_verifier_v1 as verifier
from acfqp import phase3e_ids
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ("/usr/bin/git", "-C", str(root), *arguments),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit(root: Path, message: str) -> str:
    _git(root, "add", ".")
    _git(root, "commit", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _implementation_repo(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "anchor-repository"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "H1 Anchor Test")
    _git(root, "config", "user.email", "h1-anchor@example.invalid")
    for _role, relative, _semantic_role in producer.REQUIRED_COMPONENT_SPECS:
        source = REPOSITORY_ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        destination.chmod(0o644)
    implementation_commit = _commit(root, "implementation K")
    return root, implementation_commit


def _qualified_repo(tmp_path: Path) -> tuple[Path, str, str]:
    root, implementation_commit = _implementation_repo(tmp_path)
    preregistration = producer.build_h1_lifecycle_final_preregistration_v1(
        root,
        expected_parent_commit_id=implementation_commit,
    )
    target = root / producer.FINAL_PREREGISTRATION_REPOSITORY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(preregistration.canonical_bytes)
    qualifying_commit = _commit(root, "preregistration C")
    return root, implementation_commit, qualifying_commit


def _resign_final(document: dict) -> bytes:
    payload = copy.deepcopy(document)
    payload.pop("h1_lifecycle_final_preregistration_id", None)
    payload["h1_lifecycle_final_preregistration_id"] = content_id(
        verifier.FINAL_PREREGISTRATION_DOMAIN,
        payload,
    )
    return canonical_json_bytes(payload)


def test_domains_and_static_component_closure_are_independent_duplicates() -> None:
    assert producer.REQUIRED_COMPONENT_SPECS == verifier.REQUIRED_COMPONENT_SPECS
    assert len(producer.REQUIRED_COMPONENT_SPECS) == 12
    assert len({row[0] for row in producer.REQUIRED_COMPONENT_SPECS}) == 12
    assert len({row[1] for row in producer.REQUIRED_COMPONENT_SPECS}) == 12
    assert {
        producer.SOURCE_REGISTRY_DOMAIN,
        producer.PROGRAM_SNAPSHOT_DOMAIN,
        producer.FINAL_PREREGISTRATION_DOMAIN,
        verifier.ANCHOR_DOMAIN,
        verifier.PROVENANCE_DOMAIN,
    } <= phase3e_ids.PHASE3E_DOMAIN_TAGS
    assert "lifecycle_v1" not in producer.__dict__
    assert "lifecycle_v1" not in verifier.__dict__


def test_implementation_commit_without_later_preregistration_is_not_ready(
    tmp_path: Path,
) -> None:
    root, implementation_commit = _implementation_repo(tmp_path)
    assert _git(root, "rev-parse", "HEAD") == implementation_commit
    with pytest.raises(
        verifier.H1LifecycleLocalMainAnchorNotReadyV1,
        match="no final lifecycle preregistration",
    ):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(root)


def test_two_commit_anchor_replays_git_objects_and_inspects_only_expected_id(
    tmp_path: Path,
) -> None:
    root, implementation_commit, qualifying_commit = _qualified_repo(tmp_path)
    anchor = verifier.verify_h1_lifecycle_local_main_anchor_v1(root)
    assert anchor.commit_id == qualifying_commit
    assert anchor.parent_commit_id == implementation_commit
    assert anchor.to_document()["remote_published"] is False
    assert anchor.to_document()["production_execution_authorized"] is False
    assert anchor.to_document()["snapshot_internal_semantic_replay_complete"] is True
    assert anchor.to_document()["snapshot_dependency_semantic_binding_complete"] is False
    provenance = verifier.inspect_h1_caller_pinned_lifecycle_provenance_v1(
        root,
        expected_anchor_id=anchor.anchor_id,
    )
    document = provenance.to_document()
    assert document["h1_lifecycle_local_main_anchor_id"] == anchor.anchor_id
    assert document["program_status"] == "CALLER_PINNED_MIGRATION_SEED_ONLY"
    assert document["source_authority_present"] is False
    assert document["usable_as_execution_source"] is False
    assert document["fresh_import_self_mint_prevented"] is False
    assert document["worktree_execution_bytes_verified"] is False
    assert document["production_execution_authorized"] is False
    with pytest.raises(ValueError, match="differs from the expected ID"):
        verifier.inspect_h1_caller_pinned_lifecycle_provenance_v1(
            root,
            expected_anchor_id="0" * 64,
        )
    with pytest.raises(ValueError, match="already contains"):
        producer.build_h1_lifecycle_final_preregistration_v1(
            root,
            expected_parent_commit_id=qualifying_commit,
        )


def test_issued_anchor_and_provenance_detect_private_field_mutation(
    tmp_path: Path,
) -> None:
    root, _implementation_commit, _qualifying_commit = _qualified_repo(tmp_path)
    anchor = verifier.verify_h1_lifecycle_local_main_anchor_v1(root)
    provenance = verifier.inspect_h1_caller_pinned_lifecycle_provenance_v1(
        root,
        expected_anchor_id=anchor.anchor_id,
    )
    object.__setattr__(anchor, "program_id", "0" * 64)
    with pytest.raises(ValueError, match="anchor changed"):
        _ = anchor.anchor_id
    object.__setattr__(provenance, "program_id", "0" * 64)
    with pytest.raises(ValueError, match="provenance changed"):
        _ = provenance.provenance_id


def test_worktree_change_cannot_pass_even_instantaneous_provenance_check(
    tmp_path: Path,
) -> None:
    root, _implementation_commit, _qualifying_commit = _qualified_repo(tmp_path)
    anchor = verifier.verify_h1_lifecycle_local_main_anchor_v1(root)
    candidate_path = root / producer.REQUIRED_COMPONENT_SPECS[1][1]
    candidate_path.write_bytes(candidate_path.read_bytes() + b"\n# worktree attack\n")
    # Git-object attestation remains a statement about the commit.
    assert verifier.verify_h1_lifecycle_local_main_anchor_v1(root).anchor_id == anchor.anchor_id
    with pytest.raises(ValueError, match="worktree component bytes differ"):
        verifier.inspect_h1_caller_pinned_lifecycle_provenance_v1(
            root,
            expected_anchor_id=anchor.anchor_id,
        )


def test_later_registered_component_commit_invalidates_current_binding(
    tmp_path: Path,
) -> None:
    root, _implementation_commit, _qualifying_commit = _qualified_repo(tmp_path)
    candidate_path = root / producer.REQUIRED_COMPONENT_SPECS[1][1]
    candidate_path.write_bytes(candidate_path.read_bytes() + b"\n# committed attack\n")
    _commit(root, "mutate registered source")
    with pytest.raises(ValueError, match="registered component Git mode/blob changed"):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(root)


def test_final_unknown_field_even_with_recomputed_id_is_rejected(
    tmp_path: Path,
) -> None:
    root, _implementation_commit, _qualifying_commit = _qualified_repo(tmp_path)
    target = root / producer.FINAL_PREREGISTRATION_REPOSITORY_PATH
    document = loads_canonical_json(target.read_bytes())
    assert type(document) is dict
    document["forged_future_authority"] = True
    target.write_bytes(_resign_final(document))
    _commit(root, "forged final")
    with pytest.raises(
        ValueError,
        match="fields are not exact|differs from the first|mode/blob differs",
    ):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(root)


def test_changed_parent_or_merge_qualifier_is_rejected(tmp_path: Path) -> None:
    root, implementation_commit = _implementation_repo(tmp_path)
    preregistration = producer.build_h1_lifecycle_final_preregistration_v1(
        root,
        expected_parent_commit_id=implementation_commit,
    )
    # Interpose a commit after the registered implementation parent.
    marker = root / "unregistered-marker.txt"
    marker.write_text("interposed\n", encoding="utf-8")
    _commit(root, "interposed parent")
    target = root / producer.FINAL_PREREGISTRATION_REPOSITORY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(preregistration.canonical_bytes)
    _commit(root, "wrong-parent qualifier")
    with pytest.raises(ValueError, match="single child of its registered parent"):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(root)


def test_snapshot_is_semantically_replayed_without_candidate_import() -> None:
    snapshot = REPOSITORY_ROOT / producer.PROGRAM_SNAPSHOT_REPOSITORY_PATH
    assert verifier._verify_program_snapshot(snapshot.read_bytes()) == (
        "fcbc19081265500e8d1be94bc69d1c21ed3d41272fb93909b69145bd0ef7f2a6",
        "fe62da93a45b2f2c95d39003b2b30410cb2ee23823b3760e1b20348875457e11",
        "ff439652772a017291c66184f1fd3949d8918b5ab93b4f2d02222566b3ad782d",
        62,
        144,
    )


def test_resigned_snapshot_with_changed_derived_transition_is_rejected(
    tmp_path: Path,
) -> None:
    root, _implementation_commit = _implementation_repo(tmp_path)
    target = root / producer.PROGRAM_SNAPSHOT_REPOSITORY_PATH
    snapshot = loads_canonical_json(target.read_bytes())
    assert type(snapshot) is dict
    snapshot["program"]["transitions"][0]["ordinal"] = 999
    program_payload = copy.deepcopy(snapshot["program"])
    program_payload.pop("h1_production_lifecycle_program_id")
    snapshot["program"]["h1_production_lifecycle_program_id"] = content_id(
        verifier.PROGRAM_DOMAIN,
        program_payload,
    )
    snapshot_payload = copy.deepcopy(snapshot)
    snapshot_payload.pop("h1_lifecycle_program_snapshot_id")
    snapshot["h1_lifecycle_program_snapshot_id"] = content_id(
        verifier.PROGRAM_SNAPSHOT_DOMAIN,
        snapshot_payload,
    )
    target.write_bytes(canonical_json_bytes(snapshot))
    implementation_commit = _commit(root, "resigned malformed implementation K")
    preregistration = producer.build_h1_lifecycle_final_preregistration_v1(
        root,
        expected_parent_commit_id=implementation_commit,
    )
    final = root / producer.FINAL_PREREGISTRATION_REPOSITORY_PATH
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(preregistration.canonical_bytes)
    _commit(root, "preregistration C")
    with pytest.raises(ValueError, match="transition fields changed|did not independently"):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(root)


def test_qualifying_commit_with_any_extra_tree_change_is_rejected(tmp_path: Path) -> None:
    root, implementation_commit = _implementation_repo(tmp_path)
    preregistration = producer.build_h1_lifecycle_final_preregistration_v1(
        root,
        expected_parent_commit_id=implementation_commit,
    )
    target = root / producer.FINAL_PREREGISTRATION_REPOSITORY_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(preregistration.canonical_bytes)
    (root / "extra.txt").write_text("not allowed in C\n", encoding="utf-8")
    _commit(root, "overbroad preregistration C")
    with pytest.raises(ValueError, match="add exactly one 100644 preregistration"):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(root)


def test_later_final_mode_change_is_rejected(tmp_path: Path) -> None:
    root, _implementation_commit, _qualifying_commit = _qualified_repo(tmp_path)
    target = root / producer.FINAL_PREREGISTRATION_REPOSITORY_PATH
    target.chmod(0o755)
    _commit(root, "make final executable")
    with pytest.raises(ValueError, match="mode/blob differs"):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(root)


def test_git_replace_ref_cannot_change_verified_objects(tmp_path: Path) -> None:
    root, implementation_commit, qualifying_commit = _qualified_repo(tmp_path)
    expected = verifier.verify_h1_lifecycle_local_main_anchor_v1(root).anchor_id
    _git(root, "replace", qualifying_commit, implementation_commit)
    assert verifier.verify_h1_lifecycle_local_main_anchor_v1(root).anchor_id == expected


def test_non_sha1_repository_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "sha256-repository"
    root.mkdir()
    _git(root, "init", "--object-format=sha256", "-b", "main")
    _git(root, "config", "user.name", "H1 Anchor Test")
    _git(root, "config", "user.email", "h1-anchor@example.invalid")
    with pytest.raises(ValueError, match="object format must be exact SHA-1"):
        producer.build_h1_lifecycle_final_preregistration_v1(
            root,
            expected_parent_commit_id="0" * 40,
        )


def test_shallow_history_cannot_claim_first_qualifier(tmp_path: Path) -> None:
    root, _implementation_commit, _qualifying_commit = _qualified_repo(tmp_path)
    shallow = tmp_path / "shallow-copy"
    _git(tmp_path, "clone", "--depth", "1", root.as_uri(), str(shallow))
    with pytest.raises(ValueError, match="shallow repositories"):
        verifier.verify_h1_lifecycle_local_main_anchor_v1(shallow)


def test_coherently_resigned_dependency_id_remains_an_unbound_reference() -> None:
    target = REPOSITORY_ROOT / producer.PROGRAM_SNAPSHOT_REPOSITORY_PATH
    snapshot = loads_canonical_json(target.read_bytes())
    assert type(snapshot) is dict
    original_program_id = snapshot["program"]["h1_production_lifecycle_program_id"]
    snapshot["program"]["h1_execution_topology_profile_id"] = "1" * 64
    program_payload = copy.deepcopy(snapshot["program"])
    program_payload.pop("h1_production_lifecycle_program_id")
    new_program_id = content_id(verifier.PROGRAM_DOMAIN, program_payload)
    snapshot["program"]["h1_production_lifecycle_program_id"] = new_program_id
    transitions = verifier._verify_and_recompile_transitions(snapshot["program"])
    branches = verifier._derive_branch_documents(transitions)
    analysis_payload = {
        "schema": "acfqp.h1_production_lifecycle_branch_analysis.v1",
        "schema_version": "1.0.0",
        "h1_production_lifecycle_program_id": new_program_id,
        "branch_count": len(branches),
        "branch_count_formula": "ONE_PLUS_SUM_FAILURE_EDGES_OVER_TRANSITIONS",
        "branches": branches,
        "first_failure_prefixes_complete_for_declared_candidate_edges": True,
        "production_failure_edge_completeness_claimed": False,
        "shared_path_partitions_relative_to_candidate_table_only": True,
        "post_failure_cleanup_continuation_program_bound": False,
        "complete_attempt_branches_issued": False,
        "live_runtime_branch_completeness_claimed": False,
    }
    snapshot["branch_analysis_id"] = content_id(
        verifier.BRANCH_ANALYSIS_DOMAIN,
        analysis_payload,
    )
    snapshot_payload = copy.deepcopy(snapshot)
    snapshot_payload.pop("h1_lifecycle_program_snapshot_id")
    snapshot["h1_lifecycle_program_snapshot_id"] = content_id(
        verifier.PROGRAM_SNAPSHOT_DOMAIN,
        snapshot_payload,
    )
    replay = verifier._verify_program_snapshot(canonical_json_bytes(snapshot))
    assert replay[1] == new_program_id
    assert replay[1] != original_program_id
    # Internal replay is exact, but no corresponding topology source was
    # rederived; the public anchor test above keeps that binding claim false.


def test_zero_argument_self_mint_apis_fail_closed() -> None:
    with pytest.raises(ValueError, match="zero-argument"):
        producer.official_h1_lifecycle_source_authority_v1()
    with pytest.raises(ValueError, match="zero-argument"):
        verifier.official_h1_lifecycle_source_authority_v1()
