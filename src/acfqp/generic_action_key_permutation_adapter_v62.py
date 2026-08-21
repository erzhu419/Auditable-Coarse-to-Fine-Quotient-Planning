"""Outcome-blind action-identifier permutation for matched planning ablations.

The wrapper changes only the public integer used to name an action.  Anonymous
action metadata, ground actions, transition support, state encoding and outcome
selection are unchanged.  The permutation is fixed by a versioned hash ranking
of ``(seed, old_key)`` and therefore does not inspect transition outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.phase3e_ids import canonical_json_bytes


_PERMUTATION_DOMAIN = b"acfqp:generic-action-key-permutation:v62\x00"


class GenericActionKeyPermutationAdapterV62Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericActionKeyPermutationAdapterV62Error(message)


def _permutation(seed: int, width: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if type(seed) is not int or seed < 0 or type(width) is not int or width < 2:
        _fail("V62 action permutation inventory changed")
    seed_bytes = seed.to_bytes(16, "big", signed=False)
    new_to_old = tuple(
        sorted(
            range(width),
            key=lambda old: hashlib.sha256(
                _PERMUTATION_DOMAIN
                + seed_bytes
                + old.to_bytes(8, "big", signed=False)
            ).digest(),
        )
    )
    old_to_new = [-1] * width
    for new, old in enumerate(new_to_old):
        old_to_new[old] = new
    if sorted(old_to_new) != list(range(width)):
        _fail("V62 action permutation is not bijective")
    return tuple(old_to_new), new_to_old


@dataclass(frozen=True, slots=True)
class ActionKeyPermutedAdapterV62:
    original: Any
    family: str
    seed: int
    kernel: Any
    catalogue: tuple[FlatRawActionV4, ...]
    old_to_new: tuple[int, ...]
    new_to_old: tuple[int, ...]

    def initial(self) -> Any:
        return self.original.initial()

    def actions(self, state: Any) -> tuple[Any, ...]:
        return tuple(sorted(self.original.actions(state), key=self.action_key))

    def action_key(self, action: Any) -> int:
        old = self.original.action_key(action)
        if type(old) is not int or not 0 <= old < len(self.old_to_new):
            _fail("V62 original action key escaped its catalogue")
        return self.old_to_new[old]

    def action(self, key: int) -> Any:
        if type(key) is not int or not 0 <= key < len(self.new_to_old):
            _fail("V62 permuted action key escaped its catalogue")
        return self.original.action(self.new_to_old[key])

    def active(self, state: Any) -> bool:
        return self.original.active(state)

    def success(self, state: Any) -> bool:
        return self.original.success(state)

    def encode(self, state: Any) -> tuple[int, ...]:
        return self.original.encode(state)

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision_index: int
    ) -> tuple[Any, str]:
        if type(key) is not int or not 0 <= key < len(self.new_to_old):
            _fail("V62 outcome action key escaped its catalogue")
        return self.original.select_outcome(
            state, self.new_to_old[key], episode_index, decision_index
        )


def permute_adapter_action_keys_v62(
    adapter: Any,
) -> tuple[ActionKeyPermutedAdapterV62, dict[str, Any]]:
    source = adapter.catalogue
    if (
        type(source) is not tuple
        or len(source) < 2
        or any(type(row) is not FlatRawActionV4 for row in source)
        or tuple(row.key for row in source) != tuple(range(len(source)))
        or type(adapter.seed) is not int
        or adapter.seed < 0
    ):
        _fail("V62 source action catalogue changed")
    old_to_new, new_to_old = _permutation(adapter.seed, len(source))
    catalogue = tuple(
        FlatRawActionV4(new, source[old].fields)
        for new, old in enumerate(new_to_old)
    )
    source_documents = [row.to_document() for row in source]
    target_documents = [row.to_document() for row in catalogue]
    payload = {
        "schema": "acfqp.generic_action_key_permutation.v62",
        "family": adapter.family,
        "seed": adapter.seed,
        "algorithm": "SHA256_RANK_SEED_AND_OLD_KEY",
        "algorithm_domain_hex": _PERMUTATION_DOMAIN.hex(),
        "action_count": len(source),
        "old_to_new": list(old_to_new),
        "new_to_old": list(new_to_old),
        "source_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(source_documents)
        ).hexdigest(),
        "permuted_catalogue_sha256": hashlib.sha256(
            canonical_json_bytes(target_documents)
        ).hexdigest(),
        "anonymous_descriptor_fields_preserved_exactly": all(
            catalogue[old_to_new[old]].fields == source[old].fields
            for old in range(len(source))
        ),
        "ground_action_identity_preserved_through_inverse_map": True,
        "state_encoding_and_kernel_unchanged": True,
        "transition_outcomes_accessed_to_select_permutation": False,
        "semantic_action_names_accessed": False,
        "safety_authority_present": False,
    }
    document = {
        **payload,
        "permutation_id": hashlib.sha256(
            _PERMUTATION_DOMAIN + canonical_json_bytes(payload)
        ).hexdigest(),
    }
    wrapped = ActionKeyPermutedAdapterV62(
        adapter,
        adapter.family,
        adapter.seed,
        adapter.kernel,
        catalogue,
        old_to_new,
        new_to_old,
    )
    if any(
        wrapped.action_key(wrapped.action(new)) != new
        for new in range(len(catalogue))
    ):
        _fail("V62 ground action inverse join changed")
    return wrapped, document


__all__ = (
    "ActionKeyPermutedAdapterV62",
    "permute_adapter_action_keys_v62",
)
