"""Normalize domain adapters to the FlatRawAction contract used by V44.

Many real domains expose domain-specific action objects from ``action()`` and
``actions()`` while separately carrying an anonymous FlatRawAction catalogue.
This additive wrapper keeps kernel calls on the domain objects but exposes only
the exact catalogue rows to the generic certificate engine and its receipts.
"""

from __future__ import annotations

from typing import Any, NoReturn

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4


class GenericFlatActionAdapterV45Error(ValueError):
    pass


def _fail(message: str) -> NoReturn:
    raise GenericFlatActionAdapterV45Error(message)


class _FlatKernelV45:
    __slots__ = ("_source", "_adapter")

    def __init__(self, source: Any, adapter: "FlatActionAdapterV45") -> None:
        self._source = source
        self._adapter = adapter

    def step(self, state: Any, action: FlatRawActionV4) -> Any:
        if type(action) is not FlatRawActionV4:
            _fail("V45 kernel accepts only FlatRawActionV4")
        return self._source.step(state, self._adapter._source.action(action.key))


class FlatActionAdapterV45:
    __slots__ = ("_source", "_by_key", "catalogue", "family", "kernel", "seed")

    def __init__(self, source: Any) -> None:
        catalogue = getattr(source, "catalogue", None)
        if (
            type(catalogue) is not tuple
            or not catalogue
            or any(type(row) is not FlatRawActionV4 for row in catalogue)
            or len({row.key for row in catalogue}) != len(catalogue)
        ):
            _fail("V45 source catalogue changed")
        self._source = source
        self.catalogue = catalogue
        self._by_key = {row.key: row for row in catalogue}
        self.family = source.family
        self.seed = source.seed
        self.kernel = _FlatKernelV45(source.kernel, self)

    def initial(self) -> Any:
        return self._source.initial()

    def encode(self, state: Any) -> tuple[int, ...]:
        return self._source.encode(state)

    def action(self, key: int) -> FlatRawActionV4:
        action = self._by_key.get(key)
        if action is None:
            _fail("V45 action key is absent from the flat catalogue")
        return action

    def action_key(self, action: FlatRawActionV4) -> int:
        if type(action) is not FlatRawActionV4 or self._by_key.get(action.key) != action:
            _fail("V45 action is absent from the flat catalogue")
        return action.key

    def actions(self, state: Any) -> tuple[FlatRawActionV4, ...]:
        keys = tuple(
            self._source.action_key(action) for action in self._source.actions(state)
        )
        if len(keys) != len(set(keys)) or any(key not in self._by_key for key in keys):
            _fail("V45 source legal-action projection changed")
        return tuple(self._by_key[key] for key in keys)

    def active(self, state: Any) -> bool:
        return self._source.active(state)

    def success(self, state: Any) -> bool:
        return self._source.success(state)

    def select_outcome(
        self, state: Any, key: int, episode_index: int, decision: int
    ) -> Any:
        if key not in self._by_key:
            _fail("V45 outcome key is absent from the flat catalogue")
        return self._source.select_outcome(state, key, episode_index, decision)


def normalize_flat_action_adapter_v45(source: Any) -> FlatActionAdapterV45:
    return FlatActionAdapterV45(source)


__all__ = (
    "FlatActionAdapterV45",
    "GenericFlatActionAdapterV45Error",
    "normalize_flat_action_adapter_v45",
)
