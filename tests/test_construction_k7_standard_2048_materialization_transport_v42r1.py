from __future__ import annotations

import copy
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
from typing import Any, Callable

import pytest

from acfqp import construction_k7_standard_2048_materialization_transport_v42r1 as transport
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import bootstrap_v42_standard_2048_remote_ordinal2 as bootstrap
from scripts import publish_v42_preformal_upload_journal as journal
from scripts import v42_preformal_upload_receiver as receiver


ROOT = Path(__file__).resolve().parents[1]
_RECEIVER_FIXTURE_RAW = (
    ROOT / transport.PREFORMAL_RECEIVER_SOURCE_RELATIVE
).read_bytes()


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(  # noqa: S324 - exact Git object identity
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()


def _all_fixture_source_paths() -> tuple[str, ...]:
    return tuple(
        sorted(
            set(authority.FORMAL_REMOTE_SOURCE_ROOTS)
            | {
                str(source_relative)
                for _archive, _module, member_kind, source_relative in (
                    authority.REMOTE_BOOTSTRAP_PYZ_MEMBER_SPECS
                )
                if member_kind == "COMMITTED_GIT_BLOB"
            }
        )
    )


def _live_bootstrap_constants() -> dict[str, object]:
    return {
        name: getattr(authority, name)
        for name in bootstrap._COMMITTED_BOOTSTRAP_CONSTANT_NAMES  # noqa: SLF001
    }


@lru_cache(maxsize=4)
def _fixture(
    salt: str = "one",
) -> tuple[dict[str, bytes], bytes, bytes]:
    loader_raw = (ROOT / transport.PREFORMAL_LOADER_SOURCE_RELATIVE).read_bytes()
    receiver_raw = _RECEIVER_FIXTURE_RAW
    entries: list[dict[str, str]] = []
    blobs: dict[str, bytes] = {}
    source_facts: list[dict[str, object]] = []
    for index, relative in enumerate(_all_fixture_source_paths()):
        raw = f"# {salt} source fixture {index}\n".encode("ascii")
        oid = _git_blob(raw)
        entry = {
            "relative_path": relative,
            "git_mode": "100644",
            "git_object_type": "blob",
            "git_blob_oid": oid,
        }
        entries.append(entry)
        blobs[oid] = raw
        source_facts.append(
            {
                **entry,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    for relative, raw in (
        (transport.PREFORMAL_LOADER_SOURCE_RELATIVE, loader_raw),
        (transport.PREFORMAL_RECEIVER_SOURCE_RELATIVE, receiver_raw),
        ("TRANSPORT_ONLY.txt", f"transport {salt}\n".encode("ascii")),
    ):
        oid = _git_blob(raw)
        entries.append(
            {
                "relative_path": relative,
                "git_mode": "100644",
                "git_object_type": "blob",
                "git_blob_oid": oid,
            }
        )
        blobs[oid] = raw
    entries.sort(key=lambda row: row["relative_path"])
    archive_raw, transport_facts = bootstrap._deterministic_ustar_bytes(  # noqa: SLF001
        entries, blobs
    )
    pyz_raw, pyz_artifact = bootstrap._deterministic_remote_bootstrap_pyz_bytes(  # noqa: SLF001
        entries,
        blobs,
        committed_bootstrap_constants=_live_bootstrap_constants(),
    )
    source = authority.build_source_manifest_v42r1(
        source_commit=hashlib.sha1((salt + ":commit").encode()).hexdigest(),  # noqa: S324
        source_tree=hashlib.sha1((salt + ":tree").encode()).hexdigest(),  # noqa: S324
        source_facts=source_facts,
        source_roots=list(authority.FORMAL_REMOTE_SOURCE_ROOTS),
        dynamic_import_sites=[],
    )
    manifest = authority.build_transport_manifest_v42r1(
        source_manifest=source,
        transport_facts=transport_facts,
        source_archive_sha256=hashlib.sha256(archive_raw).hexdigest(),
        source_archive_byte_count=len(archive_raw),
        remote_bootstrap_pyz_artifact=pyz_artifact,
    )
    local_attempt = authority.build_local_materialization_attempt_v42r1(
        source_manifest=source, transport_manifest=manifest
    )
    controls = {
        authority.SOURCE_MANIFEST_NAME: canonical_json_bytes(source),
        authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: canonical_json_bytes(
            local_attempt
        ),
        authority.REMOTE_BOOTSTRAP_PYZ_NAME: pyz_raw,
        authority.SOURCE_CAPSULE_NAME: archive_raw,
        authority.TRANSPORT_MANIFEST_NAME: canonical_json_bytes(manifest),
    }
    return controls, loader_raw, receiver_raw


def _context(salt: str = "one") -> dict[str, Any]:
    controls, loader_raw, receiver_raw = _fixture(salt)
    return {
        "control_raw_by_name": controls,
        "loader_source_raw": loader_raw,
        "receiver_source_raw": receiver_raw,
    }


def _token(label: str) -> str:
    return hashlib.sha256(label.encode("ascii")).hexdigest()


def _plan(
    *,
    token: str | None = None,
    salt: str = "one",
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return transport.build_preformal_upload_plan_v42r1(
        **_context(salt),
        upload_token=_token("token:" + salt) if token is None else token,
        predecessor_chain=predecessor_chain,
    )


def _attempt(
    plan: dict[str, Any],
    *,
    salt: str = "one",
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return transport.build_preformal_upload_attempt_v42r1(
        plan=plan,
        **_context(salt),
        predecessor_chain=predecessor_chain,
    )


def _parent_fact() -> dict[str, Any]:
    return {
        "path": str(authority.REMOTE_ROOT.parent),
        "node_type": "DIRECTORY",
        "mode": 0o775,
        "uid": authority.REMOTE_UID,
        "gid": authority.REMOTE_GID,
        "world_writable": False,
        "primary_gid_principals": [authority.REMOTE_USER],
        "explicit_group_members": [],
    }


def _private_directory_fact(path: str) -> dict[str, Any]:
    return {
        "path": path,
        "node_type": "DIRECTORY",
        "mode": 0o700,
        "uid": authority.REMOTE_UID,
        "gid": authority.REMOTE_GID,
    }


def _control_file_facts(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": fact["name"],
            "path": str(Path(plan["preformal_scratch_root"]) / fact["name"]),
            "node_type": "REGULAR_FILE",
            "mode": 0o400,
            "uid": authority.REMOTE_UID,
            "gid": authority.REMOTE_GID,
            "sha256": fact["sha256"],
            "byte_count": fact["byte_count"],
        }
        for fact in plan["control_facts"]
    ]


def _receipt(
    plan: dict[str, Any],
    attempt: dict[str, Any],
    *,
    salt: str = "one",
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return transport.build_preformal_upload_receipt_v42r1(
        plan=plan,
        attempt=attempt,
        scratch_parent_fact=_parent_fact(),
        scratch_root_fact=_private_directory_fact(plan["preformal_scratch_root"]),
        ledger_stage_fact=_private_directory_fact(
            plan["preformal_ledger_stage_root"]
        ),
        observed_control_file_facts=_control_file_facts(plan),
        **_context(salt),
        predecessor_chain=predecessor_chain,
    )


def _abandoned_outcome(
    plan: dict[str, Any],
    attempt: dict[str, Any],
    *,
    salt: str = "one",
    predecessor_chain: list[dict[str, dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    return transport.build_preformal_upload_outcome_v42r1(
        plan=plan,
        attempt=attempt,
        outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
        abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS,
        **_context(salt),
        predecessor_chain=predecessor_chain,
    )


def _rehash(document: dict[str, Any], *, identity: str, domain: str) -> dict[str, Any]:
    result = copy.deepcopy(document)
    result.pop(identity, None)
    result[identity] = hashlib.sha256(
        domain.encode("ascii") + b"\0" + canonical_json_bytes(result)
    ).hexdigest()
    return result


def _rehash_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return _rehash(
        plan,
        identity="preformal_upload_plan_id",
        domain="acfqp:v42-remote-ordinal2:preformal-upload-plan",
    )


def _rehash_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    return _rehash(
        attempt,
        identity="preformal_upload_attempt_id",
        domain="acfqp:v42-remote-ordinal2:preformal-upload-attempt",
    )


def _rehash_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return _rehash(
        receipt,
        identity="preformal_upload_receipt_id",
        domain="acfqp:v42-remote-ordinal2:preformal-upload-receipt",
    )


def _rehash_outcome(outcome: dict[str, Any]) -> dict[str, Any]:
    return _rehash(
        outcome,
        identity="preformal_upload_outcome_id",
        domain="acfqp:v42-remote-ordinal2:preformal-upload-outcome",
    )


def test_plan_attempt_receipt_and_complete_outcome_round_trip() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    receipt = _receipt(plan, attempt)
    outcome = transport.build_preformal_upload_outcome_v42r1(
        plan=plan,
        attempt=attempt,
        outcome_class=transport.PREFORMAL_OUTCOME_COMPLETE,
        receipt=receipt,
        **_context(),
    )

    assert transport.verify_preformal_upload_plan_v42r1(
        canonical_json_bytes(plan)
    ) == plan
    assert transport.verify_preformal_upload_plan_against_controls_v42r1(
        plan, **_context()
    ) == plan
    assert transport.verify_preformal_upload_attempt_against_controls_v42r1(
        canonical_json_bytes(attempt), plan=plan, **_context()
    ) == attempt
    assert transport.verify_preformal_upload_receipt_against_controls_v42r1(
        canonical_json_bytes(receipt), plan=plan, attempt=attempt, **_context()
    ) == receipt
    assert transport.verify_preformal_upload_outcome_v42r1(
        canonical_json_bytes(outcome),
        plan=plan,
        attempt=attempt,
        receipt=receipt,
    ) == outcome
    assert outcome["successor_plan_allowed"] is False


def test_plan_derives_exact_controls_programs_and_resource_caps() -> None:
    plan = _plan()
    controls, loader_raw, receiver_raw = _fixture()
    expected = [
        {
            "name": name,
            "sha256": hashlib.sha256(controls[name]).hexdigest(),
            "byte_count": len(controls[name]),
        }
        for name in transport.CONTROL_NAMES
    ]
    assert plan["control_facts"] == expected
    assert plan["loader_artifact"]["sha256"] == hashlib.sha256(loader_raw).hexdigest()
    assert plan["receiver_artifact"]["sha256"] == hashlib.sha256(receiver_raw).hexdigest()
    assert plan["expected_total_control_bytes"] == sum(
        fact["byte_count"] for fact in expected
    )
    assert plan["scratch_first_child_name"] == authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME
    assert plan["control_creation_order"] == list(transport.CONTROL_CREATION_ORDER)


def test_self_contained_plan_verifier_is_not_a_contextual_authority() -> None:
    plan = _plan()
    forged = copy.deepcopy(plan)
    forged["source_manifest_id"] = _token("arbitrary-source-id")
    forged = _rehash_plan(forged)

    assert transport.verify_preformal_upload_plan_v42r1(forged) == forged
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_against_controls_v42r1(
            forged, **_context()
        )


def test_cross_capsule_and_program_splices_fail_contextual_join() -> None:
    plan = _plan(salt="one")
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_against_controls_v42r1(
            plan, **_context("two")
        )
    changed_loader = _context()
    changed_loader["loader_source_raw"] += b"# drift\n"
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.build_preformal_upload_plan_v42r1(
            upload_token=_token("changed-loader"), **changed_loader
        )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda argv: argv.__setitem__(2, "/tmp/evil-ssh-config"),
        lambda argv: argv.__setitem__(7, "-oPasswordAuthentication=yes"),
        lambda argv: argv.__setitem__(17, "-oStrictHostKeyChecking=no"),
        lambda argv: argv.__setitem__(-2, "evil.example"),
        lambda argv: argv.__setitem__(-1, argv[-1] + " unexpected-second-command"),
    ],
)
def test_ssh_template_is_the_single_exact_authority(
    mutate: Callable[[list[str]], None],
) -> None:
    plan = _plan()
    tampered = copy.deepcopy(plan)
    mutate(tampered["authorized_ssh_argv_template"])
    tampered = _rehash_plan(tampered)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_v42r1(tampered)


def test_argv_materialization_is_post_identity_and_contextual() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    argv = transport.materialize_preformal_upload_ssh_argv_v42r1(
        plan=plan, attempt=attempt, **_context()
    )
    assert plan["preformal_upload_plan_id"] in argv[-1]
    assert attempt["preformal_upload_attempt_id"] in argv[-1]
    assert all("{acfqp_v42_" not in value for value in argv)
    assert argv[0] == "/usr/bin/ssh"
    assert argv[-2] == transport.REMOTE_ENDPOINT_HOST


def test_role_caps_reject_rehashed_oversize_facts_before_effects() -> None:
    plan = _plan()
    tampered = copy.deepcopy(plan)
    tampered["control_facts"][0]["byte_count"] = (
        transport.MAXIMUM_CONTROL_BYTES[tampered["control_facts"][0]["name"]] + 1
    )
    tampered = _rehash_plan(tampered)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_v42r1(tampered)

    tampered = copy.deepcopy(plan)
    tampered["receiver_artifact"]["byte_count"] = transport.MAXIMUM_RECEIVER_BYTES + 1
    tampered = _rehash_plan(tampered)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_v42r1(tampered)


def test_attempt_binds_durable_local_publication_before_network() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    assert attempt["local_publication_order"] == [
        transport.PREFORMAL_PLAN_NAME,
        transport.PREFORMAL_KNOWN_HOSTS_NAME,
        transport.PREFORMAL_ATTEMPT_NAME,
        transport.PREFORMAL_STREAM_HEADER_NAME,
        transport.PREFORMAL_NETWORK_START_NAME,
    ]
    assert attempt[
        "network_effect_permitted_only_after_successful_publication_and_fsync"
    ] is True
    tampered = copy.deepcopy(attempt)
    tampered[
        "ordinal_slot_chain_root_and_parent_must_be_fsynced_before_ssh"
    ] = False
    tampered = _rehash_attempt(tampered)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_attempt_v42r1(tampered, plan=plan)


def test_abandoned_outcome_is_the_only_typed_successor_edge() -> None:
    first = _plan(token=_token("first-token"))
    first_attempt = _attempt(first)
    abandoned = _abandoned_outcome(first, first_attempt)
    predecessor_chain = [
        {"plan": first, "attempt": first_attempt, "outcome": abandoned}
    ]
    second = _plan(
        token=_token("second-token"), predecessor_chain=predecessor_chain
    )
    second_attempt = _attempt(
        second, predecessor_chain=predecessor_chain
    )

    assert second["preformal_upload_ordinal"] == 2
    assert second["previous_preformal_upload_outcome_id"] == abandoned[
        "preformal_upload_outcome_id"
    ]
    assert second["upload_token_history"] == [
        _token("first-token"),
        _token("second-token"),
    ]
    assert transport.verify_preformal_upload_plan_against_controls_v42r1(
        second,
        predecessor_chain=predecessor_chain,
        **_context(),
    ) == second
    assert second_attempt["preformal_upload_ordinal"] == 2


def test_successor_rejects_partial_triple_and_reused_token() -> None:
    first = _plan(token=_token("first-token"))
    first_attempt = _attempt(first)
    abandoned = _abandoned_outcome(first, first_attempt)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.build_preformal_upload_plan_v42r1(
            **_context(),
            upload_token=_token("second-token"),
            predecessor_chain=[{"plan": first}],
        )
    with pytest.raises(transport.V42MaterializationTransportError):
        _plan(
            token=_token("first-token"),
            predecessor_chain=[
                {"plan": first, "attempt": first_attempt, "outcome": abandoned}
            ],
        )


def test_complete_outcome_cannot_spawn_a_successor() -> None:
    first = _plan()
    first_attempt = _attempt(first)
    receipt = _receipt(first, first_attempt)
    complete = transport.build_preformal_upload_outcome_v42r1(
        plan=first,
        attempt=first_attempt,
        outcome_class=transport.PREFORMAL_OUTCOME_COMPLETE,
        receipt=receipt,
        **_context(),
    )
    with pytest.raises(transport.V42MaterializationTransportError):
        _plan(
            token=_token("forbidden-successor"),
            predecessor_chain=[
                {"plan": first, "attempt": first_attempt, "outcome": complete}
            ],
        )


@pytest.mark.parametrize(
    ("outcome_class", "reason"),
    [
        (
            transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE,
            transport.PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS,
        ),
        (
            transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
            transport.PREFORMAL_ABANDONMENT_REASON_LOCAL,
        ),
        (transport.PREFORMAL_OUTCOME_COMPLETE, None),
    ],
)
def test_outcome_class_reason_and_receipt_contract_is_exact(
    outcome_class: str, reason: str | None
) -> None:
    plan = _plan()
    attempt = _attempt(plan)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.build_preformal_upload_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome_class=outcome_class,
            abandonment_reason_code=reason,
            **_context(),
        )


def test_ambiguous_disconnect_is_conservative_and_retryable() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    outcome = transport.build_preformal_upload_outcome_v42r1(
        plan=plan,
        attempt=attempt,
        outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
        abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS,
        **_context(),
    )
    assert outcome["remote_completion_claimed_when_receipt_absent"] is False
    assert outcome["scratch_identity_permanently_abandoned"] is True
    assert outcome["successor_plan_allowed"] is True


def test_outcome_rejects_cross_attempt_and_ordinal_999_even_if_rehashed() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    outcome = _abandoned_outcome(plan, attempt)
    other = _plan(token=_token("other-token"))
    other_attempt = _attempt(other)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_outcome_v42r1(
            outcome, plan=other, attempt=other_attempt
        )

    tampered = copy.deepcopy(outcome)
    tampered["preformal_upload_ordinal"] = 999
    tampered["upload_token_history"] = [tampered["upload_token"]] * 999
    tampered = _rehash_outcome(tampered)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_outcome_v42r1(
            tampered, plan=plan, attempt=attempt
        )


def _all_keys(value: object) -> set[str]:
    if type(value) is dict:
        return set(value) | {
            child
            for nested in value.values()
            for child in _all_keys(nested)
        }
    if type(value) is list:
        return {child for nested in value for child in _all_keys(nested)}
    return set()


def test_receipt_persists_only_named_portable_facts() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    receipt = _receipt(plan, attempt)
    forbidden = {
        "dev",
        "ino",
        "inode",
        "nlink",
        "mtime",
        "ctime",
        "atime",
        "stat_identity",
        "directory_size",
    }
    keys = _all_keys(receipt)
    assert not any(
        forbidden_name in key
        for forbidden_name in forbidden
        for key in keys
    )
    assert receipt["portable_named_facts_only"] is True
    assert receipt["scratch_root_inventory"] == list(transport.CONTROL_NAMES)
    assert receipt["ledger_stage_inventory"] == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value["scratch_parent_fact"].__setitem__("mode", 0o777),
        lambda value: value["scratch_root_fact"].__setitem__("uid", 0),
        lambda value: value["ledger_stage_fact"].__setitem__("path", "/tmp/evil"),
        lambda value: value["observed_control_file_facts"][0].__setitem__(
            "sha256", _token("wrong-control")
        ),
        lambda value: value.__setitem__("scratch_first_child_name", "wrong"),
        lambda value: value["control_creation_order"].reverse(),
        lambda value: value.__setitem__("shared_parent_directory_fsynced", False),
    ],
)
def test_receipt_rejects_portable_metadata_or_causality_drift(
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    plan = _plan()
    attempt = _attempt(plan)
    receipt = _receipt(plan, attempt)
    tampered = copy.deepcopy(receipt)
    mutate(tampered)
    tampered = _rehash_receipt(tampered)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_receipt_v42r1(
            tampered, plan=plan, attempt=attempt
        )


def test_plan_and_documents_reject_extra_fields_and_noncanonical_bytes() -> None:
    plan = _plan()
    extra = copy.deepcopy(plan)
    extra["extra"] = True
    extra = _rehash_plan(extra)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_v42r1(extra)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_v42r1(
            canonical_json_bytes(plan) + b"\n"
        )


def test_control_creation_order_and_remote_contract_cannot_be_rehashed_away() -> None:
    plan = _plan()
    tampered = copy.deepcopy(plan)
    tampered["control_creation_order"].reverse()
    tampered["remote_receiver_contract"]["control_creation_order"].reverse()
    tampered = _rehash_plan(tampered)
    with pytest.raises(transport.V42MaterializationTransportError):
        transport.verify_preformal_upload_plan_v42r1(tampered)


def test_token_branches_collide_on_one_deterministic_ordinal_slot() -> None:
    first_a = _plan(token=_token("ordinal-one-a"))
    first_b = _plan(token=_token("ordinal-one-b"))
    assert first_a["upload_token"] != first_b["upload_token"]
    assert first_a["local_ordinal_slot"] == first_b["local_ordinal_slot"]
    assert first_a["local_plan_path"] == first_b["local_plan_path"]
    assert first_a["local_attempt_path"] == first_b["local_attempt_path"]
    assert first_a["local_network_start_path"] == first_b[
        "local_network_start_path"
    ]
    assert first_a["local_publication_contract"][
        "ordinal_slot_creation"
    ] == "MKDIR_EXCLUSIVE_OR_EXACT_PREFIX_RECOVERY_NOFOLLOW_MODE_0700"
    assert first_a["local_publication_contract"][
        "empty_ordinal_slot_is_unclaimed"
    ] is True
    assert first_a["local_publication_contract"][
        "first_durable_plan_selects_ordinal_branch"
    ] is True
    assert first_a["local_publication_contract"][
        "exactly_one_plan_allowed_per_ordinal_slot"
    ] is True

    attempt = _attempt(first_a)
    abandoned = _abandoned_outcome(first_a, attempt)
    chain = [{"plan": first_a, "attempt": attempt, "outcome": abandoned}]
    second_a = _plan(token=_token("ordinal-two-a"), predecessor_chain=chain)
    second_b = _plan(token=_token("ordinal-two-b"), predecessor_chain=chain)
    assert second_a["local_ordinal_slot"] == second_b["local_ordinal_slot"]
    assert second_a["local_ordinal_slot"] != first_a["local_ordinal_slot"]
    assert second_a["local_publication_contract"][
        "predecessor_outcome_path"
    ] == first_a["local_outcome_path"]


def test_complete_predecessor_chain_is_verified_through_ordinal_three() -> None:
    first = _plan(token=_token("chain-one"))
    first_attempt = _attempt(first)
    first_outcome = _abandoned_outcome(first, first_attempt)
    chain_one = [
        {"plan": first, "attempt": first_attempt, "outcome": first_outcome}
    ]
    second = _plan(token=_token("chain-two"), predecessor_chain=chain_one)
    second_attempt = _attempt(second, predecessor_chain=chain_one)
    second_outcome = _abandoned_outcome(
        second, second_attempt, predecessor_chain=chain_one
    )
    chain_two = [
        *chain_one,
        {
            "plan": second,
            "attempt": second_attempt,
            "outcome": second_outcome,
        },
    ]
    third = _plan(token=_token("chain-three"), predecessor_chain=chain_two)
    assert third["preformal_upload_ordinal"] == 3
    assert transport.verify_preformal_upload_plan_against_controls_v42r1(
        third, predecessor_chain=chain_two, **_context()
    ) == third


def test_truncated_or_forged_deep_history_is_rejected() -> None:
    first = _plan(token=_token("history-one"))
    first_attempt = _attempt(first)
    first_outcome = _abandoned_outcome(first, first_attempt)
    chain_one = [
        {"plan": first, "attempt": first_attempt, "outcome": first_outcome}
    ]
    second = _plan(token=_token("history-two"), predecessor_chain=chain_one)

    forged_first_outcome = copy.deepcopy(first_outcome)
    forged_first_outcome["preformal_upload_plan_id"] = _token("missing-plan")
    forged_first_outcome["preformal_upload_attempt_id"] = _token(
        "missing-attempt"
    )
    forged_first_outcome = _rehash_outcome(forged_first_outcome)
    forged_second = copy.deepcopy(second)
    forged_second["previous_preformal_upload_outcome"] = forged_first_outcome
    forged_second["previous_preformal_upload_outcome_id"] = forged_first_outcome[
        "preformal_upload_outcome_id"
    ]
    forged_second = _rehash_plan(forged_second)
    assert transport.verify_preformal_upload_plan_v42r1(forged_second) == forged_second
    forged_second_attempt = transport._attempt_from_verified_plan(  # noqa: SLF001
        forged_second
    )
    forged_second_outcome = transport._outcome_payload_from_verified_documents(  # noqa: SLF001
        plan=forged_second,
        attempt=forged_second_attempt,
        outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_AMBIGUOUS,
        receipt_id=None,
        abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_AMBIGUOUS,
    )
    forged_chain = [
        *chain_one,
        {
            "plan": forged_second,
            "attempt": forged_second_attempt,
            "outcome": forged_second_outcome,
        },
    ]
    with pytest.raises(transport.V42MaterializationTransportError):
        _plan(token=_token("history-three"), predecessor_chain=forged_chain)
    with pytest.raises(transport.V42MaterializationTransportError):
        _plan(
            token=_token("truncated-history"),
            predecessor_chain=[forged_chain[-1]],
        )


def test_stream_header_and_network_start_are_acyclic_and_exact() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    header = transport.build_preformal_upload_stream_header_v42r1(
        plan=plan, attempt=attempt, **_context()
    )
    start = transport.build_preformal_network_start_v42r1(
        plan=plan, attempt=attempt, **_context()
    )
    receipt = _receipt(plan, attempt)
    assert [row["name"] for row in header["frames"]] == list(
        transport.PREFORMAL_STREAM_FRAME_ORDER
    )
    assert header["preformal_upload_attempt_id"] == attempt[
        "preformal_upload_attempt_id"
    ]
    assert start["preformal_stream_header_id"] == header[
        "preformal_stream_header_id"
    ]
    assert receipt["preformal_stream_header_id"] == header[
        "preformal_stream_header_id"
    ]
    assert transport.verify_preformal_upload_stream_header_v42r1(
        canonical_json_bytes(header), plan=plan, attempt=attempt
    ) == header
    assert transport.verify_preformal_network_start_v42r1(
        canonical_json_bytes(start), plan=plan, attempt=attempt
    ) == start


def test_remote_tcb_wire_and_fixed_ledger_contracts_are_exact() -> None:
    plan = _plan()
    tcb = plan["remote_startup_tcb_contract"]
    wire = plan["stream_protocol_contract"]
    assert tcb["python_invocation_path"] == "/usr/bin/python3"
    assert tcb["python_realpath"] == "/usr/bin/python3.12"
    assert tcb["python_realpath_sha256"] == transport.REMOTE_PYTHON_SHA256
    assert tcb["supplementary_groups"] == list(
        transport.REMOTE_SUPPLEMENTARY_GROUPS
    )
    assert tcb["python_binary_hash_does_not_bind_stdlib"] is True
    assert wire["frame_order"] == list(transport.PREFORMAL_STREAM_FRAME_ORDER)
    assert wire["plan_body_byte_cap"] == transport.MAXIMUM_PLAN_BYTES
    assert plan["fixed_transport_ledger_root"] == str(
        transport.FIXED_TRANSPORT_LEDGER_ROOT
    )


def test_effectful_journal_o_excl_slot_blocks_ordinal_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-preformal-journal-", dir="/tmp"
    ) as base:
        local_parent = Path(base)
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", local_parent)
        first_a = _plan(token=_token("journal-first-a"))
        first_b = _plan(token=_token("journal-first-b"))
        first_attempt_a = _attempt(first_a)
        first_attempt_b = _attempt(first_b)

        journal.publish_pre_network_journal_v42r1(
            plan=first_a,
            attempt=first_attempt_a,
            **_context(),
        )
        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_pre_network_journal_v42r1(
                plan=first_b,
                attempt=first_attempt_b,
                **_context(),
            )
        start = journal.publish_network_start_v42r1(
            plan=first_a, attempt=first_attempt_a, **_context()
        )
        assert start["preformal_upload_plan_id"] == first_a[
            "preformal_upload_plan_id"
        ]
        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_network_start_v42r1(
                plan=first_a, attempt=first_attempt_a, **_context()
            )

        first_outcome = _abandoned_outcome(first_a, first_attempt_a)
        journal.publish_outcome_v42r1(
            plan=first_a,
            attempt=first_attempt_a,
            outcome=first_outcome,
            **_context(),
        )
        chain = [
            {
                "plan": first_a,
                "attempt": first_attempt_a,
                "outcome": first_outcome,
            }
        ]
        second_a = _plan(
            token=_token("journal-second-a"), predecessor_chain=chain
        )
        second_b = _plan(
            token=_token("journal-second-b"), predecessor_chain=chain
        )
        second_attempt_a = _attempt(second_a, predecessor_chain=chain)
        second_attempt_b = _attempt(second_b, predecessor_chain=chain)
        journal.publish_pre_network_journal_v42r1(
            plan=second_a,
            attempt=second_attempt_a,
            predecessor_chain=chain,
            **_context(),
        )
        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_pre_network_journal_v42r1(
                plan=second_b,
                attempt=second_attempt_b,
                predecessor_chain=chain,
                **_context(),
            )


def test_local_pre_network_failure_can_close_slot_without_start_marker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-preformal-local-failure-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("local-failure"))
        attempt = _attempt(plan)
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        outcome = transport.build_preformal_upload_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE,
            abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_LOCAL,
            **_context(),
        )
        journal.publish_outcome_v42r1(
            plan=plan, attempt=attempt, outcome=outcome, **_context()
        )
        slot = Path(plan["local_ordinal_slot"])
        assert not (slot / transport.PREFORMAL_NETWORK_START_NAME).exists()
        assert (slot / transport.PREFORMAL_OUTCOME_NAME).is_file()


def test_later_publishers_reject_cross_branch_documents_before_writing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-preformal-cross-branch-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan_a = _plan(token=_token("cross-branch-a"))
        plan_b = _plan(token=_token("cross-branch-b"))
        attempt_a = _attempt(plan_a)
        attempt_b = _attempt(plan_b)
        journal.publish_pre_network_journal_v42r1(
            plan=plan_a, attempt=attempt_a, **_context()
        )

        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_network_start_v42r1(
                plan=plan_b, attempt=attempt_b, **_context()
            )
        slot = Path(plan_a["local_ordinal_slot"])
        assert not (slot / transport.PREFORMAL_NETWORK_START_NAME).exists()

        local_failure_b = transport.build_preformal_upload_outcome_v42r1(
            plan=plan_b,
            attempt=attempt_b,
            outcome_class=transport.PREFORMAL_OUTCOME_ABANDONED_FAILURE,
            abandonment_reason_code=transport.PREFORMAL_ABANDONMENT_REASON_LOCAL,
            **_context(),
        )
        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_outcome_v42r1(
                plan=plan_b,
                attempt=attempt_b,
                outcome=local_failure_b,
                **_context(),
            )
        assert not (slot / transport.PREFORMAL_OUTCOME_NAME).exists()


@pytest.mark.parametrize("stop_after", [1, 2, 3, 4])
def test_pre_network_complete_prefix_recovers_only_the_selected_plan(
    monkeypatch: pytest.MonkeyPatch, stop_after: int
) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f"acfqp-v42-preformal-prefix-{stop_after}-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan_a = _plan(token=_token(f"prefix-a-{stop_after}"))
        plan_b = _plan(token=_token(f"prefix-b-{stop_after}"))
        attempt_a = _attempt(plan_a)
        attempt_b = _attempt(plan_b)
        original = journal._write_once_at  # noqa: SLF001
        count = 0

        def fail_after_publication(
            directory_fd: int, name: str, raw: bytes, *, label: str
        ) -> Any:
            nonlocal count
            pin = original(directory_fd, name, raw, label=label)
            count += 1
            if count == stop_after:
                os.close(pin.descriptor)
                raise RuntimeError("injected crash after durable prefix")
            return pin

        monkeypatch.setattr(journal, "_write_once_at", fail_after_publication)
        with pytest.raises(RuntimeError, match="injected crash"):
            journal.publish_pre_network_journal_v42r1(
                plan=plan_a, attempt=attempt_a, **_context()
            )
        monkeypatch.setattr(journal, "_write_once_at", original)

        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_pre_network_journal_v42r1(
                plan=plan_b, attempt=attempt_b, **_context()
            )
        assert journal.publish_pre_network_journal_v42r1(
            plan=plan_a, attempt=attempt_a, **_context()
        ) == (plan_a, attempt_a)
        assert sorted(path.name for path in Path(plan_a["local_ordinal_slot"]).iterdir()) == sorted(
            [
                transport.PREFORMAL_PLAN_NAME,
                transport.PREFORMAL_KNOWN_HOSTS_NAME,
                transport.PREFORMAL_ATTEMPT_NAME,
                transport.PREFORMAL_STREAM_HEADER_NAME,
            ]
        )


def test_empty_slot_is_unclaimed_until_the_first_durable_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-preformal-unclaimed-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan_a = _plan(token=_token("empty-slot-a"))
        plan_b = _plan(token=_token("empty-slot-b"))
        attempt_a = _attempt(plan_a)
        attempt_b = _attempt(plan_b)
        original = journal._write_once_at  # noqa: SLF001

        def fail_before_first_publication(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("injected crash before durable plan")

        monkeypatch.setattr(
            journal, "_write_once_at", fail_before_first_publication
        )
        with pytest.raises(RuntimeError, match="before durable plan"):
            journal.publish_pre_network_journal_v42r1(
                plan=plan_a, attempt=attempt_a, **_context()
            )
        assert list(Path(plan_a["local_ordinal_slot"]).iterdir()) == []

        monkeypatch.setattr(journal, "_write_once_at", original)
        assert journal.publish_pre_network_journal_v42r1(
            plan=plan_b, attempt=attempt_b, **_context()
        ) == (plan_b, attempt_b)


def test_complete_outcome_recovers_from_durable_receipt_without_new_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-preformal-receipt-recovery-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("receipt-recovery"))
        attempt = _attempt(plan)
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        journal.publish_network_start_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        receipt = _receipt(plan, attempt)
        outcome = transport.build_preformal_upload_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome_class=transport.PREFORMAL_OUTCOME_COMPLETE,
            receipt=receipt,
            **_context(),
        )
        original = journal._write_once_at  # noqa: SLF001

        def crash_after_receipt(
            directory_fd: int, name: str, raw: bytes, *, label: str
        ) -> Any:
            pin = original(directory_fd, name, raw, label=label)
            if name == transport.PREFORMAL_RECEIPT_NAME:
                os.close(pin.descriptor)
                raise RuntimeError("injected crash after durable receipt")
            return pin

        monkeypatch.setattr(journal, "_write_once_at", crash_after_receipt)
        with pytest.raises(RuntimeError, match="durable receipt"):
            journal.publish_outcome_v42r1(
                plan=plan,
                attempt=attempt,
                outcome=outcome,
                receipt=receipt,
                **_context(),
            )
        slot = Path(plan["local_ordinal_slot"])
        assert (slot / transport.PREFORMAL_RECEIPT_NAME).is_file()
        assert not (slot / transport.PREFORMAL_OUTCOME_NAME).exists()

        monkeypatch.setattr(journal, "_write_once_at", original)
        assert journal.publish_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome=outcome,
            receipt=receipt,
            **_context(),
        ) == outcome
        assert journal.publish_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome=outcome,
            receipt=receipt,
            **_context(),
        ) == outcome


