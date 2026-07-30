from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import hashlib

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner
from acfqp import v075_portable_occurrence_evidence_bundle_v2 as bundle
from tests import test_v075_private_observer_boundary_v2 as observer_fixture
from tests.test_v075_observer_signed_multiround_occurrence_runner_v2 import (
    REPOSITORY_ROOT,
    _exact_schedule,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-portable-evidence-bundle-test:v2"
        + b"\x00"
        + label.encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=1)
def _build_portable_closed_bundle():
    """One reusable non-held-out K7 bundle for public IPC/replay tests."""

    generated, salt, namespace, authorization, signer = (
        observer_fixture._fixture(  # noqa: SLF001
            "portable-observer-signed-multiround-capped"
        )
    )
    schedule, verification = _exact_schedule(namespace, context_index=0)
    captured = {}

    def sink(roots):
        captured.update(roots)
        with pytest.raises(TypeError):
            roots["multiround_result"] = object()
        # The callback result is intentionally foreign.  The runner must
        # ignore it and return its already-frozen typed result.
        return {"multiround_result": object()}

    result = (
        runner.run_v075_construction_observer_signed_multiround_occurrence_v2(
            repository_root=REPOSITORY_ROOT,
            namespace=namespace,
            schedule=schedule,
            schedule_verification=verification,
            authority=authorization,
            private_salt=salt,
            private_environment=generated.secret_laws_for_commitment(),
            observer_signer=signer,
            session_external_id=_id("portable-session"),
            evidence_sink=sink,
        )
    )
    assert result is captured["multiround_result"]
    artifact = bundle.freeze_v075_portable_occurrence_evidence_bundle_v2(
        evidence_roots=captured,
    )
    return result, captured, artifact


@pytest.fixture(scope="module")
def portable_closed_bundle():
    return _build_portable_closed_bundle()


def _raw(document) -> bytes:
    return canonical_json_bytes(document)


def _rehash_complete_bundle_wrapper(document) -> bytes:
    """Rehash every public wrapper after an adversarial semantic edit."""

    prior_to_current = {}
    for record in document["artifact_records"]:
        record["dependency_record_ids"] = sorted(
            prior_to_current.get(item, item)
            for item in record["dependency_record_ids"]
        )
        prior_id = record["record_id"]
        record["record_id"] = bundle._hash(  # noqa: SLF001
            record["artifact_domain_tag"],
            {
                key: value
                for key, value in record.items()
                if key != "record_id"
            },
        )
        prior_to_current[prior_id] = record["record_id"]
    for binding in document["root_bindings"]:
        binding["record_ids"] = [
            prior_to_current.get(item, item)
            for item in binding["record_ids"]
        ]
    document["bundle_id"] = bundle._hash(  # noqa: SLF001
        bundle.DOMAIN_TAGS["bundle"],
        {
            key: value
            for key, value in document.items()
            if key != "bundle_id"
        },
    )
    return _raw(document)


def _record_for_role(document, role):
    return next(
        item
        for item in document["artifact_records"]
        if item["role"] == role
    )


