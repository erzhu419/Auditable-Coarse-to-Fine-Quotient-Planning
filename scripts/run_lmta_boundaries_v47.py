"""Seven scripted V46 replay-collection witnesses, with no learning or MCTS."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import json
from pathlib import Path
import sys
from time import perf_counter
from unittest.mock import patch

import networkx as nx
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import acfqp.science.lmta_agent_v44 as lmta_source
from acfqp.science.lmta_aim_v43 import AIMEnvironment
from acfqp.science.lmta_weighted_v46 import LMTAAgent, FlatDQNAgent, BudgetHRLAgent

AGENTS = {'FLAT_DQN': FlatDQNAgent, 'BUDGET_HRL': BudgetHRLAgent, 'LMTA_RI': LMTAAgent}


def json_value(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    raise TypeError(type(value).__name__)


def low_records(agent, lmta):
    rows = agent.low_replay if lmta else agent.ll_replay
    result = []
    for row in rows:
        if lmta:
            before, goal, action, reward, after, legal, terminal, graph_id = row
        else:
            before, action, reward, after, legal, terminal, graph_id = row
            goal = None
        result.append(dict(features=before.copy(), goal=goal, action=int(action), reward=float(reward),
            next_features=after.copy(), next_legal=legal.copy(), terminal=bool(terminal), graph_id=graph_id))
    return result


def collect_case(case_id, method, n, edges, budget, horizon, daily_budgets, seeds):
    started = perf_counter()
    counts, optimizer_calls = Counter(), Counter()
    select_events, day_events = [], []
    graph = nx.DiGraph()
    graph.add_nodes_from(range(n))
    graph.add_edges_from(edges)
    graph.graph['replay_id'] = case_id
    lmta = method == 'LMTA_RI'
    with ExitStack() as stack:
        select_original, finish_original = AIMEnvironment.select, AIMEnvironment.finish_day
        transition_original, reset_original = AIMEnvironment.transition, AIMEnvironment.reset

        def select(env, action, **kwargs):
            counts['select_calls'] += 1
            day, before = env.day, env.observation()
            remaining = daily_budgets[day] - len(env.daily_selected)
            result = select_original(env, action, **kwargs)
            after, reward, terminal = result
            select_events.append(dict(day=day, action=int(action), macro_budget=daily_budgets[day],
                macro_remaining_before=remaining, macro_remaining_after=remaining - 1,
                features=before['features'].copy(), raw_after_select_features=after['features'].copy(),
                raw_after_select_statuses=after['statuses'].copy(), raw_after_select_legal=after['legal_mask'].copy(),
                reward=float(reward), environment_terminal=bool(terminal)))
            return result

        def finish(env, **kwargs):
            counts['finish_day_calls'] += 1
            day, before = env.day, env.observation()
            selected = list(env.daily_selected)
            assert len(selected) == daily_budgets[day], 'Scripted allocation was not executed'
            result = finish_original(env, **kwargs)
            after, spread, terminal, info = result
            day_events.append(dict(day=day, selected=selected, duration=len(selected),
                before_features=before['features'].copy(), next_features=after['features'].copy(),
                before_statuses=before['statuses'].copy(), next_statuses=after['statuses'].copy(),
                spread_reward=float(spread), day_reward=float(info['day_reward']),
                environment_terminal=bool(terminal), propagation_draws=info['propagation_draws']))
            return result

        def transition(env, *args, **kwargs):
            counts['transition_calls'] += 1
            result = transition_original(env, *args, **kwargs)
            counts['propagation_draws'] += result[2]['propagation_draws']
            return result

        def reset(env, *args, **kwargs):
            counts['reset_calls'] += 1
            return reset_original(env, *args, **kwargs)

        for name, replacement in [('select', select), ('finish_day', finish),
                                  ('transition', transition), ('reset', reset)]:
            stack.enter_context(patch.object(AIMEnvironment, name, replacement))
        env = AIMEnvironment(graph, budget=budget, horizon=horizon, seed=47001)
        agent = AGENTS[method](graph, budget, horizon, seed=47000, device='cpu')
        counter_name = 'episodes' if lmta else 'training_episodes'
        # This is a control setting, not evidence of three historical episodes.
        setattr(agent, counter_name, 3)
        scripted_episode_counter_before = getattr(agent, counter_name)
        actions = iter(seeds)

        def next_seed(legal):
            action = next(actions)
            assert bool(legal[action]), 'Script requested an illegal seed'
            return action

        def baseline_action(network, observation, legal, training):
            if method == 'BUDGET_HRL' and network is agent.hl:
                action = daily_budgets[env.day]
                assert bool(legal[action]), 'Script requested an illegal budget'
                return action
            return next_seed(legal)

        if lmta:
            def fixed_search(observation, training):
                counts['controlled_search_calls'] += 1
                policy = np.zeros(32)
                policy[0] = 1.
                return policy, 0.

            def fixed_budget(joined):
                logits = torch.full((budget + 1,), -torch.inf, dtype=joined.dtype, device=joined.device)
                logits[daily_budgets[env.day]] = 0.
                return logits

            stack.enter_context(patch.object(agent, 'search', fixed_search))
            stack.enter_context(patch.object(agent.model.budget, 'forward', fixed_budget))
            stack.enter_context(patch.object(lmta_source, 'epsilon_action',
                lambda q, legal, epsilon, rng: next_seed(legal)))
            optimizers = {'HL': agent.optim, 'LL': agent.low_optim}
        else:
            stack.enter_context(patch.object(agent, '_act', baseline_action))
            optimizers = {'LL': agent.ll_optimizer}
            if method == 'BUDGET_HRL':
                optimizers['HL'] = agent.hl_optimizer
        for name, optimizer in optimizers.items():
            original = optimizer.step

            def optimizer_step(*args, name=name, original=original, **kwargs):
                optimizer_calls[name] += 1
                return original(*args, **kwargs)

            stack.enter_context(patch.object(optimizer, 'step', optimizer_step))
        result = agent.run_episode(env, training=True)
        assert next(actions, None) is None, 'Scripted seeds remain unexecuted'
        low = low_records(agent, lmta)
        if lmta:
            high = [dict(row) for row in agent.games[0]]
        elif method == 'BUDGET_HRL':
            high = [dict(features=row[0], budget=row[1], reward=row[2], next_features=row[3],
                next_legal=row[4], terminal=row[5], graph_id=row[6]) for row in agent.hl_replay]
        else:
            high = []
        gradients = sum(value for name, value in agent.counts.items() if 'gradient_steps' in name)
        states_empty = all(not optimizer.state for optimizer in optimizers.values())
        assert gradients == sum(optimizer_calls.values()) == 0 and states_empty and result['losses'] == []
        assert agent.counts.get('mcts_simulations', 0) == agent.counts.get('latent_recurrent_calls', 0) == 0
        assert len(low) < 8 and (len(agent.games) if lmta else len(high)) < 8
        assert result['raw_return'] == np.count_nonzero(env.statuses) == sum(row['day_reward'] for row in day_events)
        assert [row['action'] for row in low] == seeds
        assert counts['select_calls'] == len(seeds) and counts['finish_day_calls'] == horizon
        assert counts['transition_calls'] == horizon
        assert getattr(agent, counter_name) == 4
        boundaries = []
        for index, (raw, stored) in enumerate(zip(select_events, low)):
            day = day_events[raw['day']]
            boundaries.append(dict(low_index=index, day=raw['day'],
                macro_budget=raw['macro_budget'], macro_remaining_before=raw['macro_remaining_before'],
                raw_after_equals_stored_after=bool(np.array_equal(raw['raw_after_select_features'], stored['next_features'])),
                stored_after_equals_day_after=bool(np.array_equal(stored['next_features'], day['next_features'])),
                stored_terminal=stored['terminal'], raw_environment_terminal=raw['environment_terminal']))
        report = dict(case_id=case_id, method=method, graph=dict(nodes=n, edges=edges),
            budget=budget, horizon=horizon, scripted_daily_budgets=daily_budgets, scripted_seeds=seeds,
            initialization_seed=47000, environment_seed=47001,
            scripted_episode_counter_before=scripted_episode_counter_before,
            scripted_episode_counter_after=getattr(agent, counter_name), actual_collected_episodes=1,
            gradient_updates=gradients, optimizer_step_calls={name: optimizer_calls[name] for name in optimizers},
            optimizer_states_empty=states_empty, model_work=dict(agent.counts),
            mcts_simulations=0, raw_return=float(result['raw_return']),
            final_features=env.features().copy(), final_statuses=env.statuses.copy(),
            environment_counters=env.counters['train'], calls=dict(counts),
            select_events=select_events, day_events=day_events, low_replay=low, high_replay=high,
            boundary_comparisons=boundaries, wall_seconds=perf_counter() - started,
            assertions_passed=True)
        if lmta:
            report['mts_input_binding'] = dict(after_slot=4, update_executed=False,
                after_features_if_sampled=[row[4].copy() for row in agent.low_replay],
                source='src/acfqp/science/lmta_agent_v44.py:update_high; micro after uses r[4]',
                scope='These are retained slot values, not an executed MTS update.')
        return report


def compare_budgets(short, long):
    a, b = short['low_replay'][0], long['low_replay'][0]
    raw_a, raw_b = short['select_events'][0], long['select_events'][0]
    checks = dict(same_visible_features=bool(np.array_equal(a['features'], b['features'])),
        same_action_and_goal=a['action'] == b['action'] and a['goal'] == b['goal'],
        same_original_micro_after=bool(np.array_equal(raw_a['raw_after_select_features'], raw_b['raw_after_select_features'])),
        different_macro_context=raw_a['macro_remaining_before'] != raw_b['macro_remaining_before'],
        different_rewards=a['reward'] != b['reward'],
        different_next_features=not np.array_equal(a['next_features'], b['next_features']),
        different_macro_terminal=a['terminal'] != b['terminal'])
    assert all(checks.values())
    assert (a['reward'], b['reward'], a['terminal'], b['terminal']) == (2., 1., True, False)
    assert short['boundary_comparisons'][0]['stored_after_equals_day_after']
    assert not short['boundary_comparisons'][0]['raw_after_equals_stored_after']
    assert long['boundary_comparisons'][0]['raw_after_equals_stored_after']
    return dict(method=short['method'], cases=[short['case_id'], long['case_id']], checks=checks,
        low_feature_columns=['inactive', 'active', 'removed', 'remaining_days_fraction', 'remaining_global_budget_fraction'],
        macro_remaining_is_network_input=False,
        interpretation='The allocated macro budget is hidden from these low inputs. This is a modeling '
            'limitation with the declared macro truncation, not evidence that a stochastic transition or delayed reward is invalid.')


def run(output_dir):
    destination = output_dir / 'boundaries.json'
    if destination.exists():
        raise FileExistsError('Retain the previous boundary probe; do not overwrite')
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    started = perf_counter()
    chain = [(0, 1), (1, 2), (2, 3)]
    cases = [collect_case('flat_chain', 'FLAT_DQN', 4, chain, 1, 3, [1, 0, 0], [0])]
    flat = cases[0]
    last = flat['low_replay'][-1]
    assert flat['raw_return'] == last['reward'] == 4 and last['terminal']
    assert not last['next_legal'].any() and np.array_equal(last['next_features'], flat['final_features'])
    comparisons, zero_budget = [], []
    for method in ('BUDGET_HRL', 'LMTA_RI'):
        short = collect_case(method + '_budget_11', method, 3, [(0, 2)], 2, 2, [1, 1], [0, 1])
        long = collect_case(method + '_budget_20', method, 3, [(0, 2)], 2, 2, [2, 0], [0, 1])
        cases.extend([short, long])
        comparisons.append(compare_budgets(short, long))
        tail = collect_case(method + '_zero_budget_tail', method, 4, chain, 1, 3, [1, 0, 0], [0])
        cases.append(tail)
        assert [row['reward'] for row in tail['high_replay']] == [2., 1., 1.]
        assert [row['duration'] for row in tail['day_events']] == [1, 0, 0]
        assert tail['raw_return'] == 4 and tail['low_replay'][0]['reward'] == 2
        assert tail['low_replay'][0]['terminal']
        assert all(not np.array_equal(row['before_statuses'], row['next_statuses']) for row in tail['day_events'][1:])
        zero_budget.append(dict(method=method, case_id=tail['case_id'], daily_rewards=[2., 1., 1.],
            durations=[1, 0, 0], low_macro_terminal_target=2., complete_undiscounted_return=4.,
            interpretation='Later zero-budget propagation remains in high-level rewards and the full '
                'return. The low-level target stops at its declared macro boundary.'))
    totals = Counter()
    for case in cases:
        totals.update(case['calls'])
    assert len(cases) == 7
    assert (totals['select_calls'], totals['finish_day_calls'], totals['propagation_draws']) == (11, 17, 13)
    report = dict(schema='acfqp.lmta_boundaries.v47', status='complete', cases=cases,
        budget_context_comparisons=comparisons, zero_budget_tails=zero_budget,
        flat_terminal_reward_and_next_state_correct=True, all_assertions_passed=True,
        actual_collected_episodes=7, gradient_updates=0, mcts_simulations=0,
        physical_costs=dict(primitive_selections=totals['select_calls'], day_transitions=totals['finish_day_calls'],
            propagation_draws=totals['propagation_draws']), environment_and_controller_calls=dict(totals),
        wall_seconds=perf_counter() - started,
        scope='Scripted legal decisions on seven fresh V46 agents; no frozen-policy performance test, '
            'parameter search, gradient update, or MCTS. Episode counters are explicitly set to 3 only '
            'to bypass warmup and become 4 after one collection episode; no prior training occurred. '
            'The original collection and environment transitions are forwarded unchanged. '
            'finish_day counts physical day samples; its nested transition is not an additional sample. '
            'All new tiny-probe samples are separate from retained V44/V46 costs.')
    destination.write_text(json.dumps(report, default=json_value, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': report['status'], 'physical_costs': report['physical_costs'],
        'environment_and_controller_calls': dict(totals), 'wall_seconds': report['wall_seconds']}, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'reports/lmta_mechanism_v47')
    run(parser.parse_args().output_dir)