def test_write_once_rejects_same_byte_created_inode_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-write-once-inode-", dir="/tmp"
    ) as base:
        directory_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
        original = journal._pin_file_at  # noqa: SLF001
        replaced = False

        def replace_before_reopen(
            directory_fd: int, name: str, expected_raw: bytes, *, label: str
        ) -> Any:
            nonlocal replaced
            if not replaced:
                replaced = True
                os.unlink(name, dir_fd=directory_fd)
                replacement = os.open(
                    name,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o400,
                    dir_fd=directory_fd,
                )
                try:
                    os.write(replacement, expected_raw)
                    os.fchmod(replacement, 0o400)
                    os.fsync(replacement)
                finally:
                    os.close(replacement)
            return original(
                directory_fd, name, expected_raw, label=label
            )

        monkeypatch.setattr(journal, "_pin_file_at", replace_before_reopen)
        try:
            with pytest.raises(
                journal.V42PreformalJournalError, match="created inode"
            ):
                journal._write_once_at(  # noqa: SLF001
                    directory_fd, "BOUND", b"same bytes", label="BOUND"
                )
        finally:
            os.close(directory_fd)


def test_pin_file_rejects_same_byte_path_swap_after_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-pin-inode-", dir="/tmp"
    ) as base:
        path = Path(base) / "BOUND"
        path.write_bytes(b"same bytes")
        path.chmod(0o400)
        directory_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
        original = journal._read_exact  # noqa: SLF001
        swapped = False

        def swap_after_read(
            descriptor: int, expected_raw: bytes, *, label: str
        ) -> None:
            nonlocal swapped
            original(descriptor, expected_raw, label=label)
            if not swapped:
                swapped = True
                path.unlink()
                path.write_bytes(expected_raw)
                path.chmod(0o400)

        monkeypatch.setattr(journal, "_read_exact", swap_after_read)
        try:
            with pytest.raises(
                journal.V42PreformalJournalError, match="changed during readback"
            ):
                journal._pin_file_at(  # noqa: SLF001
                    directory_fd, "BOUND", b"same bytes", label="BOUND"
                )
        finally:
            os.close(directory_fd)


