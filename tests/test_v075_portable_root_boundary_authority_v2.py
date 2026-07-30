from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import v075_observer_signed_multiround_occurrence_runner_v2 as runner
from acfqp import v075_portable_root_boundary_authority_v2 as authority
from acfqp import v075_private_observer_boundary_v2 as observer
from tests.test_v075_portable_public_semantic_replay_v2 import (  # noqa: F401
    PROJECT_ROOT,
    real_raw_m0_bundle,
)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-m2-root-boundary-test:v2\x00" + label.encode()
    ).hexdigest()


def _root_document(*, occurrence_id: str | None = None) -> dict:
    width = 3
    document = {
        "schema": "acfqp.v075_observer_signed_root_execution.v2",
        "schema_version": runner.SCHEMA_VERSION,
        "profile_key": runner.PROFILE_KEY,
        "schedule_id": _id("schedule"),
        "schedule_verification_id": _id("schedule-verification"),
        "occurrence_id": occurrence_id or _id("occurrence"),
        "resulting_head_id": _id("head"),
        "open_prefix_verification_id": _id("prefix"),
        "discovery_intent_ids": [
            _id(f"discovery-{index}") for index in range(width)
        ],
        "discovery_receipt_ids": [
            _id(f"discovery-receipt-{index}") for index in range(width)
        ],
        "support_promotion_template_ids": [
            _id(f"promotion-{index}") for index in range(width)
        ],
        "support_freeze_ids": [
            _id(f"support-{index}") for index in range(width)
        ],
        "validation_intent_ids": [
            _id(f"validation-{index}") for index in range(width)
        ],
        "validation_receipt_ids": [
            _id(f"validation-receipt-{index}") for index in range(width)
        ],
        "root_row_binding_ids": [
            _id(f"row-{index}") for index in range(width)
        ],
        "all_preregistered_root_rows_executed_exactly_once": True,
        "all_support_promotion_templates_matched_exactly_once": True,
        "support_promotion_dependency_chain_exactly_replayed": True,
        "support_frozen_before_same_row_validation": True,
        "observer_signed_prefix_exactly_replayed": True,
        "official_execution_allowed": False,
    }
    document["support_promotion_freeze_bindings"] = [
        {
            "support_promotion_template_id": template_id,
            "support_freeze_id": freeze_id,
        }
        for template_id, freeze_id in zip(
            document["support_promotion_template_ids"],
            document["support_freeze_ids"],
            strict=True,
        )
    ]
    document["execution_id"] = runner._hash(  # noqa: SLF001
        "root_execution",
        document,
    )
    return document


@pytest.mark.parametrize(
    "attack",
    (
        "hidden_field",
        "stale_id",
        "wrong_boolean",
        "duplicate",
        "width",
        "binding_transplant",
    ),
)
def test_root_execution_view_strictly_replays_raw_producer_bytes(
    attack: str,
) -> None:
    document = _root_document()
    honest = canonical_json_bytes(document)
    view = authority.V075PortableRootExecutionProducerViewV2(honest)
    assert view.execution_id == document["execution_id"]
    assert view.to_document() == document
    assert view.view_id == view.view_id

    attacked = deepcopy(document)
    if attack == "hidden_field":
        attacked["hidden"] = False
    elif attack == "stale_id":
        attacked["schedule_id"] = _id("foreign-schedule")
    elif attack == "wrong_boolean":
        attacked[
            "support_promotion_dependency_chain_exactly_replayed"
        ] = False
    elif attack == "duplicate":
        attacked["support_freeze_ids"][1] = attacked[
            "support_freeze_ids"
        ][0]
    elif attack == "width":
        attacked["validation_receipt_ids"].pop()
    else:
        attacked["support_promotion_freeze_bindings"][0][
            "support_freeze_id"
        ] = attacked["support_freeze_ids"][1]
    with pytest.raises(
        authority.V075PortableRootBoundaryV2InvariantViolation
    ):
        authority.V075PortableRootExecutionProducerViewV2(
            canonical_json_bytes(attacked)
        )


def test_root_execution_view_rejects_cached_mutation() -> None:
    view = authority.V075PortableRootExecutionProducerViewV2(
        canonical_json_bytes(_root_document())
    )
    original = view.schedule_id
    object.__setattr__(view, "schedule_id", _id("mutated-schedule"))
    try:
        with pytest.raises(
            authority.V075PortableRootBoundaryV2InvariantViolation,
            match="stale or mutated",
        ):
            _ = view.view_id
    finally:
        object.__setattr__(view, "schedule_id", original)
    assert view.view_id == view.view_id


def _occurrence(label: str):
    return authority.identity.V075BatchNativeOccurrenceIdentityV1(
        authority.identity._OCCURRENCE_IDENTITY_ISSUER,  # noqa: SLF001
        _id(f"{label}-namespace"),
        _id(f"{label}-context"),
        authority.identity.worker.V075WorkerArmV1.NO_PRIOR,
        0,
        _id(f"{label}-threshold"),
        _id(f"{label}-cap"),
        None,
    )


