"""Producer/core-free semantic verification of the frozen V56r1 campaign."""

from __future__ import annotations

from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import heapq
import random
from typing import Any, Iterator, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v56 as domains_v56
from acfqp import construction_k7_domain_registry_extension_v56r1 as domains_v56r1
from acfqp.domains.stochastic_balanced_batch_refinement import (
    generate_stochastic_balanced_batch_refinement,
)
from acfqp.domains.stochastic_batch_refinement import (
    BatchRefinementAction,
    BatchRefinementState,
    BatchRefinementStatus,
    select_seeded_batch_refinement_outcome_v1,
)
from acfqp.domains.stochastic_coupled_exchange import (
    CoupledExchangeAction,
    CoupledExchangeState,
    CoupledExchangeStatus,
    generate_stochastic_coupled_exchange,
    select_seeded_coupled_exchange_outcome_v1,
)
from acfqp.generic_atomic_expression_world_model_v4 import (
    FlatRawActionV4,
    FlatRawTransitionV4,
    GenericAtomicExpressionWorldModelV4Error,
    execute_generic_atomic_support_v4,
    missing_relation_values_v4,
    plan_generic_atomic_program_v4,
)
from acfqp.generic_joint_factor_residual_world_model_v9 import (
    synthesize_joint_factor_residual_world_model_v9,
)
from acfqp.generic_layout_factorized_world_model_v5 import (
    align_generic_occurrence_v5,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11 import (
    MDLAdaptiveJointCandidateV11,
    exact_candidate_replay_v11,
    synthesize_mdl_adaptive_joint_candidate_v11,
)
from acfqp.generic_mdl_adaptive_joint_synthesizer_v11r1 import (
    mdl_confidence_or_exact_frontier_stop_update_v11r1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    canonical_json_bytes,
    loads_canonical_json,
)


EXPECTED_CAMPAIGN_ID = "0f5032377cd52b021133fe03a4ab4a34613a230bd3ae25efa43e02ca911521a8"
EXPECTED_CAMPAIGN_BYTE_COUNT = 16_064_927
EXPECTED_CAMPAIGN_SHA256 = "67188187a8fcda709fdcd287d653c3140a7dcf40618b4588faae355ff761f3e5"
EXPECTED_PREREGISTRATION_ID = (
    "422df5321236e8e9b7f7516bae1e88fe428ef794fa940a2bae00479af00d52ed"
)
EXPECTED_V56_FAILURE_ID = (
    "7d0e88ba7d78d96c6ff635515313707cda915fde39f5902e0a7d202bcf05348c"
)
VERIFICATION_ID = "8aa9de632593f60ae8ac59cac3f0affa25568caf011211271913d8732e66733f"
EXPECTED_CANONICAL_BYTE_COUNT = 1_984
EXPECTED_CANONICAL_SHA256 = "ff828ce63c0a6a9acb2e5ad7ce5ca6cf83ed72ece2b2d46391d1c7d9cdcda5cd"

_TOKENS = {"A": 9_001, "F": 9_007, "S": 9_011}
_BALANCED_SEEDS = tuple(range(563_101, 563_133))
_COUPLED_SEEDS = tuple(range(564_101, 564_133))
_PLANNING_COUNT = 4
_FACTOR_LIBRARY_LABELS = 370
_FACTOR_CREDIT = 16
_CONFIDENCE_RESERVE = 48
_INVALIDATED_PENALTY = 16
_MAXIMUM_RELATION_OUTPUT = 64
_MAXIMUM_LOCAL_RESYNTHESES = 8
_LIBRARY = {
    "factor_library_id": (
        "46aa60cc33ca61238612342ed9fe73e91cfa7bfb639b4a8f0afa29c491428162"
    ),
    "cross_schema_subprograms": [
        {
            "signature_sha256": signature,
            "source_schema_pairs": [[7, 5], [9, 6]],
        }
        for signature in (
            "012651c74d7a2c07190817603bc2aeb9a069c8c1dc5a3f9d828518a03aeb367e",
            "16fcf756e4d606282a0f656f4ab960069273f8f895d8a0abcf7f0d530c07a072",
            "c2fe69a54e58afa7f6c68992e4ea16eb6aa5800b6543d9c1022729dc6ebc52b5",
        )
    ],
}
_GENERIC_DOMAINS = {
    "layout": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_LAYOUT_V54_DOMAIN,
    "program": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_PROGRAM_V54_DOMAIN,
    "support": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_SUPPORT_V54_DOMAIN,
    "model": CONSTRUCTION_K7_JOINT_FACTOR_RESIDUAL_MODEL_V54_DOMAIN,
}
_V56_DOMAINS = {
    "candidate": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_CANDIDATE_V56_DOMAIN,
    "failed_certificate": (
        domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_FAILED_CERTIFICATE_V56_DOMAIN
    ),
    "distinction": (
        domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_LOCAL_DISTINCTION_V56_DOMAIN
    ),
    "episode": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_EPISODE_V56_DOMAIN,
    "validation": (
        domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_ISOLATED_VALIDATION_V56_DOMAIN
    ),
    "ood": domains_v56.CONSTRUCTION_K7_MDL_ADAPTIVE_OOD_REJECTION_V56_DOMAIN,
}
_V56R1_DOMAINS = {
    "acquisition": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_ACQUISITION_V56R1_DOMAIN
    ),
    "sample_tax": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_SAMPLE_TAX_V56R1_DOMAIN
    ),
    "campaign": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_CAMPAIGN_V56R1_DOMAIN
    ),
    "verification": (
        domains_v56r1.CONSTRUCTION_K7_MDL_ADAPTIVE_VERIFICATION_V56R1_DOMAIN
    ),
}


class ConstructionK7MDLAdaptiveIndependentVerifierV56R1Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise ConstructionK7MDLAdaptiveIndependentVerifierV56R1Error(message)


