"""Finite faults that would invalidate V145 coverage or policy comparisons."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from scripts import analyze_controlled_predictive_coverage_expansion_v145 as audit


def game_fixture():
    game = dict(life=1, query='risk8', replica=3, seed=14490100003, method='LEARNED',
        initial_board=[0]*16, choices=[], spawned_cells=[], spawned_ranks=[])
    for step in range(12):
        a = dict(action='LEFT', afterstate=[1]+[0]*15, score=4)
        b = dict(action='DOWN', afterstate=[0, 1]+[0]*14, score=0)
        if step in (0, 5): a['action'] = 'DOWN'
        if step in (3, 10): a['afterstate'][0] = 11
        game['choices'].append(dict(selection=dict(candidate_choice=a, baseline_choice=b),
            afterstate=[step % 3, 0]+[0]*14, previous_action='DOWN', simulation_seed=step))
        game['spawned_cells'].append(15); game['spawned_ranks'].append(1)
    return game


def game_roster():
    rows, valid = {}, {}
    for life in audit.LIVES:
        for query in audit.QUERIES:
            for method, utility in zip(audit.METHODS, (2., 3., 4., 5.)):
                for replica in range(audit.REPLICAS):
                    key = life, query, method, replica
                    rows[key] = dict(result=dict(status='WON', utility=utility+life, score=2048, steps=10))
                    valid[key] = True
    return rows, valid


def short_control_fixture():
    seed = audit.BASE+90000000; rng = audit.random.Random(seed); board = [0]*16
    work = audit.Counter(); initial = []
    def spawn(after):
        empty = [i for i, value in enumerate(after) if not value]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random() < .9 else 2
        result = list(after); result[cell] = rank; work['environment_random_draws'] += 2
        return result, cell, rank
    for _ in range(2):
        board, cell, rank = spawn(board); initial.append(dict(cell=cell, rank=rank)); work['initial_spawns'] += 1
    row = dict(life=0, query='risk1', method='H2', replica=0, seed=seed,
        initial_board=board[:], initial_spawns=initial, choices=[], actions=[], scores=[], spawned_cells=[], spawned_ranks=[])
    prior = 'DOWN'
    for step in range(3):
        _, exits, swipes = audit.previous.legal_exits(tuple(board))
        work.update(ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=swipes)
        values = {action: dict(afterstate=list(after), score=score, value=score/2048., tail_value=0.)
                  for action, (after, score) in exits.items()}
        action = min(values, key=lambda a: (-values[a]['value'], a)); chosen = values[action]
        row['choices'].append(dict(action=action, **chosen, status='ACTIVE', value_kind='estimated_return',
            action_values=values, work=dict(choose_calls=1), previous_action=prior, simulation_seed=None))
        board, cell, rank = spawn(chosen['afterstate']); prior = action
        row['actions'].append(action); row['scores'].append(chosen['score'])
        row['spawned_cells'].append(cell); row['spawned_ranks'].append(rank)
        work.update(ground_explicit_swipe_calls=1, ground_swipe_calls=1, sampled_transitions=1)
    _, _, swipes = audit.previous.legal_exits(tuple(board))
    work.update(ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=swipes)
    score = sum(row['scores']); row['final_board'] = board
    row['result'] = dict(steps=3, status='CUTOFF', score=score, components=[score/2048., 0., 0.], utility=None,
        seconds=1., decision_seconds=.5, environment_counts=dict(work), policy_counts=dict(choose_calls=3), learning_counts={})
    return row


class CoverageAuditTests(unittest.TestCase):
    def test_midpoint_selection_filters_same_action_and_terminal_pairs(self):
        roots, eligible = audit.selected_game_roots(game_fixture())
        self.assertEqual(eligible, 8)
        self.assertEqual([r['step'] for r in roots], [2, 6, 8, 11])
        self.assertEqual([r['source_ordinal'] for r in roots], [1, 3, 5, 7])
        self.assertEqual(roots[0]['root_id'], 'v145:1:risk8:3:2')
        self.assertEqual(roots[0]['board'], [1]+[0]*14+[1])
        self.assertEqual(roots[0]['suffix_seeds'], list(range(audit.BASE+1130000, audit.BASE+1130008)))
        game = game_fixture(); game['result'] = dict(score=-10000)
        self.assertEqual(audit.selected_game_roots(game)[0], roots)

    def test_incomplete_eligible_roster_does_not_repeat_roots(self):
        game = game_fixture(); game['choices'] = game['choices'][:4]
        roots, eligible = audit.selected_game_roots(game)
        self.assertEqual(eligible, 2); self.assertEqual(roots, [])

    def test_replay_and_expansion_are_equal_attempts_without_validation(self):
        rows = [dict(life=0, query='risk1', split=split, root_id=f'old{n}')
                for n, split in enumerate(('TRAIN', 'TRAIN', 'VALIDATION'))]
        new = [dict(row, root_id=row['root_id'].replace('old', 'new')) for row in rows]
        actual = audit.training_sequences(rows, new, 0, 'risk1')
        self.assertEqual([r['root_id'] for r in actual['PRIOR']], ['old0', 'old1'])
        self.assertEqual([r['root_id'] for r in actual['REPLAY']], ['old0', 'old1', 'old0', 'old1'])
        self.assertEqual([r['root_id'] for r in actual['UPDATED']], ['old0', 'old1', 'new0', 'new1'])

    def test_update_attempts_are_not_confused_with_effective_updates(self):
        work = dict(update_calls=1024, pair_updates=320, unidentifiable_pairs=704,
            pair_predictions=1024, feature_board_reads=32768, feature_rank_reads=393216,
            weight_address_updates=1200, component_weight_updates=3600)
        expected = dict(attempts=1024, updates=320)
        self.assertTrue(audit.fit_work_valid(work, expected))
        bad = dict(work, update_calls=320)
        self.assertFalse(audit.fit_work_valid(bad, expected))

    def test_four_method_aggregation_and_cutoff_preservation(self):
        rows, valid = game_roster(); result = audit.full_game_comparison(rows, valid)
        self.assertTrue(result['complete'])
        self.assertEqual(result['comparisons']['UPDATED-H2']['risk1']['mean'], 3.)
        self.assertEqual(result['comparisons']['UPDATED-REPLAY']['risk8']['mean'], 1.)
        self.assertEqual(result['comparisons']['REPLAY-PRIOR']['risk8']['positive'], 4)
        rows[(0, 'risk8', 'UPDATED', 7)]['result'].update(status='CUTOFF', utility=None)
        result = audit.full_game_comparison(rows, valid)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['comparisons']['UPDATED-H2']['risk8']['mean'])
        self.assertEqual(result['methods']['UPDATED']['risk8']['lifecycles'][0]['games'], 8)

    def test_outer_disagreement_counter_is_not_native_h1_work(self):
        counts = dict(candidate_disagreements=8, candidate_choose_calls=20, candidate_model_sampled_transitions=200)
        self.assertEqual(audit.unprefix(counts, 'candidate_'), dict(choose_calls=20, model_sampled_transitions=200))

    def test_v145_stream_and_cost_mutations_are_detected(self):
        row = short_control_fixture()
        with patch.object(audit, 'MAX_STEPS', 3), patch.object(audit.old, 'MAX_STEPS', 3), \
                patch.object(audit.planning, 'planning_counts_valid', return_value=True):
            checks, work = audit.control_checks(row, {})
            self.assertTrue(all(checks.values()), checks); self.assertEqual(work, 28)
            changed = deepcopy(row); changed['seed'] -= 100000000
            self.assertFalse(audit.control_checks(changed, {})[0]['control_seed'])
            changed = deepcopy(row); changed['result']['environment_counts']['sampled_transitions'] -= 1
            self.assertFalse(audit.control_checks(changed, {})[0]['control_trace'])
            changed = deepcopy(row); changed['result']['policy_counts']['choose_calls'] -= 1
            self.assertFalse(audit.control_checks(changed, {})[0]['control_cost_totals'])

    def test_settings_exactly_match_frozen_runner(self):
        from scripts import run_controlled_predictive_coverage_expansion_v145 as run
        self.assertEqual(audit.expected_settings(), run.settings())


if __name__ == '__main__': unittest.main()