def test_occurrence_binding_requires_exact_replayed_m0_bytes() -> None:
    occurrence = _occurrence("occurrence-bytes")
    honest_raw = canonical_json_bytes(occurrence.to_document())
    honest = authority._RootRecordBindingV2(  # noqa: SLF001
        _id("occurrence-bytes-record"),
        0,
        "OCCURRENCE_IDENTITY",
        "acfqp.v075_batch_native_occurrence.v1",
        occurrence.occurrence_id,
        (),
        honest_raw,
    )
    assert (
        authority._validate_occurrence_binding_against_m0(  # noqa: SLF001
            binding=honest,
            occurrence=occurrence,
        )
        == occurrence
    )
    attacked_document = occurrence.to_document()
    attacked_document["context_id"] = _id("foreign-occurrence-context")
    attacked = authority._RootRecordBindingV2(  # noqa: SLF001
        _id("occurrence-bytes-attacked-record"),
        0,
        "OCCURRENCE_IDENTITY",
        "acfqp.v075_batch_native_occurrence.v1",
        occurrence.occurrence_id,
        (),
        canonical_json_bytes(attacked_document),
    )
    with pytest.raises(
        authority.V075PortableRootBoundaryV2InvariantViolation,
        match="exact M0 occurrence bytes",
    ):
        authority._validate_occurrence_binding_against_m0(  # noqa: SLF001
            binding=attacked,
            occurrence=occurrence,
        )


def _rehash_root_document(document: dict) -> dict:
    document = deepcopy(document)
    document.pop("execution_id", None)
    document["execution_id"] = runner._hash(  # noqa: SLF001
        "root_execution",
        document,
    )
    return document


