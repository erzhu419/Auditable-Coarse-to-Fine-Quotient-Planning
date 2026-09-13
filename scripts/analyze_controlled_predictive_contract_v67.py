"""Summarize structural compression separately from arithmetic timing gains."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from time import perf_counter


def summarize(directory):
    started=perf_counter()
    manifest=json.loads((directory/'manifest.json').read_text())
    rows=[json.loads(line) for line in (directory/'cases.jsonl').read_text().splitlines()]
    complete=(manifest['status']=='complete' and len(rows)==16
        and [r['case']['name'] for r in rows]==[c['name'] for c in manifest['cases']])
    variants={}
    for variant in manifest['variants']:
        construction,planning,audit=Counter(),Counter(),Counter()
        for row in rows:
            arm=row['arms'][variant]
            construction.update(arm['construction_counts']);planning.update(arm['planning_counts'])
            audit.update(arm['audit']['counts'])
        variants[variant]=dict(construction_counts=dict(construction),planning_counts=dict(planning),
            audit_counts=dict(audit),valid_cases=sum(r['arms'][variant]['audit']['valid'] for r in rows),
            structural_valid_cases=sum(r['arms'][variant]['audit']['structural_valid'] for r in rows),
            total_model_bytes=sum(r['arms'][variant]['model_bytes'] for r in rows),
            method_total_seconds=sum(r['arms'][variant]['times']['total_seconds'] for r in rows),
            audit_seconds=sum(r['arms'][variant]['audit']['elapsed_seconds'] for r in rows),
            strict_switches=sum(r['arms'][variant]['audit']['strict_query_switches']['required'] for r in rows),
            violated_switches=sum(r['arms'][variant]['audit']['strict_query_switches']['violations'] for r in rows))
    baseline,contract=variants['BASELINE'],variants['CONTRACT']
    ratios=dict(active_states=contract['construction_counts']['active_states']/baseline['construction_counts']['active_states'],
        action_rows=contract['planning_counts']['state_action_rows']/baseline['planning_counts']['state_action_rows'],
        planning_outcomes=contract['planning_counts']['outcomes']/baseline['planning_counts']['outcomes'],
        model_bytes=contract['total_model_bytes']/baseline['total_model_bytes'],
        method_total_seconds=contract['method_total_seconds']/baseline['method_total_seconds'])
    portable=complete and all(r['portable']['passed'] for r in rows)
    correct=complete and baseline['valid_cases']==16 and contract['valid_cases']==16 and portable
    bridge=correct and ratios['active_states']<1 and ratios['action_rows']<1
    reference_counts,ground_counts,portable_planning,portable_prediction=Counter(),Counter(),Counter(),Counter()
    for row in rows:
        reference_counts.update(row['independent_ground']['reference_counts'])
        ground_counts.update(row['independent_ground']['construction_counts'])
        portable_planning.update(row['portable'].get('planning_counts',{}))
        portable_prediction.update(row['portable'].get('prediction_counts',{}))
    return dict(schema='acfqp.controlled_predictive_contract_analysis.v67',complete=complete,
        contract_correct_on_all_declared_states=correct,portable_models_verified=portable,
        structural_bridge_established=bridge,
        finite_joint_benefit_observed=bridge and ratios['model_bytes']<1 and ratios['method_total_seconds']<1,
        contract_over_baseline=ratios,variants=variants,
        per_case=[dict(name=r['case']['name'],contract_states=r['arms']['CONTRACT']['construction_counts'].get('contract_states',0),
            active_states={v:r['arms'][v]['construction_counts']['active_states'] for v in variants},
            reference_cells=r['independent_ground']['reference_quotient']['active_cells'],
            contract_valid=r['arms']['CONTRACT']['audit']['valid'],
            contract_errors=r['arms']['CONTRACT']['audit']['errors'],
            unsafe_valid=r['arms']['UNSAFE']['audit']['valid'],
            unsafe_witness=r['arms']['UNSAFE']['audit']['worst_counterexample']) for r in rows],
        accounting=dict(whole_runner_seconds=manifest['whole_runner_seconds'],
            independent_ground_counts=dict(ground_counts),reference_counts=dict(reference_counts),
            ground_construction_seconds=sum(r['independent_ground']['construction_seconds'] for r in rows),
            reference_seconds=sum(r['independent_ground']['reference_seconds'] for r in rows),
            oracle_quotient_seconds=sum(r['independent_ground']['reference_quotient']['construction_seconds'] for r in rows),
            portable_command_seconds=sum(r['portable']['command_wall_seconds'] for r in rows),
            portable_planning_counts=dict(portable_planning),portable_prediction_counts=dict(portable_prediction),
            random_samples=0,learned_updates=0,analysis_seconds_before_serialization=perf_counter()-started),
        limitations='Previously exposed finite roots, known mechanics, one timing run. Action contracts are derived locally from known mechanics without a ground closure. The result is not unknown-dynamics learning or a general-game guarantee. Unsafe control failures are retained separately. Terminal folding is identical in the two primary arms.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_contract_v67')
    directory=parser.parse_args().output
    result=summarize(directory)
    with (directory/'analysis.json').open('x') as handle:
        json.dump(result,handle,indent=2,allow_nan=False);handle.write('\n')
    print(json.dumps({k:result[k] for k in ('complete','contract_correct_on_all_declared_states',
        'structural_bridge_established','finite_joint_benefit_observed','contract_over_baseline')}))