def test_whole_predecessor_snapshot_detects_swap_during_successor_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-predecessor-snapshot-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        first = _plan(token=_token("snapshot-first"))
        first_attempt = _attempt(first)
        journal.publish_pre_network_journal_v42r1(
            plan=first, attempt=first_attempt, **_context()
        )
        journal.publish_network_start_v42r1(
            plan=first, attempt=first_attempt, **_context()
        )
        first_outcome = _abandoned_outcome(first, first_attempt)
        journal.publish_outcome_v42r1(
            plan=first,
            attempt=first_attempt,
            outcome=first_outcome,
            **_context(),
        )
        chain = [
            {"plan": first, "attempt": first_attempt, "outcome": first_outcome}
        ]
        second = _plan(
            token=_token("snapshot-second"), predecessor_chain=chain
        )
        second_attempt = _attempt(second, predecessor_chain=chain)
        journal.publish_pre_network_journal_v42r1(
            plan=second,
            attempt=second_attempt,
            predecessor_chain=chain,
            **_context(),
        )
        original = journal._write_once_at  # noqa: SLF001

        def swap_predecessor_after_marker(
            directory_fd: int, name: str, raw: bytes, *, label: str
        ) -> Any:
            pin = original(directory_fd, name, raw, label=label)
            if name == transport.PREFORMAL_NETWORK_START_NAME:
                predecessor_plan = Path(first["local_plan_path"])
                persisted = predecessor_plan.read_bytes()
                predecessor_plan.unlink()
                predecessor_plan.write_bytes(persisted)
                predecessor_plan.chmod(0o400)
            return pin

        monkeypatch.setattr(
            journal, "_write_once_at", swap_predecessor_after_marker
        )
        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_network_start_v42r1(
                plan=second,
                attempt=second_attempt,
                predecessor_chain=chain,
                **_context(),
            )