@dataclass(frozen=True, slots=True)
class _GroundAdapter:
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    encode: Any

    def initial(self) -> Any:
        return self.kernel.initial_distribution()[0][1]

    def actions(self, state: Any) -> tuple[Any, ...]:
        return tuple(self.kernel.actions(state))

    def action_key(self, action: Any) -> int:
        return action.rule if self.family == "BALANCED_BATCH_REFINEMENT" else action.exchange

    def action(self, key: int) -> Any:
        return (
            BatchRefinementAction(key)
            if self.family == "BALANCED_BATCH_REFINEMENT"
            else CoupledExchangeAction(key)
        )

    def active(self, state: Any) -> bool:
        return (
            state.status is BatchRefinementStatus.ACTIVE
            if self.family == "BALANCED_BATCH_REFINEMENT"
            else state.status is CoupledExchangeStatus.ACTIVE
        )

    def success(self, state: Any) -> bool:
        return (
            state.status is BatchRefinementStatus.SUCCESS
            if self.family == "BALANCED_BATCH_REFINEMENT"
            else state.status is CoupledExchangeStatus.SUCCESS
        )

    def probe_state(self, key: int) -> Any:
        rule = self.kernel.rules[key]
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return BatchRefinementState(
                rule.source_stage, 0, 0, 0, BatchRefinementStatus.ACTIVE
            )
        return CoupledExchangeState(
            rule.source_stage,
            0,
            0,
            0,
            0,
            rule.source_stage,
            CoupledExchangeStatus.ACTIVE,
        )

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        outcomes = self.kernel.step(state, self.action(key))
        if self.family == "BALANCED_BATCH_REFINEMENT":
            return select_seeded_batch_refinement_outcome_v1(
                outcomes,
                seed=self.seed,
                episode_index=episode_index,
                decision_index=decision_index,
            )
        return select_seeded_coupled_exchange_outcome_v1(
            outcomes,
            seed=self.seed,
            episode_index=episode_index,
            decision_index=decision_index,
        )


