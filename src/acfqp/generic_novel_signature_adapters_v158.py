"""Metadata-only signature perturbations with unchanged stochastic kernels."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_quaternary_relation_workflow_adapter_v153 import QuaternaryRelationWorkflowFlatAdapterV153, build_quaternary_relation_workflow_adapter_v153
from acfqp.generic_relation_fanout_routing_adapter_v154 import RelationFanoutRoutingFlatAdapterV154, build_relation_fanout_routing_adapter_v154


POSITIVE_FAMILY = "STOCHASTIC_QUATERNARY_RELATION_WORKFLOW_NOVEL_METADATA_SIGNATURE"
FALLBACK_FAMILY = "STOCHASTIC_RELATION_FANOUT_ROUTING_NOVEL_METADATA_SIGNATURE"


def _recode_repeated_noninitial_values(adapter: Any, *, source_support: int, maximum_fields: int):
    initial_keys = {adapter.action_key(action) for action in adapter.actions(adapter.initial())}
    catalogue = list(adapter.catalogue)
    changed = 0
    for field in range(len(catalogue[0].fields)):
        counts = Counter(action.fields[field] for action in catalogue)
        if len(counts) != source_support:
            continue
        eligible = [action.key for action in catalogue if action.key not in initial_keys and counts[action.fields[field]] >= 2]
        if not eligible:
            continue
        key = min(eligible)
        action = catalogue[key]
        fields = list(action.fields)
        fields[field] = adapter.seed * 1_000_000 + 15_800 + field
        catalogue[key] = FlatRawActionV4(action.key, tuple(fields))
        changed += 1
        if changed == maximum_fields:
            break
    if changed != maximum_fields:
        raise ValueError("V158 could not derive the registered metadata perturbation")
    return tuple(catalogue)


def build_novel_positive_signature_adapter_v158(seed: int, config: Mapping[str, Any]):
    base = build_quaternary_relation_workflow_adapter_v153(seed, config)
    catalogue = _recode_repeated_noninitial_values(base, source_support=3, maximum_fields=1)
    return QuaternaryRelationWorkflowFlatAdapterV153(POSITIVE_FAMILY, seed, base.kernel, catalogue, base.encode)


def build_novel_fallback_signature_adapter_v158(seed: int, config: Mapping[str, Any]):
    base = build_relation_fanout_routing_adapter_v154(seed, config)
    catalogue = _recode_repeated_noninitial_values(base, source_support=2, maximum_fields=1)
    return RelationFanoutRoutingFlatAdapterV154(FALLBACK_FAMILY, seed, base.kernel, catalogue, base.encode)


__all__ = (
    "FALLBACK_FAMILY",
    "POSITIVE_FAMILY",
    "build_novel_fallback_signature_adapter_v158",
    "build_novel_positive_signature_adapter_v158",
)