def test_complete_portable_table_raw_replays_and_keeps_all_locks_closed(
    portable_closed_bundle,
) -> None:
    result, roots, artifact = portable_closed_bundle
    replayed = bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
        artifact.canonical_bytes
    )
    document = replayed.to_document()
    roles = {item.role for item in replayed.records}
    assert tuple(roots) == bundle.REQUIRED_ROOT_NAMES
    assert replayed.bundle_id == artifact.bundle_id
    assert replayed.canonical_bytes == artifact.canonical_bytes
    assert result.canonical_bytes == roots["multiround_result"].canonical_bytes
    assert {
        "SIGNED_CONTROL_JOURNAL_HEAD",
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY",
        "CONTROLLED_ROOT_INTENT",
        "TRANSITION_STREAM",
        "SIGNED_BATCH_REQUEST",
        "SIGNED_BATCH_OUTCOME",
        "SIGNED_OBSERVATION_BATCH",
        "SIGNED_APPEND_RECEIPT",
        "CONTROLLED_ROOT_APPEND",
        "OBSERVER_SIGNED_SUPPORT_EVIDENCE",
        "CONTROLLED_COMPLETE_SUPPORT_FREEZE",
        "LIVE_MODEL_EPOCH",
        "NUMERICAL_MODEL",
        "NUMERICAL_PLANNING_PROOF",
        "DYNAMIC_CHILD_CLOSURE",
        "DYNAMIC_CHILD_CLOSURE_VERIFICATION",
        "SIGNED_BATCH_JOURNAL_CLOSURE",
        "SIGNED_CONTROL_CLOSURE",
        "SIGNED_CONTROL_RECONCILIATION",
        "CONTROLLED_JOURNAL_CLOSURE",
        "CONSTRUCTION_LINEAGE",
        "CONSTRUCTION_LIFECYCLE",
        "CONSTRUCTION_PLANNING_INPUT",
        "CLOSED_RECONCILIATION",
        "MULTIROUND_RESULT",
    } <= roles
    seen = set()
    for index, record in enumerate(replayed.records):
        assert record.index == index
        assert set(record.dependency_record_ids) <= seen
        seen.add(record.record_id)
    assert document["semantic_registry_replay_complete"] is False
    assert document["fresh_heldout_accessed"] is False
    assert document["official_execution_allowed"] is False
    assert document["production_authorizing"] is False
    assert document["scientific_endpoint_credit_allowed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False


def test_portable_record_byte_mutation_and_role_transplant_fail(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    original = artifact.to_document()

    mutated = deepcopy(original)
    record = mutated["artifact_records"][0]
    raw_hex = record["canonical_artifact_bytes_hex"]
    record["canonical_artifact_bytes_hex"] = (
        raw_hex[:-1] + ("0" if raw_hex[-1] != "0" else "1")
    )
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="canonical JSON|content ID|raw bytes|UTF-8",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(mutated)
        )

    transplanted = deepcopy(original)
    record = transplanted["artifact_records"][0]
    record["role"] = "MULTIROUND_RESULT"
    record["artifact_domain_tag"] = (
        bundle.DOMAIN_TAGS["record"] + ":multiround_result"
    )
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="role-transplanted|foreign schema",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(transplanted)
        )


@pytest.mark.parametrize("location", ["bundle", "record"])
def test_portable_hidden_extra_fields_fail(
    portable_closed_bundle,
    location,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    if location == "bundle":
        attacked["hidden"] = True
    else:
        attacked["artifact_records"][0]["hidden"] = True
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="hidden extra fields",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(attacked)
        )


def test_portable_missing_duplicate_and_unknown_dependencies_fail(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    original = artifact.to_document()

    missing = deepcopy(original)
    dependency_id = next(
        dependency
        for record in missing["artifact_records"]
        for dependency in record["dependency_record_ids"]
    )
    missing["artifact_records"] = [
        record
        for record in missing["artifact_records"]
        if record["record_id"] != dependency_id
    ]
    missing["artifact_count"] -= 1
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="missing",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(missing)
        )

    duplicate = deepcopy(original)
    duplicate["artifact_records"].append(
        deepcopy(duplicate["artifact_records"][-1])
    )
    duplicate["artifact_count"] += 1
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="duplicate",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(duplicate)
        )

    unknown = deepcopy(original)
    unknown["artifact_records"][-1]["dependency_record_ids"].append(
        _id("unknown-dependency")
    )
    unknown["artifact_records"][-1]["dependency_record_ids"].sort()
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="missing",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(unknown)
        )


