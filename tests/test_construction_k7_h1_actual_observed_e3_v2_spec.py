from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_h1_domain_registry_extension_v10 as domains_v10
from acfqp import construction_k7_h1_domain_registry_extension_v11 as domains_v11
from acfqp import construction_k7_h1_domain_registry_extension_v12 as domains_v12
from acfqp import construction_k7_h1_domain_registry_extension_v13 as domains_v13
from acfqp import construction_k7_h1_domain_registry_extension_v14 as domains_v14
from acfqp import construction_k7_h1_domain_registry_extension_v15 as domains_v15


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = REPOSITORY_ROOT / "specs" / "K7_H1_ACTUAL_OBSERVED_E3_V2.md"
SPEC_SHA256 = "83a99ff977c736d8f06cc6afc2e2e0ad6b0063f7b1aa7fe438777e06992dfc56"


def test_normative_v2_spec_bytes_are_frozen() -> None:
    assert hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest() == SPEC_SHA256


def test_v15_registry_is_exact_additive_and_domain_separated() -> None:
    expected = {
        "construction_k7_h1_actual_observed_e3_v2_profile_v1": (
            "acfqp:construction-k7-h1-actual-observed-e3-v2-profile:v1"
        ),
        "construction_k7_h1_actual_observed_e3_v2_stage_plan_v1": (
            "acfqp:construction-k7-h1-actual-observed-e3-v2-stage-plan:v1"
        ),
        "construction_k7_h1_actual_observed_e3_v2_execution_source_closure_v1": (
            "acfqp:construction-k7-h1-actual-observed-e3-v2-execution-source-closure:v1"
        ),
        "construction_k7_h1_route_wide_runtime_lease_successor_v1": (
            "acfqp:construction-k7-h1-route-wide-runtime-lease-successor:v1"
        ),
        "construction_k7_h1_actual_observed_e3_v2_guardian_session_genesis_v1": (
            "acfqp:construction-k7-h1-actual-observed-e3-v2-guardian-session-genesis:v1"
        ),
        "construction_k7_h1_actual_process_birth_intent_v1": (
            "acfqp:construction-k7-h1-actual-process-birth-intent:v1"
        ),
        "construction_k7_h1_actual_process_birth_permit_v1": (
            "acfqp:construction-k7-h1-actual-process-birth-permit:v1"
        ),
        "construction_k7_h1_shared_pid_cell_binding_v1": (
            "acfqp:construction-k7-h1-shared-pid-cell-binding:v1"
        ),
        "construction_k7_h1_pidfd_escrow_receipt_v2": (
            "acfqp:construction-k7-h1-pidfd-escrow-receipt:v2"
        ),
        "construction_k7_h1_cgroup_membership_observation_v1": (
            "acfqp:construction-k7-h1-cgroup-membership-observation:v1"
        ),
        "construction_k7_h1_actual_process_birth_observation_v1": (
            "acfqp:construction-k7-h1-actual-process-birth-observation:v1"
        ),
        "construction_k7_h1_guardian_birth_ack_v1": (
            "acfqp:construction-k7-h1-guardian-birth-ack:v1"
        ),
        "construction_k7_h1_actual_process_creator_release_v1": (
            "acfqp:construction-k7-h1-actual-process-creator-release:v1"
        ),
        "construction_k7_h1_actual_process_death_observation_v1": (
            "acfqp:construction-k7-h1-actual-process-death-observation:v1"
        ),
        "construction_k7_h1_actual_process_creator_reap_attestation_v1": (
            "acfqp:construction-k7-h1-actual-process-creator-reap-attestation:v1"
        ),
        "construction_k7_h1_actual_observed_e3_v2_native_cleanup_barrier_v1": (
            "acfqp:construction-k7-h1-actual-observed-e3-v2-native-cleanup-barrier:v1"
        ),
        "construction_k7_h1_actual_observed_e3_v2_completion_v1": (
            "acfqp:construction-k7-h1-actual-observed-e3-v2-completion:v1"
        ),
        "construction_k7_h1_e4_v2_live_supervisor_context_v1": (
            "acfqp:construction-k7-h1-e4-v2-live-supervisor-context:v1"
        ),
        "construction_k7_h1_e4_v2_in_supervisor_completion_v1": (
            "acfqp:construction-k7-h1-e4-v2-in-supervisor-completion:v1"
        ),
        "construction_k7_h1_route_wide_actual_peak_observation_v1": (
            "acfqp:construction-k7-h1-route-wide-actual-peak-observation:v1"
        ),
        "construction_k7_h1_route_wide_runtime_lease_closure_v1": (
            "acfqp:construction-k7-h1-route-wide-runtime-lease-closure:v1"
        ),
        "construction_k7_h1_actual_observed_e3_v2_protocol_failure_closure_v1": (
            "acfqp:construction-k7-h1-actual-observed-e3-v2-protocol-failure-closure:v1"
        ),
    }
    assert dict(domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15) == expected
    assert len(domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_V15) == 22
    prior = set().union(
        domains_v10.K7_H1_DOMAIN_TAG_EXTENSION_V10,
        domains_v11.K7_H1_DOMAIN_TAG_EXTENSION_V11,
        domains_v12.K7_H1_DOMAIN_TAG_EXTENSION_V12,
        domains_v13.K7_H1_DOMAIN_TAG_EXTENSION_V13,
        domains_v14.K7_H1_DOMAIN_TAG_EXTENSION_V14,
    )
    assert domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_V15.isdisjoint(prior)

    payload = {"schema": "acfqp.test.k7_h1_actual_observed_e3_v2_spec.v1"}
    identifiers = {
        domains_v15.extension_content_id_v15(domain, payload)
        for domain in domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_V15
    }
    assert len(identifiers) == 22
    for domain in domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_V15:
        assert domains_v15.extension_content_id_v15(
            domain, payload
        ) == domains_v15.extension_content_id_v15(domain, payload)

    with pytest.raises(TypeError):
        domains_v15.K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15["foreign"] = "x"  # type: ignore[index]
    for foreign in (
        "acfqp:foreign:v1",
        domains_v14.CONSTRUCTION_K7_H1_EXTERNAL_PROCESS_INTENT_V1_DOMAIN,
        None,
    ):
        with pytest.raises(ValueError, match="absent"):
            domains_v15.extension_content_id_v15(foreign, payload)  # type: ignore[arg-type]