def test_prefix_recovery_fsyncs_visible_plan_before_advancing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-prefix-fsync-recovery-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("prefix-fsync-recovery"))
        attempt = _attempt(plan)
        original_fsync = journal.os.fsync
        failed = False

        def fail_first_regular_fsync(descriptor: int) -> None:
            nonlocal failed
            if stat.S_ISREG(os.fstat(descriptor).st_mode) and not failed:
                failed = True
                raise OSError(5, "injected regular-file fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(journal.os, "fsync", fail_first_regular_fsync)
        with pytest.raises(OSError, match="injected regular-file fsync"):
            journal.publish_pre_network_journal_v42r1(
                plan=plan, attempt=attempt, **_context()
            )
        plan_path = Path(plan["local_plan_path"])
        assert plan_path.read_bytes() == canonical_json_bytes(plan)
        plan_identity = (plan_path.stat().st_dev, plan_path.stat().st_ino)

        plan_fsynced = False

        def track_recovery_fsync(descriptor: int) -> None:
            nonlocal plan_fsynced
            observed = os.fstat(descriptor)
            if (observed.st_dev, observed.st_ino) == plan_identity:
                plan_fsynced = True
            original_fsync(descriptor)

        original_write = journal._write_once_at  # noqa: SLF001

        def require_plan_fsync_before_advance(
            directory_fd: int, name: str, raw: bytes, *, label: str
        ) -> Any:
            if name == transport.PREFORMAL_KNOWN_HOSTS_NAME:
                assert plan_fsynced
            return original_write(directory_fd, name, raw, label=label)

        monkeypatch.setattr(journal.os, "fsync", track_recovery_fsync)
        monkeypatch.setattr(
            journal, "_write_once_at", require_plan_fsync_before_advance
        )
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        assert plan_fsynced


def test_receipt_recovery_fsyncs_visible_receipt_before_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-receipt-fsync-recovery-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("receipt-fsync-recovery"))
        attempt = _attempt(plan)
        journal.publish_pre_network_journal_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        journal.publish_network_start_v42r1(
            plan=plan, attempt=attempt, **_context()
        )
        receipt = _receipt(plan, attempt)
        outcome = transport.build_preformal_upload_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome_class=transport.PREFORMAL_OUTCOME_COMPLETE,
            receipt=receipt,
            **_context(),
        )
        original_fsync = journal.os.fsync
        failed = False

        def fail_receipt_fsync(descriptor: int) -> None:
            nonlocal failed
            target = ""
            try:
                target = os.readlink(f"/proc/self/fd/{descriptor}")
            except OSError:
                pass
            if target.endswith("/" + transport.PREFORMAL_RECEIPT_NAME) and not failed:
                failed = True
                raise OSError(5, "injected receipt fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(journal.os, "fsync", fail_receipt_fsync)
        with pytest.raises(OSError, match="injected receipt fsync"):
            journal.publish_outcome_v42r1(
                plan=plan,
                attempt=attempt,
                outcome=outcome,
                receipt=receipt,
                **_context(),
            )
        receipt_path = Path(plan["local_receipt_path"])
        assert receipt_path.read_bytes() == canonical_json_bytes(receipt)
        receipt_identity = (
            receipt_path.stat().st_dev,
            receipt_path.stat().st_ino,
        )

        receipt_fsynced = False

        def track_receipt_fsync(descriptor: int) -> None:
            nonlocal receipt_fsynced
            observed = os.fstat(descriptor)
            if (observed.st_dev, observed.st_ino) == receipt_identity:
                receipt_fsynced = True
            original_fsync(descriptor)

        original_write = journal._write_once_at  # noqa: SLF001

        def require_receipt_fsync_before_outcome(
            directory_fd: int, name: str, raw: bytes, *, label: str
        ) -> Any:
            if name == transport.PREFORMAL_OUTCOME_NAME:
                assert receipt_fsynced
            return original_write(directory_fd, name, raw, label=label)

        monkeypatch.setattr(journal.os, "fsync", track_receipt_fsync)
        monkeypatch.setattr(
            journal, "_write_once_at", require_receipt_fsync_before_outcome
        )
        journal.publish_outcome_v42r1(
            plan=plan,
            attempt=attempt,
            outcome=outcome,
            receipt=receipt,
            **_context(),
        )
        assert receipt_fsynced


def test_secure_birth_is_independent_of_hostile_umask_and_postbirth_fchmod(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-secure-birth-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("secure-birth"))
        attempt = _attempt(plan)

        def forbidden_fchmod(*args: Any, **kwargs: Any) -> Any:
            raise OSError(5, "post-birth fchmod must not be required")

        monkeypatch.setattr(journal.os, "fchmod", forbidden_fchmod)
        prior_umask = os.umask(0o777)
        try:
            journal.publish_pre_network_journal_v42r1(
                plan=plan, attempt=attempt, **_context()
            )
        finally:
            os.umask(prior_umask)
        assert stat.S_IMODE(Path(plan["local_chain_root"]).stat().st_mode) == 0o700
        slot = Path(plan["local_ordinal_slot"])
        assert stat.S_IMODE(slot.stat().st_mode) == 0o700
        assert all(
            stat.S_IMODE(path.stat().st_mode) == 0o400
            for path in slot.iterdir()
        )


def test_contextual_chain_is_detached_before_effectful_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-detached-chain-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        first_a = _plan(token=_token("detached-first-a"))
        first_attempt_a = _attempt(first_a)
        journal.publish_pre_network_journal_v42r1(
            plan=first_a, attempt=first_attempt_a, **_context()
        )
        journal.publish_network_start_v42r1(
            plan=first_a, attempt=first_attempt_a, **_context()
        )
        first_outcome_a = _abandoned_outcome(first_a, first_attempt_a)
        journal.publish_outcome_v42r1(
            plan=first_a,
            attempt=first_attempt_a,
            outcome=first_outcome_a,
            **_context(),
        )
        row_a = {
            "plan": first_a,
            "attempt": first_attempt_a,
            "outcome": first_outcome_a,
        }
        caller_chain = [row_a]
        second = _plan(
            token=_token("detached-second"), predecessor_chain=caller_chain
        )
        second_attempt = _attempt(second, predecessor_chain=caller_chain)

        first_b = _plan(token=_token("detached-first-b"))
        first_attempt_b = _attempt(first_b)
        first_outcome_b = _abandoned_outcome(first_b, first_attempt_b)
        row_b = {
            "plan": first_b,
            "attempt": first_attempt_b,
            "outcome": first_outcome_b,
        }
        original_open_snapshot = journal._open_snapshot  # noqa: SLF001

        def mutate_caller_and_disk(**kwargs: Any) -> Any:
            assert kwargs["predecessor_chain"] is not caller_chain
            caller_chain[0] = row_b
            slot = Path(first_a["local_ordinal_slot"])
            for name, raw in journal._expected_predecessor_publications(  # noqa: SLF001
                row_b
            ):
                path = slot / name
                path.unlink()
                path.write_bytes(raw)
                path.chmod(0o400)
            return original_open_snapshot(**kwargs)

        monkeypatch.setattr(journal, "_open_snapshot", mutate_caller_and_disk)
        with pytest.raises(journal.V42PreformalJournalError):
            journal.publish_pre_network_journal_v42r1(
                plan=second,
                attempt=second_attempt,
                predecessor_chain=caller_chain,
                **_context(),
            )
        assert not Path(second["local_ordinal_slot"]).exists()


def test_predecessor_outcome_is_fsynced_before_successor_slot_birth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-predecessor-durability-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        first = _plan(token=_token("predecessor-durability-first"))
        first_attempt = _attempt(first)
        journal.publish_pre_network_journal_v42r1(
            plan=first, attempt=first_attempt, **_context()
        )
        journal.publish_network_start_v42r1(
            plan=first, attempt=first_attempt, **_context()
        )
        first_outcome = _abandoned_outcome(first, first_attempt)
        original_fsync = journal.os.fsync
        failed = False

        def fail_outcome_fsync(descriptor: int) -> None:
            nonlocal failed
            target = ""
            try:
                target = os.readlink(f"/proc/self/fd/{descriptor}")
            except OSError:
                pass
            if target.endswith("/" + transport.PREFORMAL_OUTCOME_NAME) and not failed:
                failed = True
                raise OSError(5, "injected predecessor outcome fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(journal.os, "fsync", fail_outcome_fsync)
        with pytest.raises(OSError, match="predecessor outcome fsync"):
            journal.publish_outcome_v42r1(
                plan=first,
                attempt=first_attempt,
                outcome=first_outcome,
                **_context(),
            )
        outcome_path = Path(first["local_outcome_path"])
        assert outcome_path.read_bytes() == canonical_json_bytes(first_outcome)
        outcome_identity = (
            outcome_path.stat().st_dev,
            outcome_path.stat().st_ino,
        )
        chain = [
            {"plan": first, "attempt": first_attempt, "outcome": first_outcome}
        ]
        second = _plan(
            token=_token("predecessor-durability-second"),
            predecessor_chain=chain,
        )
        second_attempt = _attempt(second, predecessor_chain=chain)

        outcome_fsynced = False

        def track_outcome_fsync(descriptor: int) -> None:
            nonlocal outcome_fsynced
            observed = os.fstat(descriptor)
            if (observed.st_dev, observed.st_ino) == outcome_identity:
                outcome_fsynced = True
            original_fsync(descriptor)

        original_create = journal._create_directory_at  # noqa: SLF001

        def require_outcome_fsync_before_slot_birth(
            parent_fd: int, name: str, *, label: str
        ) -> Any:
            if label == "pre-formal current ordinal slot":
                assert outcome_fsynced
            return original_create(parent_fd, name, label=label)

        monkeypatch.setattr(journal.os, "fsync", track_outcome_fsync)
        monkeypatch.setattr(
            journal,
            "_create_directory_at",
            require_outcome_fsync_before_slot_birth,
        )
        journal.publish_pre_network_journal_v42r1(
            plan=second,
            attempt=second_attempt,
            predecessor_chain=chain,
            **_context(),
        )
        assert outcome_fsynced


def test_directory_creation_fsync_failures_do_not_leak_descriptors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-directory-fd-cleanup-", dir="/tmp"
    ) as base:
        parent_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY)
        before = len(os.listdir("/proc/self/fd"))

        def fail_fsync(descriptor: int) -> None:
            raise OSError(5, "injected directory fsync failure")

        monkeypatch.setattr(journal.os, "fsync", fail_fsync)
        try:
            for index in range(8):
                with pytest.raises(OSError, match="directory fsync"):
                    journal._create_directory_at(  # noqa: SLF001
                        parent_fd,
                        f"child-{index}",
                        label=f"child {index}",
                    )
            after = len(os.listdir("/proc/self/fd"))
            assert after == before
        finally:
            os.close(parent_fd)