def _relationship_case() -> SimpleNamespace:
    occurrence = _occurrence("relationship")
    width = 2
    rows = tuple(
        SimpleNamespace(row_binding_id=_id(f"relationship-row-{index}"))
        for index in range(width)
    )
    discoveries = tuple(
        SimpleNamespace(
            kind=authority.acquisition.V075InitialIntentKindV2.ROOT_DISCOVERY,
            intent_id=_id(f"relationship-discovery-{index}"),
            row_binding=rows[index],
            dependency_intent_ids=(),
        )
        for index in range(width)
    )
    promotions = tuple(
        SimpleNamespace(
            kind=(
                authority.acquisition.V075InitialIntentKindV2
                .SUPPORT_PROMOTION_TEMPLATE
            ),
            intent_id=_id(f"relationship-promotion-{index}"),
            row_binding=rows[index],
            dependency_intent_ids=(discoveries[index].intent_id,),
        )
        for index in range(width)
    )
    validations = tuple(
        SimpleNamespace(
            kind=authority.acquisition.V075InitialIntentKindV2.ROOT_VALIDATION,
            intent_id=_id(f"relationship-validation-{index}"),
            row_binding=rows[index],
            dependency_intent_ids=(promotions[index].intent_id,),
        )
        for index in range(width)
    )
    schedule = SimpleNamespace(
        schedule_id=_id("relationship-schedule"),
        intents=(*discoveries, *promotions, *validations),
    )
    verification = SimpleNamespace(
        verification_id=_id("relationship-verification")
    )
    heads = tuple(
        SimpleNamespace(head_id=_id(f"relationship-head-{index}"))
        for index in range(2 * width + 1)
    )
    discovery_appends = []
    supports = []
    for index, witness in enumerate(discoveries):
        receipt = SimpleNamespace(
            receipt_id=_id(f"relationship-discovery-receipt-{index}")
        )
        semantic = SimpleNamespace(
            role=(
                authority.control
                .V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            semantic_artifact_id=witness.intent_id,
            support_freeze_id=None,
        )
        append = SimpleNamespace(
            intent=SimpleNamespace(
                semantic_authority=semantic,
                stream_identity=SimpleNamespace(
                    row_binding_id=witness.row_binding.row_binding_id
                ),
            ),
            receipt=receipt,
            resulting_head=heads[index + 1],
        )
        discovery_appends.append(append)
        supports.append(
            SimpleNamespace(
                freeze_id=_id(f"relationship-support-{index}"),
                row_binding_id=witness.row_binding.row_binding_id,
                discovery_append_receipt_id=receipt.receipt_id,
            )
        )
    validation_appends = []
    for index, witness in enumerate(validations):
        receipt = SimpleNamespace(
            receipt_id=_id(f"relationship-validation-receipt-{index}")
        )
        semantic = SimpleNamespace(
            role=(
                authority.control
                .V075ControlledBatchSemanticAuthorityRoleV2
                .INITIAL_SCHEDULE_ROW_INTENT
            ),
            semantic_artifact_id=witness.intent_id,
            support_freeze_id=supports[index].freeze_id,
        )
        validation_appends.append(
            SimpleNamespace(
                intent=SimpleNamespace(
                    semantic_authority=semantic,
                    stream_identity=SimpleNamespace(
                        row_binding_id=witness.row_binding.row_binding_id
                    ),
                ),
                receipt=receipt,
                resulting_head=heads[width + index + 1],
            )
        )
    appends = (*discovery_appends, *validation_appends)
    prefix = SimpleNamespace(
        verification_id=_id("relationship-prefix"),
        heads=heads,
        appends=appends,
        support_freezes=tuple(supports),
        current_head_id=heads[-1].head_id,
        head_ids=tuple(item.head_id for item in heads),
        receipt_ids=tuple(item.receipt.receipt_id for item in appends),
        support_freeze_ids=tuple(item.freeze_id for item in supports),
    )
    m0_graph = SimpleNamespace(
        occurrence=occurrence,
        schedule=schedule,
        verification=verification,
    )
    replay = SimpleNamespace(
        typed_graph=SimpleNamespace(
            appends=appends,
            heads=heads,
            support_freezes=tuple(supports),
            open_prefixes=(prefix,),
            m1a_result=SimpleNamespace(
                typed_graph=SimpleNamespace(
                    m0_result=SimpleNamespace(typed_graph=m0_graph)
                )
            ),
        )
    )
    root_document = _root_document(occurrence_id=occurrence.occurrence_id)
    root_document.update(
        {
            "schedule_id": schedule.schedule_id,
            "schedule_verification_id": verification.verification_id,
            "resulting_head_id": heads[-1].head_id,
            "open_prefix_verification_id": prefix.verification_id,
            "discovery_intent_ids": [
                item.intent_id for item in discoveries
            ],
            "discovery_receipt_ids": [
                item.receipt.receipt_id for item in discovery_appends
            ],
            "support_promotion_template_ids": [
                item.intent_id for item in promotions
            ],
            "support_freeze_ids": [
                item.freeze_id for item in supports
            ],
            "validation_intent_ids": [
                item.intent_id for item in validations
            ],
            "validation_receipt_ids": [
                item.receipt.receipt_id for item in validation_appends
            ],
            "root_row_binding_ids": [
                item.row_binding.row_binding_id for item in discoveries
            ],
            "support_promotion_freeze_bindings": [
                {
                    "support_promotion_template_id": promotion.intent_id,
                    "support_freeze_id": support.freeze_id,
                }
                for promotion, support in zip(
                    promotions,
                    supports,
                    strict=True,
                )
            ],
        }
    )
    root_document = _rehash_root_document(root_document)
    return SimpleNamespace(
        occurrence=occurrence,
        replay=replay,
        root_document=root_document,
        validation_appends=validation_appends,
        prefix=prefix,
    )


@pytest.mark.parametrize(
    "attack",
    (
        "discovery_order",
        "support_mapping",
        "validation_support",
        "resulting_head",
        "prefix_identity",
        "prefix_members",
    ),
)
def test_root_relationship_mutations_fail_closed(attack: str) -> None:
    case = _relationship_case()
    authority._validate_root_execution_relationship(  # noqa: SLF001
        replay=case.replay,
        occurrence=case.occurrence,
        root=authority.V075PortableRootExecutionProducerViewV2(
            canonical_json_bytes(case.root_document)
        ),
    )
    document = deepcopy(case.root_document)
    if attack == "discovery_order":
        document["discovery_intent_ids"].reverse()
    elif attack == "support_mapping":
        document["support_freeze_ids"][0] = _id("foreign-support")
        document["support_promotion_freeze_bindings"][0][
            "support_freeze_id"
        ] = document["support_freeze_ids"][0]
    elif attack == "validation_support":
        case.validation_appends[
            0
        ].intent.semantic_authority.support_freeze_id = _id(
            "foreign-validation-support"
        )
    elif attack == "resulting_head":
        document["resulting_head_id"] = _id("foreign-resulting-head")
    elif attack == "prefix_identity":
        document["open_prefix_verification_id"] = _id("foreign-prefix")
    else:
        case.prefix.receipt_ids = tuple(reversed(case.prefix.receipt_ids))
    root = authority.V075PortableRootExecutionProducerViewV2(
        canonical_json_bytes(_rehash_root_document(document))
    )
    with pytest.raises(
        authority.V075PortableRootBoundaryV2InvariantViolation
    ):
        authority._validate_root_execution_relationship(  # noqa: SLF001
            replay=case.replay,
            occurrence=case.occurrence,
            root=root,
        )


@dataclass(frozen=True)
class _Record:
    index: int
    role: str
    record_id: str
    dependency_record_ids: tuple[str, ...]


def _small_dag_records() -> tuple[_Record, ...]:
    ids = tuple(_id(f"dag-{index}") for index in range(4))
    return (
        _Record(0, "OCCURRENCE_IDENTITY", ids[0], ()),
        _Record(1, "UPSTREAM_PUBLIC", ids[1], (ids[0],)),
        _Record(2, "ROOT_EXECUTION", ids[2], (ids[1],)),
        _Record(
            3,
            authority.m1a.M1A_VERIFICATION_ROLE,
            ids[3],
            (ids[2],),
        ),
    )


def test_iterative_dag_full_structural_and_private_states() -> None:
    records = _small_dag_records()
    nodes = authority._iterative_root_dependency_nodes(  # noqa: SLF001
        records=records,
        upstream_public_record_ids=frozenset({records[1].record_id}),
        private_verification_record_ids=frozenset(
            {records[3].record_id}
        ),
    )
    assert nodes[0].semantically_resolved is True
    assert nodes[1].semantically_resolved is True
    assert nodes[2].semantically_resolved is True
    assert nodes[3].semantically_resolved is False
    assert nodes[3].resolver_kind is (
        authority.V075PortableRootResolverKindV2
        .NO_REGISTERED_SEMANTIC_AUTHORITY
    )

    unresolved = authority._iterative_root_dependency_nodes(  # noqa: SLF001
        records=records,
        upstream_public_record_ids=frozenset(),
        private_verification_record_ids=frozenset(
            {records[3].record_id}
        ),
    )
    assert unresolved[0].semantically_resolved is True
    assert unresolved[1].semantically_resolved is False
    assert unresolved[2].semantically_resolved is False


def test_iterative_dag_scales_at_4096_direct_edges() -> None:
    count = 4096
    ids = tuple(_id(f"chain-{index}") for index in range(count))
    records = tuple(
        _Record(
            index,
            (
                "OCCURRENCE_IDENTITY"
                if index == 0
                else (
                    "ROOT_EXECUTION"
                    if index == count - 1
                    else "UPSTREAM_PUBLIC"
                )
            ),
            ids[index],
            (() if index == 0 else (ids[index - 1],)),
        )
        for index in range(count)
    )
    nodes = authority._iterative_root_dependency_nodes(  # noqa: SLF001
        records=records,
        upstream_public_record_ids=frozenset(ids[1:-1]),
        private_verification_record_ids=frozenset(),
    )
    assert len(nodes) == count
    assert nodes[-1].semantically_resolved is True
    assert sum(
        len(item.direct_dependency_record_ids) for item in nodes
    ) == count - 1


def _attestation(
    *,
    role: str,
    record_id: str,
    dependency_id: str | None,
    status: authority.V075PortableRootRoleClosureStatusV2,
) -> authority.V075PortableRootRecordAttestationV2:
    unresolved = (
        ()
        if status
        is authority.V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
        else (dependency_id,)
    )
    resolved = (() if unresolved else (() if dependency_id is None else (dependency_id,)))
    direct = (() if dependency_id is None else (dependency_id,))
    return authority.V075PortableRootRecordAttestationV2(
        authority._ATTESTATION_ISSUER,  # noqa: SLF001
        _id("closure-bundle"),
        _id("closure-graph"),
        _id("closure-dag"),
        record_id,
        0,
        role,
        _id(f"semantic-{role}"),
        _id(f"raw-{role}"),
        10,
        direct,
        resolved,
        unresolved,
        (() if not unresolved else ("UNRESOLVED",)),
        (
            authority.V075PortableRootResolverKindV2
            .M2_OCCURRENCE_IDENTITY
            if role == "OCCURRENCE_IDENTITY"
            else authority.V075PortableRootResolverKindV2.M2_ROOT_EXECUTION
        ),
        status,
    )


def test_role_closure_tristate_is_explicit() -> None:
    occurrence_record = SimpleNamespace(
        role="OCCURRENCE_IDENTITY",
        record_id=_id("closure-occurrence-record"),
    )
    full = _attestation(
        role="OCCURRENCE_IDENTITY",
        record_id=occurrence_record.record_id,
        dependency_id=None,
        status=authority.V075PortableRootRoleClosureStatusV2.FULL_PUBLIC,
    )
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=_id("closure-bundle"),
        typed_graph_id=_id("closure-graph"),
        dependency_dag_id=_id("closure-dag"),
        records=(occurrence_record,),
        attestations=(full,),
    )
    by_role = {item.role: item for item in closures}
    assert by_role["OCCURRENCE_IDENTITY"].status is (
        authority.V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
    )
    assert by_role["ROOT_EXECUTION"].status is (
        authority.V075PortableRootRoleClosureStatusV2
        .NOT_PRESENT_IN_OCCURRENCE
    )
    absent = by_role["ROOT_EXECUTION"].to_document()
    assert absent["absence_is_not_native_zero"] is True
    assert absent["absence_is_not_completion"] is True

    root_record = SimpleNamespace(
        role="ROOT_EXECUTION",
        record_id=_id("closure-root-record"),
    )
    structural = _attestation(
        role="ROOT_EXECUTION",
        record_id=root_record.record_id,
        dependency_id=_id("closure-unresolved-dependency"),
        status=(
            authority.V075PortableRootRoleClosureStatusV2
            .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
        ),
    )
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=_id("closure-bundle"),
        typed_graph_id=_id("closure-graph"),
        dependency_dag_id=_id("closure-dag"),
        records=(occurrence_record, root_record),
        attestations=(full, structural),
    )
    assert closures[1].status is (
        authority.V075PortableRootRoleClosureStatusV2
        .STRUCTURAL_ONLY_TRANSITIVE_UNRESOLVED
    )


