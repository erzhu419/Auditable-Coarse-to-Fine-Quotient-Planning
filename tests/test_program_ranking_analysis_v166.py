"""Independent semantic ranking audit detects consequential pairing errors."""
from copy import deepcopy

import pytest

from acfqp.science import controlled_predictive_program_ranking_analysis_v166 as audit
from acfqp.science import controlled_predictive_program_ranking_v166 as core


def fixture_data():
    candidates, programs, roots, branches, rows = [], [], [], [], []
    prototypes = [dict(candidate_id='P0', first_action='LEFT', probe_action='DOWN', true_suffix=['UP']*3, false_suffix=['RIGHT']*3),
                  dict(candidate_id='P1', first_action='UP', probe_action='LEFT', true_suffix=['DOWN']*3, false_suffix=['RIGHT']*3)]
    for life in range(4):
        for query in ('risk1', 'risk8'):
            pool = deepcopy(prototypes if query == 'risk1' else prototypes[:1])
            candidates.append(dict(heldout_life=life, query=query, candidates=pool))
            selected = 'P0' if query == 'risk8' or life < 2 else 'P1'
            programs.append(dict(heldout_life=life, query=query,
                                 programs={'LEARNED': dict(candidate_id=selected, mapping=dict(true='A', false='B'))}))
            for slot in range(4):
                roots.append(dict(root_id=f'{life}:{query}:{slot}', life=life, query=query, slot=slot, board=[0]*16))
    for root in roots:
        for fold in range(4):
            if fold == root['life']: continue
            modes = ['H2']+[f'P{candidate}_{arm}' for candidate in (range(2) if root['query'] == 'risk1' else range(1)) for arm in ('A', 'B')]
            for suffix in range(4):
                predicate = None if root['slot'] == 0 and suffix == 3 else True
                direction = 1 if root['slot'] < 2 else -1
                if suffix >= 2 and root['slot'] in (1, 2): direction *= -1
                for mode in modes:
                    arm = 'H2' if mode == 'H2' else mode[-1]
                    plan = dict(branch_id=f"{root['root_id']}:{fold}:{suffix}:{mode}", root_id=root['root_id'],
                                heldout_life=fold, suffix=suffix, mode=mode, seed=root['life']*1000+root['slot']*10+suffix)
                    branches.append(plan)
                    won = True if arm == 'H2' or predicate is None else (root['slot']+suffix+(arm == 'B')) % 3 != 0
                    reward = 100. if arm == 'H2' or predicate is None else 100.+25*direction*(1 if arm == 'A' else -1)
                    vector = [reward, float(not won), float(won)]
                    module = dict(predicate=predicate, actual_word=['LEFT'], actual_probe='DOWN',
                                  prefix_steps=1 if predicate is None else 4, attempts=1 if predicate is None else 4,
                                  exit_reason='terminal' if predicate is None else 'budget', exit_step=1 if predicate is None else 4)
                    rows.append(dict(plan, query=root['query'], score=reward*2048, steps=10,
                                     status='WON' if won else 'LOST', components=vector,
                                     utility=audit._utility(vector, root['query']), module=module))
    return candidates, programs, roots, branches, rows


def test_independent_metadata_counts_and_all_arithmetic_agree():
    data = fixture_data(); roster = core.build_roster(*data[:4]); result = core.evaluate(roster, data[4])
    independent = audit.independent_roster(*data[:4])
    assert independent['counts'] == dict(semantic_strata=3, semantic_roots=48, logical_triplets=192,
                                        logical_branch_references=576, unique_physical_branch_rows=512)
    checked = audit.audit(*data, roster, result)
    assert checked['valid'], [c for c in checked['checks'] if not c['passed']]


def test_missing_first_donor_is_not_replaced_or_root_deleted():
    data = fixture_data()
    plan = next(p for p in data[3] if p['root_id'] == '0:risk1:0' and p['heldout_life'] == 1 and p['mode'] == 'P0_A')
    data[3].remove(plan)
    roster = audit.independent_roster(*data[:4])
    assert roster['strata'][0]['histories'][0]['donor']['heldout_life'] == 1
    assert roster['counts']['semantic_roots'] == 48 and not roster['complete']
    assert not audit.independent_evaluate(roster, data[4])['complete']


def test_two_halves_are_separate_and_rank_flips_are_retained():
    data = fixture_data(); roster = audit.independent_roster(*data[:4])
    before = audit.independent_evaluate(roster, data[4])
    changed = deepcopy(data[4])
    for row in changed:
        if row['suffix'] >= 2 and row['mode'].endswith('_B') and row['module']['predicate'] is not None:
            row['components'][0] += 100
            row['score'] = row['components'][0]*2048
            row['utility'] = audit._utility(row['components'], row['query'])
    after = audit.independent_evaluate(roster, changed)
    assert before['groups']['half01'] == after['groups']['half01']
    assert before['groups']['half23'] != after['groups']['half23']
    flips = [r for r in before['stability']['root_rows'] if r['contrasts']['A-B']['sign_flip']]
    assert len(flips) == 24
    assert audit._rank_comparison(0., 1.)['tie_change'] and not audit._rank_comparison(0., 1.)['sign_flip']


def test_reward_risk_covariance_and_equal_weight_propagation():
    differences = [dict(reward_effect=10., risk_effect=-8., utility=2.), dict(reward_effect=0., risk_effect=8., utility=8.)]
    decomposition = audit._decomposition(differences)
    assert decomposition['reward_risk_sample_covariance'] == -80.
    assert decomposition['utility_sample_variance'] == pytest.approx(decomposition['reward_sample_variance']+decomposition['risk_sample_variance']+2*decomposition['reward_risk_sample_covariance'])
    pooled = audit._pool_decomposition([audit._pool_decomposition([decomposition]*4)]*4)
    assert pooled['utility_mean_variance'] == decomposition['utility_mean_variance']/16


@pytest.mark.parametrize('corruption', ['seed', 'none_path', 'cutoff', 'terminal_vector'])
def test_corrupt_triplet_keeps_incomplete_cohort(corruption):
    data = fixture_data(); roster = audit.independent_roster(*data[:4])
    row = next(r for r in data[4] if r['root_id'] == '0:risk1:0' and r['heldout_life'] == 1 and r['suffix'] == 3 and r['mode'] == 'P0_B')
    if corruption == 'seed': row['seed'] += 1
    elif corruption == 'none_path': row['module']['exit_step'] += 1
    elif corruption == 'cutoff': row.update(status='CUTOFF', utility=None)
    else: row['status'] = 'LOST'
    assert not audit.independent_evaluate(roster, data[4])['complete']


def test_mutated_interval_covariance_or_sign_flip_fails_audit():
    data = fixture_data(); roster = core.build_roster(*data[:4]); good = core.evaluate(roster, data[4])
    for corruption in ('ci', 'covariance', 'sign_flip'):
        changed = deepcopy(good)
        if corruption == 'ci': changed['groups']['half01']['stratum_summaries'][0]['metrics']['utility']['conditional_suffix_ci95'][0] -= .1
        elif corruption == 'covariance': changed['groups']['half01']['root_rows'][0]['variance_decomposition']['A-B']['reward_risk_mean_covariance'] += .1
        else: changed['stability']['root_rows'][0]['contrasts']['A-B']['sign_flip'] = True
        assert not audit.audit(*data, roster, changed)['valid']