def test_absolute_parent_verification_failure_does_not_leak_descriptor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-parent-fd-cleanup-", dir="/tmp"
    ) as base:
        local_parent = Path(base)
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", local_parent)
        before = len(os.listdir("/proc/self/fd"))

        def reject_first_component(pin: Any) -> None:
            raise journal.V42PreformalJournalError(
                "injected parent component verification failure"
            )

        monkeypatch.setattr(
            journal, "_verify_directory_pin", reject_first_component
        )
        with pytest.raises(
            journal.V42PreformalJournalError,
            match="parent component verification",
        ):
            journal._open_absolute_parent(  # noqa: SLF001
                {"local_transport_parent": str(local_parent)}
            )
        after = len(os.listdir("/proc/self/fd"))
        assert after == before


def test_fifo_at_expected_prefix_name_is_rejected_without_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-fifo-prefix-", dir="/tmp"
    ) as base:
        monkeypatch.setattr(transport, "LOCAL_TRANSPORT_PARENT", Path(base))
        plan = _plan(token=_token("fifo-prefix"))
        attempt = _attempt(plan)
        original_write = journal._write_once_at  # noqa: SLF001

        def stop_before_plan(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("leave an empty unclaimed slot")

        monkeypatch.setattr(journal, "_write_once_at", stop_before_plan)
        with pytest.raises(RuntimeError, match="empty unclaimed"):
            journal.publish_pre_network_journal_v42r1(
                plan=plan, attempt=attempt, **_context()
            )
        monkeypatch.setattr(journal, "_write_once_at", original_write)
        os.mkfifo(plan["local_plan_path"], 0o400)

        child = os.fork()
        if child == 0:
            signal.alarm(2)
            try:
                journal.publish_pre_network_journal_v42r1(
                    plan=plan, attempt=attempt, **_context()
                )
            except journal.V42PreformalJournalError:
                os._exit(0)
            except BaseException:
                os._exit(2)
            os._exit(3)
        _, status = os.waitpid(child, 0)
        assert os.WIFEXITED(status)
        assert os.WEXITSTATUS(status) == 0


def test_no_builder_argument_can_supply_opaque_ids_ordinal_or_ssh_template() -> None:
    parameters = transport.build_preformal_upload_plan_v42r1.__annotations__
    assert "source_manifest_id" not in parameters
    assert "transport_manifest_id" not in parameters
    assert "preformal_upload_ordinal" not in parameters
    assert "previous_preformal_upload_outcome_id" not in parameters
    assert "authorized_ssh_argv_template" not in parameters


def _receiver_wire(
    *,
    plan: dict[str, Any],
    attempt: dict[str, Any],
    salt: str = "one",
    header: dict[str, Any] | None = None,
    body_overrides: dict[str, bytes] | None = None,
) -> tuple[dict[str, Any], bytes]:
    controls, _loader_raw, _receiver_raw = _fixture(salt)
    if header is None:
        header = transport.build_preformal_upload_stream_header_v42r1(
            plan=plan, attempt=attempt, **_context(salt)
        )
    bodies = {
        receiver.PLAN_NAME: canonical_json_bytes(plan),
        receiver.ATTEMPT_NAME: canonical_json_bytes(attempt),
        **controls,
    }
    bodies.update(body_overrides or {})
    header_raw = canonical_json_bytes(header)
    wire = (
        receiver.MAGIC
        + len(header_raw).to_bytes(8, "big")
        + header_raw
        + b"".join(bodies[name] for name in receiver.FRAME_ORDER)
    )
    return header, wire


def _read_receiver_ingress(
    wire: bytes, *, plan: dict[str, Any], attempt: dict[str, Any]
) -> tuple[
    tuple[
        dict[str, object],
        dict[str, object],
        dict[str, object],
        dict[str, bytes],
        dict[str, object],
    ],
    bytes,
]:
    _controls, loader_raw, receiver_raw = _fixture()
    with tempfile.TemporaryFile() as stream:
        stream.write(wire)
        stream.seek(0)
        result = receiver._read_and_verify_ingress_v42r1(  # noqa: SLF001
            stream.fileno(),
            plan_id=plan["preformal_upload_plan_id"],
            attempt_id=attempt["preformal_upload_attempt_id"],
            loader_sha256=hashlib.sha256(loader_raw).hexdigest(),
            loader_byte_count=len(loader_raw),
            receiver_sha256=hashlib.sha256(receiver_raw).hexdigest(),
            receiver_byte_count=len(receiver_raw),
        )
        remaining = stream.read()
    return result, remaining


def test_receiver_pure_contract_attempt_header_and_receipt_are_byte_exact() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    header = transport.build_preformal_upload_stream_header_v42r1(
        plan=plan, attempt=attempt, **_context()
    )
    receipt = _receipt(plan, attempt)

    assert receiver._expected_remote_tcb_contract() == plan[  # noqa: SLF001
        "remote_startup_tcb_contract"
    ]
    assert receiver._expected_stream_contract() == plan[  # noqa: SLF001
        "stream_protocol_contract"
    ]
    assert receiver._expected_receiver_contract() == plan[  # noqa: SLF001
        "remote_receiver_contract"
    ]
    assert receiver._attempt_from_plan(plan) == attempt  # noqa: SLF001
    assert receiver._header_from_documents(plan, attempt) == header  # noqa: SLF001
    receiver_receipt = receiver._build_receipt_v42r1(  # noqa: SLF001
        plan=plan,
        attempt=attempt,
        header=header,
        parent_fact=_parent_fact(),
    )
    assert receiver_receipt == receipt
    assert canonical_json_bytes(receiver_receipt) == canonical_json_bytes(receipt)


def test_receiver_ingress_round_trip_prebuffers_only_nonarchive_frames() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    header, wire = _receiver_wire(plan=plan, attempt=attempt)
    (observed_plan, observed_attempt, observed_header, buffered, archive_frame), remaining = (
        _read_receiver_ingress(wire, plan=plan, attempt=attempt)
    )
    controls, _loader_raw, _receiver_raw = _fixture()

    assert observed_plan == plan
    assert observed_attempt == attempt
    assert observed_header == header
    assert archive_frame == header["frames"][-1]
    assert buffered == {
        receiver.PLAN_NAME: canonical_json_bytes(plan),
        receiver.ATTEMPT_NAME: canonical_json_bytes(attempt),
        **{
            name: controls[name]
            for name in receiver.FRAME_ORDER[2:-1]
        },
    }
    assert receiver.ARCHIVE_NAME not in buffered
    assert remaining == controls[receiver.ARCHIVE_NAME]


def test_receiver_ingress_rejects_noncanonical_reordered_and_spliced_frames() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    header, wire = _receiver_wire(plan=plan, attempt=attempt)
    prefix_count = len(receiver.MAGIC) + 8
    header_raw = canonical_json_bytes(header)

    malformed_magic = bytes([wire[0] ^ 1]) + wire[1:]
    with pytest.raises(receiver._ReceiverFailure):  # noqa: SLF001
        _read_receiver_ingress(malformed_magic, plan=plan, attempt=attempt)

    noncanonical_header = header_raw + b" "
    noncanonical_wire = (
        receiver.MAGIC
        + len(noncanonical_header).to_bytes(8, "big")
        + noncanonical_header
        + wire[prefix_count + len(header_raw) :]
    )
    with pytest.raises(receiver._ReceiverFailure):  # noqa: SLF001
        _read_receiver_ingress(noncanonical_wire, plan=plan, attempt=attempt)

    reordered = copy.deepcopy(header)
    reordered["frames"][2], reordered["frames"][3] = (
        reordered["frames"][3],
        reordered["frames"][2],
    )
    reordered.pop("preformal_stream_header_id")
    reordered["preformal_stream_header_id"] = receiver._content_id(  # noqa: SLF001
        receiver._DOMAIN + "preformal-stream-header", reordered  # noqa: SLF001
    )
    _unused, reordered_wire = _receiver_wire(
        plan=plan, attempt=attempt, header=reordered
    )
    with pytest.raises(receiver._ReceiverFailure):  # noqa: SLF001
        _read_receiver_ingress(reordered_wire, plan=plan, attempt=attempt)

    other_plan = _plan(salt="two")
    other_attempt = _attempt(other_plan, salt="two")
    other_attempt_raw = canonical_json_bytes(other_attempt)
    spliced = copy.deepcopy(header)
    spliced["frames"][1]["sha256"] = hashlib.sha256(other_attempt_raw).hexdigest()
    spliced["frames"][1]["byte_count"] = len(other_attempt_raw)
    spliced.pop("preformal_stream_header_id")
    spliced["preformal_stream_header_id"] = receiver._content_id(  # noqa: SLF001
        receiver._DOMAIN + "preformal-stream-header", spliced  # noqa: SLF001
    )
    _unused, spliced_wire = _receiver_wire(
        plan=plan,
        attempt=attempt,
        header=spliced,
        body_overrides={receiver.ATTEMPT_NAME: other_attempt_raw},
    )
    with pytest.raises(receiver._ReceiverFailure):  # noqa: SLF001
        _read_receiver_ingress(spliced_wire, plan=plan, attempt=attempt)


def test_receiver_ingress_rejects_truncation_and_nonarchive_body_tampering() -> None:
    plan = _plan()
    attempt = _attempt(plan)
    _header, wire = _receiver_wire(plan=plan, attempt=attempt)
    controls, _loader_raw, _receiver_raw = _fixture()
    archive_count = len(controls[receiver.ARCHIVE_NAME])
    nonarchive_wire = wire[:-archive_count]

    with pytest.raises(receiver._ReceiverFailure):  # noqa: SLF001
        _read_receiver_ingress(nonarchive_wire[:-1], plan=plan, attempt=attempt)

    header_count = int.from_bytes(
        wire[len(receiver.MAGIC) : len(receiver.MAGIC) + 8], "big"
    )
    first_body = len(receiver.MAGIC) + 8 + header_count
    tampered = bytearray(wire)
    tampered[first_body] ^= 1
    with pytest.raises(receiver._ReceiverFailure):  # noqa: SLF001
        _read_receiver_ingress(bytes(tampered), plan=plan, attempt=attempt)


def test_receiver_source_executes_in_isolated_no_site_stdlib_namespace() -> None:
    _controls, _loader_raw, receiver_raw = _fixture()
    probe = "\n".join(
        (
            "import sys",
            "raw = sys.stdin.buffer.read()",
            "ns = {'__name__': 'receiver_artifact_probe', '__file__': '<receiver>', '__package__': None}",
            "exec(compile(raw, '<receiver>', 'exec', dont_inherit=True), ns, ns)",
            "assert callable(ns.get('main_v42r1'))",
            "assert not any(name == 'acfqp' or name.startswith('acfqp.') for name in sys.modules)",
            "assert all('Auditable Coarse-to-Fine Quotient Planning' not in path for path in sys.path)",
            "sys.stdout.buffer.write(b'RECEIVER_STDLIB_ONLY')",
        )
    )
    completed = subprocess.run(
        ["/usr/bin/python3", "-I", "-S", "-B", "-c", probe],
        input=receiver_raw,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"LC_CTYPE": "C.UTF-8"},
        close_fds=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    assert completed.stdout == b"RECEIVER_STDLIB_ONLY"
    assert completed.stderr == b""


def test_receiver_control_birth_is_secure_and_hashes_before_first_fsync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-receiver-control-", dir="/tmp"
    ) as base:
        parent_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        directory_pin: dict[str, object] | None = None
        file_pin: dict[str, object] | None = None
        prior_umask = os.umask(0o777)
        try:
            directory_pin = receiver._create_directory_at(  # noqa: SLF001
                parent_fd, "scratch", label="test scratch"
            )
            events: list[str] = []
            original_pin = receiver._pin_file_at  # noqa: SLF001
            original_fsync = receiver.os.fsync

            def traced_pin(*args: Any, **kwargs: Any) -> dict[str, object]:
                events.append("HASH_AND_PIN")
                return original_pin(*args, **kwargs)

            def traced_fsync(descriptor: int) -> None:
                events.append("FSYNC")
                original_fsync(descriptor)

            monkeypatch.setattr(receiver, "_pin_file_at", traced_pin)
            monkeypatch.setattr(receiver.os, "fsync", traced_fsync)
            raw = b"receiver control bytes\n"
            file_pin = receiver._create_control_from_bytes(  # noqa: SLF001
                directory_fd=directory_pin["descriptor"],
                name="CONTROL.bin",
                raw=raw,
                fact={
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_count": len(raw),
                },
            )
            assert events == ["HASH_AND_PIN", "FSYNC", "FSYNC"]
            observed_dir = os.stat(base + "/scratch", follow_symlinks=False)
            observed_file = os.stat(
                base + "/scratch/CONTROL.bin", follow_symlinks=False
            )
            assert stat.S_IMODE(observed_dir.st_mode) == 0o700
            assert stat.S_IMODE(observed_file.st_mode) == 0o400
            assert Path(base, "scratch", "CONTROL.bin").read_bytes() == raw
        finally:
            os.umask(prior_umask)
            if file_pin is not None:
                os.close(file_pin["descriptor"])
            if directory_pin is not None:
                os.close(directory_pin["descriptor"])
            os.close(parent_fd)