def test_api_has_only_raw_public_authorities_and_all_locks_closed() -> None:
    parameters = inspect.signature(
        authority.replay_v075_portable_root_boundary_v2
    ).parameters
    assert tuple(parameters) == (
        "repository_root",
        "portable_bundle_bytes",
        "public_context_closure_bytes",
    )
    assert {
        "private_salt",
        "private_environment",
        "signer",
        "observer_session",
        "verification",
        "issuer",
    }.isdisjoint(parameters)
    source = Path(authority.__file__).read_text(encoding="utf-8")
    assert "_ROOT_EXECUTION_" + "ISSUER" not in source
    assert "verify_loaded_private_observer_batch_closure_v2" not in source
    assert authority.OFFICIAL_EXECUTION_ALLOWED is False
    assert authority.PRODUCTION_AUTHORIZING is False
    assert authority.FRESH_HELDOUT_ACCESS_ALLOWED is False
    assert authority.PRIVATE_INPUT_CHANNELS_ALLOWED is False
    assert authority.PRIVATE_REPLAY_PERFORMED is False
    assert authority.M1A_PRIVATE_VERIFICATION_CLAIM_CONSUMED is False
    assert authority.PLAN_CERTIFICATE_ISSUANCE_ALLOWED is False
    assert authority.INFEASIBILITY_CERTIFICATE_ISSUANCE_ALLOWED is False
    with pytest.raises(
        authority.V075PortableRootBoundaryProductionV2NotReady
    ):
        authority.open_v075_production_from_portable_root_boundary_v2()