def test_portable_cyclic_and_out_of_order_dependencies_fail(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    original = artifact.to_document()

    cyclic = deepcopy(original)
    first = cyclic["artifact_records"][0]
    second = cyclic["artifact_records"][1]
    first["dependency_record_ids"] = [second["record_id"]]
    second["dependency_record_ids"] = [first["record_id"]]
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="cyclic",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(cyclic)
        )

    out_of_order = deepcopy(original)
    child_index = next(
        index
        for index, record in enumerate(out_of_order["artifact_records"])
        if record["dependency_record_ids"]
    )
    dependency_id = out_of_order["artifact_records"][child_index][
        "dependency_record_ids"
    ][0]
    dependency_index = next(
        index
        for index, record in enumerate(out_of_order["artifact_records"])
        if record["record_id"] == dependency_id
    )
    dependent = out_of_order["artifact_records"].pop(child_index)
    if dependency_index > child_index:
        dependency_index -= 1
    out_of_order["artifact_records"].insert(dependency_index, dependent)
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="out-of-order",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(out_of_order)
        )


def test_portable_unknown_role_and_production_entrypoint_remain_closed(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    attacked["artifact_records"][0]["role"] = "UNKNOWN_ROLE"
    attacked["artifact_records"][0]["artifact_domain_tag"] = (
        bundle.DOMAIN_TAGS["record"] + ":unknown_role"
    )
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="role-transplanted",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _raw(attacked)
        )
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceProductionV2NotReady
    ):
        bundle.open_v075_production_portable_occurrence_evidence_bundle_v2()


@pytest.mark.parametrize(
    ("role", "field", "value", "message"),
    (
        (
            "MULTIROUND_RESULT",
            "private_environment",
            {"hidden": "law"},
            "undeclared raw fields|private material",
        ),
        (
            "LIVE_MODEL_EPOCH",
            "official_execution_allowed",
            True,
            "forbidden claim",
        ),
        (
            "LIVE_MODEL_EPOCH",
            "plan_certificate",
            True,
            "forbidden claim",
        ),
    ),
)
def test_rehashed_private_field_and_embedded_claim_attacks_fail(
    portable_closed_bundle,
    role,
    field,
    value,
    message,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    record = _record_for_role(attacked, role)
    raw_document = bundle._strict_json_document(  # noqa: SLF001
        bytes.fromhex(record["canonical_artifact_bytes_hex"]),
        label="attack source",
    )
    raw_document[field] = value
    record["canonical_artifact_bytes_hex"] = _raw(raw_document).hex()
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match=message,
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(attacked)
        )


def test_rehashed_cached_content_id_and_same_schema_role_transplant_fail(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle

    cached_id_attack = deepcopy(artifact.to_document())
    record = _record_for_role(cached_id_attack, "MULTIROUND_RESULT")
    raw_document = bundle._strict_json_document(  # noqa: SLF001
        bytes.fromhex(record["canonical_artifact_bytes_hex"]),
        label="cached ID attack",
    )
    forged_result_id = _id("forged-result-cached-id")
    raw_document["result_id"] = forged_result_id
    record["semantic_artifact_id"] = forged_result_id
    record["canonical_artifact_bytes_hex"] = _raw(raw_document).hex()
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="cached content ID differs from semantic recomputation",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(cached_id_attack)
        )

    role_attack = deepcopy(artifact.to_document())
    record = _record_for_role(role_attack, "CONTROLLED_ROOT_INTENT")
    record["role"] = "CONTROLLED_CHILD_INTENT"
    record["artifact_domain_tag"] = (
        bundle.DOMAIN_TAGS["record"] + ":controlled_child_intent"
    )
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="embedded semantic authority",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(role_attack)
        )


@pytest.mark.parametrize("operation", ["delete", "add"])
def test_rehashed_dependency_edge_attacks_fail(
    portable_closed_bundle,
    operation,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    records = attacked["artifact_records"]
    if operation == "delete":
        target = next(
            item for item in records if item["dependency_record_ids"]
        )
        target["dependency_record_ids"].pop()
    else:
        target = next(
            item
            for item in records
            if any(
                earlier["record_id"]
                not in item["dependency_record_ids"]
                for earlier in records[: item["index"]]
            )
        )
        earlier = records[: target["index"]]
        injected = next(
            item["record_id"]
            for item in earlier
            if item["record_id"] not in target["dependency_record_ids"]
        )
        target["dependency_record_ids"].append(injected)
        target["dependency_record_ids"].sort()
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="dependencies differ from raw artifact semantics",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(attacked)
        )


