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
    baseline,causal=variants['BASELINE'],variants['CAUSAL']
    ratios=dict(active_states=causal['construction_counts']['active_states']/baseline['construction_counts']['active_states'],
        action_rows=causal['planning_counts']['state_action_rows']/baseline['planning_counts']['state_action_rows'],
        planning_outcomes=causal['planning_counts']['outcomes']/baseline['planning_counts']['outcomes'],
        model_bytes=causal['total_model_bytes']/baseline['total_model_bytes'],
        method_total_seconds=causal['method_total_seconds']/baseline['method_total_seconds'])
    repair_path=directory/'portable_repair.json'
    repair=json.loads(repair_path.read_text()) if repair_path.exists() else None
    portable=(complete and all(r['portable']['passed'] for r in rows)) or (
        complete and repair is not None and repair['passed']
        and [r['case'] for r in repair['cases']]==[r['case']['name'] for r in rows])
    correct=complete and baseline['valid_cases']==16 and causal['valid_cases']==16 and portable
    bridge=correct and ratios['active_states']<1 and ratios['action_rows']<1
    reference_counts,ground_counts,portable_planning,portable_prediction=Counter(),Counter(),Counter(),Counter()
    for row in rows:
        reference_counts.update(row['independent_ground']['reference_counts'])
        ground_counts.update(row['independent_ground']['construction_counts'])
        portable_planning.update(row['portable'].get('planning_counts',{}))
        portable_prediction.update(row['portable'].get('prediction_counts',{}))
    return dict(schema='acfqp.controlled_predictive_causal_analysis.v66',complete=complete,
        causal_correct_on_all_declared_states=correct,portable_models_verified=portable,
        structural_bridge_established=bridge,
        finite_joint_benefit_observed=bridge and ratios['model_bytes']<1 and ratios['method_total_seconds']<1,
        causal_over_baseline=ratios,variants=variants,
        per_case=[dict(name=r['case']['name'],forgotten=r['arms']['CAUSAL']['rule']['forgotten_ranks'],
            active_states={v:r['arms'][v]['construction_counts']['active_states'] for v in variants},
            reference_cells=r['independent_ground']['reference_quotient']['active_cells'],
            causal_valid=r['arms']['CAUSAL']['audit']['valid'],
            causal_errors=r['arms']['CAUSAL']['audit']['errors'],
            unsafe_valid=r['arms']['UNSAFE']['audit']['valid'],
            unsafe_witness=r['arms']['UNSAFE']['audit']['worst_counterexample']) for r in rows],
        accounting=dict(whole_runner_seconds=manifest['whole_runner_seconds'],
            portable_initial_failures=sum(not r['portable']['passed'] for r in rows),
            portable_repair_wall_seconds=repair['wall_seconds'] if repair else 0.,
            portable_repair_planning_counts={key:sum(r.get('planning_counts',{}).get(key,0)
                +r.get('additional_inprocess_planning_counts',{}).get(key,0) for r in repair['cases'])
                for key in causal['planning_counts']} if repair else {},
            independent_ground_counts=dict(ground_counts),reference_counts=dict(reference_counts),
            ground_construction_seconds=sum(r['independent_ground']['construction_seconds'] for r in rows),
            reference_seconds=sum(r['independent_ground']['reference_seconds'] for r in rows),
            oracle_quotient_seconds=sum(r['independent_ground']['reference_quotient']['construction_seconds'] for r in rows),
            portable_command_seconds=sum(r['portable']['command_wall_seconds'] for r in rows),
            portable_planning_counts=dict(portable_planning),portable_prediction_counts=dict(portable_prediction),
            random_samples=0,learned_updates=0,analysis_seconds_before_serialization=perf_counter()-started),
        limitations='Previously exposed finite roots, known mechanics, one timing run. The new structural rule is synthesized from each root without a ground closure; this is not a learned unknown-dynamics model or a general-game guarantee. Unsafe control failures are retained separately. Terminal folding is identical in the two primary arms.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_causal_v66')
    directory=parser.parse_args().output
    result=summarize(directory)
    with (directory/'analysis.json').open('x') as handle:
        json.dump(result,handle,indent=2,allow_nan=False);handle.write('\n')
    print(json.dumps({k:result[k] for k in ('complete','causal_correct_on_all_declared_states',
        'structural_bridge_established','finite_joint_benefit_observed','causal_over_baseline')}))
