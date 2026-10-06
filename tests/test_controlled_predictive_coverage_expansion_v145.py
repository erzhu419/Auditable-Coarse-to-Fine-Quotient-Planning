"""Finite retained-trace selection and terminal target pairing; no simulation."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from acfqp.science.controlled_predictive_coverage_expansion_v145 import (
    BASE, build_cohort, build_examples, suffix_seed)

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT/'reports/v145_runtime_tmp/core_checks'


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = ROOT/'reports/controlled_predictive_coverage_expansion_v145.core_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before, newly_sampled_environment_transitions=0,
        newly_sampled_model_transitions=0, native_planner_calls=0,
        scope='Synthetic retained game arrays, deterministic root identities and terminal outcome components.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def synthetic_game(life, query, replica, method='LEARNED'):
    choices = []
    for step in range(10):
        baseline = dict(action='DOWN', afterstate=[2, 1]+[0]*14, score=4)
        candidate = dict(action='LEFT', afterstate=[1, 2]+[0]*14, score=12)
        if step == 0:
            candidate = deepcopy(baseline)
        if step == 9:
            candidate['afterstate'][0] = 11
        selection = dict(baseline_action=baseline['action'], candidate_action=candidate['action'],
            baseline_choice=baseline, candidate_choice=candidate, terminal_pair_bypass=step == 9,
            selected_h1=step % 2 == 0, estimated_advantage=float(step), predicted_tail_difference=[0., 0., 0.])
        choices.append(dict(action='DOWN', afterstate=[0, step+1]+[0]*14,
            previous_action='DOWN' if step == 0 else 'LEFT', simulation_seed=1000+step, selection=selection))
    return dict(life=life, query=query, replica=replica, method=method, seed=50000+life*100+replica,
        initial_board=[1, 0, 1]+[0]*13, choices=choices, spawned_cells=[0]*10,
        spawned_ranks=[1]*10, result=dict(status='LOST', utility=-999.))


def snapshots(tag='base', mutate=None):
    result = []
    for life in range(4):
        path = TEMP/f'{tag}_{life}.jsonl.gz'
        with gzip.open(path, 'wt') as stream:
            for query in ('risk1', 'risk8'):
                for replica in range(8):
                    for method in ('H2', 'ZERO', 'LEARNED'):
                        game = synthetic_game(life, query, replica, method)
                        if mutate:
                            mutate(game)
                        stream.write(json.dumps(game)+'\n')
        result.append(dict(life=life, advantage_control_trace=str(path)))
    return result


@pytest.fixture(scope='module')
def cohort():
    return build_cohort(snapshots())


def paired_rows(cohort):
    for root in cohort['roots']:
        for suffix, seed in enumerate(root['suffix_seeds']):
            branches = {}
            for method, prefix in (('H1_CONT', 'candidate'), ('H2', 'baseline')):
                is_candidate = method == 'H1_CONT'
                score = root[prefix+'_score']
                scores = [score, (4096+4*suffix) if is_candidate else (2048+2*suffix)]
                lost = suffix % 2 == 0 if is_candidate else suffix % 3 == 0
                branches[root['choices'][method]] = dict(seed=seed, root_board=root['board'],
                    first_action=root['choices'][method], first_afterstate=root[prefix+'_after'], scores=scores,
                    result=dict(status='LOST' if lost else 'WON',
                        components=[sum(scores)/2048., float(lost), float(not lost)]))
            yield dict(root_id=root['root_id'], suffix=suffix, seed=seed, continuation='H2', branches=branches)


def test_midpoint_roster_counts_ids_and_retained_spawn_reconstruction(cohort):
    assert len(cohort['roots']) == 256
    assert cohort['physical_branches'] == 4096 and cohort['paired_records'] == 2048
    assert cohort['source_rows_read'] == dict(physical_game_records=192, learned_games=64,
        learned_decisions=640, eligible_decisions=512)
    first = cohort['roots'][:4]
    assert [root['step'] for root in first] == [2, 4, 6, 8]
    assert [root['source_ordinal'] for root in first] == [1, 3, 5, 7]
    for root in first:
        assert root['root_id'] == f"v145:0:risk1:0:{root['step']}"
        assert root['source_game_roots'] == 8 and root['actions'] == ['DOWN', 'LEFT']
        assert root['board'] == [1, root['step']]+[0]*14
        assert root['previous_action'] == 'LEFT' and root['simulation_seed'] == 1000+root['step']
        assert root['candidate_score'] == 12 and root['baseline_score'] == 4
        assert root['immediate_difference'] == 8/2048.


def test_root_selection_does_not_use_selected_action_predictions_or_game_outcome(cohort):
    def mutate(game):
        game['result'] = dict(status='WON', utility=1e6)
        for choice in game['choices']:
            selection = choice['selection']
            selection['selected_h1'] = not selection['selected_h1']
            selection['estimated_advantage'] *= -999
            selection['predicted_tail_difference'] = [999., 999., 999.]
    assert build_cohort(snapshots('outcomes_changed', mutate)) == cohort


def test_suffix_streams_have_exact_formula_and_do_not_overlap(cohort):
    seeds = [seed for root in cohort['roots'] for seed in root['suffix_seeds']]
    assert len(set(seeds)) == 2048
    assert suffix_seed(3, 'risk8', 7, 3, 7) == BASE+3100000+70000+300+7
    for root in cohort['roots']:
        assert root['suffix_seeds'] == [suffix_seed(root['life'], root['query'], root['replica'], root['slot'], s)
                                        for s in range(8)]


def test_eligible_shortfall_is_not_filled_with_other_or_terminal_states():
    def mutate(game):
        if game['life'] == 0 and game['query'] == 'risk1' and game['replica'] == 0:
            for choice in game['choices'][1:8]:
                choice['selection']['terminal_pair_bypass'] = True
    with pytest.raises(ValueError, match='four eligible'):
        build_cohort(snapshots('shortfall', mutate))


def test_pair_targets_average_common_suffixes_subtract_immediate_once_and_split_whole_games(cohort):
    result = build_examples(cohort, paired_rows(cohort))
    assert result['source_rows_read'] == dict(paired_records=2048, physical_branches=4096)
    examples = result['examples']
    assert len(examples) == 256 and sum(e['split'] == 'TRAIN' for e in examples) == 128
    for example in examples:
        assert example['origin'] == 'V145' and example['suffixes'] == 8
        assert example['target_total'] == [2063/2048., .125, -.125]
        assert example['target_tail'] == [2055/2048., .125, -.125]
        assert example['split'] == ('TRAIN' if example['replica'] < 4 else 'VALIDATION')


@pytest.mark.parametrize('field', ['seed', 'root_board', 'first_action', 'first_afterstate', 'scores'])
def test_branch_binding_mismatches_fail_before_training(cohort, field):
    rows = list(paired_rows(cohort)); branch = deepcopy(rows[0]['branches']['LEFT'])
    replacement = dict(seed=-1, root_board=[9]*16, first_action='UP', first_afterstate=[8]*16, scores=[0, 4108])
    branch[field] = replacement[field]; rows[0]['branches']['LEFT'] = branch
    with pytest.raises(ValueError, match='first-action branch'):
        build_examples(cohort, rows)


@pytest.mark.parametrize('kind', ['cutoff', 'components', 'missing', 'duplicate', 'continuation'])
def test_incomplete_or_wrong_terminal_supervision_is_not_averaged(cohort, kind):
    rows = list(paired_rows(cohort))
    if kind == 'cutoff':
        rows[0]['branches']['LEFT']['result']['status'] = 'CUTOFF'
    elif kind == 'components':
        rows[0]['branches']['LEFT']['result']['components'][1] = .5
    elif kind == 'missing':
        rows.pop()
    elif kind == 'duplicate':
        rows[-1] = rows[-2]
    else:
        rows[0]['continuation'] = 'LEARNED'
    with pytest.raises(ValueError, match='supervision|components|suffix roster|source identity'):
        build_examples(cohort, rows)