def test_each_m2_layer_deep_validates_each_child_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    occurrence = authority.identity.V075BatchNativeOccurrenceIdentityV1(
        authority.identity._OCCURRENCE_IDENTITY_ISSUER,  # noqa: SLF001
        _id("count-namespace"),
        _id("count-context"),
        authority.identity.worker.V075WorkerArmV1.NO_PRIOR,
        0,
        _id("count-threshold"),
        _id("count-cap"),
        None,
    )
    root_view = authority.V075PortableRootExecutionProducerViewV2(
        canonical_json_bytes(
            _root_document(occurrence_id=occurrence.occurrence_id)
        )
    )
    occurrence_record_id = _id("count-occurrence-record")
    root_record_id = _id("count-root-record")
    bindings = (
        authority._RootRecordBindingV2(  # noqa: SLF001
            occurrence_record_id,
            0,
            "OCCURRENCE_IDENTITY",
            "acfqp.v075_batch_native_occurrence.v1",
            occurrence.occurrence_id,
            (),
            canonical_json_bytes(occurrence.to_document()),
        ),
        authority._RootRecordBindingV2(  # noqa: SLF001
            root_record_id,
            1,
            "ROOT_EXECUTION",
            "acfqp.v075_observer_signed_root_execution.v2",
            root_view.execution_id,
            (occurrence_record_id,),
            root_view.canonical_bytes,
        ),
    )
    fake_m1b = object.__new__(
        authority.m1b.V075PortableSignedControlGraphReplayV2
    )
    object.__setattr__(fake_m1b, "bundle_id", _id("count-bundle"))
    object.__setattr__(
        fake_m1b,
        "occurrence_id",
        occurrence.occurrence_id,
    )
    object.__setattr__(
        fake_m1b,
        "public_context_closure_id",
        _id("count-context-closure"),
    )
    object.__setattr__(
        fake_m1b,
        "typed_graph",
        SimpleNamespace(
            _graph_id=_id("count-m1b-graph"),
            m1a_result=SimpleNamespace(
                typed_graph=SimpleNamespace(record_bindings=())
            ),
        ),
    )
    object.__setattr__(
        fake_m1b,
        "dependency_dag",
        SimpleNamespace(
            nodes=(
                SimpleNamespace(
                    record_id=occurrence_record_id,
                    record_index=0,
                    role="OCCURRENCE_IDENTITY",
                    direct_dependency_record_ids=(),
                    semantically_resolved=False,
                ),
                SimpleNamespace(
                    record_id=root_record_id,
                    record_index=1,
                    role="ROOT_EXECUTION",
                    direct_dependency_record_ids=(occurrence_record_id,),
                    semantically_resolved=False,
                ),
            )
        ),
    )
    object.__setattr__(fake_m1b, "_result_id", _id("count-m1b-result"))
    m1b_calls = 0

    def count_m1b(_self) -> None:
        nonlocal m1b_calls
        m1b_calls += 1

    monkeypatch.setattr(
        authority.m1b.V075PortableSignedControlGraphReplayV2,
        "_assert_current",
        count_m1b,
    )
    monkeypatch.setattr(
        authority,
        "_validate_root_execution_relationship",
        lambda **_kwargs: None,
    )
    typed_graph = authority.V075PortableRootBoundaryTypedGraphV2(
        authority._TYPED_GRAPH_ISSUER,  # noqa: SLF001
        fake_m1b.bundle_id,
        fake_m1b.public_context_closure_id,
        occurrence.occurrence_id,
        fake_m1b,
        occurrence,
        root_view,
        bindings,
    )
    assert m1b_calls == 1
    typed_graph._assert_current()  # noqa: SLF001
    assert m1b_calls == 2

    records = (
        _Record(0, "OCCURRENCE_IDENTITY", occurrence_record_id, ()),
        _Record(
            1,
            "ROOT_EXECUTION",
            root_record_id,
            (occurrence_record_id,),
        ),
    )
    nodes = authority._iterative_root_dependency_nodes(  # noqa: SLF001
        records=records,
        upstream_public_record_ids=frozenset(),
        private_verification_record_ids=frozenset(),
    )
    dag = authority.V075PortableRootDependencyDAGV2(
        authority._DAG_ISSUER,  # noqa: SLF001
        fake_m1b.bundle_id,
        fake_m1b._result_id,  # noqa: SLF001
        typed_graph._graph_id,  # noqa: SLF001
        (),
        (),
        nodes,
    )
    attestations = authority._build_attestations(  # noqa: SLF001
        bundle_id=fake_m1b.bundle_id,
        typed_graph_id=typed_graph._graph_id,  # noqa: SLF001
        dag=dag,
        bindings=bindings,
    )
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=fake_m1b.bundle_id,
        typed_graph_id=typed_graph._graph_id,  # noqa: SLF001
        dependency_dag_id=dag._dag_id,  # noqa: SLF001
        records=bindings,
        attestations=attestations,
    )
    layer_calls = {"typed": 0, "dag": 0, "attestation": 0, "closure": 0}

    def count_typed(_self) -> None:
        layer_calls["typed"] += 1

    def count_dag(_self) -> None:
        layer_calls["dag"] += 1

    def count_attestation(_self) -> None:
        layer_calls["attestation"] += 1

    def count_closure(_self) -> None:
        layer_calls["closure"] += 1

    monkeypatch.setattr(
        authority.V075PortableRootBoundaryTypedGraphV2,
        "_assert_current",
        count_typed,
    )
    monkeypatch.setattr(
        authority.V075PortableRootDependencyDAGV2,
        "_assert_current",
        count_dag,
    )
    monkeypatch.setattr(
        authority.V075PortableRootRecordAttestationV2,
        "_assert_current",
        count_attestation,
    )
    monkeypatch.setattr(
        authority.V075PortableRootRoleClosureV2,
        "_assert_current",
        count_closure,
    )
    authority.V075PortableRootBoundaryReplayV2(
        authority._RESULT_ISSUER,  # noqa: SLF001
        fake_m1b.bundle_id,
        occurrence.occurrence_id,
        fake_m1b.public_context_closure_id,
        typed_graph,
        dag,
        attestations,
        closures,
    )
    assert layer_calls == {
        "typed": 1,
        "dag": 1,
        "attestation": 2,
        "closure": 2,
    }


