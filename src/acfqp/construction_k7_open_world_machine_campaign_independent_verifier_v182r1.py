"""Producer-free replay of the fresh V182r1 universal-machine campaign."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping, NoReturn, Sequence

from acfqp import construction_k7_domain_registry_extension_v182 as domains
from acfqp import construction_k7_domain_registry_extension_v182r1 as domains_r1
from acfqp import construction_k7_open_world_machine_manifest_reveal_v182r1 as reveal
from acfqp import construction_k7_open_world_machine_protocol_v182 as protocol
from acfqp.open_world_machine_compiled_model_v182 import (
    CompiledMachineWorldModelV182,
    RawMachineTransitionV182,
    compile_machine_world_model_v182,
)
from acfqp.open_world_machine_oracle_v182 import (
    OpaqueMachineOracleV182,
    reveal_opaque_machine_oracle_v182,
)
from acfqp.open_world_machine_planner_v182 import MachinePlannerSessionV182
from acfqp.open_world_universal_machine_v182 import ProgramV182
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


EXPECTED_CAMPAIGN_ID = "0" * 64
EXPECTED_CAMPAIGN_BYTE_COUNT = 0
EXPECTED_CAMPAIGN_SHA256 = "0" * 64
EXPECTED_VERIFICATION_ID = "0" * 64
EXPECTED_VERIFICATION_BYTE_COUNT = 0
EXPECTED_VERIFICATION_SHA256 = "0" * 64

_TOP_FIELDS = {
    "COUNTER_COMPLETENESS_GATE",
    "WORKLOAD_ECONOMICS_GATE",
    "all_local_ground_labels_followed_certificate_failure",
    "all_registered_episodes_terminal",
    "arbitrary_domain_transfer_claimed",
    "archive_mdl_discount_used",
    "arm_results",
    "broad_iid_sample_efficiency_claimed",
    "campaign_id",
    "execution_preregistration_id",
    "finite_candidate_program_catalog_used",
    "label_axes_separate_from_execution_and_compute",
    "language_program_length_unbounded",
    "manifest_commitments",
    "manifest_reveal_id",
    "named_domain_family_used",
    "no_prior_target_total_labels",
    "occurrence_search_resource_bounded",
    "official_N_break_even",
    "official_execution_allowed",
    "official_scalar_cost",
    "ood_no_transfer_control",
    "partial_support_probability_authority_present",
    "planner_consumed_only_compiled_models",
    "prior_target_total_labels",
    "progress_checkpoint_count",
    "progress_checkpoint_ids",
    "protocol_id",
    "same_synthesizer_and_stop_rule_both_arms",
    "schema",
    "source_archive_program_count",
    "source_compiled_model",
    "source_label_count",
    "source_observations",
    "source_synthesis_events",
    "target_labels_avoided",
    "total_work_dominance_claimed",
}
_ARM_FIELDS = {
    "acquisition",
    "acquisition_synthesis_events",
    "all_local_ground_labels_followed_certificate_failure",
    "arm",
    "certificate_count",
    "episodes",
    "execution_step_count",
    "ground_transition_argument_passed_to_planner",
    "planning_compute_events",
    "planning_consumed_only_compiled_model",
    "recovery_compilation_events",
    "target_acquisition_label_count",
    "target_local_ground_label_count",
    "target_total_label_count",
    "terminal_episode_count",
}
_ACQUISITION_FIELDS = {
    "archive_mdl_discount_used",
    "archive_reference_count",
    "arm",
    "block_history",
    "compiled_model",
    "cumulative_synthesis_events",
    "revalidated_prior_credit",
    "same_synthesizer_and_stop_rule",
    "source_label_count",
    "source_observations",
    "stopped",
    "witness_blind_acquisition",
}
_HISTORY_FIELDS = {
    "block_index",
    "compiled",
    "compiled_model_id",
    "confirmation_zero_error",
    "cumulative_source_label_count",
    "effective_confirmation_count",
    "enumeration_events",
    "model_reused_without_recompile",
    "revalidated_prior_credit",
    "stable_confirmation_count",
}
_EPISODE_FIELDS = {
    "execution_step_count",
    "initial_state",
    "local_ground_label_count",
    "occurrence_index",
    "steps",
    "terminal",
    "terminal_state",
}
_STEP_FIELDS = {
    "certificate",
    "certificate_failure",
    "certificate_support_matched",
    "compiled_model_id_after_step",
    "decision_index",
    "local_ground_distinction_acquired",
    "local_ground_distinction_requires_preceding_failure",
    "observation",
    "predicted_support",
    "selected_action",
    "state",
}


class OpenWorldMachineIndependentVerifierV182R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldMachineIndependentVerifierV182R1Error(message)


def _object(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} is not exact bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _oracle(index: int) -> OpaqueMachineOracleV182:
    return reveal_opaque_machine_oracle_v182(
        manifest_bytes=canonical_json_bytes(reveal.MANIFEST_DOCUMENTS_V182R1[index]),
        expected_commitment=protocol.MANIFEST_COMMITMENTS_V182[index],
    )


def _compile(
    rows: Sequence[RawMachineTransitionV182],
    archive: Iterable[ProgramV182] = (),
) -> CompiledMachineWorldModelV182:
    return compile_machine_world_model_v182(
        rows,
        maximum_enumeration_events_per_scalar=(
            protocol.MAXIMUM_ENUMERATION_EVENTS_PER_SCALAR
        ),
        maximum_instruction_count=protocol.MAXIMUM_INSTRUCTION_COUNT,
        maximum_execution_steps=protocol.MAXIMUM_EXECUTION_STEPS,
        register_count=protocol.REGISTER_COUNT,
        maximum_residual_support=protocol.MAXIMUM_RESIDUAL_SUPPORT,
        archive=archive,
    )


def _synthesis_events(model: CompiledMachineWorldModelV182) -> int:
    return sum(
        row.synthesis.enumeration_events for row in model.coordinates
    ) + model.terminal_synthesis.enumeration_events


def _archive_count(model: CompiledMachineWorldModelV182) -> int:
    return sum(
        int(row.synthesis.archive_reference_used) for row in model.coordinates
    ) + int(model.terminal_synthesis.archive_reference_used)


def _row(document: Any) -> RawMachineTransitionV182:
    if type(document) is not dict or set(document) != {
        "schema",
        "occurrence_index",
        "query_index",
        "state",
        "action",
        "successor",
        "terminal",
        "observation_id",
    }:
        _fail("V182r1 raw observation fields changed")
    row = RawMachineTransitionV182.observe(
        occurrence_index=document["occurrence_index"],
        query_index=document["query_index"],
        state=document["state"],
        action=document["action"],
        successor=document["successor"],
        terminal=document["terminal"],
    )
    if row.to_document() != document:
        _fail("V182r1 raw observation identity changed")
    return row


def _exact_oracle_row(
    oracle: OpaqueMachineOracleV182, row: RawMachineTransitionV182
) -> None:
    expected = oracle.query(
        occurrence_index=row.occurrence_index,
        query_index=row.query_index,
        state=row.state,
        action=row.action,
    )
    if expected != row:
        _fail("V182r1 retained raw outcome changed under oracle replay")


def _acquisition_input(
    oracle: OpaqueMachineOracleV182, unique_index: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v182r1:witness-blind-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + unique_index.to_bytes(8, "big")
    ).digest()
    return (
        tuple(
            digest[index] % modulus
            for index, modulus in enumerate(oracle.initial_moduli)
        ),
        tuple(
            digest[16 + index] % oracle.action_cardinality
            for index in range(oracle.action_width)
        ),
    )


def _verify_acquisition(
    document: Any,
    *,
    oracle: OpaqueMachineOracleV182,
    arm: str,
    archive: Sequence[ProgramV182],
) -> tuple[list[RawMachineTransitionV182], CompiledMachineWorldModelV182]:
    if type(document) is not dict or set(document) != _ACQUISITION_FIELDS:
        _fail("V182r1 acquisition fields changed")
    rows = [_row(item) for item in document["source_observations"]]
    if not (
        document["arm"] == arm
        and document["source_label_count"] == len(rows)
        and document["source_label_count"] % protocol.ACQUISITION_BLOCK_SIZE == 0
        and protocol.MINIMUM_TARGET_LABELS
        <= len(rows)
        <= protocol.MAXIMUM_TARGET_LABELS
        and document["stopped"] is True
        and document["same_synthesizer_and_stop_rule"] is True
        and document["archive_mdl_discount_used"] is False
        and document["witness_blind_acquisition"] is True
    ):
        _fail("V182r1 acquisition claim or denominator changed")
    occurrence = 182_100 + protocol.ARMS.index(arm)
    unique_per_block = (
        protocol.ACQUISITION_BLOCK_SIZE // protocol.ACQUISITION_REPEAT_COUNT
    )
    for position, row in enumerate(rows):
        block_index = position // protocol.ACQUISITION_BLOCK_SIZE
        within = position % protocol.ACQUISITION_BLOCK_SIZE
        local_unique = within // protocol.ACQUISITION_REPEAT_COUNT
        repeat = within % protocol.ACQUISITION_REPEAT_COUNT
        unique_index = block_index * unique_per_block + local_unique
        state, action = _acquisition_input(oracle, unique_index)
        query_index = (
            block_index * protocol.ACQUISITION_BLOCK_SIZE
            + local_unique * protocol.ACQUISITION_REPEAT_COUNT
            + repeat
        )
        if not (
            row.occurrence_index == occurrence
            and row.query_index == query_index
            and row.state == state
            and row.action == action
        ):
            _fail("V182r1 witness-blind acquisition schedule changed")
        _exact_oracle_row(oracle, row)
    histories = document["block_history"]
    if (
        type(histories) is not list
        or len(histories) != len(rows) // protocol.ACQUISITION_BLOCK_SIZE
        or any(type(item) is not dict or set(item) != _HISTORY_FIELDS for item in histories)
    ):
        _fail("V182r1 acquisition history changed")
    model: CompiledMachineWorldModelV182 | None = None
    stable = 0
    credit = 0
    cumulative_events = 0
    archive_count = 0
    for block_index, history in enumerate(histories):
        end = (block_index + 1) * protocol.ACQUISITION_BLOCK_SIZE
        prefix = rows[:end]
        block = rows[end - protocol.ACQUISITION_BLOCK_SIZE : end]
        covered = model is not None and all(model.covers(row) for row in block)
        compiled = False
        events = 0
        if end >= protocol.MINIMUM_TARGET_LABELS:
            if covered:
                stable += 1
            else:
                model = _compile(prefix, archive)
                compiled = True
                stable = 0
                events = _synthesis_events(model)
                cumulative_events += events
                archive_count = _archive_count(model)
                credit = int(
                    arm == "REVALIDATED_MACHINE_PRIOR"
                    and archive_count > 0
                    and all(model.covers(row) for row in prefix)
                ) * protocol.REVALIDATED_PRIOR_CONFIRMATION_CREDIT
        expected = {
            "block_index": block_index,
            "cumulative_source_label_count": end,
            "compiled": compiled,
            "model_reused_without_recompile": covered,
            "confirmation_zero_error": covered,
            "stable_confirmation_count": stable,
            "revalidated_prior_credit": credit,
            "effective_confirmation_count": stable + credit,
            "enumeration_events": events,
            "compiled_model_id": model.compiled_model_id if model else None,
        }
        if history != expected:
            _fail("V182r1 acquisition stop-rule replay changed")
        if stable + credit >= protocol.STABLE_CONFIRMATION_BLOCKS and end != len(rows):
            _fail("V182r1 acquisition continued after its frozen stop rule")
    if model is None or stable + credit < protocol.STABLE_CONFIRMATION_BLOCKS:
        _fail("V182r1 acquisition stopped without its confidence rule")
    if not (
        document["compiled_model"] == model.to_document()
        and document["cumulative_synthesis_events"] == cumulative_events
        and document["archive_reference_count"] == archive_count
        and document["revalidated_prior_credit"] == credit
    ):
        _fail("V182r1 acquisition model or compute accounting changed")
    return rows, model


def _verify_arm(
    document: Any,
    *,
    oracle: OpaqueMachineOracleV182,
    arm: str,
    archive: Sequence[ProgramV182],
) -> dict[str, int]:
    if type(document) is not dict or set(document) != _ARM_FIELDS:
        _fail("V182r1 arm result fields changed")
    acquisition_rows, model = _verify_acquisition(
        document["acquisition"],
        oracle=oracle,
        arm=arm,
        archive=archive,
    )
    model_rows = list(acquisition_rows)
    episodes = document["episodes"]
    if type(episodes) is not list or len(episodes) != protocol.IID_OCCURRENCES_PER_ARM:
        _fail("V182r1 episode denominator changed")
    execution_steps = 0
    local_labels = 0
    planning_events = 0
    certificates = 0
    recovery_events = 0
    for offset, episode in enumerate(episodes):
        if type(episode) is not dict or set(episode) != _EPISODE_FIELDS:
            _fail("V182r1 episode fields changed")
        occurrence = 182_200 + protocol.ARMS.index(arm) * 100 + offset
        state = oracle.initial_state(occurrence)
        session = MachinePlannerSessionV182(
            model, legal_actions=oracle.legal_actions(), horizon=oracle.horizon
        )
        steps = episode["steps"]
        if type(steps) is not list or not steps:
            _fail("V182r1 episode has no execution steps")
        if not (
            episode["occurrence_index"] == occurrence
            and episode["initial_state"] == list(state)
            and episode["execution_step_count"] == len(steps)
            and len(steps) <= protocol.MAXIMUM_DECISIONS_PER_OCCURRENCE
        ):
            _fail("V182r1 occurrence identity or decision cap changed")
        episode_local = 0
        for decision, step in enumerate(steps):
            if type(step) is not dict or set(step) != _STEP_FIELDS:
                _fail("V182r1 step fields changed")
            certificate = session.certify(state)
            if not certificate.certified or certificate.selected_action is None:
                _fail("V182r1 retained plan was not certified")
            predicted = model.predict_support(state, certificate.selected_action)
            observed = oracle.query(
                occurrence_index=occurrence,
                query_index=decision,
                state=state,
                action=certificate.selected_action,
            )
            matched = observed.successor in predicted and (
                model.terminal(observed.successor) is observed.terminal
            )
            local = not matched
            expected_failure = None if matched else "FAILED_MISSING_SUPPORT_OR_TERMINAL"
            if not (
                step["decision_index"] == decision
                and step["state"] == list(state)
                and step["certificate"] == certificate.to_document()
                and step["selected_action"] == list(certificate.selected_action)
                and step["predicted_support"] == [list(row) for row in predicted]
                and step["observation"] == observed.to_document()
                and step["certificate_support_matched"] is matched
                and step["certificate_failure"] == expected_failure
                and step["local_ground_distinction_acquired"] is local
                and step["local_ground_distinction_requires_preceding_failure"] is True
            ):
                _fail("V182r1 plan, transition, or recovery ordering changed")
            certificates += 1
            planning_events += certificate.planning_compute_events
            execution_steps += 1
            if local:
                local_labels += 1
                episode_local += 1
                model_rows.append(observed)
                model = _compile(model_rows, archive)
                recovery_events += _synthesis_events(model)
                session = MachinePlannerSessionV182(
                    model,
                    legal_actions=oracle.legal_actions(),
                    horizon=oracle.horizon,
                )
                if not model.covers(observed):
                    _fail("V182r1 replayed local repair did not restore coverage")
            if step["compiled_model_id_after_step"] != model.compiled_model_id:
                _fail("V182r1 post-step compiled-model identity changed")
            state = observed.successor
        if not (
            oracle.terminal(state)
            and episode["terminal"] is True
            and episode["terminal_state"] == list(state)
            and episode["local_ground_label_count"] == episode_local
        ):
            _fail("V182r1 terminal episode replay changed")
    acquisition = document["acquisition"]
    if not (
        document["arm"] == arm
        and document["terminal_episode_count"] == len(episodes)
        and document["target_acquisition_label_count"]
        == acquisition["source_label_count"]
        and document["target_local_ground_label_count"] == local_labels
        and document["target_total_label_count"]
        == acquisition["source_label_count"] + local_labels
        and document["execution_step_count"] == execution_steps
        and document["planning_compute_events"] == planning_events
        and document["certificate_count"] == certificates
        and document["acquisition_synthesis_events"]
        == acquisition["cumulative_synthesis_events"]
        and document["recovery_compilation_events"] == recovery_events
        and document["planning_consumed_only_compiled_model"] is True
        and document["ground_transition_argument_passed_to_planner"] is False
        and document["all_local_ground_labels_followed_certificate_failure"] is True
    ):
        _fail("V182r1 arm accounting or claim locks changed")
    return {
        "labels": document["target_total_label_count"],
        "steps": execution_steps,
        "certificates": certificates,
        "local_labels": local_labels,
    }


def _verify_progress(
    root: Path,
    *,
    execution_id: str,
    expected_ids: Sequence[str],
) -> None:
    if not isinstance(root, Path) or not root.is_dir():
        _fail("V182r1 retained progress directory is absent")
    paths = sorted(root.glob("checkpoint-*.json"))
    if len(paths) != len(expected_ids):
        _fail("V182r1 progress checkpoint denominator changed")
    previous = None
    for sequence, (path, expected_id) in enumerate(zip(paths, expected_ids, strict=True)):
        document = _object(path.read_bytes(), "V182r1 progress checkpoint")
        payload = dict(document)
        checkpoint_id = payload.pop("progress_checkpoint_id", None)
        if not (
            set(payload)
            == {
                "schema",
                "execution_preregistration_id",
                "sequence",
                "previous_checkpoint_id",
                "stage",
                "payload",
                "outcome_progress_not_official_claim",
                "official_execution_allowed",
            }
            and checkpoint_id == expected_id
            and checkpoint_id
            == domains_r1.extension_content_id_v182r1(
                domains_r1.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V182R1_DOMAIN,
                payload,
            )
            and payload["execution_preregistration_id"] == execution_id
            and payload["sequence"] == sequence
            and payload["previous_checkpoint_id"] == previous
            and payload["outcome_progress_not_official_claim"] is True
            and payload["official_execution_allowed"] is False
        ):
            _fail("V182r1 progress checkpoint chain changed")
        previous = checkpoint_id


def verify_open_world_machine_campaign_independently_v182r1(
    campaign_bytes: bytes,
    progress_root: Path,
) -> dict[str, Any]:
    protocol_document = protocol.freeze_open_world_machine_protocol_v182().to_document()
    reveal_document = reveal.freeze_open_world_machine_manifest_reveal_v182r1().to_document()
    document = _object(campaign_bytes, "V182r1 campaign")
    if set(document) != _TOP_FIELDS:
        _fail("V182r1 campaign field set changed")
    payload = dict(document)
    campaign_id = payload.pop("campaign_id", None)
    if not (
        document["schema"] == "acfqp.open_world_machine_campaign.v182r1"
        and document["protocol_id"] == protocol_document["protocol_id"]
        and document["manifest_reveal_id"] == reveal_document["manifest_reveal_id"]
        and document["manifest_commitments"]
        == list(protocol.MANIFEST_COMMITMENTS_V182)
        and campaign_id
        == domains.extension_content_id_v182(
            domains.CONSTRUCTION_K7_CAMPAIGN_V182_DOMAIN,
            payload,
        )
    ):
        _fail("V182r1 campaign identity or predecessor join changed")
    source_oracle, target_oracle, ood_oracle = (_oracle(index) for index in range(3))
    source_rows = [_row(item) for item in document["source_observations"]]
    if len(source_rows) != protocol.OFFLINE_SOURCE_LABELS:
        _fail("V182r1 offline source label denominator changed")
    for row in source_rows:
        _exact_oracle_row(source_oracle, row)
    source_model = _compile(source_rows)
    archive = source_model.reusable_program_archive()
    if not (
        document["source_compiled_model"] == source_model.to_document()
        and document["source_label_count"] == len(source_rows)
        and document["source_synthesis_events"] == _synthesis_events(source_model)
        and document["source_archive_program_count"] == len(archive)
    ):
        _fail("V182r1 source model or compute accounting changed")
    ood = document["ood_no_transfer_control"]
    if not (
        type(ood) is dict
        and set(ood)
        == {
            "source_schema_signature",
            "ood_schema_signature",
            "prior_transfer_rejected",
            "rejected_before_target_query",
            "ood_target_query_count",
        }
        and ood["source_schema_signature"] == list(source_oracle.schema_signature())
        and ood["ood_schema_signature"] == list(ood_oracle.schema_signature())
        and source_oracle.schema_signature() != ood_oracle.schema_signature()
        and ood["prior_transfer_rejected"] is True
        and ood["rejected_before_target_query"] is True
        and ood["ood_target_query_count"] == 0
    ):
        _fail("V182r1 strict OOD no-transfer control changed")
    arm_documents = document["arm_results"]
    if type(arm_documents) is not list or [row.get("arm") for row in arm_documents] != list(protocol.ARMS):
        _fail("V182r1 matched arm order changed")
    summaries = {}
    for arm_document, arm in zip(arm_documents, protocol.ARMS, strict=True):
        summaries[arm] = _verify_arm(
            arm_document,
            oracle=target_oracle,
            arm=arm,
            archive=archive if arm == "REVALIDATED_MACHINE_PRIOR" else (),
        )
    prior = summaries["REVALIDATED_MACHINE_PRIOR"]
    no_prior = summaries["EMPTY_ARCHIVE_NO_PRIOR"]
    _verify_progress(
        progress_root,
        execution_id=document["execution_preregistration_id"],
        expected_ids=document["progress_checkpoint_ids"],
    )
    if not (
        document["prior_target_total_labels"] == prior["labels"]
        and document["no_prior_target_total_labels"] == no_prior["labels"]
        and document["target_labels_avoided"] == no_prior["labels"] - prior["labels"]
        and document["target_labels_avoided"] > 0
        and document["all_registered_episodes_terminal"] is True
        and document["same_synthesizer_and_stop_rule_both_arms"] is True
        and document["archive_mdl_discount_used"] is False
        and document["planner_consumed_only_compiled_models"] is True
        and document["all_local_ground_labels_followed_certificate_failure"] is True
        and document["label_axes_separate_from_execution_and_compute"] is True
        and document["progress_checkpoint_count"]
        == len(document["progress_checkpoint_ids"])
        and document["finite_candidate_program_catalog_used"] is False
        and document["named_domain_family_used"] is False
        and document["language_program_length_unbounded"] is True
        and document["occurrence_search_resource_bounded"] is True
        and document["partial_support_probability_authority_present"] is False
        and document["broad_iid_sample_efficiency_claimed"] is False
        and document["arbitrary_domain_transfer_claimed"] is False
        and document["total_work_dominance_claimed"] is False
        and document["COUNTER_COMPLETENESS_GATE"] == "NOT_RUN"
        and document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
        and document["official_scalar_cost"] is None
        and document["official_N_break_even"] is None
        and document["official_execution_allowed"] is False
    ):
        _fail("V182r1 campaign summary or claim locks changed")
    if EXPECTED_CAMPAIGN_ID != "0" * 64 and not (
        campaign_id == EXPECTED_CAMPAIGN_ID
        and len(campaign_bytes) == EXPECTED_CAMPAIGN_BYTE_COUNT
        and hashlib.sha256(campaign_bytes).hexdigest() == EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("V182r1 frozen campaign bytes changed")
    verification_payload = {
        "schema": "acfqp.open_world_machine_campaign_verification.v182r1",
        "execution_preregistration_id": document["execution_preregistration_id"],
        "campaign_id": campaign_id,
        "campaign_byte_count": len(campaign_bytes),
        "campaign_sha256": hashlib.sha256(campaign_bytes).hexdigest(),
        "source_observation_count": len(source_rows),
        "target_observation_count": sum(
            row["target_acquisition_label_count"] + row["execution_step_count"]
            for row in arm_documents
        ),
        "certificate_count": sum(row["certificate_count"] for row in arm_documents),
        "execution_step_count": sum(row["execution_step_count"] for row in arm_documents),
        "target_labels_avoided": document["target_labels_avoided"],
        "progress_checkpoint_count": document["progress_checkpoint_count"],
        "source_programs_reconstructed": True,
        "target_acquisition_reconstructed": True,
        "compiled_models_reconstructed": True,
        "abstract_plans_and_certificates_reconstructed": True,
        "target_executions_reconstructed": True,
        "certificate_failure_only_recovery_reconstructed": True,
        "strict_ood_no_transfer_reconstructed": True,
        "producer_module_imported": False,
        "finite_registered_campaign_verified": True,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_execution_allowed": False,
    }
    result = {
        **verification_payload,
        "verification_id": domains.extension_content_id_v182(
            domains.CONSTRUCTION_K7_VERIFICATION_V182_DOMAIN,
            verification_payload,
        ),
    }
    raw = canonical_json_bytes(result)
    if EXPECTED_VERIFICATION_ID != "0" * 64 and not (
        result["verification_id"] == EXPECTED_VERIFICATION_ID
        and len(raw) == EXPECTED_VERIFICATION_BYTE_COUNT
        and hashlib.sha256(raw).hexdigest() == EXPECTED_VERIFICATION_SHA256
    ):
        _fail("V182r1 frozen verification bytes changed")
    return result


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "EXPECTED_CAMPAIGN_BYTE_COUNT",
    "EXPECTED_CAMPAIGN_SHA256",
    "EXPECTED_VERIFICATION_ID",
    "EXPECTED_VERIFICATION_BYTE_COUNT",
    "EXPECTED_VERIFICATION_SHA256",
    "OpenWorldMachineIndependentVerifierV182R1Error",
    "verify_open_world_machine_campaign_independently_v182r1",
)
