"""Summarize frozen V41 policies, literal resources and exploratory route rules."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
from time import perf_counter

DEFAULT_RESULTS = Path(__file__).resolve().parents[1] / 'reports/rate_distortion_v41'
QUALITY_TOLERANCE = 1e-10
CALIBRATION_TOLERANCE = 1e-6


def _policy_summary(row):
    return {name: row[name] for name in (
        'root_value', 'root_regret', 'predicted_root_value', 'root_bias',
        'relative_absolute_root_bias', 'maximum_state_regret',
        'maximum_absolute_state_bias', 'legal_q_error_inf', 'terminal_prediction')}


def _comparison(candidate, control):
    candidate_correct = candidate['root_regret'] <= QUALITY_TOLERANCE
    control_correct = control['root_regret'] <= QUALITY_TOLERANCE
    return {
        'root_regret_change': candidate['root_regret'] - control['root_regret'],
        'root_bias_change': candidate['root_bias'] - control['root_bias'],
        'absolute_root_bias_change': abs(candidate['root_bias']) - abs(control['root_bias']),
        'relative_absolute_root_bias_change': candidate['relative_absolute_root_bias'] - control['relative_absolute_root_bias'],
        'root_policy_repaired': not control_correct and candidate_correct,
        'root_policy_new_error': control_correct and not candidate_correct,
        'root_regret_improved': candidate['root_regret'] < control['root_regret'] - QUALITY_TOLERANCE,
        'root_regret_worsened': candidate['root_regret'] > control['root_regret'] + QUALITY_TOLERANCE,
        'changed_policy_states': [index for index, (new, old) in enumerate(zip(candidate['policy'], control['policy'])) if new != old],
    }


def summarize(summary, cases):
    rows, fit_checks = [], []
    acquisition = {'rows': 0, 'outcomes': 0, 'acquisition_seconds': 0., 'metric_seconds': 0., 'exact_solve_seconds': 0.}
    stages = defaultdict(list)
    for case in cases:
        acquisition['rows'] += case['closure_counts']['exact_transition_row_calls']
        acquisition['outcomes'] += case['closure_counts']['exact_outcomes_enumerated']
        for name, value in case['costs'].items():
            acquisition[name] = acquisition.get(name, 0.) + value
            stages['shared_' + name].append(value)
        for name in ('readout_seconds', 'independent_evaluation_seconds'):
            stages['exact_tie_policy_' + name].append(case['exact_tie_policy'][name])
        for units, condition in case['conditions'].items():
            primary, controls = condition['primary'], condition['controls']
            deployment, comparison = primary['deployment'], condition['compiled_comparison']
            contrasts = {name: _comparison(primary, controls[name]) for name in ('flat', 'clamp')}
            numeric_smaller = deployment['complete_numeric_array_bytes'] < case['ground_model_array_bytes']
            preparation_faster = primary['one_query_prepare_seconds'] < case['exact_one_query_prepare_seconds']
            for beta in condition['all_fixed_betas']:
                structure = beta['layers']
                fit_checks.append({'case': case['case'], 'units': units, 'beta': beta['beta'],
                    'cross_layer_mass_max': structure['cross_layer_mass_max'],
                    'full_cross_layer_mass_max': structure['full_cross_layer_mass_max'],
                    'posterior_block_mass_max': structure['posterior_block_mass_max'],
                    'terminal_row_pure': structure['terminal_row_pure'],
                    'terminal_code_unique': structure['terminal_code_unique'],
                    'decoder_layer_consistent': structure['decoder_layer_consistent'],
                    'terminal_prediction': beta['terminal_prediction'],
                    'two_step_check_error': beta['two_step_check_error']})
                for name in ('readout_seconds', 'independent_evaluation_seconds'):
                    stages['all_fixed_beta_' + name].append(beta[name])
            for name, value in condition['experiment_costs'].items():
                stages[name].append(value)
            for control in controls.values():
                for name in ('readout_seconds', 'independent_evaluation_seconds'):
                    stages['retained_control_' + name].append(control[name])
            for name in ('readout_seconds', 'independent_evaluation_seconds'):
                stages['adaptive_final_' + name].append(condition['adaptive'][name])
            rows.append({
                'case': case['case'], 'units': units, 'primary_beta': condition['primary_beta'],
                'optimal_root_value': case['exact_root_optimum'],
                'exact_tie_policy': _policy_summary(case['exact_tie_policy']),
                'layered': _policy_summary(primary),
                'controls': {name: {**_policy_summary(controls[name]),
                    'changes_from_v40_strict_argmax': controls[name]['changes_from_v40_strict_argmax']} for name in ('flat', 'clamp')},
                'layered_minus_control': contrasts,
                'active_codes': primary['active_codes'], 'information_bits': primary['information_bits'],
                'information_fraction': primary['information_fraction'],
                'layers': primary['layers'], 'two_step_check_error': primary['two_step_check_error'],
                'original_unit_abstract_residual': primary['original_unit_abstract_residual'],
                'solve_updates': primary['solve_updates'],
                'resources': {
                    'operator_array_bytes': deployment['array_bytes'],
                    'legal_readout_array_bytes': deployment['legal_readout_array_bytes'],
                    'u_array_bytes': deployment['u_array_bytes'],
                    'complete_numeric_array_bytes': deployment['complete_numeric_array_bytes'],
                    'ground_model_array_bytes': case['ground_model_array_bytes'],
                    'exact_policy_cache_array_bytes': case['exact_policy_cache_array_bytes'],
                    'exact_policy_and_values_cache_array_bytes': case['exact_policy_and_values_cache_array_bytes'],
                    'layered_fixed_policy_cache_array_bytes': deployment['fixed_policy_cache_array_bytes'],
                    'retained_flat_operator_plus_readout_and_u_bytes': controls['flat']['v40_operator_plus_readout_and_u_bytes'],
                    'operator_and_readout_archive_bytes': deployment['operator_and_readout_archive_bytes'],
                    'diagnostic_witness_archive_bytes': deployment['diagnostic_witness_archive_bytes'],
                    'state_board_lookup_included': deployment['state_board_lookup_included'],
                    'numeric_model_smaller_than_ground': numeric_smaller},
                'one_query_costs': {
                    'candidate_prepare_seconds': primary['one_query_prepare_seconds'],
                    'exact_DP_prepare_seconds': case['exact_one_query_prepare_seconds'],
                    'candidate_minus_exact_DP_seconds': primary['one_query_prepare_seconds'] - case['exact_one_query_prepare_seconds'],
                    'candidate_prepare_faster': preparation_faster,
                    'primary_fit_seconds': primary['fit_seconds'], 'primary_compile_seconds': primary['compile_seconds'],
                    'primary_solve_seconds': primary['solve_seconds'], 'primary_readout_seconds': primary['readout_seconds'],
                    'primary_embedding_seconds': primary['embedding_seconds'], 'primary_grounding_seconds': primary['grounding_seconds']},
                'resource_joint_condition': numeric_smaller and preparation_faster,
                'snapshots_compared': comparison['snapshots'],
                'action_disagreement_events': len(comparison['action_disagreement_events']),
                'maximum_snapshot_root_value_change': max((abs(event['root_value_change']) for event in comparison['action_disagreement_events']), default=0.),
                'maximum_snapshot_state_value_change': max((event['maximum_state_value_change'] for event in comparison['action_disagreement_events']), default=0.),
                'maximum_snapshot_update_error': comparison['max_update_error'],
                'maximum_snapshot_ground_error': comparison['max_ground_error'],
                'adaptive_secondary': {**_policy_summary(condition['adaptive']), 'beta': condition['adaptive']['beta'],
                    'snapshot_backup_units': condition['adaptive']['snapshot_backup_units'],
                    'paid_backup_units': condition['adaptive']['paid_backup_units']},
                'experiment_costs': condition['experiment_costs'],
            })
    six = len(rows) == 6 and len(cases) == 3
    quality = six and all(row['layered']['root_regret'] <= QUALITY_TOLERANCE for row in rows)
    calibration_changes = [row['layered_minus_control']['flat']['relative_absolute_root_bias_change'] for row in rows]
    calibration = six and all(value <= CALIBRATION_TOLERANCE for value in calibration_changes) and any(value < -CALIBRATION_TOLERANCE for value in calibration_changes)
    joint = sum(row['resource_joint_condition'] for row in rows)
    paid_stages = {name: math.fsum(values) for name, values in stages.items()}
    paid_sum = math.fsum(paid_stages.values())
    operational = {
        'six_primary_beta10_conditions': six and all(row['primary_beta'] == 10. for row in rows),
        'all_five_betas_retained': len(fit_checks) == 30 and all([beta['beta'] for beta in condition['all_fixed_betas']] == [6., 7., 8., 9., 10.] for case in cases for condition in case['conditions'].values()),
        'acquisition_75_rows_334_outcomes': acquisition['rows'] == 75 and acquisition['outcomes'] == 334,
        'all_layer_and_terminal_invariants': all(row['cross_layer_mass_max'] == row['full_cross_layer_mass_max'] == row['posterior_block_mass_max'] == row['terminal_prediction'] == 0.
            and row['terminal_row_pure'] and row['terminal_code_unique'] and row['decoder_layer_consistent'] for row in fit_checks),
        'all_two_step_checks': all(row['two_step_check_error'] <= 1e-12 for row in fit_checks),
        'all_snapshot_numerical_checks': all(row['maximum_snapshot_update_error'] <= 1e-12 and row['maximum_snapshot_ground_error'] <= 1e-12 for row in rows),
        'fresh_process_valid': summary['fresh_process_replay']['valid'],
        'new_sampled_environment_draws_zero': summary['new_sampled_environment_draws'] == 0,
    }
    return {
        'schema': 'acfqp.rate_distortion_layered_analysis.v41', 'rows': rows,
        'reconstruction_acquisition': acquisition,
        'total_compared_snapshots': sum(row['snapshots_compared'] for row in rows),
        'total_action_disagreement_events': sum(row['action_disagreement_events'] for row in rows),
        'all_beta_structural_checks': fit_checks, 'fresh_process_replay': summary['fresh_process_replay'],
        'operational_checks': operational, 'operational_checks_passed': all(operational.values()),
        'quality_all_six': quality, 'calibration_no_worse_and_some_better': calibration,
        'resource_joint_condition_count': joint,
        'continue_efficiency_branch': quality and calibration and joint >= 1,
        'quality_changes': {control: {name: sum(row['layered_minus_control'][control][name] for row in rows)
            for name in ('root_policy_repaired', 'root_policy_new_error', 'root_regret_improved', 'root_regret_worsened')} for control in ('flat', 'clamp')},
        'calibration_changes': {control: {
            'improved_over_1e_minus6': sum(row['layered_minus_control'][control]['relative_absolute_root_bias_change'] < -CALIBRATION_TOLERANCE for row in rows),
            'worsened_over_1e_minus6': sum(row['layered_minus_control'][control]['relative_absolute_root_bias_change'] > CALIBRATION_TOLERANCE for row in rows)} for control in ('flat', 'clamp')},
        'paid_costs': {'recorded_disjoint_stages_seconds': paid_stages, 'recorded_stage_sum_seconds': paid_sum,
            'experiment_wall_seconds': summary['wall_seconds'], 'wall_minus_recorded_stages_seconds': summary['wall_seconds'] - paid_sum},
        'route_scope': 'Exploratory route decision using the predeclared beta10 candidate in all six fixed conditions; scientific failure remains a result. Clamp and adaptive outcomes are additional controls, not selectable replacements for the primary candidate.',
        'cost_scope': 'Measured stages are counted once. Case acquisition and distance are shared across units and betas; all performed fits, compiles, fixed solves, adaptive work and recorded readout/evaluation remain paid. The wall-time remainder includes unitemized work and serialization. One-query candidate/exact-DP comparisons use the runner\'s distinct preparation costs; retained V40 construction timings are not a contemporaneous speed comparison. Numeric payload, archives and diagnostic witnesses are separate; board-to-state lookup is excluded equally. Repeating a fixed task can use a cached policy without another backup.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results-dir', type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    started = perf_counter()
    summary = json.loads((args.results_dir / 'summary.json').read_text())
    cases = [json.loads((args.results_dir / filename).read_text()) for filename in summary['case_files']]
    result = summarize(summary, cases)
    result['analysis_seconds'] = perf_counter() - started
    with (args.results_dir / 'analysis.json').open('x', encoding='utf-8') as writer:
        json.dump(result, writer, indent=2, allow_nan=False)
        writer.write('\n')
    print(json.dumps({name: result[name] for name in ('operational_checks_passed', 'quality_all_six',
        'calibration_no_worse_and_some_better', 'resource_joint_condition_count', 'continue_efficiency_branch',
        'total_compared_snapshots', 'total_action_disagreement_events')}, indent=2))


if __name__ == '__main__':
    main()