def test_rehashed_named_root_permutation_fails(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    bindings = {
        item["name"]: item for item in attacked["root_bindings"]
    }
    (
        bindings["initial_schedule"]["record_ids"],
        bindings["initial_schedule_verification"]["record_ids"],
    ) = (
        bindings["initial_schedule_verification"]["record_ids"],
        bindings["initial_schedule"]["record_ids"],
    )
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="named roots differ from authoritative result lineage",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(attacked)
        )


def test_sink_snapshot_includes_private_cached_content_ids(
    portable_closed_bundle,
) -> None:
    result, roots, _artifact = portable_closed_bundle
    before = runner._snapshot_construction_evidence_roots(roots)  # noqa: SLF001
    prior_result_id = result._result_id  # noqa: SLF001
    try:
        object.__setattr__(
            result,
            "_result_id",
            _id("mutated-cached-result-id"),
        )
        assert (
            runner._snapshot_construction_evidence_roots(  # noqa: SLF001
                roots
            )
            != before
        )
    finally:
        object.__setattr__(result, "_result_id", prior_result_id)


@pytest.mark.parametrize(
    ("nested_path", "field", "value"),
    (
        (
            "semantic_authority",
            "semantic_verification_id",
            _id("forged-nested-semantic-verification"),
        ),
        (
            "stream_identity",
            "seed_serialized",
            True,
        ),
    ),
)
def test_rehashed_nested_registered_document_byte_mismatch_fails(
    portable_closed_bundle,
    nested_path,
    field,
    value,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    intent = _record_for_role(attacked, "CONTROLLED_ROOT_INTENT")
    document = bundle._strict_json_document(  # noqa: SLF001
        bytes.fromhex(intent["canonical_artifact_bytes_hex"]),
        label="nested registered document mismatch attack",
    )
    document[nested_path][field] = value
    intent["canonical_artifact_bytes_hex"] = _raw(document).hex()
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match=(
            "embedded registered artifact canonical bytes differ from "
            "its unique record"
        ),
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(attacked)
        )


def test_rehashed_nested_registered_document_missing_record_fails(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    intent = _record_for_role(attacked, "CONTROLLED_ROOT_INTENT")
    document = bundle._strict_json_document(  # noqa: SLF001
        bytes.fromhex(intent["canonical_artifact_bytes_hex"]),
        label="missing nested record attack",
    )
    document["semantic_authority"]["binding_id"] = _id(
        "missing-nested-authority-record"
    )
    intent["canonical_artifact_bytes_hex"] = _raw(document).hex()
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="has no unique matching record",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(attacked)
        )


def test_rehashed_duplicate_semantic_record_ambiguity_fails(
    portable_closed_bundle,
) -> None:
    _result, _roots, artifact = portable_closed_bundle
    attacked = deepcopy(artifact.to_document())
    original = _record_for_role(
        attacked,
        "CONTROLLED_ROOT_SEMANTIC_AUTHORITY",
    )
    duplicate = deepcopy(original)
    duplicate["index"] = len(attacked["artifact_records"])
    duplicate["record_id"] = _id("duplicate-record-placeholder")
    attacked["artifact_records"].append(duplicate)
    attacked["artifact_count"] += 1
    with pytest.raises(
        bundle.V075PortableOccurrenceEvidenceV2InvariantViolation,
        match="duplicate or cross-role semantic artifact IDs",
    ):
        bundle.verify_v075_portable_occurrence_evidence_bundle_bytes_v2(
            _rehash_complete_bundle_wrapper(attacked)
        )