def test_receiver_post_pin_fsync_failure_does_not_leak_descriptors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-receiver-fsync-failure-", dir="/tmp"
    ) as base:
        parent_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        directory_pin = receiver._create_directory_at(  # noqa: SLF001
            parent_fd, "scratch", label="test scratch"
        )
        original_fsync = receiver.os.fsync
        injected = False

        def fail_first_fsync(descriptor: int) -> None:
            nonlocal injected
            if not injected:
                injected = True
                raise OSError("injected receiver file fsync failure")
            original_fsync(descriptor)

        monkeypatch.setattr(receiver.os, "fsync", fail_first_fsync)
        before = len(os.listdir("/proc/self/fd"))
        raw = b"must close both writer and read pin\n"
        try:
            with pytest.raises(OSError, match="injected receiver file fsync"):
                receiver._create_control_from_bytes(  # noqa: SLF001
                    directory_fd=directory_pin["descriptor"],
                    name="CONTROL.bin",
                    raw=raw,
                    fact={
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "byte_count": len(raw),
                    },
                )
            after = len(os.listdir("/proc/self/fd"))
            assert after == before
        finally:
            os.close(directory_pin["descriptor"])
            os.close(parent_fd)


def test_receiver_fifo_pin_is_rejected_without_blocking() -> None:
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-receiver-fifo-", dir="/tmp"
    ) as base:
        parent_fd = os.open(base, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        os.mkfifo(Path(base, "CONTROL.bin"), 0o400)
        child = os.fork()
        if child == 0:
            signal.alarm(2)
            try:
                receiver._pin_file_at(  # noqa: SLF001
                    parent_fd,
                    "CONTROL.bin",
                    expected_sha256=hashlib.sha256(b"x").hexdigest(),
                    expected_count=1,
                    label="hostile fifo",
                )
            except receiver._ReceiverFailure:  # noqa: SLF001
                os._exit(0)
            except BaseException:
                os._exit(2)
            os._exit(3)
        _, status = os.waitpid(child, 0)
        os.close(parent_fd)
        assert os.WIFEXITED(status)
        assert os.WEXITSTATUS(status) == 0


def test_receiver_archive_requires_exact_eof_and_closes_writer_on_failure() -> None:
    raw = b"exact archive body"
    fact = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_count": len(raw),
    }
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-receiver-archive-eof-", dir="/tmp"
    ) as base:
        directory_fd = os.open(
            base, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        )
        before = len(os.listdir("/proc/self/fd"))
        try:
            with tempfile.TemporaryFile() as stream:
                stream.write(raw + b"TRAILING")
                stream.seek(0)
                with pytest.raises(
                    receiver._ReceiverFailure,  # noqa: SLF001
                    match="trailing stream bytes",
                ):
                    receiver._create_archive_from_stream(  # noqa: SLF001
                        directory_fd=directory_fd,
                        input_fd=stream.fileno(),
                        name=receiver.ARCHIVE_NAME,
                        fact=fact,
                    )
            after = len(os.listdir("/proc/self/fd"))
            assert after == before
            archive = Path(base, receiver.ARCHIVE_NAME)
            assert archive.read_bytes() == raw
            assert stat.S_IMODE(archive.stat().st_mode) == 0o400
        finally:
            os.close(directory_fd)


