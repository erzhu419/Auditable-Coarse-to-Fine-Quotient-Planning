"""Summarize retained V69 generation, correctness, and complete method costs."""
from collections import Counter,defaultdict
import argparse
import json
from pathlib import Path
from time import perf_counter


def summed(rows):
    result=Counter()
    for row in rows:result.update({k:v for k,v in row.items() if type(v) in (int,float)})
    return dict(result)


def analyze(directory):
    started=perf_counter();manifest=json.loads((directory/'manifest.json').read_text())
    records=[json.loads(line) for line in (directory/'targets.jsonl').read_text().splitlines()]
    cases=[r for r in records if r['status']=='complete']
    complete=manifest['status']=='complete' and len(cases)==len(records)==32
    source_fee=manifest['acquisition']['seconds']+manifest['rule']['fit_seconds']
    result=dict(complete=complete,declared_targets=32,completed_targets=len(cases),
        limited_targets=[r['case'] for r in records if r['status']!='complete'],
        rule=manifest['rule'],source_acquisition=manifest['acquisition'],
        source_semantics_reference=manifest['source_semantics_reference'],arms={})
    if not cases:
        raise ValueError('no completed target models; inspect retained resource failures')
    for variant in ('FULL','COMPOSED'):
        costs=[r['arms'][variant]['costs'] for r in cases]
        audits=[r['arms'][variant]['audit'] for r in cases]
        queries=[q for a in audits for q in a['queries'].values()]
        roots=[root for q in queries for root in q['root_metrics']]
        levels=defaultdict(Counter);novel=defaultdict(Counter)
        for a in audits:
            for h,row in a['by_horizon'].items():
                levels[h].update({k:v for k,v in row.items() if k!='largest_group'})
            for h,row in a['novel_semantics'].items():novel[h].update(row)
        construction_use=sum(c['times']['total'] for c in costs)
        routing=sum(r['portable'].get('routing_seconds' if variant=='COMPOSED' else 'full_routing_seconds',0.) for r in cases)
        result['arms'][variant]=dict(scientifically_correct_targets=sum(a['scientific_correct'] for a in audits),
            construction=summed(c['construction'] for c in costs),planning=summed(c['planning_counts'] for c in costs),
            model_bytes=sum(c['model_bytes'] for c in costs),by_horizon={h:dict(v) for h,v in sorted(levels.items())},
            novel_semantics={h:dict(v) for h,v in sorted(novel.items())},
            maximum_joint_total_variation=max(a['maximum_joint_total_variation'] for a in audits),
            maximum_value_loss=max(q['maximum_value_loss'] for q in queries),
            maximum_metric_prediction_error=max(q['maximum_metric_prediction_error'] for q in queries),
            strict_max_lex_action_mismatches=sum(q['strict_max_lex_action_mismatches'] for q in queries),
            root_queries=len(roots),optimal_executable_root_queries=sum(r['value_loss']<=1e-12 and r['actual']['unsupported']<=1e-12 for r in roots),
            strict_query_switches=summed(a['strict_query_switches'] for a in audits),
            times=dict(construction_and_14_queries=construction_use,matched_observation_routing=routing,
                source_inclusive_construction_and_queries=source_fee+construction_use,
                source_inclusive_with_routing=source_fee+construction_use+routing,
                stages=summed(c['times'] for c in costs),audit_seconds=sum(a['elapsed_seconds'] for a in audits)))
    full,composed=result['arms']['FULL'],result['arms']['COMPOSED']
    same_work=all(r['arms']['FULL']['costs']['construction'][key]==r['arms']['COMPOSED']['costs']['construction'][key]
        for r in cases for key in ('concrete_states','concrete_action_rows','concrete_successor_entries','h0_boards_generated'))
    preserved=complete and all(a['scientifically_correct_targets']==32 for a in result['arms'].values())
    portable=complete and all(r['portable']['passed'] for r in cases)
    higher_full=sum(v['candidate_active_cells'] for h,v in full['by_horizon'].items() if int(h)>1)
    higher_composed=sum(v['candidate_active_cells'] for h,v in composed['by_horizon'].items() if int(h)>1)
    result.update(policy_and_dynamics_preserved=preserved,portable_passed=portable,
        concrete_expansion_identical=same_work,higher_active_cells=dict(full=higher_full,composed=higher_composed),
        ratios=dict(active_states=composed['construction']['active_states']/full['construction']['active_states'],
            higher_active_states=higher_composed/higher_full,
            planning_action_rows=composed['planning']['state_action_rows']/full['planning']['state_action_rows'],
            model_bytes=composed['model_bytes']/full['model_bytes'],
            source_inclusive_construction_and_queries=composed['times']['source_inclusive_construction_and_queries']/full['times']['source_inclusive_construction_and_queries'],
            source_inclusive_with_routing=composed['times']['source_inclusive_with_routing']/full['times']['source_inclusive_with_routing']))
    result['finite_compositional_transfer_established']=preserved and portable
    result['finite_higher_compression_established']=preserved and portable and higher_composed<higher_full
    result['finite_total_cost_benefit_with_routing']=preserved and portable and result['ratios']['source_inclusive_with_routing']<1
    result['general_strategic_learning_solved']=False
    result['verification']=dict(ground_counts=summed(r['ground']['counts'] for r in cases),
        reference_counts=summed(r['ground']['reference_counts'] for r in cases),
        ground_seconds=sum(r['ground']['seconds'] for r in cases),
        reference_seconds=sum(r['ground']['reference_seconds'] for r in cases),
        portable_command_seconds=sum(r['portable']['command_seconds'] for r in cases),
        routing_counts=summed(r['portable'].get('routing_counts',{}) for r in cases))
    result['timing']=dict(runner_seconds=manifest['wall_seconds'],analysis_seconds_before_write=perf_counter()-started)
    result['scope']='Fixed source-supervised DSL, exact spawn teacher, new dense 2048 H3/H4 boards. Source fee is once per arm deployment; validation fees are separate. Both methods generate complete concrete support. Routing reconstructs contracts and is not constant-time encoding. Timing is a single descriptive comparison.'
    (directory/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('complete','policy_and_dynamics_preserved','portable_passed',
        'concrete_expansion_identical','higher_active_cells','ratios')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--input',type=Path,required=True)
    analyze(parser.parse_args().input)
