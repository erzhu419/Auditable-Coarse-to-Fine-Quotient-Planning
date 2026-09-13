"""Direct H1 action-consequence contracts with a shared analytic baseline."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import math
from time import perf_counter

from .controlled_predictive_causal_forgetting_v66 import _classify, _check_root
from .controlled_predictive_quotient_v1 import FiniteModel, Outcome


@dataclass(frozen=True)
class ActionContractRule:
    horizon: int
    variant: str


@dataclass(frozen=True)
class Build:
    model: FiniteModel
    boards: dict[int, tuple[int, ...]]
    state_index: dict
    rule: ActionContractRule
    counts: dict[str, int]
    elapsed_seconds: float


def _terminal_weights(moved, work):
    """Return exact tenths of WON and LOST probability, without spawning boards."""
    work['analytic_terminal_rows'] += 1
    if max(moved) >= 11:
        return 10, 0
    empties = [cell for cell, rank in enumerate(moved) if rank == 0]
    if len(empties) >= 2:
        return 0, 0
    vacancy = empties[0]
    for cell, rank in enumerate(moved):
        if not rank:
            continue
        for neighbor in ((cell + 1,) if cell % 4 != 3 else ()) + ((cell + 4,) if cell < 12 else ()):
            work['analytic_existing_pair_checks'] += 1
            if moved[neighbor] == rank:
                return 0, 0
    neighbors = []
    if vacancy % 4: neighbors.append(vacancy - 1)
    if vacancy % 4 != 3: neighbors.append(vacancy + 1)
    if vacancy >= 4: neighbors.append(vacancy - 4)
    if vacancy < 12: neighbors.append(vacancy + 4)
    work['analytic_vacancy_neighbor_checks'] += len(neighbors)
    neighbor_ranks = {moved[cell] for cell in neighbors}
    loss = (0 if 1 in neighbor_ranks else 9) + (0 if 2 in neighbor_ranks else 1)
    return 0, loss


def _contract(moves, work):
    work['action_contract_evaluations'] += 1
    result = []
    for action, moved, score in moves:
        won, lost = _terminal_weights(moved, work)
        result.append((action, score, won, lost))
    return tuple(result)


def action_contract(board: tuple[int, ...], work: Counter | None = None):
    """The action-labelled H1 reward/terminal kernel; terminal boards return ()."""
    if work is None: work = Counter()
    status, moves = _classify(board, work)
    return _contract(moves, work) if status == 'ACTIVE' else ()


def _active_key(board, h, rule, contract):
    if h != 1 or rule.variant == 'BASELINE':
        return h, board
    if rule.variant == 'CONTRACT':
        return 1, ('ACTION_CONTRACT', contract)
    return 1, ('REWARD_ONLY_CONTRACT', tuple((a, r) for a, r, _, _ in contract))


def encode_key(board, h, rule):
    status, moves = _classify(board)
    if status != 'ACTIVE': return h, status
    if h == 0: return 0, 'CUTOFF'
    contract = _contract(moves, Counter()) if h == 1 and rule.variant != 'BASELINE' else ()
    return _active_key(board, h, rule, contract)


def build_model(board, horizon, variant, max_states=30_000):
    """Build directly; only H>1 generates individual stochastic successors.

    Every arm uses the same analytic H1 row generation. CONTRACT additionally
    merges identical H1 contracts. UNSAFE merges reward-only signatures and
    retains the first encountered terminal kernel, exposing risk aliasing.
    """
    started = perf_counter()
    _check_root(board, horizon)
    if variant not in {'BASELINE', 'CONTRACT', 'UNSAFE'}:
        raise ValueError('unknown V67 variant')
    if type(max_states) is not int or max_states < 1:
        raise ValueError('max_states must be positive')
    rule = ActionContractRule(horizon, variant)
    work = Counter(root_tiles_encoded=16)
    states, boards, layers, statuses, rows, queue = {}, {}, {}, {}, {}, []

    def add(key, status):
        if key in states:
            work['existing_terminal_state_visits' if status != 'ACTIVE' else 'existing_active_state_visits'] += 1
            return states[key], False
        if len(states) >= max_states:
            error = ValueError(f'complete V67 model exceeds max_states={max_states}')
            error.counts = dict(work)
            raise error
        state = len(states)
        states[key] = state
        layers[state], statuses[state] = key[0], status
        return state, True

    def terminal(h, status):
        return add((h, status), status)[0]

    def register(current, remaining):
        if remaining > 1 or variant == 'BASELINE':
            if (remaining, current) in states:
                work['existing_active_state_visits'] += 1
                return states[remaining, current]
        status, moves = _classify(current, work)
        if status != 'ACTIVE': return terminal(remaining, status)
        if remaining == 0: return terminal(0, 'CUTOFF')
        contract = _contract(moves, work) if remaining == 1 else ()
        key = _active_key(current, remaining, rule, contract)
        state, fresh = add(key, 'ACTIVE')
        if fresh:
            if remaining > 1 or variant == 'BASELINE': boards[state] = current
            queue.append((state, remaining, contract if remaining == 1 else moves))
        elif remaining == 1 and variant != 'BASELINE':
            work['contract_state_reuses'] += 1
        return state

    root = register(tuple(board), horizon)
    for state, remaining, data in queue:
        if remaining == 1:
            for action, score, won, lost in data:
                row = []
                for status, weight in (('WON', won), ('LOST', lost), ('CUTOFF', 10-won-lost)):
                    if weight:
                        row.append(Outcome(weight/10., terminal(0, status), score/2048.))
                rows[state, action] = tuple(row)
                work['analytic_model_action_rows'] += 1
                work['model_transition_rows'] += 1
                work['model_successor_entries'] += len(row)
        else:
            for action, moved, score in data:
                empties = [cell for cell, rank in enumerate(moved) if rank == 0]
                mass = defaultdict(list)
                for cell in empties:
                    for rank, probability in ((1, .9), (2, .1)):
                        child = list(moved); child[cell] = rank
                        target = register(tuple(child), remaining-1)
                        mass[target].append(probability/len(empties))
                        work['spawn_support_entries'] += 1
                rows[state, action] = tuple(Outcome(math.fsum(parts), target, score/2048.)
                    for target, parts in sorted(mass.items()))
                work['model_transition_rows'] += 1
                work['model_successor_entries'] += len(mass)
    model = FiniteModel(layers, statuses, rows, (root,))
    work['registered_states'] = len(states)
    work['active_states'] = sum(status == 'ACTIVE' for status in statuses.values())
    work['terminal_states'] = len(states)-work['active_states']
    work['literal_board_states'] = len(boards)
    work['contract_states'] = work['active_states']-len(boards)
    work['h0_boards_generated'] = 0
    return Build(model, boards, states, rule, dict(work), perf_counter()-started)
