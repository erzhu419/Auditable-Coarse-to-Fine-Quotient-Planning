from __future__ import annotations

import hashlib

import pytest

from acfqp import construction_k7_domain_registry_extension_v180r12r4 as domains
from acfqp import construction_k7_domain_registry_extension_v180r12r4e as evidence_domains
from acfqp import construction_k7_domain_registry_extension_v180r12r3 as predecessor_domains
from acfqp import (
    construction_k7_domain_registry_extension_v180r12r3r1
    as immediate_predecessor_domains,
)
from acfqp.phase3e_ids import canonical_json_bytes


EXPECTED = {
    "campaign_measurement_protocol": (
        "acfqp:construction-k7-campaign-measurement-protocol:v180r12r4"
    ),
    "execution_authorization": (
        "acfqp:construction-k7-campaign-measurement-execution-authorization:v180r12r4"
    ),
    "campaign_measurement_execution_slot": (
        "acfqp:construction-k7-campaign-measurement-execution-slot:v180r12r4"
    ),
    "campaign_measurement_attempt": (
        "acfqp:construction-k7-campaign-measurement-attempt:v180r12r4"
    ),
    "authorization_evidence": (
        "acfqp:construction-k7-campaign-measurement-authorization-evidence:v180r12r4"
    ),
    "prelaunch_external_root": (
        "acfqp:construction-k7-campaign-measurement-prelaunch-external-root:v180r12r4"
    ),
    "prelaunch_manifest": (
        "acfqp:construction-k7-campaign-measurement-prelaunch-manifest:v180r12r4"
    ),
    "prelaunch_materialization_terminal": (
        "acfqp:construction-k7-campaign-measurement-prelaunch-materialization-terminal:v180r12r4"
    ),
    "prelaunch_materialization_failure": (
        "acfqp:construction-k7-campaign-measurement-prelaunch-materialization-failure:v180r12r4"
    ),
    "launch_attempt": (
        "acfqp:construction-k7-campaign-measurement-launch-attempt:v180r12r4"
    ),
    "launch_receipt": (
        "acfqp:construction-k7-campaign-measurement-launch-receipt:v180r12r4"
    ),
    "launch_failure": (
        "acfqp:construction-k7-campaign-measurement-launch-failure:v180r12r4"
    ),
    "terminal_bundle": (
        "acfqp:construction-k7-campaign-measurement-terminal-bundle:v180r12r4"
    ),
    "campaign_evidence_inventory_bundle": (
        "acfqp:construction-k7-campaign-evidence-inventory-bundle:v180r12r4"
    ),
    "campaign_os_receipt_bundle": (
        "acfqp:construction-k7-campaign-os-receipt-bundle:v180r12r4"
    ),
    "verification": (
        "acfqp:construction-k7-campaign-measurement-verification:v180r12r4"
    ),
    "failure": "acfqp:construction-k7-campaign-measurement-failure:v180r12r4",
    "production_evidence": (
        "acfqp:construction-k7-campaign-measurement-production-evidence:v180r12r4"
    ),
}


def test_registry_is_exact_immutable_and_exports_every_domain() -> None:
    assert dict(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4) == EXPECTED
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R12R4 == frozenset(EXPECTED.values())
    for key, domain in EXPECTED.items():
        assert getattr(domains, f"CONSTRUCTION_K7_{key.upper()}_V180R12R4_DOMAIN") == domain
    with pytest.raises(TypeError):
        domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4["extra"] = "x"


def test_successor_domains_are_fresh_and_disjoint_from_failed_predecessor() -> None:
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R12R4.isdisjoint(
        predecessor_domains.K7_DOMAIN_TAG_EXTENSION_V180R12R3
    )
    assert domains.K7_DOMAIN_TAG_EXTENSION_V180R12R4.isdisjoint(
        immediate_predecessor_domains.K7_DOMAIN_TAG_EXTENSION_V180R12R3R1
    )
    assert set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4) == set(
        predecessor_domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R3
    )
    assert set(domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R4) == set(
        immediate_predecessor_domains.K7_DOMAIN_TAG_EXTENSION_REGISTRY_V180R12R3R1
    )


def test_content_id_uses_exact_domain_null_canonical_payload_formula() -> None:
    payload = {"z": 2, "a": [True, None, "x"]}
    domain = EXPECTED["campaign_measurement_protocol"]
    expected = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    assert domains.extension_content_id_v180r12r4(domain, payload) == expected
    assert domains.extension_content_id_v180r12r4(
        EXPECTED["failure"], payload
    ) != expected


def test_campaign_measurement_attempt_identity_is_exact_sensitive_and_type_separated() -> None:
    fields = {
        "protocol_id": "1" * 64,
        "authorization_id": "2" * 64,
        "authorization_evidence_id": "3" * 64,
        "campaign_measurement_execution_slot_id": "4" * 64,
        "logical_occurrence_id": "5" * 64,
        "execution_nonce": "6" * 64,
    }
    payload = {
        "schema": domains.CAMPAIGN_MEASUREMENT_ATTEMPT_SCHEMA,
        **fields,
    }
    derived = domains.derive_campaign_measurement_attempt_id_v180r12r4(**fields)
    predecessor_derived = (
        predecessor_domains.derive_campaign_measurement_attempt_id_v180r12r3(
            **fields
        )
    )
    immediate_predecessor_derived = (
        immediate_predecessor_domains.derive_campaign_measurement_attempt_id_v180r12r3r1(
            **fields
        )
    )
    assert derived == domains.extension_content_id_v180r12r4(
        domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN,
        payload,
    )
    for index, name in enumerate(fields, start=7):
        mutated = dict(fields)
        mutated[name] = f"{index:x}" * 64
        assert (
            domains.derive_campaign_measurement_attempt_id_v180r12r4(**mutated)
            != derived
        )
    assert derived != domains.extension_content_id_v180r12r4(
        domains.CONSTRUCTION_K7_LAUNCH_ATTEMPT_V180R12R4_DOMAIN, payload
    )
    assert derived != predecessor_derived
    assert derived != immediate_predecessor_derived
    assert derived != (
        "457a889a690549ad5efaeb6d3f4799ec2a859068d93eac71730088f90889f967"
    )
    assert derived != (
        "cbffcb66d23630ef46fa014f9467d3ac3054b39dde32ec0b9de22bba41078040"
    )
    assert (
        domains.CONSTRUCTION_K7_CAMPAIGN_MEASUREMENT_ATTEMPT_V180R12R4_DOMAIN
        != evidence_domains.CONSTRUCTION_K7_CAMPAIGN_ATTEMPT_RECORD_V180R12R4E_DOMAIN
    )


@pytest.mark.parametrize("value", [None, "", "0" * 63, "G" * 64, 1])
def test_campaign_measurement_attempt_rejects_noncanonical_identity_input(
    value,
) -> None:
    fields = {
        "protocol_id": "1" * 64,
        "authorization_id": "2" * 64,
        "authorization_evidence_id": "3" * 64,
        "campaign_measurement_execution_slot_id": "4" * 64,
        "logical_occurrence_id": "5" * 64,
        "execution_nonce": "6" * 64,
    }
    for name in fields:
        mutated = dict(fields)
        mutated[name] = value
        with pytest.raises(ValueError, match="lowercase 64-hex"):
            domains.derive_campaign_measurement_attempt_id_v180r12r4(**mutated)


@pytest.mark.parametrize("domain", ["", "unknown", None, 1])
def test_unregistered_domain_is_rejected(domain) -> None:
    with pytest.raises(ValueError, match="absent from V180r12r4"):
        domains.extension_content_id_v180r12r4(domain, {})