def _synthetic_layers_for_attack(
    monkeypatch: pytest.MonkeyPatch,
    *,
    label: str,
) -> SimpleNamespace:
    occurrence = _occurrence(label)
    root_view = authority.V075PortableRootExecutionProducerViewV2(
        canonical_json_bytes(
            _root_document(occurrence_id=occurrence.occurrence_id)
        )
    )
    occurrence_record_id = _id(f"{label}-occurrence-record")
    root_record_id = _id(f"{label}-root-record")
    private_record_id = _id(f"{label}-private-verification-record")
    bindings = (
        authority._RootRecordBindingV2(  # noqa: SLF001
            occurrence_record_id,
            0,
            "OCCURRENCE_IDENTITY",
            "acfqp.v075_batch_native_occurrence.v1",
            occurrence.occurrence_id,
            (),
            canonical_json_bytes(occurrence.to_document()),
        ),
        authority._RootRecordBindingV2(  # noqa: SLF001
            root_record_id,
            1,
            "ROOT_EXECUTION",
            "acfqp.v075_observer_signed_root_execution.v2",
            root_view.execution_id,
            (occurrence_record_id,),
            root_view.canonical_bytes,
        ),
    )
    m1b_spine = (
        SimpleNamespace(
            record_id=occurrence_record_id,
            record_index=0,
            role="OCCURRENCE_IDENTITY",
            direct_dependency_record_ids=(),
            semantically_resolved=True,
        ),
        SimpleNamespace(
            record_id=root_record_id,
            record_index=1,
            role="ROOT_EXECUTION",
            direct_dependency_record_ids=(occurrence_record_id,),
            semantically_resolved=False,
        ),
        SimpleNamespace(
            record_id=private_record_id,
            record_index=2,
            role=authority.m1a.M1A_VERIFICATION_ROLE,
            direct_dependency_record_ids=(root_record_id,),
            semantically_resolved=False,
        ),
    )
    fake_m1b = object.__new__(
        authority.m1b.V075PortableSignedControlGraphReplayV2
    )
    object.__setattr__(fake_m1b, "bundle_id", _id(f"{label}-bundle"))
    object.__setattr__(
        fake_m1b,
        "occurrence_id",
        occurrence.occurrence_id,
    )
    object.__setattr__(
        fake_m1b,
        "public_context_closure_id",
        _id(f"{label}-context-closure"),
    )
    object.__setattr__(
        fake_m1b,
        "typed_graph",
        SimpleNamespace(
            _graph_id=_id(f"{label}-m1b-graph"),
            m1a_result=SimpleNamespace(
                typed_graph=SimpleNamespace(
                    record_bindings=(
                        SimpleNamespace(
                            record_id=private_record_id,
                            role=authority.m1a.M1A_VERIFICATION_ROLE,
                        ),
                    )
                )
            ),
        ),
    )
    object.__setattr__(
        fake_m1b,
        "dependency_dag",
        SimpleNamespace(nodes=m1b_spine),
    )
    object.__setattr__(
        fake_m1b,
        "_result_id",
        _id(f"{label}-m1b-result"),
    )
    monkeypatch.setattr(
        authority.m1b.V075PortableSignedControlGraphReplayV2,
        "_assert_current",
        lambda _self: None,
    )
    monkeypatch.setattr(
        authority,
        "_validate_root_execution_relationship",
        lambda **_kwargs: None,
    )
    graph = authority.V075PortableRootBoundaryTypedGraphV2(
        authority._TYPED_GRAPH_ISSUER,  # noqa: SLF001
        fake_m1b.bundle_id,
        fake_m1b.public_context_closure_id,
        occurrence.occurrence_id,
        fake_m1b,
        occurrence,
        root_view,
        bindings,
    )
    records = (
        _Record(0, "OCCURRENCE_IDENTITY", occurrence_record_id, ()),
        _Record(
            1,
            "ROOT_EXECUTION",
            root_record_id,
            (occurrence_record_id,),
        ),
        _Record(
            2,
            authority.m1a.M1A_VERIFICATION_ROLE,
            private_record_id,
            (root_record_id,),
        ),
    )
    nodes = authority._iterative_root_dependency_nodes(  # noqa: SLF001
        records=records,
        upstream_public_record_ids=frozenset({occurrence_record_id}),
        private_verification_record_ids=frozenset({private_record_id}),
    )
    dag = authority.V075PortableRootDependencyDAGV2(
        authority._DAG_ISSUER,  # noqa: SLF001
        fake_m1b.bundle_id,
        fake_m1b._result_id,  # noqa: SLF001
        graph._graph_id,  # noqa: SLF001
        (occurrence_record_id,),
        (private_record_id,),
        nodes,
    )
    attestations = authority._build_attestations(  # noqa: SLF001
        bundle_id=fake_m1b.bundle_id,
        typed_graph_id=graph._graph_id,  # noqa: SLF001
        dag=dag,
        bindings=bindings,
    )
    closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=fake_m1b.bundle_id,
        typed_graph_id=graph._graph_id,  # noqa: SLF001
        dependency_dag_id=dag._dag_id,  # noqa: SLF001
        records=bindings,
        attestations=attestations,
    )
    result = authority.V075PortableRootBoundaryReplayV2(
        authority._RESULT_ISSUER,  # noqa: SLF001
        fake_m1b.bundle_id,
        occurrence.occurrence_id,
        fake_m1b.public_context_closure_id,
        graph,
        dag,
        attestations,
        closures,
    )
    return SimpleNamespace(
        occurrence=occurrence,
        root_view=root_view,
        bindings=bindings,
        fake_m1b=fake_m1b,
        graph=graph,
        dag=dag,
        attestations=attestations,
        closures=closures,
        result=result,
        record_ids=(
            occurrence_record_id,
            root_record_id,
            private_record_id,
        ),
    )


