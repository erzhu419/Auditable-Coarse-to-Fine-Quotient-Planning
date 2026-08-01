from __future__ import annotations

from contextlib import contextmanager
import hashlib
from types import SimpleNamespace

import pytest

from acfqp.phase3e_ids import (
    PHASE3E_DOMAIN_TAGS,
    V075_K7_ROOT_CAP_COLD_CACHE_EPOCH_V1_DOMAIN,
    V075_K7_ROOT_CAP_COLD_CACHE_PROFILE_V1_DOMAIN,
    V075_K7_ROOT_CAP_OWNED_PARTIAL_RESULT_V1_DOMAIN,
)
from acfqp import v075_k7_root_cap_owned_partial_runner_v1 as owned


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-owned-partial-schema-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def test_owned_wrapper_domains_are_registered() -> None:
    assert {
        V075_K7_ROOT_CAP_COLD_CACHE_PROFILE_V1_DOMAIN,
        V075_K7_ROOT_CAP_COLD_CACHE_EPOCH_V1_DOMAIN,
        V075_K7_ROOT_CAP_OWNED_PARTIAL_RESULT_V1_DOMAIN,
    } <= PHASE3E_DOMAIN_TAGS


def test_cold_cache_epoch_commits_requirements_not_future_completion() -> None:
    profile = owned.official_v075_k7_root_cap_cold_cache_profile_v1()
    epoch = owned.V075K7RootCapColdCacheEpochV1(
        owned._CACHE_EPOCH_ISSUER,  # noqa: SLF001
        profile.profile_id,
        _id("occurrence"),
        _id("schedule"),
        _id("session-external-id"),
    )
    profile_document = profile.to_document()
    epoch_document = epoch.to_document()
    assert profile_document["clear_after_owned_scope_required"] is True
    assert epoch_document["clear_after_owned_scope_required"] is True
    assert "clear_after_owned_scope_committed" not in epoch_document
    assert "cold_cache_cleared_after_owned_scope" not in epoch_document


def test_owned_wrapper_orders_isolated_epoch_terminal_cleanup_and_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    execution_profile = SimpleNamespace(profile_id=_id("execution-profile"))
    schedule = SimpleNamespace(
        occurrence=SimpleNamespace(occurrence_id=_id("occurrence")),
        schedule_id=_id("schedule"),
    )
    registry = SimpleNamespace(registry_id=_id("registry"))
    stage = SimpleNamespace(stage_profile_id=_id("stage"))
    boundary = SimpleNamespace(manifest_id=_id("boundary"))
    transcript = SimpleNamespace()
    result = SimpleNamespace()
    wrapped = SimpleNamespace()

    monkeypatch.setattr(
        owned.execution_identity,
        "official_v075_k7_root_cap_execution_identity_profile_v1",
        lambda: execution_profile,
    )

    def validate_identity(**_kwargs) -> None:
        events.append("identity-validate")

    monkeypatch.setattr(
        owned.execution_identity,
        "validate_v075_k7_root_cap_execution_identity_v1",
        validate_identity,
    )
    monkeypatch.setattr(
        owned.registry_v6,
        "official_counter_registry_v6",
        lambda: registry,
    )
    monkeypatch.setattr(
        owned.registry_v6,
        "official_stage_profile_v6",
        lambda _registry: stage,
    )
    monkeypatch.setattr(
        owned,
        "official_k7_root_cap_operation_boundary_manifest_v3",
        lambda: boundary,
    )

    @contextmanager
    def isolate():
        events.append("isolation-enter")
        try:
            yield
        finally:
            events.append("isolation-exit")

    def clear() -> None:
        events.append("clear")

    monkeypatch.setattr(
        owned.bernoulli,
        "isolate_exact_bernoulli_math_cache_v1",
        isolate,
    )
    monkeypatch.setattr(
        owned.bernoulli,
        "clear_exact_bernoulli_math_cache_v1",
        clear,
    )

    def freeze_epoch(**_kwargs):
        events.append("epoch-freeze")
        return SimpleNamespace(epoch_id=_id("epoch"))

    monkeypatch.setattr(owned, "_freeze_cold_cache_epoch", freeze_epoch)

    @contextmanager
    def accounting_scope(**_kwargs):
        events.append("accounting-enter")
        try:
            yield SimpleNamespace(is_terminal=False)
        finally:
            events.append("accounting-exit")

    @contextmanager
    def operational_scope():
        events.append("operational-enter")
        try:
            yield
        finally:
            events.append("operational-exit")

    monkeypatch.setattr(
        owned.accounting_runtime,
        "activate_owned_construction_accounting_v1",
        accounting_scope,
    )
    monkeypatch.setattr(
        owned.operational_context,
        "_activate_owned_no_full_replay_v3",
        operational_scope,
    )

    def driver(**kwargs):
        events.append("driver")
        kwargs["evidence_sink"]({"detached_test_root": object()})
        return result

    monkeypatch.setattr(
        owned.runner,
        "_run_v075_k7_root_cap_owned_partial_driver_v1",
        driver,
    )

    def complete():
        events.append("complete")
        return transcript

    monkeypatch.setattr(
        owned.accounting_runtime,
        "complete_owned_occurrence_v1",
        complete,
    )

    def freeze_wrapper(*_args):
        events.append("wrapper-freeze")
        return wrapped

    monkeypatch.setattr(
        owned,
        "V075K7RootCapOwnedPartialResultV1",
        freeze_wrapper,
    )

    def snapshot(_roots):
        events.append("snapshot")
        return b"stable"

    monkeypatch.setattr(
        owned.runner,
        "_snapshot_construction_evidence_roots",
        snapshot,
    )

    def user_sink(_roots) -> None:
        events.append("user-sink")

    actual = owned.run_v075_k7_root_cap_owned_partial_v1(
        repository_root="/unused",
        namespace=object(),
        schedule=schedule,
        schedule_verification=object(),
        authority=object(),
        private_salt=b"unused",
        private_environment=(),
        observer_signer=object(),
        session_external_id="session",
        evidence_sink=user_sink,
    )
    assert actual is wrapped
    assert events == [
        "identity-validate",
        "isolation-enter",
        "clear",
        "epoch-freeze",
        "accounting-enter",
        "operational-enter",
        "driver",
        "complete",
        "operational-exit",
        "accounting-exit",
        "clear",
        "isolation-exit",
        "wrapper-freeze",
        "snapshot",
        "user-sink",
        "snapshot",
    ]
