"""Retained-label and aggregation integration checks without native planners."""
from copy import deepcopy
import gzip
import json
from pathlib import Path

import pytest

from scripts import run_controlled_predictive_transfer_diagnosis_v146 as runner

TEMP = Path(__file__).resolve().parents[1]/'reports/v146_runtime_tmp'


@pytest.fixture(scope='module', autouse=True)
def ledger(request):
    TEMP.mkdir(parents=True, exist_ok=True)
    before = request.session.testsfailed
    yield
    path = TEMP/'runner_checks.json'
    payload = json.loads(path.read_text()) if path.exists() else dict(attempts=[])
    payload['attempts'].append(dict(
        tests=sum(item.module.__name__ == __name__ for item in request.session.items),
        failures=request.session.testsfailed-before,
        newly_sampled_environment_transitions=0, newly_sampled_model_transitions=0,
        scope='Synthetic retained gzip records, scalar diagnostics and hierarchical aggregation.'))
    path.write_text(json.dumps(payload, indent=2)+'\n')


def fixture_rows(name, same_old=False, mutation=None):
    cohorts, selected, traces = {}, {}, {}
    for origin in runner.ORIGINS:
        key = origin+'-heldout'
        same = origin == 'OLD' and same_old
        root = dict(root_id=key, life=0, query='risk8', replica=4, suffix_seeds=list(range(8)),
                    choices=dict(H1_CONT='LEFT', H2='LEFT' if same else 'RIGHT'))
        cohorts[origin] = [root, dict(root_id=origin+'-train')]
        selected[origin] = [dict(root_id=key, target_total=[0., 0., 0.] if same else [3.5, -.5, .5])]
        rows = []
        for suffix in range(8):
            def branch(components):
                return dict(seed=suffix, result=dict(
                    status='WON' if components[2] else 'LOST', components=components,
                    utility=runner.utility(components, 'risk8')))
            branches = dict(LEFT=branch([suffix, suffix % 2, 1-suffix % 2]), RIGHT=branch([0, 1, 0]))
            if origin == 'OLD':
                branches.update(UP=branch([0, 1, 0]), DOWN=branch([0, 1, 0]))
            rows.append(dict(root_id=key, suffix=suffix, seed=suffix, continuation='H2', branches=branches))
        if mutation:
            mutation(origin, rows, selected[origin])
        # TRAIN outcomes have no usable result; held-out processing must skip them.
        rows.append(dict(root_id=origin+'-train', branches={key: {} for key in range(4)}))
        path = TEMP/(name+'_'+origin+'.jsonl.gz')
        with gzip.open(path, 'wt') as stream:
            for row in rows:
                stream.write(json.dumps(row)+'\n')
        traces[origin] = [dict(life=0, path=str(path))]
    return cohorts, selected, traces


def test_retained_scalar_utility_keeps_component_covariance_and_target_mean():
    labels, _, checks = runner.retained_labels(*fixture_rows('covariance'))
    assert all(checks.values())
    expected = [16., 1., 18., 3., 20., 5., 22., 7.]
    assert labels['NEW', 'NEW-heldout'] == expected
    result = runner.label_diagnostics(expected, {})
    assert result['mean'] == 11.5
    assert result['mean_noise_variance'] == 8.75
    assert result['variance'] != pytest.approx(6.+64.*2./7.+64.*2./7.)


def test_old_same_action_uses_one_physical_branch_and_skips_train_outcomes():
    labels, counts, checks = runner.retained_labels(*fixture_rows('dedup', same_old=True))
    assert all(checks.values())
    assert labels['OLD', 'OLD-heldout'] == [0.]*8
    assert len(labels) == 2
    assert counts['paired_records_scanned'] == 18
    assert counts['physical_branch_records_scanned'] == 56  # OLD 4, NEW 2, plus TRAIN records.
    assert counts['paired_records_selected'] == 16
    assert counts['selected_physical_branch_records'] == 24  # OLD 1, NEW 2 per suffix.


def test_retained_suffix_identity_terminal_and_component_mean_failures_are_flagged():
    def corrupt(origin, rows, examples):
        if origin == 'NEW':
            rows[0]['seed'] = 100
            rows[1]['branches']['LEFT']['result']['status'] = 'CUTOFF'
            examples[0]['target_total'][0] += 1.
    _, _, checks = runner.retained_labels(*fixture_rows('bad', mutation=corrupt))
    assert not checks['paired_identity']
    assert not checks['terminal_labels']
    assert not checks['retained_target_means']


def test_aggregation_weights_games_and_lives_equally_and_excludes_zero_geometry():
    rows = []
    for life in range(4):
        for replica in range(4, 8):
            zero = life == 0 and replica == 4
            for slot in range(3 if zero else 1):
                diag = runner.label_diagnostics([0.]*8, dict.fromkeys(runner.METHODS, 0.))
                diag['mean_noise_variance'] = 8. if life or replica == 5 else 0.
                coverage = float(life == 0 and replica == 5)
                geometry = dict(covered_norm_fraction=coverage, projection_fraction=coverage,
                                max_abs_cosine=coverage, orthogonal_to_training=not coverage)
                rows.append(dict(root_id=f'{life}:{replica}:{slot}', life=life, replica=replica,
                    candidate_action='LEFT', baseline_action='RIGHT', difference=[] if zero else [[1, 1]],
                    labels=[0.]*8, label_diagnostics=diag,
                    geometry={method:deepcopy(geometry) for method in runner.METHODS}))
    result = runner.aggregate(rows)
    assert result['roots'] == 18 and result['nonzero_features'] == 15
    assert result['metrics']['mean_noise_variance'] == 6.5
    assert result['metrics']['zero_feature'] == 1./16.
    assert result['metrics']['PRIOR.covered_norm_fraction'] == pytest.approx(1./12.)
    assert result['lifecycles'][0]['games'][0]['metrics']['PRIOR.projection_fraction'] is None


def test_settings_keep_fixed_heldout_cohort_and_zero_new_learning_or_sampling():
    settings = runner.settings()
    assert settings['primary_origin'] == 'NEW'
    assert settings['heldout_replicas'] == [4, 5, 6, 7]
    assert settings['methods'] == ['PRIOR', 'REPLAY', 'UPDATED']
    assert settings['suffixes'] == 8 and settings['roots_per_game'] == 4
    assert settings['fixed_halves'] == [[0, 1, 2, 3], [4, 5, 6, 7]]
    assert settings['unique_balanced_partitions'] == 35
    for key in ('new_environment_samples', 'new_model_samples', 'training_update_attempts', 'new_control_games'):
        assert settings[key] == 0