@pytest.mark.parametrize(
    ("layer", "attribute", "message"),
    (
        ("graph", "_graph_id", "typed graph identity is stale"),
        ("dag", "_dag_id", "dependency DAG identity is stale"),
        (
            "attestations",
            "_attestation_id",
            "record attestation identity is stale",
        ),
        ("closures", "_closure_id", "role closure identity is stale"),
        ("result", "_result_id", "replay result identity is stale"),
    ),
)
def test_every_m2_layer_rejects_stale_cached_identity(
    monkeypatch: pytest.MonkeyPatch,
    layer: str,
    attribute: str,
    message: str,
) -> None:
    built = _synthetic_layers_for_attack(
        monkeypatch,
        label=f"stale-{layer}",
    )
    target = getattr(built, layer)
    if type(target) is tuple:
        target = target[0]
    original = getattr(target, attribute)
    object.__setattr__(target, attribute, _id(f"forged-{layer}-cache"))
    try:
        with pytest.raises(
            authority.V075PortableRootBoundaryV2InvariantViolation,
            match=message,
        ):
            target._assert_current()  # noqa: SLF001
    finally:
        object.__setattr__(target, attribute, original)


def test_self_consistent_forged_dag_registry_full_chain_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = _synthetic_layers_for_attack(
        monkeypatch,
        label="forged-registry",
    )
    all_record_ids = tuple(sorted(built.record_ids))
    forged_records = tuple(
        _Record(
            item.record_index,
            item.role,
            item.record_id,
            item.direct_dependency_record_ids,
        )
        for item in built.dag.nodes
    )
    forged_nodes = authority._iterative_root_dependency_nodes(  # noqa: SLF001
        records=forged_records,
        upstream_public_record_ids=frozenset(all_record_ids),
        private_verification_record_ids=frozenset(),
    )
    object.__setattr__(
        built.dag,
        "upstream_public_record_ids",
        all_record_ids,
    )
    object.__setattr__(
        built.dag,
        "private_verification_record_ids",
        (),
    )
    object.__setattr__(built.dag, "nodes", forged_nodes)
    object.__setattr__(
        built.dag,
        "_dag_id",
        authority._hash("dependency_dag", built.dag._payload()),  # noqa: SLF001
    )
    for item in built.attestations:
        object.__setattr__(
            item,
            "dependency_dag_id",
            built.dag._dag_id,  # noqa: SLF001
        )
        object.__setattr__(
            item,
            "_attestation_id",
            authority._hash(  # noqa: SLF001
                "record_attestation",
                item._payload(),  # noqa: SLF001
            ),
        )
    attestation_by_role = {
        item.role: item for item in built.attestations
    }
    for item in built.closures:
        object.__setattr__(
            item,
            "dependency_dag_id",
            built.dag._dag_id,  # noqa: SLF001
        )
        object.__setattr__(
            item,
            "attestation_ids",
            (attestation_by_role[item.role]._attestation_id,),  # noqa: SLF001
        )
        object.__setattr__(
            item,
            "_closure_id",
            authority._hash("role_closure", item._payload()),  # noqa: SLF001
        )
    object.__setattr__(
        built.result,
        "_result_id",
        authority._hash(  # noqa: SLF001
            "aggregate",
            built.result._payload(),  # noqa: SLF001
        ),
    )
    built.dag._assert_current()  # noqa: SLF001
    assert all(
        item.dependency_dag_id == built.dag._dag_id  # noqa: SLF001
        for item in built.attestations
    )
    assert all(
        item.dependency_dag_id == built.dag._dag_id  # noqa: SLF001
        for item in built.closures
    )
    with pytest.raises(
        authority.V075PortableRootBoundaryV2InvariantViolation,
        match="forged its M1B-derived authority registries",
    ):
        built.result._assert_current()  # noqa: SLF001