def _balanced_interface(seed: int, kernel: Any):
    state_order = list(range(6))
    action_order = list(range(5))
    random.Random(seed ^ 0x56A17).shuffle(state_order)
    random.Random(seed ^ 0x56B29).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    rule.source_stage,
                    rule.anonymous_advance_class,
                    rule.unit_increment,
                    rule.risk_increment,
                    1,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )

    def encode(state: BatchRefinementState) -> tuple[int, ...]:
        status = _TOKENS[
            "A"
            if state.status is BatchRefinementStatus.ACTIVE
            else "S"
            if state.status is BatchRefinementStatus.SUCCESS
            else "F"
        ]
        semantic = (
            state.stage,
            state.units,
            state.risk,
            status,
            kernel.risk_capacity,
            kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return catalogue, encode


def _coupled_interface(seed: int, kernel: Any):
    state_order = list(range(10))
    action_order = list(range(6))
    random.Random(seed ^ 0x56C37).shuffle(state_order)
    random.Random(seed ^ 0x56D49).shuffle(action_order)
    catalogue = tuple(
        FlatRawActionV4(
            key,
            tuple(
                (
                    seed * 100 + rule.source_stage,
                    seed * 100 + rule.destination_stage,
                    rule.primary_increment,
                    rule.secondary_increment,
                    rule.risk_increment,
                    seed * 10_000 + key,
                )[index]
                for index in action_order
            ),
        )
        for key, rule in enumerate(kernel.rules)
    )

    def encode(state: CoupledExchangeState) -> tuple[int, ...]:
        status = _TOKENS[
            "A"
            if state.status is CoupledExchangeStatus.ACTIVE
            else "S"
            if state.status is CoupledExchangeStatus.SUCCESS
            else "F"
        ]
        semantic = (
            seed * 100 + state.stage,
            state.primary,
            state.secondary,
            state.bonus,
            state.risk,
            state.steps,
            status,
            kernel.risk_capacity,
            kernel.target_primary,
            seed * 100 + kernel.goal_stage,
        )
        return tuple(semantic[index] for index in state_order)

    return catalogue, encode


def _adapter(family: str, seed: int) -> _GroundAdapter:
    if family == "BALANCED_BATCH_REFINEMENT":
        kernel, witness = generate_stochastic_balanced_batch_refinement(
            stage_count=9, unit_base=5, seed=seed
        )
        catalogue, encode = _balanced_interface(seed, kernel)
    elif family == "COUPLED_EXCHANGE":
        kernel, witness = generate_stochastic_coupled_exchange(
            stage_count=7, primary_base=5, seed=seed
        )
        catalogue, encode = _coupled_interface(seed, kernel)
    else:  # pragma: no cover
        _fail("V56r1 independent family changed")
    del witness
    return _GroundAdapter(family, seed, kernel, catalogue, encode)


def _transition_batch(
    adapter: _GroundAdapter, state: Any, key: int, index: int
) -> tuple[FlatRawTransitionV4, ...]:
    legal = adapter.actions(state)
    action = adapter.action(key)
    if action not in legal:
        _fail("V56r1 independent ground query became illegal")
    rows = []
    for offset, outcome in enumerate(adapter.kernel.step(state, action)):
        successor = outcome.next_state
        legal_after = adapter.actions(successor)
        rows.append(
            FlatRawTransitionV4(
                0,
                index + offset,
                adapter.encode(state),
                tuple(adapter.action_key(row) for row in legal),
                adapter.catalogue[key],
                adapter.encode(successor),
                tuple(adapter.action_key(row) for row in legal_after),
                None if legal_after else adapter.success(successor),
            )
        )
    return tuple(rows)


def _frontier(adapter: _GroundAdapter) -> Iterator[tuple[FlatRawTransitionV4, ...]]:
    initial = adapter.initial()
    frontier = [(0, 0, initial)]
    seen = {initial}
    insertion = 1
    pending = deque()
    transition_index = 0
    while frontier or pending:
        if not pending:
            negative_depth, _ordinal, state = heapq.heappop(frontier)
            depth = -negative_depth
            pending.extend((state, action, depth) for action in adapter.actions(state))
        state, action, depth = pending.popleft()
        key = adapter.action_key(action)
        batch = _transition_batch(adapter, state, key, transition_index)
        transition_index += len(batch)
        for outcome in adapter.kernel.step(state, action):
            successor = outcome.next_state
            if adapter.active(successor) and successor not in seen:
                seen.add(successor)
                heapq.heappush(frontier, (-(depth + 1), insertion, successor))
                insertion += 1
        yield batch


def _raw_sha(rows: tuple[FlatRawTransitionV4, ...]) -> str:
    return hashlib.sha256(
        canonical_json_bytes([row.to_document() for row in rows])
    ).hexdigest()


def _candidate(
    rows: tuple[FlatRawTransitionV4, ...],
    catalogue: tuple[FlatRawActionV4, ...],
    labels: int,
) -> MDLAdaptiveJointCandidateV11:
    return synthesize_mdl_adaptive_joint_candidate_v11(
        rows,
        catalogue,
        _LIBRARY,
        support_label_count=labels,
        generic_domains=_GENERIC_DOMAINS,
        candidate_domain=_V56_DOMAINS["candidate"],
        candidate_content_id=domains_v56.extension_content_id_v56,
        minimum_reusable_factor_count=3,
    )


def _acquisition_document(
    *,
    adapter: _GroundAdapter,
    arm: str,
    prior: bool,
    labels: int,
    rows: tuple[FlatRawTransitionV4, ...],
    candidate: MDLAdaptiveJointCandidateV11,
    issued_at: int,
    invalidated: int,
    disagreements: int,
    history: list[dict[str, Any]],
    stop: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.mdl_adaptive_acquisition.v56r1",
        "failed_predecessor_id": EXPECTED_V56_FAILURE_ID,
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": arm,
        "factor_prior_enabled": prior,
        "ground_support_labels": labels,
        "raw_transition_count": len(rows),
        "raw_transition_sha256": _raw_sha(rows),
        "candidate": dict(candidate.public_document),
        "candidate_issued_at_support_label": issued_at,
        "invalidated_candidate_count": invalidated,
        "candidate_program_disagreement_count": disagreements,
        "stopping_history": history,
        "terminal_stop_update": dict(stop),
        "stopped_by_mdl_confidence_margin": stop[
            "stopped_by_mdl_confidence_margin"
        ],
        "stopped_by_exact_reachable_frontier_closure": stop[
            "exact_reachable_frontier_closure_stop"
        ],
        "candidate_synthesis_attempted_after_every_support_query": True,
        "minimum_candidate_label_floor_consumed": False,
        "confirmation_block_consumed": False,
        "witness_blind_depth_frontier_policy": True,
        "generation_witness_accessed": False,
        "full_frontier_calibration_consumed": False,
        "same_synthesizer_query_order_mdl_confidence_and_frontier_rule": True,
        "only_switched_variable": "REGISTERED_FACTOR_CODE_CREDIT_UNITS",
    }
    return {
        **payload,
        "acquisition_id": domains_v56r1.extension_content_id_v56r1(
            _V56R1_DOMAINS["acquisition"], payload
        ),
    }


def _acquire_matched(adapter: _GroundAdapter) -> dict[str, dict[str, Any]]:
    rows: list[FlatRawTransitionV4] = []
    batches: list[tuple[FlatRawTransitionV4, ...]] = []
    candidate: MDLAdaptiveJointCandidateV11 | None = None
    issued_at = 0
    invalidated = 0
    disagreements = 0
    previous_fingerprint = None
    pending = {
        "ANONYMOUS_FACTOR_PRIOR_ON": True,
        "STRICT_NO_PRIOR": False,
    }
    histories = {arm: [] for arm in pending}
    results: dict[str, dict[str, Any]] = {}
    maximum = 128 if adapter.family == "BALANCED_BATCH_REFINEMENT" else 160
    stream = iter(_frontier(adapter))
    try:
        batch = next(stream)
    except StopIteration:  # pragma: no cover
        _fail("V56r1 independent frontier was empty")
    for labels in range(1, maximum + 1):
        try:
            next_batch = next(stream)
            exhausted = False
        except StopIteration:
            next_batch = None
            exhausted = True
        rows.extend(batch)
        batches.append(batch)
        reason = "NO_COMPLETE_CANDIDATE_YET"
        replay = None
        if candidate is not None:
            replay = exact_candidate_replay_v11(
                candidate, tuple(rows), adapter.catalogue
            )
            if replay["exact"] is not True:
                invalidated += 1
                previous_fingerprint = candidate.public_document[
                    "program_fingerprint_sha256"
                ]
                candidate = None
                reason = "COUNTEREVIDENCE_INVALIDATED_COMPLETE_CANDIDATE"
        if candidate is None:
            try:
                candidate = _candidate(tuple(rows), adapter.catalogue, labels)
            except Exception:
                for arm in tuple(pending):
                    histories[arm].append(
                        {
                            "support_label_count": labels,
                            "raw_transition_sha256": _raw_sha(tuple(rows)),
                            "update_reason": reason,
                            "candidate_available": False,
                            "witness_blind_reachable_frontier_exhausted": exhausted,
                        }
                    )
                if exhausted:
                    _fail("V56r1 independent frontier closed without a candidate")
                if next_batch is None:  # pragma: no cover
                    raise AssertionError
                batch = next_batch
                continue
            issued_at = labels
            fingerprint = candidate.public_document["program_fingerprint_sha256"]
            if previous_fingerprint is not None and fingerprint != previous_fingerprint:
                disagreements += 1
            reason = (
                "FIRST_COMPLETE_CANDIDATE_SYNTHESIZED"
                if invalidated == 0
                else "COUNTEREVIDENCE_TRIGGERED_COMPLETE_RESYNTHESIS"
            )
        for arm, prior in tuple(pending.items()):
            stop = mdl_confidence_or_exact_frontier_stop_update_v11r1(
                candidate,
                tuple(rows),
                adapter.catalogue,
                factor_prior_enabled=prior,
                invalidated_candidate_count=invalidated,
                candidate_program_disagreement_count=disagreements,
                factor_signature_credit_units=_FACTOR_CREDIT,
                confidence_reserve_units=_CONFIDENCE_RESERVE,
                invalidated_candidate_penalty_units=_INVALIDATED_PENALTY,
                minimum_reusable_factor_count=3,
                witness_blind_reachable_frontier_exhausted=exhausted,
            )
            histories[arm].append(
                {
                    "support_label_count": labels,
                    "raw_transition_sha256": _raw_sha(tuple(rows)),
                    "update_reason": reason,
                    "candidate_available": True,
                    "candidate_id": candidate.public_document["candidate_id"],
                    "exact_replay": replay,
                    "stop_update": stop,
                }
            )
            if stop["stopped"] is not True:
                continue
            document = _acquisition_document(
                adapter=adapter,
                arm=arm,
                prior=prior,
                labels=labels,
                rows=tuple(rows),
                candidate=candidate,
                issued_at=issued_at,
                invalidated=invalidated,
                disagreements=disagreements,
                history=list(histories[arm]),
                stop=stop,
            )
            results[arm] = {
                "document": document,
                "candidate": candidate,
                "rows": tuple(rows),
                "batches": tuple(batches),
            }
            del pending[arm]
        if not pending:
            prior_result = results["ANONYMOUS_FACTOR_PRIOR_ON"]
            no_prior_result = results["STRICT_NO_PRIOR"]
            common = tuple(
                row
                for item in no_prior_result["batches"][
                    : len(prior_result["batches"])
                ]
                for row in item
            )
            if prior_result["rows"] != common:
                _fail("V56r1 independent matched acquisition prefix changed")
            return results
        if exhausted:
            _fail("V56r1 independent exact frontier failed to stop both arms")
        if next_batch is None:  # pragma: no cover
            raise AssertionError
        batch = next_batch
    _fail("V56r1 independent acquisition crossed its cap")


def _relation_fields(program: Mapping[str, Any]) -> dict[str, int]:
    result: dict[str, int] = {}

    def visit(expression: Any) -> None:
        if type(expression) is not list:
            return
        if (
            len(expression) >= 3
            and expression[0] == "E04"
            and type(expression[2]) is list
            and expression[2][:1] == ["E01"]
        ):
            result[expression[1]] = expression[2][1]
        for item in expression:
            visit(item)

    for assignment in program["compiled_assignments"]:
        visit(assignment["expression"])
    return result


def _candidate_cap(state: tuple[int, ...], name: str) -> int:
    suffix = name.rsplit("_", 1)[-1]
    if suffix.isascii() and suffix.isdigit():
        column = int(suffix)
        if 0 <= column < len(state) and state[column] > 0:
            return min(_MAXIMUM_RELATION_OUTPUT, state[column] - 1)
    return _MAXIMUM_RELATION_OUTPUT


def _recover_relation(
    program: Mapping[str, Any],
    binding: Mapping[str, Any],
    state: tuple[int, ...],
    action: FlatRawActionV4,
    actual: set[tuple[int, ...]],
    name: str,
    relation_input: int,
    overlay: Mapping[str, Mapping[int, int]],
) -> int:
    matches = []
    for value in range(_candidate_cap(state, name) + 1):
        trial = {key: dict(values) for key, values in overlay.items()}
        trial.setdefault(name, {})[relation_input] = value
        try:
            predicted = set(
                execute_generic_atomic_support_v4(
                    program,
                    state,
                    action,
                    binding,
                    relation_overlay=trial,
                )
            )
        except (GenericAtomicExpressionWorldModelV4Error, ZeroDivisionError):
            continue
        if predicted == actual:
            matches.append(value)
    if len(matches) != 1:
        _fail("V56r1 independent local relation recovery was not unique")
    return matches[0]


def _certificate(
    adapter: _GroundAdapter,
    arm: str,
    episode_index: int,
    decision_index: int,
    program_id: str,
    kind: str,
    detail: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.mdl_adaptive_failed_certificate.v56",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": arm,
        "episode_index": episode_index,
        "decision_index": decision_index,
        "program_id": program_id,
        "failure_kind": kind,
        "failure_detail": dict(detail),
        "ground_query_performed_before_failure": False,
    }
    return {
        **payload,
        "failed_certificate_id": domains_v56.extension_content_id_v56(
            _V56_DOMAINS["failed_certificate"], payload
        ),
    }


def _distinction(
    failure: Mapping[str, Any],
    kind: str,
    detail: Mapping[str, Any],
    labels: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.mdl_adaptive_local_distinction.v56",
        "failed_certificate_id": failure["failed_certificate_id"],
        "distinction_kind": kind,
        "distinction_detail": dict(detail),
        "query_after_failed_certificate": True,
        "ground_support_labels": labels,
    }
    return {
        **payload,
        "local_distinction_id": domains_v56.extension_content_id_v56(
            _V56_DOMAINS["distinction"], payload
        ),
    }


def _abstract_episode(
    adapter: _GroundAdapter,
    arm: str,
    episode_index: int,
    acquisition: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    candidate = acquisition["candidate"]
    evidence_rows = list(acquisition["rows"])
    covered = {(row.pre, row.action.key) for row in evidence_rows}
    failures: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    overlay: dict[str, dict[int, int]] = {}
    actions: list[int] = []
    tapes: list[str] = []
    planning_compute = 0
    peak_cache = 0
    local_labels = 0
    resynthesis_count = 0
    recovery_attempts = 0
    state = adapter.initial()
    decision = 0
    initial_candidate_id = candidate.public_document["candidate_id"]
    while adapter.active(state):
        program = candidate.program
        layout = candidate.layout
        _aligned_rows, aligned_catalogue = align_generic_occurrence_v5(
            tuple(evidence_rows),
            adapter.catalogue,
            layout,
            canonical_occurrence=0,
        )
        binding = program["occurrence_bindings"][0]
        raw_state = adapter.encode(state)
        canonical_state = tuple(
            raw_state[index] for index in layout.state_canonical_to_raw
        )
        fields = _relation_fields(program)
        missing = sorted(
            {
                item
                for action in aligned_catalogue
                for item in missing_relation_values_v4(
                    program,
                    action,
                    binding,
                    relation_overlay=overlay,
                )
            }
        )
        for name, relation_input in missing:
            failure = _certificate(
                adapter,
                arm,
                episode_index,
                decision,
                program["program_id"],
                "MISSING_COMPILED_RELATION_SUPPORT",
                {"relation_name": name, "relation_input": relation_input},
            )
            failures.append(failure)
            field = fields[name]
            aligned_action = next(
                row for row in aligned_catalogue if row.fields[field] == relation_input
            )
            probe = adapter.probe_state(aligned_action.key)
            raw_probe = adapter.encode(probe)
            canonical_probe = tuple(
                raw_probe[index] for index in layout.state_canonical_to_raw
            )
            actual = {
                tuple(
                    adapter.encode(outcome.next_state)[index]
                    for index in layout.state_canonical_to_raw
                )
                for outcome in adapter.kernel.step(
                    probe, adapter.action(aligned_action.key)
                )
            }
            value = _recover_relation(
                program,
                binding,
                canonical_probe,
                aligned_action,
                actual,
                name,
                relation_input,
                overlay,
            )
            overlay.setdefault(name, {})[relation_input] = value
            distinctions.append(
                _distinction(
                    failure,
                    "RELATION_OUTPUT_RECOVERED",
                    {
                        "relation_name": name,
                        "relation_input": relation_input,
                        "relation_output": value,
                    },
                    1,
                )
            )
            local_labels += 1
        plan, evaluations, cache_size = plan_generic_atomic_program_v4(
            program,
            canonical_state,
            aligned_catalogue,
            binding,
            relation_overlay=overlay,
        )
        key = plan[0]
        planning_compute += evaluations
        peak_cache = max(peak_cache, cache_size)
        pair = (raw_state, key)
        if pair not in covered:
            failure = _certificate(
                adapter,
                arm,
                episode_index,
                decision,
                program["program_id"],
                "MISSING_QUERY_LOCAL_STATE_ACTION_SUPPORT",
                {"raw_state": list(raw_state), "action_key": key},
            )
            failures.append(failure)
            batch = _transition_batch(adapter, state, key, len(evidence_rows))
            local_labels += 1
            aligned_batch, _ = align_generic_occurrence_v5(
                batch,
                adapter.catalogue,
                layout,
                canonical_occurrence=0,
            )
            actual = {row.post for row in aligned_batch}
            aligned_action = next(row for row in aligned_catalogue if row.key == key)
            try:
                predicted = set(
                    execute_generic_atomic_support_v4(
                        program,
                        canonical_state,
                        aligned_action,
                        binding,
                        relation_overlay=overlay,
                    )
                )
            except Exception:
                predicted = set()
            evidence_rows.extend(batch)
            covered.add(pair)
            if predicted != actual:
                recovery_attempts += 1
                if recovery_attempts > _MAXIMUM_LOCAL_RESYNTHESES:
                    _fail("V56r1 independent local resynthesis cap crossed")
                candidate = _candidate(
                    tuple(evidence_rows),
                    adapter.catalogue,
                    acquisition["document"]["ground_support_labels"] + local_labels,
                )
                overlay = {}
                resynthesis_count += 1
                distinctions.append(
                    _distinction(
                        failure,
                        "QUERY_LOCAL_COUNTEREXAMPLE_RESYNTHESIZED_PROGRAM",
                        {
                            "predicted_support": [list(row) for row in sorted(predicted)],
                            "actual_support": [list(row) for row in sorted(actual)],
                            "successor_candidate_id": candidate.public_document[
                                "candidate_id"
                            ],
                        },
                        1,
                    )
                )
                continue
            distinctions.append(
                _distinction(
                    failure,
                    "QUERY_LOCAL_SUPPORT_CONFIRMED_WITHOUT_PROGRAM_CHANGE",
                    {"action_key": key, "support_cardinality": len(actual)},
                    1,
                )
            )
        outcome, tape = adapter.select_outcome(
            state, key, episode_index, decision
        )
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
        decision += 1
    payload = {
        "schema": "acfqp.mdl_adaptive_receding_episode.v56",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": arm,
        "initial_candidate_id": initial_candidate_id,
        "final_candidate_id": candidate.public_document["candidate_id"],
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning_compute,
        "peak_planning_cache_entries": peak_cache,
        "local_ground_support_labels": local_labels,
        "failed_certificate_count": len(failures),
        "local_program_resynthesis_count": resynthesis_count,
        "all_ground_queries_followed_failed_certificates": (
            local_labels
            == sum(row["ground_support_labels"] for row in distinctions)
            and len(failures) == len(distinctions)
        ),
        "success": adapter.success(state),
    }
    return (
        {
            **payload,
            "episode_id": domains_v56.extension_content_id_v56(
                _V56_DOMAINS["episode"], payload
            ),
        },
        failures,
        distinctions,
    )


def _strict_choice(
    adapter: _GroundAdapter, state: Any, cache: dict[Any, Any]
) -> tuple[int, int, int]:
    choices: dict[Any, int] = {}
    labels = 0

    @lru_cache(maxsize=None)
    def solve(current: Any) -> bool:
        nonlocal labels
        if adapter.success(current):
            return True
        if not adapter.active(current):
            return False
        for action in adapter.actions(current):
            key = adapter.action_key(action)
            pair = (current, key)
            if pair not in cache:
                cache[pair] = tuple(
                    row.next_state for row in adapter.kernel.step(current, action)
                )
                labels += 1
            if all(solve(successor) for successor in cache[pair]):
                choices[current] = key
                return True
        return False

    if not solve(state) or state not in choices:
        _fail("V56r1 independent strict planner found no continuation")
    return choices[state], solve.cache_info().currsize, labels


def _strict_episode(adapter: _GroundAdapter, episode_index: int) -> dict[str, Any]:
    state = adapter.initial()
    cache: dict[Any, Any] = {}
    actions: list[int] = []
    tapes: list[str] = []
    planning = 0
    peak = 0
    labels = 0
    decision = 0
    while adapter.active(state):
        key, compute, new_labels = _strict_choice(adapter, state, cache)
        outcome, tape = adapter.select_outcome(
            state, key, episode_index, decision
        )
        state = outcome.next_state
        actions.append(key)
        tapes.append(tape)
        planning += compute
        peak = max(peak, compute)
        labels += new_labels
        decision += 1
    payload = {
        "schema": "acfqp.mdl_adaptive_receding_episode.v56",
        "family": adapter.family,
        "seed": adapter.seed,
        "arm": "STRICT_EXACT_CONTEXT",
        "initial_candidate_id": None,
        "final_candidate_id": None,
        "action_keys": actions,
        "outcome_tape_sha256": tapes,
        "execution_steps": len(actions),
        "planning_compute_events": planning,
        "peak_planning_cache_entries": peak,
        "local_ground_support_labels": labels,
        "failed_certificate_count": 0,
        "local_program_resynthesis_count": 0,
        "all_ground_queries_followed_failed_certificates": True,
        "success": adapter.success(state),
    }
    return {
        **payload,
        "episode_id": domains_v56.extension_content_id_v56(
            _V56_DOMAINS["episode"], payload
        ),
    }


def _validation(
    adapter: _GroundAdapter, acquisitions: Mapping[str, Any]
) -> dict[str, Any]:
    batches = tuple(_frontier(adapter))
    rows = tuple(row for batch in batches for row in batch)
    arms = {}
    for arm, acquisition in sorted(acquisitions.items()):
        replay = exact_candidate_replay_v11(
            acquisition["candidate"], rows, adapter.catalogue
        )
        arms[arm] = {
            **replay,
            "candidate_id": acquisition["candidate"].public_document[
                "candidate_id"
            ],
        }
    payload = {
        "schema": "acfqp.mdl_adaptive_isolated_validation.v56",
        "family": adapter.family,
        "seed": adapter.seed,
        "full_frontier_ground_support_labels": len(batches),
        "full_frontier_raw_transition_count": len(rows),
        "full_frontier_raw_transition_sha256": _raw_sha(rows),
        "arm_replay": arms,
        "validation_rows_consumed_for_acquisition": False,
        "validation_rows_consumed_for_binding": False,
        "validation_rows_consumed_for_planning": False,
        "honest_partial_dynamics_reported": True,
    }
    return {
        **payload,
        "isolated_validation_id": domains_v56.extension_content_id_v56(
            _V56_DOMAINS["validation"], payload
        ),
    }


def _verify_occurrence(args: tuple[Any, ...]) -> dict[str, Any]:
    (
        family,
        family_index,
        seed,
        expected_prior,
        expected_no_prior,
        expected_episodes,
        expected_validation,
    ) = args
    adapter = _adapter(family, seed)
    acquisitions = _acquire_matched(adapter)
    if acquisitions["ANONYMOUS_FACTOR_PRIOR_ON"]["document"] != expected_prior:
        _fail(f"V56r1 independent prior acquisition changed at {family} {seed}")
    if acquisitions["STRICT_NO_PRIOR"]["document"] != expected_no_prior:
        _fail(f"V56r1 independent no-prior acquisition changed at {family} {seed}")
    failures: list[dict[str, Any]] = []
    distinctions: list[dict[str, Any]] = []
    local = {"ANONYMOUS_FACTOR_PRIOR_ON": 0, "STRICT_NO_PRIOR": 0}
    execution = {arm: 0 for arm in (*local, "STRICT_EXACT_CONTEXT")}
    planning = dict(execution)
    validation_labels = 0
    validation_mismatches = 0
    if family_index < _PLANNING_COUNT:
        rebuilt = {}
        for arm in ("ANONYMOUS_FACTOR_PRIOR_ON", "STRICT_NO_PRIOR"):
            episode, arm_failures, arm_distinctions = _abstract_episode(
                adapter, arm, family_index, acquisitions[arm]
            )
            rebuilt[arm] = episode
            failures.extend(arm_failures)
            distinctions.extend(arm_distinctions)
            local[arm] = episode["local_ground_support_labels"]
        rebuilt["STRICT_EXACT_CONTEXT"] = _strict_episode(adapter, family_index)
        if rebuilt != expected_episodes:
            _fail(f"V56r1 independent held-out episodes changed at {family} {seed}")
        if len({tuple(row["action_keys"]) for row in rebuilt.values()}) != 1:
            _fail("V56r1 independent matched plans diverged")
        for arm, row in rebuilt.items():
            execution[arm] = row["execution_steps"]
            planning[arm] = row["planning_compute_events"]
        validation = _validation(adapter, acquisitions)
        if validation != expected_validation:
            _fail(f"V56r1 independent validation changed at {family} {seed}")
        validation_labels = validation["full_frontier_ground_support_labels"]
        validation_mismatches = sum(
            row["support_mismatch_count"]
            for row in validation["arm_replay"].values()
        )
    elif expected_episodes or expected_validation is not None:
        _fail("V56r1 unregistered planning occurrence gained evidence")
    return {
        "family": family,
        "seed": seed,
        "prior_labels": expected_prior["ground_support_labels"],
        "no_prior_labels": expected_no_prior["ground_support_labels"],
        "prior_local": local["ANONYMOUS_FACTOR_PRIOR_ON"],
        "no_prior_local": local["STRICT_NO_PRIOR"],
        "prior_exact_frontier": expected_prior[
            "stopped_by_exact_reachable_frontier_closure"
        ],
        "no_prior_exact_frontier": expected_no_prior[
            "stopped_by_exact_reachable_frontier_closure"
        ],
        "prior_invalidated": expected_prior["invalidated_candidate_count"],
        "no_prior_invalidated": expected_no_prior["invalidated_candidate_count"],
        "prior_program_disagreements": expected_prior[
            "candidate_program_disagreement_count"
        ],
        "no_prior_program_disagreements": expected_no_prior[
            "candidate_program_disagreement_count"
        ],
        "failures": failures,
        "distinctions": distinctions,
        "execution": execution,
        "planning": planning,
        "validation_labels": validation_labels,
        "validation_mismatches": validation_mismatches,
    }


def _sample_tax(campaign: Mapping[str, Any], results: list[dict[str, Any]]):
    prior_labels = sum(row["prior_labels"] for row in results)
    no_prior_labels = sum(row["no_prior_labels"] for row in results)
    prior_local = sum(row["prior_local"] for row in results)
    no_prior_local = sum(row["no_prior_local"] for row in results)
    family_rows = {}
    for family in ("BALANCED_BATCH_REFINEMENT", "COUPLED_EXCHANGE"):
        rows = [row for row in results if row["family"] == family]
        family_rows[family] = {
            "occurrence_count": len(rows),
            "factor_prior_on_acquisition_labels": sum(
                row["prior_labels"] for row in rows
            ),
            "strict_no_prior_acquisition_labels": sum(
                row["no_prior_labels"] for row in rows
            ),
            "factor_prior_on_exact_frontier_closure_count": sum(
                row["prior_exact_frontier"] for row in rows
            ),
            "strict_no_prior_exact_frontier_closure_count": sum(
                row["no_prior_exact_frontier"] for row in rows
            ),
        }
        family_rows[family]["incremental_label_reduction"] = (
            family_rows[family]["strict_no_prior_acquisition_labels"]
            - family_rows[family]["factor_prior_on_acquisition_labels"]
        )
    curve = []
    prior_running = _FACTOR_LIBRARY_LABELS
    no_prior_running = 0
    break_even = None
    for index, row in enumerate(results, start=1):
        prior_running += row["prior_labels"]
        no_prior_running += row["no_prior_labels"]
        reduction = no_prior_running - prior_running
        curve.append(
            {
                "occurrence_count": index,
                "family": row["family"],
                "factor_prior_on_lifetime_labels": prior_running,
                "strict_no_prior_lifetime_labels": no_prior_running,
                "net_label_reduction": reduction,
            }
        )
        if break_even is None and reduction > 0:
            break_even = index
    online = (no_prior_labels + no_prior_local) - (prior_labels + prior_local)
    payload = {
        "schema": "acfqp.mdl_adaptive_sample_tax.v56r1",
        "failed_v56_predecessor_id": EXPECTED_V56_FAILURE_ID,
        "factor_library_labels_prior_on_only": _FACTOR_LIBRARY_LABELS,
        "factor_prior_on_acquisition_labels": prior_labels,
        "strict_no_prior_acquisition_labels": no_prior_labels,
        "incremental_acquisition_label_reduction": no_prior_labels - prior_labels,
        "factor_prior_on_local_recovery_labels": prior_local,
        "strict_no_prior_local_recovery_labels": no_prior_local,
        "online_label_reduction_including_local_recovery": online,
        "lifetime_label_reduction_after_factor_library_tax": (
            online - _FACTOR_LIBRARY_LABELS
        ),
        "diagnostic_break_even_occurrence_count": break_even,
        "family_projections": family_rows,
        "prefix_curve": curve,
        "same_synthesizer_query_order_mdl_confidence_and_frontier_rule": True,
        "only_registered_factor_code_credit_switched": True,
        "fixed_minimum_label_floor_consumed": False,
        "fixed_confirmation_block_consumed": False,
        "official_break_even_claimed": False,
    }
    expected = {
        **payload,
        "sample_tax_id": domains_v56r1.extension_content_id_v56r1(
            _V56R1_DOMAINS["sample_tax"], payload
        ),
    }
    if campaign["sample_tax"] != expected:
        _fail("V56r1 independent sample-tax reconstruction changed")
    return expected


def _verify_ood(campaign: Mapping[str, Any]) -> int:
    catalogue = tuple(
        FlatRawActionV4(index, (bit, 1))
        for index, bit in enumerate((1, 2, 4))
    )
    rows = []
    for mask in (0, 1, 2):
        for key, bit in enumerate((1, 2, 4)):
            successor = mask | bit
            status = "F" if successor & 4 else "S" if successor == 3 else "A"
            rows.append(
                FlatRawTransitionV4(
                    0,
                    len(rows),
                    (mask, _TOKENS["A"], 3, 4, 1),
                    (0, 1, 2),
                    catalogue[key],
                    (successor, _TOKENS[status], 3, 4, 1),
                    () if status != "A" else (0, 1, 2),
                    None if status == "A" else status == "S",
                )
            )
    model = synthesize_joint_factor_residual_world_model_v9(
        {0: tuple(rows)},
        {0: catalogue},
        _LIBRARY,
        layout_domain=_GENERIC_DOMAINS["layout"],
        program_domain=_GENERIC_DOMAINS["program"],
        support_domain=_GENERIC_DOMAINS["support"],
        factor_domain=_GENERIC_DOMAINS["model"],
        result_domain=_GENERIC_DOMAINS["model"],
        minimum_reusable_factor_count=3,
    )
    payload = {
        "schema": "acfqp.mdl_adaptive_ood_rejection.v56",
        "joint_model_id": model["joint_model_id"],
        "factorable_reusable_count": model["factorable_reusable_count"],
        "minimum_reusable_factor_count": 3,
        "complete_ood_program_synthesized_from_raw_observations": True,
        "prior_transfer_attempted": False,
        "ood_outcome_execution_performed": False,
        "outcome": "STRICT_SIGNATURE_THRESHOLD_OOD_NO_TRANSFER",
    }
    expected = {
        **payload,
        "ood_rejection_id": domains_v56.extension_content_id_v56(
            _V56_DOMAINS["ood"], payload
        ),
    }
    if campaign["ood_rejection"] != expected or model["transfer_admitted"] is not False:
        _fail("V56r1 independent OOD reconstruction changed")
    return model["factorable_reusable_count"]


def verify_mdl_adaptive_campaign_bytes_v56r1(raw: bytes) -> dict[str, Any]:
    if (
        type(raw) is not bytes
        or len(raw) != EXPECTED_CAMPAIGN_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CAMPAIGN_SHA256
    ):
        _fail("frozen V56r1 campaign bytes changed")
    campaign = loads_canonical_json(raw)
    if type(campaign) is not dict or campaign.get("campaign_id") != EXPECTED_CAMPAIGN_ID:
        _fail("frozen V56r1 campaign identity changed")
    payload = {key: value for key, value in campaign.items() if key != "campaign_id"}
    if (
        domains_v56r1.extension_content_id_v56r1(
            _V56R1_DOMAINS["campaign"], payload
        )
        != EXPECTED_CAMPAIGN_ID
    ):
        _fail("V56r1 campaign content ID changed")
    if (
        campaign.get("preregistration_id") != EXPECTED_PREREGISTRATION_ID
        or campaign.get("failed_v56_predecessor_id") != EXPECTED_V56_FAILURE_ID
    ):
        _fail("V56r1 predecessor or preregistration identity changed")
    if (
        campaign.get("minimum_candidate_label_floor_consumed") is not False
        or campaign.get("confirmation_block_consumed") is not False
        or campaign.get("full_frontier_target_layout_calibration_consumed")
        is not False
        or campaign.get("exact_frontier_closure_is_a_stop_not_a_calibration_input")
        is not True
    ):
        _fail("V56r1 forbidden floor, block, or calibration input changed")
    if (
        campaign.get("official_execution_allowed") is not False
        or campaign.get("official_scalar_cost") is not None
        or campaign.get("official_N_break_even") is not None
        or campaign.get("WORKLOAD_ECONOMICS_GATE") != "NOT_RUN"
        or campaign.get("COUNTER_COMPLETENESS_GATE") != "NOT_RUN"
    ):
        _fail("V56r1 locked official gates changed")
    prior_rows = campaign.get("acquisitions", {}).get(
        "ANONYMOUS_FACTOR_PRIOR_ON"
    )
    no_prior_rows = campaign.get("acquisitions", {}).get("STRICT_NO_PRIOR")
    if type(prior_rows) is not list or type(no_prior_rows) is not list:
        _fail("V56r1 acquisition inventories changed")
    occurrence_specs = [
        ("BALANCED_BATCH_REFINEMENT", index, seed)
        for index, seed in enumerate(_BALANCED_SEEDS)
    ] + [
        ("COUPLED_EXCHANGE", index, seed)
        for index, seed in enumerate(_COUPLED_SEEDS)
    ]
    if len(prior_rows) != len(occurrence_specs) or len(no_prior_rows) != len(
        occurrence_specs
    ):
        _fail("V56r1 acquisition occurrence count changed")
    episode_by_arm = {
        arm: {(row["family"], row["seed"]): row for row in rows}
        for arm, rows in campaign["episodes"].items()
    }
    validation_by_key = {
        (row["family"], row["seed"]): row
        for row in campaign["isolated_full_frontier_validations"]
    }
    arguments = []
    for position, (family, family_index, seed) in enumerate(occurrence_specs):
        episodes = (
            {
                arm: episode_by_arm[arm][(family, seed)]
                for arm in (
                    "ANONYMOUS_FACTOR_PRIOR_ON",
                    "STRICT_NO_PRIOR",
                    "STRICT_EXACT_CONTEXT",
                )
            }
            if family_index < _PLANNING_COUNT
            else {}
        )
        arguments.append(
            (
                family,
                family_index,
                seed,
                prior_rows[position],
                no_prior_rows[position],
                episodes,
                validation_by_key.get((family, seed)),
            )
        )
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_verify_occurrence, arguments))
    rebuilt_failures = [
        item for row in results for item in row["failures"]
    ]
    rebuilt_distinctions = [
        item for row in results for item in row["distinctions"]
    ]
    if rebuilt_failures != campaign["failed_certificates"]:
        _fail("V56r1 failed-certificate reconstruction changed")
    if rebuilt_distinctions != campaign["local_distinctions"]:
        _fail("V56r1 local-distinction reconstruction changed")
    sample = _sample_tax(campaign, results)
    ood_reusable = _verify_ood(campaign)
    accounting = {
        "offline_factor_library_labels": _FACTOR_LIBRARY_LABELS,
        "factor_prior_on_target_acquisition_labels": sample[
            "factor_prior_on_acquisition_labels"
        ],
        "strict_no_prior_target_acquisition_labels": sample[
            "strict_no_prior_acquisition_labels"
        ],
        "factor_prior_on_local_recovery_labels": sample[
            "factor_prior_on_local_recovery_labels"
        ],
        "strict_no_prior_local_recovery_labels": sample[
            "strict_no_prior_local_recovery_labels"
        ],
        "isolated_validation_labels": sum(
            row["validation_labels"] for row in results
        ),
        "factor_prior_on_execution_steps": sum(
            row["execution"]["ANONYMOUS_FACTOR_PRIOR_ON"] for row in results
        ),
        "strict_no_prior_execution_steps": sum(
            row["execution"]["STRICT_NO_PRIOR"] for row in results
        ),
        "direct_execution_steps": sum(
            row["execution"]["STRICT_EXACT_CONTEXT"] for row in results
        ),
        "factor_prior_on_planning_compute_events": sum(
            row["planning"]["ANONYMOUS_FACTOR_PRIOR_ON"] for row in results
        ),
        "strict_no_prior_planning_compute_events": sum(
            row["planning"]["STRICT_NO_PRIOR"] for row in results
        ),
        "direct_planning_compute_events": sum(
            row["planning"]["STRICT_EXACT_CONTEXT"] for row in results
        ),
        "certificate_compute_events": len(rebuilt_failures),
        "all_axes_separate": True,
    }
    if campaign["accounting"] != accounting:
        _fail("V56r1 separated accounting reconstruction changed")
    return {
        "acquisition_occurrence_count": len(results),
        "family_occurrence_counts": {
            family: sum(row["family"] == family for row in results)
            for family in (
                "BALANCED_BATCH_REFINEMENT",
                "COUPLED_EXCHANGE",
            )
        },
        "factor_prior_on_acquisition_labels": sample[
            "factor_prior_on_acquisition_labels"
        ],
        "strict_no_prior_acquisition_labels": sample[
            "strict_no_prior_acquisition_labels"
        ],
        "incremental_acquisition_label_reduction": sample[
            "incremental_acquisition_label_reduction"
        ],
        "online_label_reduction_including_local_recovery": sample[
            "online_label_reduction_including_local_recovery"
        ],
        "lifetime_label_reduction_after_factor_library_tax": sample[
            "lifetime_label_reduction_after_factor_library_tax"
        ],
        "diagnostic_break_even_occurrence_count": sample[
            "diagnostic_break_even_occurrence_count"
        ],
        "factor_prior_exact_frontier_closure_count": sum(
            row["prior_exact_frontier"] for row in results
        ),
        "strict_no_prior_exact_frontier_closure_count": sum(
            row["no_prior_exact_frontier"] for row in results
        ),
        "planning_episode_count_all_arms": sum(
            len(rows) for rows in campaign["episodes"].values()
        ),
        "failed_certificate_count": len(rebuilt_failures),
        "local_distinction_count": len(rebuilt_distinctions),
        "isolated_validation_label_count": accounting[
            "isolated_validation_labels"
        ],
        "isolated_validation_support_mismatch_count": sum(
            row["validation_mismatches"] for row in results
        ),
        "prior_invalidated_candidate_count": sum(
            row["prior_invalidated"] for row in results
        ),
        "no_prior_invalidated_candidate_count": sum(
            row["no_prior_invalidated"] for row in results
        ),
        "prior_candidate_program_disagreement_count": sum(
            row["prior_program_disagreements"] for row in results
        ),
        "no_prior_candidate_program_disagreement_count": sum(
            row["no_prior_program_disagreements"] for row in results
        ),
        "ood_reusable_count": ood_reusable,
        "ood_transfer_admitted": False,
    }


