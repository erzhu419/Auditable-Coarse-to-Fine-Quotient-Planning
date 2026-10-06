"""Finite V147 checks for feature aliasing, LMS, accounting and fresh streams."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from scripts import analyze_controlled_predictive_shared_local_advantage_v147 as audit



def example():
    return dict(replica=0, candidate_after=[1]+[0]*15,
        baseline_after=[0]*16, target_tail=[2., -.25, .25], immediate_difference=.5)

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

class SharedAuditTests(unittest.TestCase):
    def test_frozen_runner_settings_and_zero_control_match(self):
        from scripts import run_controlled_predictive_shared_local_advantage_v147 as run
        self.assertEqual(audit.expected_settings(),run.settings())
        self.assertEqual(audit.METHODS,('H2','ZERO','UPDATED','SHARED'))
        self.assertEqual(audit.expected_settings()['physical_games'],256)

    def test_geometry_counts_collapsed_disagreements_without_imputing_zero_coverage(self):
        informative=dict(example(),candidate_action='LEFT',baseline_action='DOWN')
        collapsed=dict(informative,baseline_after=[0]*15+[1])
        difference=audit.feature_difference(informative['candidate_after'],informative['baseline_after'])
        geometry=audit.SVDGeometry([sorted(difference.items())])
        result=audit.geometry_metrics([informative,collapsed],geometry,'SHARED')
        self.assertEqual(result['roots'],2)
        self.assertEqual(result['collapsed_disagreements'],1)
        self.assertEqual(result['nonzero_features'],1)
        self.assertEqual(result['covered_norm_fraction'],1)
        self.assertAlmostEqual(result['projection_fraction'],1)

    def test_signed_multiplicity_and_normalized_step(self):
            row = example(); difference = audit.feature_difference(row['candidate_after'], row['baseline_after'])
            self.assertTrue(any(v < 0 for v in difference.values()))
            self.assertTrue(any(abs(v) > 1 for v in difference.values()))
            self.assertEqual(sum(difference.values()), 0)
            fitted = audit.fit_oracle([row], passes=1)
            prediction = audit.predict_difference(difference, fitted['weights'])
            for actual, expected in zip(prediction, row['target_tail']): self.assertAlmostEqual(actual, .1*expected)
            reverse = audit.feature_difference(row['baseline_after'], row['candidate_after'])
            self.assertEqual(reverse, {k: -v for k, v in difference.items()})

    def test_frozen_payload_detects_changed_weights(self):
            fitted = audit.fit_oracle([example()], passes=2)
            payload = dict(radix=11, updates=fitted['updates'], frozen=True,
                weights=[[key, *values] for key, values in sorted(fitted['weights'].items())])
            self.assertTrue(audit.model_matches(payload, fitted))
            payload['weights'][0][1] += .01
            self.assertFalse(audit.model_matches(payload, fitted))

    def test_control_stream_and_cost_mutations(self):
            row = short_control_fixture()
            with patch.object(audit, 'MAX_STEPS', 3), patch.object(audit.old, 'MAX_STEPS', 3), \
                    patch.object(audit.planning, 'planning_counts_valid', return_value=True):
                checks, work = audit.control_checks(row, {})
                self.assertTrue(all(checks.values()), checks)
                self.assertEqual(work, 28)
                changed = deepcopy(row); changed['spawned_ranks'][1] = 3-changed['spawned_ranks'][1]
                self.assertFalse(audit.control_checks(changed, {})[0]['control_spawn_stream'])
                changed = deepcopy(row); changed['result']['policy_counts']['choose_calls'] -= 1
                self.assertFalse(audit.control_checks(changed, {})[0]['control_cost_totals'])

    def test_gate_zero_and_terminal_bypass(self):
            board = [1, 1, 2, 0]+[0]*12
            def choice(action, value):
                after, score, changed = audit.prior.prior.ground.swipe_board_v1(tuple(board), audit.prior.prior.ground.Swipe2048Action(action))
                return dict(action=action, afterstate=list(after), score=score, value=value, status='ACTIVE',
                    action_values={action: dict(afterstate=list(after), score=score)})
            a, b = choice('LEFT', 0.), choice('DOWN', 1.)
            delta = 4/2048.
            selection = dict(candidate_choice=a, baseline_choice=b, candidate_action='LEFT', baseline_action='DOWN',
                candidate_score=4, baseline_score=0, same_action=False, terminal_pair_bypass=False,
                predicted_tail_difference=[0., 0., 0.], immediate_difference=delta,
                estimated_advantage=delta, selected_h1=True)
            difference = audit.feature_difference(a['afterstate'], b['afterstate'])
            union = audit.feature_counts(a['afterstate']).keys() | audit.feature_counts(b['afterstate']).keys()
            work = dict(choose_calls=1, candidate_disagreements=1, selected_h1=1)
            learner = dict(feature_board_reads=32, feature_rank_reads=128, feature_occurrences=80, unary_feature_occurrences=32, pair_feature_occurrences=48,
                pair_distinct_addresses=len(union), pair_nonzero_difference_addresses=len(difference),
                pair_signed_difference_occurrences=sum(abs(v) for v in difference.values()), pair_predictions=1,
                weight_address_lookups=len(difference), component_weight_reads=3*len(difference))
            work.update({'learner_'+key: value for key, value in learner.items()})
            record = dict(selection=selection, work=work, action='LEFT', afterstate=a['afterstate'], score=4, status='ACTIVE', value=1.+delta,
                value_kind='baseline_h2_proxy_plus_learned_advantage', action_values={
                    'LEFT': dict(afterstate=a['afterstate'], score=4, value=1.+delta, tail_value=1.),
                    'DOWN': dict(afterstate=b['afterstate'], score=0, value=1., tail_value=1.)})
            with patch.object(audit.planning, 'planning_counts_valid', return_value=True), \
                    patch.object(audit, 'compact_choice_valid', return_value=True), \
                    patch.object(audit.h1, 'h1_counts_valid', return_value={}), \
                    patch.object(audit.h1, 'root_choice_checks', return_value={}):
                self.assertTrue(all(audit.gate_checks(board, record, 'risk1', {}).values()))
                record['selection']['estimated_advantage'] *= -1
                self.assertFalse(audit.gate_checks(board, record, 'risk1', {})['gate_equation'])
                record['selection']['estimated_advantage'] = 0.
                a['afterstate'][0] = 11; a['action_values']['LEFT']['afterstate'] = a['afterstate']
                selection.update(terminal_pair_bypass=True, selected_h1=False)
                record.update(action='DOWN', value=1., action_values={'DOWN': record['action_values']['DOWN']},
                    work=dict(choose_calls=1, candidate_disagreements=1, terminal_pair_bypasses=1))
                self.assertTrue(all(audit.gate_checks(board, record, 'risk1', {}).values()))

    def test_shared_empty_board_address_counts(self):
        expected={0:4,11:8,22:4,33:4,44:8,407:4,418:8}
        self.assertEqual(dict(audit.shared_feature_counts([0]*16)),expected)
        self.assertEqual(sum(expected.values()),40)

    def test_aliasing_counts_attempts_without_weight_updates(self):
        row=example();row['candidate_after']=[1]+[0]*15;row['baseline_after']=[0]*15+[1]
        fitted=audit.fit_oracle([row],passes=2)
        self.assertEqual(fitted['weights'],{})
        self.assertEqual(fitted['updates'],0)
        self.assertEqual(fitted['attempts'],2)
        self.assertEqual(fitted['work']['unidentifiable_pairs'],2)
        self.assertEqual(fitted['work']['feature_rank_reads'],256)
        self.assertEqual(fitted['work']['feature_occurrences'],160)

    def test_old_and_shared_feature_work_are_distinct(self):
        row=example()
        old=audit.prediction_work(row['candidate_after'],row['baseline_after'],'UPDATED')
        shared=audit.prediction_work(row['candidate_after'],row['baseline_after'],'SHARED')
        self.assertEqual(old['feature_rank_reads'],384)
        self.assertEqual(shared['feature_rank_reads'],128)
        self.assertEqual(shared['unary_feature_occurrences'],32)
        self.assertEqual(shared['pair_feature_occurrences'],48)

    def test_comparison_keeps_cutoff_cells(self):
        rows,valid={},{}
        for life in audit.LIVES:
            for query in audit.QUERIES:
                for method,value in zip(audit.METHODS,(1.,2.,3.,4.)):
                    for replica in range(8):
                        key=(life,query,method,replica)
                        rows[key]={'result':dict(status='WON',utility=value+life,score=2048,steps=100)}
                        valid[key]=True
        result=audit.full_game_comparison(rows,valid)
        self.assertTrue(result['complete'])
        self.assertEqual(result['comparisons']['SHARED-UPDATED']['risk1']['mean'],1.)
        rows[0,'risk8','SHARED',0]['result'].update(status='CUTOFF',utility=None)
        result=audit.full_game_comparison(rows,valid)
        self.assertFalse(result['complete'])
        self.assertIsNone(result['comparisons']['SHARED-H2']['risk8']['mean'])

if __name__=='__main__':unittest.main()