def test_self_consistent_forged_direct_edge_spine_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = _synthetic_layers_for_attack(
        monkeypatch,
        label="forged-spine",
    )
    occurrence_binding, root_binding = built.bindings
    forged_root_binding = authority._RootRecordBindingV2(  # noqa: SLF001
        root_binding.record_id,
        root_binding.record_index,
        root_binding.role,
        root_binding.artifact_schema,
        root_binding.semantic_artifact_id,
        (),
        root_binding.canonical_artifact_bytes,
    )
    forged_bindings = (occurrence_binding, forged_root_binding)
    object.__setattr__(built.graph, "record_bindings", forged_bindings)
    built.graph._validate()  # noqa: SLF001
    object.__setattr__(
        built.graph,
        "_graph_id",
        authority._hash(  # noqa: SLF001
            "typed_graph",
            built.graph._identity_payload(),  # noqa: SLF001
        ),
    )
    occurrence_record_id, root_record_id, private_record_id = (
        built.record_ids
    )
    forged_records = (
        _Record(0, "OCCURRENCE_IDENTITY", occurrence_record_id, ()),
        _Record(1, "ROOT_EXECUTION", root_record_id, ()),
        _Record(
            2,
            authority.m1a.M1A_VERIFICATION_ROLE,
            private_record_id,
            (root_record_id,),
        ),
    )
    forged_nodes = authority._iterative_root_dependency_nodes(  # noqa: SLF001
        records=forged_records,
        upstream_public_record_ids=frozenset({occurrence_record_id}),
        private_verification_record_ids=frozenset({private_record_id}),
    )
    forged_dag = authority.V075PortableRootDependencyDAGV2(
        authority._DAG_ISSUER,  # noqa: SLF001
        built.fake_m1b.bundle_id,
        built.fake_m1b._result_id,  # noqa: SLF001
        built.graph._graph_id,  # noqa: SLF001
        (occurrence_record_id,),
        (private_record_id,),
        forged_nodes,
    )
    forged_attestations = authority._build_attestations(  # noqa: SLF001
        bundle_id=built.fake_m1b.bundle_id,
        typed_graph_id=built.graph._graph_id,  # noqa: SLF001
        dag=forged_dag,
        bindings=forged_bindings,
    )
    forged_closures = authority._build_role_closures(  # noqa: SLF001
        bundle_id=built.fake_m1b.bundle_id,
        typed_graph_id=built.graph._graph_id,  # noqa: SLF001
        dependency_dag_id=forged_dag._dag_id,  # noqa: SLF001
        records=forged_bindings,
        attestations=forged_attestations,
    )
    with pytest.raises(
        authority.V075PortableRootBoundaryV2InvariantViolation,
        match="direct-edge spine differs from hardened M1B",
    ):
        authority.V075PortableRootBoundaryReplayV2(
            authority._RESULT_ISSUER,  # noqa: SLF001
            built.fake_m1b.bundle_id,
            built.occurrence.occurrence_id,
            built.fake_m1b.public_context_closure_id,
            built.graph,
            forged_dag,
            forged_attestations,
            forged_closures,
        )


@pytest.fixture(scope="module")
def real_k7_m2(real_raw_m0_bundle):
    patcher = pytest.MonkeyPatch()

    def forbidden(*_args, **_kwargs):
        raise AssertionError("M2 crossed the private replay boundary")

    patcher.setattr(
        observer,
        "verify_loaded_private_observer_batch_closure_v2",
        forbidden,
    )
    try:
        yield authority.replay_v075_portable_root_boundary_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=(
                real_raw_m0_bundle["bundle"].canonical_bytes
            ),
            public_context_closure_bytes=(
                real_raw_m0_bundle["closure"].canonical_bytes
            ),
        )
    finally:
        patcher.undo()


def test_real_k7_closes_occurrence_and_root_without_private_replay(
    real_raw_m0_bundle,
    real_k7_m2,
) -> None:
    assert tuple(item.role for item in real_k7_m2.role_closures) == (
        "OCCURRENCE_IDENTITY",
        "ROOT_EXECUTION",
    )
    assert all(
        item.status
        is authority.V075PortableRootRoleClosureStatusV2.FULL_PUBLIC
        for item in real_k7_m2.role_closures
    )
    root = real_k7_m2.typed_graph.root_execution
    m1b_graph = real_k7_m2.typed_graph.m1b_result.typed_graph
    assert root.resulting_head_id in {
        item.head_id for item in m1b_graph.heads
    }
    assert root.open_prefix_verification_id in {
        item.verification_id for item in m1b_graph.open_prefixes
    }
    assert set(root.support_freeze_ids) <= {
        item.freeze_id for item in m1b_graph.support_freezes
    }
    private_records = tuple(
        item
        for item in m1b_graph.m1a_result.typed_graph.record_bindings
        if item.role == authority.m1a.M1A_VERIFICATION_ROLE
    )
    assert len(private_records) == 1
    private_id = private_records[0].record_id
    assert real_k7_m2.dependency_dag.nodes_by_id[
        private_id
    ].semantically_resolved is False
    document = real_k7_m2.to_document()
    assert document[
        "root_execution_public_semantic_closure_complete"
    ] is True
    assert document["private_replay_performed"] is False
    assert document["m1a_private_verification_claim_consumed"] is False
    assert document["official_execution_allowed"] is False
    assert document["plan_certificate"] is False
    assert document["infeasibility_certificate"] is False

    raw = bytearray(real_raw_m0_bundle["bundle"].canonical_bytes)
    raw[-2] = ord("1") if raw[-2] != ord("1") else ord("2")
    with pytest.raises(
        authority.V075PortableRootBoundaryV2InvariantViolation,
        match="hardened M1B",
    ):
        authority.replay_v075_portable_root_boundary_v2(
            repository_root=PROJECT_ROOT,
            portable_bundle_bytes=bytes(raw),
            public_context_closure_bytes=(
                real_raw_m0_bundle["closure"].canonical_bytes
            ),
        )