def freeze_mdl_adaptive_verification_v56r1(campaign_bytes: bytes) -> bytes:
    projection = verify_mdl_adaptive_campaign_bytes_v56r1(campaign_bytes)
    payload = {
        "schema": "acfqp.mdl_adaptive_independent_verification.v56r1",
        "campaign_id": EXPECTED_CAMPAIGN_ID,
        "campaign_byte_count": EXPECTED_CAMPAIGN_BYTE_COUNT,
        "campaign_sha256": EXPECTED_CAMPAIGN_SHA256,
        "failed_v56_predecessor_id": EXPECTED_V56_FAILURE_ID,
        "producer_module_imported": False,
        "campaign_core_module_imported": False,
        "raw_two_domain_acquisition_sequences_reconstructed": True,
        "mdl_candidates_and_both_stop_disjuncts_reconstructed": True,
        "receding_abstract_plans_and_outcome_tapes_replayed": True,
        "certificate_failure_only_local_recovery_reconstructed": True,
        "isolated_full_frontier_validations_reconstructed": True,
        "sample_tax_accounting_and_ood_reconstructed": True,
        "scientific_projection_exact": True,
        "projection": projection,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
    }
    document = {
        **payload,
        "verification_id": domains_v56r1.extension_content_id_v56r1(
            _V56R1_DOMAINS["verification"], payload
        ),
    }
    raw = canonical_json_bytes(document)
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("frozen V56r1 independent verification changed")
    return raw


def verify_mdl_adaptive_verification_bytes_v56r1(raw: bytes) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail("V56r1 verification requires bytes")
    document = loads_canonical_json(raw)
    if type(document) is not dict:
        _fail("V56r1 verification document changed")
    payload = {
        key: value for key, value in document.items() if key != "verification_id"
    }
    if (
        domains_v56r1.extension_content_id_v56r1(
            _V56R1_DOMAINS["verification"], payload
        )
        != document.get("verification_id")
    ):
        _fail("V56r1 verification content ID changed")
    if VERIFICATION_ID != "0" * 64 and (
        document["verification_id"] != VERIFICATION_ID
        or len(raw) != EXPECTED_CANONICAL_BYTE_COUNT
        or hashlib.sha256(raw).hexdigest() != EXPECTED_CANONICAL_SHA256
    ):
        _fail("V56r1 verification frozen bytes changed")
    return document


__all__ = (
    "EXPECTED_CAMPAIGN_ID",
    "VERIFICATION_ID",
    "freeze_mdl_adaptive_verification_v56r1",
    "verify_mdl_adaptive_campaign_bytes_v56r1",
    "verify_mdl_adaptive_verification_bytes_v56r1",
)