def test_spec_freezes_five_actual_births_and_e5a_to_e4_v2_chain() -> None:
    text = SPEC_PATH.read_text(encoding="utf-8")
    for exact in (
        "Status: normative construction specification only; implementation slice 1\nabsent.",
        "Proposed contract: `2.0.59-E-C-E5B-B2`.",
        "Profile key: `construction_k7_h1_actual_observed_e3_v2`.",
        "Readiness: `SPECIFICATION_ONLY`.",
        "ACTIVE -> RUNNING -> PEAK_READ -> CLOSED",
        "External Process Journal V1 is a nonauthoritative V14 structural reference.",
        "V15 domain registration is not slice 1.",
    ):
        assert exact in text

    rows = (
        "| 1 | `SUPERVISOR` | external guardian | `CONTROL` | runtime lease `RUNNING` |",
        "| 2 | `PIDFD_PROBE` | live supervisor | `CONTROL` | supervisor READY and E4 V2 context prepared |",
        "| 3 | `BROKER` | live supervisor | `CONTROL` | probe death and creator reap complete |",
        "| 4 | `WORKER` | live broker | `WORKER` | broker READY and E3 V2 payloads prepared |",
        "| 5 | `BUSINESS` | live broker | `BUSINESS` | worker death and creator reap complete |",
    )
    positions = [text.index(row) for row in rows]
    assert positions == sorted(positions)

    protocol_headings = (
        "### 1. Frozen pre-birth snapshot",
        "### 2. One-shot permit and kernel transition",
        "### 3. Guardian-read shared PID cell",
        "### 4. PIDFD escrow and live cgroup membership",
        "### 5. Birth observation, ACK and release",
    )
    protocol_positions = [text.index(heading) for heading in protocol_headings]
    assert protocol_positions == sorted(protocol_positions)
    assert "A sender-reported PID is never a\nsubstitute for that read." in text
    assert "trusted creator-reap attestation" in text
    assert "E4 V2 launches no process." in text
    assert "V15 reserves 22 disjoint construction domains" in text


def test_spec_freezes_slice_order_and_every_current_authority_lock() -> None:
    text = SPEC_PATH.read_text(encoding="utf-8")
    slices = (
        "`RUNTIME_LEASE_AND_SUPERVISOR_BIRTH_SLICE`",
        "`FIVE_BIRTH_TOPOLOGY_SLICE`",
        "`E3_V2_SEMANTIC_SLICE`",
        "`E4_V2_AND_ROUTE_CLOSURE_SLICE`",
        "`FORMAL_SHARED_RESOURCE_PROJECTION_SLICE`",
    )
    positions = [text.index(name) for name in slices]
    assert positions == sorted(positions)

    for lock in (
        "implementation_slice_1_present = false",
        "implementation_slice_2_present = false",
        "implementation_slice_3_present = false",
        "implementation_slice_4_present = false",
        "implementation_slice_5_present = false",
        "actual_observed_e3_v2_execution_present = false",
        "e5a_runtime_lease_successor_present = false",
        "guardian_gated_five_actual_births_present = false",
        "guardian_read_shared_pid_cell_authority_present = false",
        "guardian_verified_cgroup_membership_authority_present = false",
        "creator_reap_authority_present = false",
        "actual_observed_e3_v2_completion_present = false",
        "live_supervisor_e4_v2_completion_present = false",
        "route_wide_actual_peak_authority_present = false",
        "production_shared_resource_receipts_present = false",
        "fq11_counter_completeness_present = false",
        "formal_counter_records_issued = false",
        "formal_work_vector_issued = false",
        "formal_comparison_vector_issued = false",
        "formal_actual_projection_proof_issued = false",
        "current_access_authority_present = false",
        "formal_v7_authority_present = false",
        "terminal_or_campaign_authority_present = false",
        "complete_bundle_authority_present = false",
        "official_execution_allowed = false",
        "official_scalar_cost = null",
        "official_N_break_even = null",
        "COUNTER_COMPLETENESS_GATE = NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE = NOT_RUN",
    ):
        assert lock in text

    assert not (
        REPOSITORY_ROOT
        / "src"
        / "acfqp"
        / "construction_k7_h1_actual_observed_e3_v2.py"
    ).exists()


def test_v15_exports_only_registered_domain_api() -> None:
    expected_domains = {
        name
        for name in vars(domains_v15)
        if name.startswith("CONSTRUCTION_K7_H1_") and name.endswith("_DOMAIN")
    }
    assert set(domains_v15.__all__) == expected_domains | {
        "K7_H1_DOMAIN_TAG_EXTENSION_REGISTRY_V15",
        "K7_H1_DOMAIN_TAG_EXTENSION_V15",
        "extension_content_id_v15",
    }