def test_receiver_materializer_creates_exact_order_inventory_and_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = copy.deepcopy(_plan())
    controls, _loader_raw, _receiver_raw = _fixture()
    with tempfile.TemporaryDirectory(
        prefix="acfqp-v42-receiver-materializer-", dir="/tmp"
    ) as base:
        token = plan["upload_token"]
        plan["preformal_scratch_root"] = (
            base + "/" + receiver.PREFORMAL_SCRATCH_PREFIX + token
        )
        plan["preformal_ledger_stage_root"] = (
            base + "/" + receiver.PREFORMAL_LEDGER_STAGE_PREFIX + token
        )
        attempt = receiver._attempt_from_plan(plan)  # noqa: SLF001
        header = receiver._header_from_documents(plan, attempt)  # noqa: SLF001
        parent_fact = {
            "path": base,
            "node_type": "DIRECTORY",
            "mode": stat.S_IMODE(os.stat(base).st_mode),
            "uid": os.getuid(),
            "gid": os.getgid(),
            "world_writable": False,
            "primary_gid_principals": [authority.REMOTE_USER],
            "explicit_group_members": [],
        }

        def fake_open_parent() -> tuple[
            int, list[dict[str, object]], int, dict[str, object]
        ]:
            root_fd = os.open(
                "/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            parent_fd = os.open(
                base,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            return root_fd, [{"descriptor": parent_fd}], parent_fd, parent_fact

        creation_order: list[str] = []
        original_open_new = receiver._open_new_control  # noqa: SLF001

        def traced_open_new(directory_fd: int, name: str, label: str) -> int:
            creation_order.append(name)
            return original_open_new(directory_fd, name, label)

        monkeypatch.setattr(receiver, "REMOTE_PARENT", base)
        monkeypatch.setattr(receiver, "FIXED_REMOTE_ROOT", base + "/fixed-root")
        monkeypatch.setattr(
            receiver,
            "FIXED_TRANSPORT_LEDGER_ROOT",
            base + "/fixed-transport-ledger",
        )
        monkeypatch.setattr(receiver, "_open_remote_parent", fake_open_parent)
        monkeypatch.setattr(
            receiver, "_verify_remote_parent", lambda _pins, _parent_fd: None
        )
        monkeypatch.setattr(receiver, "_open_new_control", traced_open_new)

        buffered = {
            name: controls[name] for name in receiver.FRAME_ORDER[2:-1]
        }
        before = len(os.listdir("/proc/self/fd"))
        with tempfile.TemporaryFile() as archive_stream:
            archive_stream.write(controls[receiver.ARCHIVE_NAME])
            archive_stream.seek(0)
            receipt = receiver._materialize_and_build_receipt_v42r1(  # noqa: SLF001
                input_fd=archive_stream.fileno(),
                plan=plan,
                attempt=attempt,
                header=header,
                buffered=buffered,
                archive_frame=header["frames"][-1],
            )
        after = len(os.listdir("/proc/self/fd"))

        assert after == before
        assert creation_order == list(receiver.CONTROL_CREATION_ORDER)
        assert sorted(os.listdir(plan["preformal_scratch_root"])) == list(
            receiver.CONTROL_NAMES
        )
        assert os.listdir(plan["preformal_ledger_stage_root"]) == []
        for fact in plan["control_facts"]:
            path = Path(plan["preformal_scratch_root"], fact["name"])
            assert path.read_bytes() == controls[fact["name"]]
            observed = path.stat(follow_symlinks=False)
            assert stat.S_IMODE(observed.st_mode) == 0o400
            assert observed.st_nlink == 1
        assert receipt["scratch_parent_fact"] == parent_fact
        assert receipt["control_creation_order"] == list(
            receiver.CONTROL_CREATION_ORDER
        )
        assert receipt["fixed_remote_root_effect_performed"] is False
        assert receipt["trusted_bootstrap_effect_performed"] is False
