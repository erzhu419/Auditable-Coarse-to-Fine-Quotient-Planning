"""Outcome-free receipt for the complete anonymous planner action catalogue."""

from __future__ import annotations

from typing import Any, Iterable, Mapping, NoReturn

from acfqp import construction_k7_domain_registry_extension_v107 as domains


class GenericCompleteAnonymousActionCatalogueReceiptV107Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericCompleteAnonymousActionCatalogueReceiptV107Error(message)


def build_complete_anonymous_action_catalogue_receipt_v107(
    catalogue: Iterable[Any],
    *,
    family: str,
    seed: int,
) -> dict[str, Any]:
    actions = tuple(catalogue)
    rows = [
        {
            "action_key": action.key,
            "anonymous_fields": list(action.fields),
        }
        for action in actions
    ]
    widths = {len(row["anonymous_fields"]) for row in rows}
    keys = [row["action_key"] for row in rows]
    if (
        type(family) is not str
        or not family
        or type(seed) is not int
        or not rows
        or any(type(key) is not int for key in keys)
        or len(set(keys)) != len(keys)
        or len(widths) != 1
        or next(iter(widths)) <= 0
        or any(
            any(type(value) is not int for value in row["anonymous_fields"])
            for row in rows
        )
    ):
        _fail("V107 anonymous action catalogue inventory changed")
    payload = {
        "schema": "acfqp.complete_anonymous_action_catalogue_receipt.v107",
        "family": family,
        "seed": seed,
        "action_descriptor_rows": rows,
        "action_key_count": len(rows),
        "action_field_width": next(iter(widths)),
        "catalogue_order_is_exact_planner_iteration_order": True,
        "catalogue_complete_at_target_adapter_boundary": True,
        "catalogue_enumerated_before_target_episode_outcomes": True,
        "catalogue_contains_transition_outcomes": False,
        "semantic_action_names_present": False,
        "catalogue_is_planning_input_not_safety_authority": True,
        "complete_ground_world_model_claimed": False,
    }
    return {
        **payload,
        "catalogue_receipt_id": domains.extension_content_id_v107(
            domains.CONSTRUCTION_K7_COMPLETE_ANONYMOUS_ACTION_CATALOGUE_RECEIPT_V107_DOMAIN,
            payload,
        ),
    }


def verify_complete_anonymous_action_catalogue_receipt_v107(
    document: Any,
) -> dict[str, Any]:
    if type(document) is not dict:
        _fail("V107 catalogue receipt type changed")
    rows = document.get("action_descriptor_rows")
    if type(rows) is not list:
        _fail("V107 catalogue descriptor rows changed")

    class _Action:
        def __init__(self, row: Mapping[str, Any]):
            if type(row) is not dict or set(row) != {
                "action_key",
                "anonymous_fields",
            }:
                _fail("V107 catalogue row schema changed")
            self.key = row["action_key"]
            fields = row["anonymous_fields"]
            if type(fields) is not list:
                _fail("V107 catalogue row fields changed")
            self.fields = tuple(fields)

    expected = build_complete_anonymous_action_catalogue_receipt_v107(
        tuple(_Action(row) for row in rows),
        family=document.get("family"),
        seed=document.get("seed"),
    )
    if document != expected:
        _fail("V107 catalogue receipt semantics changed")
    return expected


__all__ = (
    "build_complete_anonymous_action_catalogue_receipt_v107",
    "verify_complete_anonymous_action_catalogue_receipt_v107",
)
