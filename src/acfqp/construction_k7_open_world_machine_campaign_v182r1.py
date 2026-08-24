"""Fresh matched V182 campaign over commitment-hidden machine domains."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
from typing import Any, Iterable, NoReturn, Sequence

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
from acfqp.phase3e_ids import canonical_json_bytes


class OpenWorldMachineCampaignV182R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise OpenWorldMachineCampaignV182R1Error(message)


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


def _archive_reference_count(model: CompiledMachineWorldModelV182) -> int:
    return sum(
        int(row.synthesis.archive_reference_used) for row in model.coordinates
    ) + int(model.terminal_synthesis.archive_reference_used)


def _acquisition_input(
    oracle: OpaqueMachineOracleV182, unique_index: int
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    digest = hashlib.sha256(
        b"acfqp:v182r1:witness-blind-acquisition\x00"
        + oracle.manifest_commitment.encode()
        + unique_index.to_bytes(8, "big")
    ).digest()
    state = tuple(
        digest[index] % modulus
        for index, modulus in enumerate(oracle.initial_moduli)
    )
    action = tuple(
        digest[16 + index] % oracle.action_cardinality
        for index in range(oracle.action_width)
    )
    return state, action


def _query_block(
    oracle: OpaqueMachineOracleV182,
    *,
    occurrence_index: int,
    block_index: int,
) -> tuple[RawMachineTransitionV182, ...]:
    rows = []
    unique_per_block = (
        protocol.ACQUISITION_BLOCK_SIZE // protocol.ACQUISITION_REPEAT_COUNT
    )
    for local_unique in range(unique_per_block):
        unique_index = block_index * unique_per_block + local_unique
        state, action = _acquisition_input(oracle, unique_index)
        for repeat in range(protocol.ACQUISITION_REPEAT_COUNT):
            query_index = (
                block_index * protocol.ACQUISITION_BLOCK_SIZE
                + local_unique * protocol.ACQUISITION_REPEAT_COUNT
                + repeat
            )
            rows.append(
                oracle.query(
                    occurrence_index=occurrence_index,
                    query_index=query_index,
                    state=state,
                    action=action,
                )
            )
    return tuple(rows)


class _ProgressV182R1:
    def __init__(self, root: Path, execution_preregistration_id: str) -> None:
        if not isinstance(root, Path) or not root.is_dir() or any(root.iterdir()):
            _fail("V182r1 progress directory must be private, present, and empty")
        self._root = root
        self._execution_id = execution_preregistration_id
        self._previous: str | None = None
        self._sequence = 0
        self.ids: list[str] = []

    def append(self, stage: str, payload: dict[str, Any]) -> None:
        body = {
            "schema": "acfqp.open_world_machine_progress.v182r1",
            "execution_preregistration_id": self._execution_id,
            "sequence": self._sequence,
            "previous_checkpoint_id": self._previous,
            "stage": stage,
            "payload": payload,
            "outcome_progress_not_official_claim": True,
            "official_execution_allowed": False,
        }
        document = {
            **body,
            "progress_checkpoint_id": domains_r1.extension_content_id_v182r1(
                domains_r1.CONSTRUCTION_K7_PROGRESS_CHECKPOINT_V182R1_DOMAIN,
                body,
            ),
        }
        raw = canonical_json_bytes(document)
        path = self._root / f"checkpoint-{self._sequence:04d}.json"
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o400,
        )
        try:
            if os.write(descriptor, raw) != len(raw):
                _fail("V182r1 progress checkpoint short write")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        directory = os.open(
            self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self._previous = document["progress_checkpoint_id"]
        self.ids.append(self._previous)
        self._sequence += 1


@dataclass(frozen=True, slots=True)
class _AcquisitionV182R1:
    arm: str
    observations: tuple[RawMachineTransitionV182, ...]
    model: CompiledMachineWorldModelV182
    block_history: tuple[dict[str, Any], ...]
    cumulative_synthesis_events: int
    archive_reference_count: int
    revalidated_prior_credit: int

    def to_document(self) -> dict[str, Any]:
        return {
            "arm": self.arm,
            "source_label_count": len(self.observations),
            "source_observations": [row.to_document() for row in self.observations],
            "compiled_model": self.model.to_document(),
            "block_history": list(self.block_history),
            "cumulative_synthesis_events": self.cumulative_synthesis_events,
            "archive_reference_count": self.archive_reference_count,
            "revalidated_prior_credit": self.revalidated_prior_credit,
            "stopped": True,
            "same_synthesizer_and_stop_rule": True,
            "archive_mdl_discount_used": False,
            "witness_blind_acquisition": True,
        }


def _acquire_target(
    oracle: OpaqueMachineOracleV182,
    *,
    arm: str,
    archive: Sequence[ProgramV182],
    progress: _ProgressV182R1,
) -> _AcquisitionV182R1:
    observations: list[RawMachineTransitionV182] = []
    history: list[dict[str, Any]] = []
    model: CompiledMachineWorldModelV182 | None = None
    stable = 0
    credit = 0
    cumulative_events = 0
    archive_count = 0
    occurrence_index = 182_100 + protocol.ARMS.index(arm)
    block_count = protocol.MAXIMUM_TARGET_LABELS // protocol.ACQUISITION_BLOCK_SIZE
    for block_index in range(block_count):
        block = _query_block(
            oracle,
            occurrence_index=occurrence_index,
            block_index=block_index,
        )
        covered = model is not None and all(model.covers(row) for row in block)
        observations.extend(block)
        compiled = False
        events = 0
        if len(observations) >= protocol.MINIMUM_TARGET_LABELS:
            if covered:
                stable += 1
            else:
                model = _compile(observations, archive)
                compiled = True
                stable = 0
                events = _synthesis_events(model)
                cumulative_events += events
                archive_count = _archive_reference_count(model)
                credit = int(
                    arm == "REVALIDATED_MACHINE_PRIOR"
                    and archive_count > 0
                    and all(model.covers(row) for row in observations)
                ) * protocol.REVALIDATED_PRIOR_CONFIRMATION_CREDIT
        history_row = {
            "block_index": block_index,
            "cumulative_source_label_count": len(observations),
            "compiled": compiled,
            "model_reused_without_recompile": covered,
            "confirmation_zero_error": covered,
            "stable_confirmation_count": stable,
            "revalidated_prior_credit": credit,
            "effective_confirmation_count": stable + credit,
            "enumeration_events": events,
            "compiled_model_id": model.compiled_model_id if model else None,
        }
        history.append(history_row)
        progress.append(
            "TARGET_ACQUISITION_BLOCK",
            {"arm": arm, **history_row},
        )
        if (
            model is not None
            and stable + credit >= protocol.STABLE_CONFIRMATION_BLOCKS
        ):
            return _AcquisitionV182R1(
                arm,
                tuple(observations),
                model,
                tuple(history),
                cumulative_events,
                archive_count,
                credit,
            )
    _fail(f"V182r1 target acquisition did not stop for {arm}")


def _run_episodes(
    oracle: OpaqueMachineOracleV182,
    *,
    arm: str,
    acquisition: _AcquisitionV182R1,
    archive: Sequence[ProgramV182],
    progress: _ProgressV182R1,
) -> dict[str, Any]:
    model_rows = list(acquisition.observations)
    model = acquisition.model
    episodes = []
    local_labels = 0
    execution_steps = 0
    planning_events = 0
    certificate_count = 0
    recovery_compilation_events = 0
    for occurrence_offset in range(protocol.IID_OCCURRENCES_PER_ARM):
        occurrence_index = 182_200 + protocol.ARMS.index(arm) * 100 + occurrence_offset
        state = oracle.initial_state(occurrence_index)
        session = MachinePlannerSessionV182(
            model,
            legal_actions=oracle.legal_actions(),
            horizon=oracle.horizon,
        )
        steps = []
        for decision_index in range(protocol.MAXIMUM_DECISIONS_PER_OCCURRENCE):
            certificate = session.certify(state)
            certificate_count += 1
            planning_events += certificate.planning_compute_events
            if not certificate.certified or certificate.selected_action is None:
                _fail("V182r1 compiled model failed before an executable action")
            predicted = model.predict_support(state, certificate.selected_action)
            observed = oracle.query(
                occurrence_index=occurrence_index,
                query_index=decision_index,
                state=state,
                action=certificate.selected_action,
            )
            execution_steps += 1
            matched = observed.successor in predicted and (
                model.terminal(observed.successor) is observed.terminal
            )
            local = False
            failure = None
            if not matched:
                if local_labels >= protocol.MAXIMUM_TARGET_GROUND_LABELS_PER_ARM:
                    _fail("V182r1 local-ground label cap exhausted")
                failure = "FAILED_MISSING_SUPPORT_OR_TERMINAL"
                local = True
                local_labels += 1
                model_rows.append(observed)
                model = _compile(model_rows, archive)
                recovery_compilation_events += _synthesis_events(model)
                session = MachinePlannerSessionV182(
                    model,
                    legal_actions=oracle.legal_actions(),
                    horizon=oracle.horizon,
                )
                if not model.covers(observed):
                    _fail("V182r1 local distinction did not repair model coverage")
            step = {
                "decision_index": decision_index,
                "state": list(state),
                "certificate": certificate.to_document(),
                "selected_action": list(certificate.selected_action),
                "predicted_support": [list(row) for row in predicted],
                "observation": observed.to_document(),
                "certificate_support_matched": matched,
                "certificate_failure": failure,
                "local_ground_distinction_acquired": local,
                "local_ground_distinction_requires_preceding_failure": True,
                "compiled_model_id_after_step": model.compiled_model_id,
            }
            steps.append(step)
            state = observed.successor
            if observed.terminal:
                break
        if not oracle.terminal(state):
            _fail("V182r1 episode crossed its decision cap")
        episode = {
            "occurrence_index": occurrence_index,
            "initial_state": steps[0]["state"],
            "steps": steps,
            "execution_step_count": len(steps),
            "terminal_state": list(state),
            "terminal": True,
            "local_ground_label_count": sum(
                int(row["local_ground_distinction_acquired"]) for row in steps
            ),
        }
        episodes.append(episode)
        progress.append(
            "TARGET_EPISODE_TERMINAL",
            {
                "arm": arm,
                "occurrence_index": occurrence_index,
                "execution_step_count": len(steps),
                "local_ground_label_count": episode["local_ground_label_count"],
                "terminal": True,
            },
        )
    return {
        "arm": arm,
        "acquisition": acquisition.to_document(),
        "episodes": episodes,
        "terminal_episode_count": len(episodes),
        "target_acquisition_label_count": len(acquisition.observations),
        "target_local_ground_label_count": local_labels,
        "target_total_label_count": len(acquisition.observations) + local_labels,
        "execution_step_count": execution_steps,
        "planning_compute_events": planning_events,
        "certificate_count": certificate_count,
        "acquisition_synthesis_events": acquisition.cumulative_synthesis_events,
        "recovery_compilation_events": recovery_compilation_events,
        "planning_consumed_only_compiled_model": True,
        "ground_transition_argument_passed_to_planner": False,
        "all_local_ground_labels_followed_certificate_failure": True,
    }


def run_open_world_machine_campaign_v182r1(
    progress_directory: Path,
    *,
    execution_preregistration_id: str,
) -> dict[str, Any]:
    protocol_document = protocol.freeze_open_world_machine_protocol_v182().to_document()
    reveal_document = reveal.freeze_open_world_machine_manifest_reveal_v182r1().to_document()
    progress = _ProgressV182R1(progress_directory, execution_preregistration_id)
    source_oracle, target_oracle, ood_oracle = (_oracle(index) for index in range(3))
    if source_oracle.schema_signature() != target_oracle.schema_signature():
        _fail("V182r1 matched source and target schema changed")
    if source_oracle.schema_signature() == ood_oracle.schema_signature():
        _fail("V182r1 OOD schema negative control collapsed")
    source_rows = []
    source_block_count = (
        protocol.OFFLINE_SOURCE_LABELS // protocol.ACQUISITION_BLOCK_SIZE
    )
    for block_index in range(source_block_count):
        source_rows.extend(
            _query_block(
                source_oracle,
                occurrence_index=182_000,
                block_index=block_index,
            )
        )
    source_model = _compile(source_rows)
    archive = source_model.reusable_program_archive()
    progress.append(
        "OFFLINE_SOURCE_MODEL_COMPILED",
        {
            "source_label_count": len(source_rows),
            "compiled_model_id": source_model.compiled_model_id,
            "archive_program_count": len(archive),
            "synthesis_events": _synthesis_events(source_model),
        },
    )
    ood = {
        "source_schema_signature": list(source_oracle.schema_signature()),
        "ood_schema_signature": list(ood_oracle.schema_signature()),
        "prior_transfer_rejected": True,
        "rejected_before_target_query": True,
        "ood_target_query_count": 0,
    }
    rows = []
    for arm in protocol.ARMS:
        arm_archive = archive if arm == "REVALIDATED_MACHINE_PRIOR" else ()
        acquisition = _acquire_target(
            target_oracle,
            arm=arm,
            archive=arm_archive,
            progress=progress,
        )
        rows.append(
            _run_episodes(
                target_oracle,
                arm=arm,
                acquisition=acquisition,
                archive=arm_archive,
                progress=progress,
            )
        )
    by_arm = {row["arm"]: row for row in rows}
    prior = by_arm["REVALIDATED_MACHINE_PRIOR"]
    no_prior = by_arm["EMPTY_ARCHIVE_NO_PRIOR"]
    if not (
        prior["terminal_episode_count"] == protocol.IID_OCCURRENCES_PER_ARM
        and no_prior["terminal_episode_count"] == protocol.IID_OCCURRENCES_PER_ARM
        and prior["target_total_label_count"] < no_prior["target_total_label_count"]
    ):
        _fail("V182r1 registered matched sample-tax comparison did not pass")
    payload = {
        "schema": "acfqp.open_world_machine_campaign.v182r1",
        "execution_preregistration_id": execution_preregistration_id,
        "protocol_id": protocol_document["protocol_id"],
        "manifest_reveal_id": reveal_document["manifest_reveal_id"],
        "manifest_commitments": list(protocol.MANIFEST_COMMITMENTS_V182),
        "source_observations": [row.to_document() for row in source_rows],
        "source_compiled_model": source_model.to_document(),
        "source_label_count": len(source_rows),
        "source_synthesis_events": _synthesis_events(source_model),
        "source_archive_program_count": len(archive),
        "ood_no_transfer_control": ood,
        "arm_results": rows,
        "prior_target_total_labels": prior["target_total_label_count"],
        "no_prior_target_total_labels": no_prior["target_total_label_count"],
        "target_labels_avoided": (
            no_prior["target_total_label_count"] - prior["target_total_label_count"]
        ),
        "all_registered_episodes_terminal": True,
        "same_synthesizer_and_stop_rule_both_arms": True,
        "archive_mdl_discount_used": False,
        "planner_consumed_only_compiled_models": True,
        "all_local_ground_labels_followed_certificate_failure": True,
        "label_axes_separate_from_execution_and_compute": True,
        "progress_checkpoint_ids": list(progress.ids),
        "progress_checkpoint_count": len(progress.ids),
        "finite_candidate_program_catalog_used": False,
        "named_domain_family_used": False,
        "language_program_length_unbounded": True,
        "occurrence_search_resource_bounded": True,
        "partial_support_probability_authority_present": False,
        "broad_iid_sample_efficiency_claimed": False,
        "arbitrary_domain_transfer_claimed": False,
        "total_work_dominance_claimed": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "campaign_id": domains.extension_content_id_v182(
            domains.CONSTRUCTION_K7_CAMPAIGN_V182_DOMAIN,
            payload,
        ),
    }


__all__ = (
    "OpenWorldMachineCampaignV182R1Error",
    "run_open_world_machine_campaign_v182r1",
)
