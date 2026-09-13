"""Read retained V68 evidence; no additional fit, planning, or environment calls."""
from collections import Counter, defaultdict
import argparse
import json
import math
from pathlib import Path
from time import perf_counter


def analyze(directory):
    started = perf_counter()
    manifest = json.loads((directory/'manifest.json').read_text())
    cases = [json.loads(line) for line in (directory/'targets.jsonl').read_text().splitlines()]
    complete = manifest['status']=='complete' and len(cases)==manifest['target_cases']==24
    result = dict(complete=complete, target_cases=len(cases), source=manifest['source'], arms={},
                  source_active_overlap=sum(c['source_active_overlap'] for c in cases))
    support = defaultdict(Counter)
    for case in cases:
        for horizon, row in case['arms']['QUOTIENT']['audit']['source_support']['by_horizon'].items():
            support[horizon].update(row)
    result['source_semantic_support_by_horizon'] = {h:dict(row, fraction=row['source_supported_states']/row['active_states'])
        for h,row in sorted(support.items())}
    result['source_supported_target_roots'] = sum(root['source_supported'] for case in cases
        for root in case['arms']['QUOTIENT']['audit']['source_support']['roots'])
    for variant in ('QUOTIENT','RAW'):
        costs = manifest['models'][variant]
        roots, query_stats, levels = [], defaultdict(list), defaultdict(Counter)
        strict, model_errors, audit_counts = Counter(), Counter(), Counter()
        exact_cases = 0
        for case in cases:
            audit = case['arms'][variant]['audit']
            exact_cases += audit['exact_controlled_equivalence']
            strict.update({k:v for k,v in audit['strict_query_switches'].items() if k!='preserved'})
            model_errors.update(audit['controlled_model_errors']); audit_counts.update(audit['counts'])
            for name, row in audit['queries'].items():
                roots.extend(row['root_metrics']); query_stats[name].extend(row['root_metrics'])
                for h, level in row['by_horizon'].items():
                    levels[h].update({k:v for k,v in level.items() if k in
                        ('states','action_errors','illegal_or_missing_actions','value_loss_sum','unsupported_probability_sum')})
        def means(rows):
            return dict(root_queries=len(rows),
                mean_value=math.fsum(r['actual']['value'] for r in rows)/len(rows),
                mean_value_loss=math.fsum(r['value_loss'] for r in rows)/len(rows),
                maximum_value_loss=max(r['value_loss'] for r in rows),
                optimal_root_queries=sum(abs(r['value_loss'])<=1e-12 and r['actual']['unsupported']<=1e-12 for r in rows),
                mean_unsupported_probability=math.fsum(r['actual']['unsupported'] for r in rows)/len(rows),
                root_queries_with_unsupported=sum(r['actual']['unsupported']>1e-12 for r in rows),
                mean_natural_failure=math.fsum(r['actual']['natural_failure'] for r in rows)/len(rows),
                mean_success=math.fsum(r['actual']['success'] for r in rows)/len(rows),
                maximum_absolute_prediction_error=max(abs(r['prediction_error']) for r in rows if r['prediction_error'] is not None))
        result['arms'][variant] = dict(costs=costs, roots=means(roots), per_query={n:means(r) for n,r in query_stats.items()},
            by_horizon={h:dict(v) for h,v in levels.items()}, exact_controlled_cases=exact_cases,
            strict_query_switches=dict(strict), controlled_model_errors=dict(model_errors), audit_counts=dict(audit_counts),
            audit_seconds=sum(c['arms'][variant]['audit']['elapsed_seconds'] for c in cases),
            target_audit_encoding_seconds=sum(c['arms'][variant]['encoding_seconds'] for c in cases))
    paired = []
    for case in cases:
        for name, q in case['arms']['QUOTIENT']['audit']['queries'].items():
            r = case['arms']['RAW']['audit']['queries'][name]
            paired.extend(a['actual']['value']-b['actual']['value'] for a,b in zip(q['root_metrics'], r['root_metrics']))
    result['quotient_minus_raw'] = dict(mean_value_difference=math.fsum(paired)/len(paired),
        better=sum(d>1e-12 for d in paired), tied=sum(abs(d)<=1e-12 for d in paired), worse=sum(d< -1e-12 for d in paired))
    result['exact_transfer_established'] = complete and all(a['exact_controlled_cases']==24
        and a['costs']['portable']['passed'] for a in result['arms'].values())
    result['quotient_exact_transfer_established'] = complete and result['arms']['QUOTIENT']['exact_controlled_cases']==24 and result['arms']['QUOTIENT']['costs']['portable']['passed']
    result['general_strategic_learning_solved'] = False
    result['counts'] = dict(target_ground=dict(sum((Counter(c['ground']['counts']) for c in cases),Counter())),
        reference=dict(sum((Counter(c['ground']['reference_counts']) for c in cases),Counter())))
    result['times'] = dict(runner_seconds=manifest['wall_seconds'],
        source_teacher_seconds=manifest['source']['teacher_seconds'],
        ground_seconds=sum(c['ground']['seconds'] for c in cases),
        reference_seconds=sum(c['ground']['reference_seconds'] for c in cases),
        target_support_seconds=sum(c['ground']['support_seconds'] for c in cases),
        analysis_seconds_before_write=perf_counter()-started)
    result['scope'] = 'Source-only frozen known-mechanics-teacher distillation, fixed dense-board H3 cohort and 14 correlated queries. Exact semantic support is an expressibility diagnostic, not a bound on achievable policy reward. Abort probability is distinct from natural loss. Different policy quality precludes a performance-preserving speedup claim.'
    (directory/'analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ('complete','source_supported_target_roots','source_semantic_support_by_horizon','quotient_minus_raw','quotient_exact_transfer_established')}, indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    analyze(parser.parse_args().input)
