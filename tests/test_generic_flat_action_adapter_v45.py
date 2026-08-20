from __future__ import annotations

from dataclasses import dataclass
import hashlib

from acfqp.generic_atomic_expression_world_model_v4 import FlatRawActionV4
from acfqp.generic_flat_action_adapter_v45 import normalize_flat_action_adapter_v45
from acfqp.generic_portable_certificate_query_priority_v44 import (
    compile_portable_certificate_query_priority_v44,
    run_portable_priority_certificate_episode_v44,
)
from acfqp.generic_reusable_version_space_certificate_planner_v43 import (
    run_reusable_version_space_certificate_episode_v43,
)
from acfqp.phase3e_ids import canonical_json_bytes
from test_generic_reusable_version_space_certificate_planner_v43 import (
    _Adapter,
    _Outcome,
    _source_fixture,
)


@dataclass(frozen=True)
class _DomainAction:
    delta: int


class _DomainKernel:
    def step(self, state, action):
        next_position = state[0] + action.delta
        terminal = next_position >= state[1]
        return tuple(
            _Outcome((next_position, state[1], residual, 9 if terminal else 4))
            for residual in (state[2], state[2] + action.delta + 1)
        )


class _DomainAdapter:
    family = "ANONYMOUS_DOMAIN_ACTION_PROGRESS"
    seed = 450_001

    def __init__(self, catalogue):
        self.catalogue = catalogue
        self.kernel = _DomainKernel()
        self._domain = {
            row.key: _DomainAction(row.fields[0]) for row in catalogue
        }

    def initial(self):
        return (0, 4, 10, 4)

    def encode(self, state):
        return state

    def action(self, key):
        return self._domain[key]

    def action_key(self, action):
        return next(key for key, row in self._domain.items() if row == action)

    def actions(self, state):
        return tuple(self._domain.values()) if self.active(state) else ()

    def active(self, state):
        return state[3] == 4

    def success(self, state):
        return state[3] == 9

    def select_outcome(self, state, key, episode_index, decision):
        outcomes = self.kernel.step(state, self.action(key))
        offset = (episode_index + decision) % len(outcomes)
        tape = hashlib.sha256(
            canonical_json_bytes(
                {
                    "state": list(state),
                    "key": key,
                    "episode_index": episode_index,
                    "decision": decision,
                    "offset": offset,
                }
            )
        ).hexdigest()
        return outcomes[offset], tape


def test_v45_keeps_domain_actions_in_kernel_and_flat_actions_in_receipts():
    candidate, rows, catalogue, model = _source_fixture()
    source_episode = run_reusable_version_space_certificate_episode_v43(
        _Adapter(catalogue),
        candidate,
        rows,
        reusable_model=model,
        model_source_episode_index=0,
        episode_index=1,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    priority = compile_portable_certificate_query_priority_v44(
        source_episode, candidate
    )
    adapter = normalize_flat_action_adapter_v45(_DomainAdapter(catalogue))
    result = run_portable_priority_certificate_episode_v44(
        adapter,
        candidate,
        (),
        reusable_model=model,
        portable_query_priority=priority,
        model_source_episode_index=0,
        episode_index=2,
        maximum_abstract_depth=2,
        maximum_execution_steps=8,
    )
    assert result["success"] is True
    assert result["portable_priority_ordering_accepted_count"] > 0
    assert all(
        set(row["selected_action"]) == {"action_key", "anonymous_fields"}
        for row in result["raw_local_transition_rows"]
    )
