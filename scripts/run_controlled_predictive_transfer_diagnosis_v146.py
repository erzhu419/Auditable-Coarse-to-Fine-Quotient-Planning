"""Diagnose retained paired-label noise and training support without new samples."""
import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path
import shutil
import sys
from time import perf_counter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import analyze_controlled_predictive_paired_advantage_v144 as features
from acfqp.science.controlled_predictive_label_noise_v146 import label_diagnostics
from acfqp.science.controlled_predictive_feature_transfer_v146 import TrainingGeometry

SOURCE=ROOT/'reports/controlled_predictive_coverage_expansion_v145'
LIVES,QUERIES=range(4),features.QUERIES
METHODS=('PRIOR','REPLAY','UPDATED')
ORIGINS=('OLD','NEW')


def read(path):return json.loads(Path(path).read_text())
def save(path,value):Path(path).write_text(json.dumps(value,separators=(',',':'))+'\n')
def mean(values):
    values=[v for v in values if v is not None]
    return math.fsum(values)/len(values) if values else None
def utility(components,query):
    q=QUERIES[query]
    return q['reward_weight']*components[0]-q['failure_penalty']*components[1]+q['goal_bonus']*components[2]


def settings():
    return dict(lives=list(LIVES),queries=QUERIES,origins=list(ORIGINS),methods=list(METHODS),
        primary_origin='NEW',heldout_replicas=[4,5,6,7],roots_per_game=4,suffixes=8,
        fixed_halves=[[0,1,2,3],[4,5,6,7]],unique_balanced_partitions=35,
        noise='unbiased per-suffix sample variance / 8; scalar paired utility',
        corrected_error='squared error minus mean noise variance, untrimmed',
        geometry_rank_relative_tolerance=1e-10,geometry_roundoff_relative_tolerance=1e-8,
        aggregation='roots within game, games within life, then four lives equally',
        new_environment_samples=0,new_model_samples=0,training_update_attempts=0,new_control_games=0)


def prepare():
    run,analysis,capsule=map(read,(SOURCE/'run.json',SOURCE/'analysis.json',SOURCE/'source_capsule.json'))
    if not(run['status']=='complete' and analysis['complete'] and analysis['primary_complete']):
        raise ValueError('V145 must be complete before retained-data diagnosis')
    old_dir=Path(capsule['prior_examples_ref']).parent;old_source=read(old_dir/'source_capsule.json')
    examples=dict(OLD=read(capsule['prior_examples_ref'])['examples'],NEW=read(SOURCE/'examples.json')['examples'])
    source_cohorts=dict(OLD=read(old_source['cohort_ref'])['roots'],NEW=read(SOURCE/'cohort.json')['roots'])
    selected={origin:[e for e in rows if e['split']=='VALIDATION'] for origin,rows in examples.items()}
    for origin,rows in selected.items():
        roster=Counter((r['life'],r['query'],r['replica']) for r in rows)
        if roster!=Counter({(l,q,r):4 for l in LIVES for q in QUERIES for r in range(4,8)}):
            raise ValueError('held-out original-game roster differs')
        rows.sort(key=lambda e:(e['life'],list(QUERIES).index(e['query']),e['replica'],e['slot']))
    traces=dict(OLD=[dict(life=s['life'],path=s['paired_consequences_trace']) for s in old_source['snapshots']],
        NEW=[dict(life=s['life'],path=str(SOURCE/s['consequences_trace'])) for s in run['acquisition_lifecycles']])
    return run,examples,source_cohorts,selected,traces


def retained_labels(cohorts,selected,traces):
    labels={};counts=Counter();checks=dict(paired_identity=True,terminal_labels=True,retained_target_means=True)
    for origin in ORIGINS:
        examples={e['root_id']:e for e in selected[origin]}
        roots={r['root_id']:r for r in cohorts[origin] if r['root_id'] in examples}
        groups={key:{} for key in roots}
        for trace in traces[origin]:
            counts['compressed_trace_bytes_read']+=Path(trace['path']).stat().st_size
            with gzip.open(trace['path'],'rt') as stream:
                for line in stream:
                    row=json.loads(line);counts['paired_records_scanned']+=1
                    counts['physical_branch_records_scanned']+=len(row['branches'])
                    if row['root_id'] not in roots:continue
                    root=roots[row['root_id']];suffix=row['suffix']
                    checks['paired_identity']&=(root['life']==trace['life'] and suffix in range(8)
                        and row['seed']==root['suffix_seeds'][suffix] and row['continuation']=='H2'
                        and suffix not in groups[row['root_id']])
                    a,b=(row['branches'][root['choices'][m]] for m in ('H1_CONT','H2'))
                    checks['terminal_labels']&=all(c['result']['status'] in ('WON','LOST') and c['seed']==row['seed'] for c in (a,b))
                    components=[a['result']['components'][k]-b['result']['components'][k] for k in range(3)]
                    value=utility(components,root['query'])
                    checks['terminal_labels']&=features.close(value,a['result']['utility']-b['result']['utility'])
                    groups[row['root_id']][suffix]=(value,components)
                    counts['paired_records_selected']+=1
                    counts['selected_physical_branch_records']+=len({root['choices']['H1_CONT'],root['choices']['H2']})
        for key,rows in groups.items():
            if sorted(rows)!=list(range(8)):raise ValueError('incomplete held-out suffix roster')
            labels[origin,key]=[rows[i][0] for i in range(8)]
            averaged=[mean(rows[i][1][k] for i in range(8)) for k in range(3)]
            checks['retained_target_means']&=all(features.close(a,b) for a,b in zip(averaged,examples[key]['target_total']))
    return labels,dict(counts),checks


def aggregate(rows):
    """Preserve game/life denominators; no independent-root inference."""
    metrics={}
    def root_values(row):
        d=row['label_diagnostics'];result=dict(mean_noise_variance=d['mean_noise_variance'],
            label_mean_squared=d['mean']**2,same_action=float(row['candidate_action']==row['baseline_action']),
            zero_feature=float(not row['difference']),all_suffixes_zero=float(all(v==0 for v in row['labels'])))
        for block in ('fixed_halves','partitions'):
            for name in ('sign_agreement','gate_agreement','positive_both','negative_both','mixed_sign','zero_both','one_zero'):
                result[block+'.'+name]=float(d[block][name])
        for method in METHODS:
            for name in ('squared_error','noise_adjusted_squared_error','cross_half_squared_error','select_h1'):
                result[method+'.'+name]=float(d['methods'][method][name])
            for name in ('covered_norm_fraction','projection_fraction','max_abs_cosine'):
                result[method+'.'+name]=row['geometry'][method][name] if row['difference'] else None
            result[method+'.orthogonal_nonzero']=float(row['geometry'][method]['orthogonal_to_training']) if row['difference'] else None
        return result
    for row in rows:metrics[row['root_id']]=root_values(row)
    keys=next(iter(metrics.values())).keys();lives=[]
    for life in LIVES:
        games=[]
        for replica in range(4,8):
            group=[r for r in rows if r['life']==life and r['replica']==replica]
            games.append(dict(replica=replica,roots=len(group),nonzero_features=sum(bool(r['difference']) for r in group),
                metrics={k:mean(metrics[r['root_id']][k] for r in group) for k in keys}))
        lives.append(dict(life=life,games=games,roots=sum(g['roots'] for g in games),
            nonzero_features=sum(g['nonzero_features'] for g in games),
            metrics={k:mean(g['metrics'][k] for g in games) for k in keys}))
    return dict(roots=len(rows),nonzero_features=sum(bool(r['difference']) for r in rows),lifecycles=lives,
        metrics={k:mean(l['metrics'][k] for l in lives) for k in keys})


def snapshot(directory):
    files=[Path(__file__),ROOT/'specs/TRANSFER_DIAGNOSIS_V146.md',Path(features.__file__)]
    files.extend(ROOT/f'src/acfqp/science/controlled_predictive_{name}_v146.py'
        for name in ('label_noise','feature_transfer'))
    files.extend(ROOT/f'tests/test_{name}_v146.py' for name in (
        'controlled_predictive_label_noise','controlled_predictive_feature_transfer',
        'run_controlled_predictive_transfer_diagnosis','verify_controlled_predictive_transfer_diagnosis'))
    files.append(ROOT/'scripts/verify_controlled_predictive_transfer_diagnosis_v146.py')
    for path in files:
        target=directory/'source'/path.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)


def run(directory):
    started=perf_counter();directory=directory.resolve();directory.mkdir(parents=True,exist_ok=False)
    source_run,examples,cohorts,selected,traces=prepare()
    frozen=dict(schema='acfqp.transfer_diagnosis.v146.inputs',status='frozen',settings=settings(),
        source_run_ref=str(SOURCE/'run.json'),source_analysis_ref=str(SOURCE/'analysis.json'),
        inherited_costs_ref=str(SOURCE/'analysis.json')+'#costs-and-inherited_work',traces=traces,
        cohort=[dict(origin=o,**{k:e[k] for k in ('root_id','life','query','replica','slot')}) for o in ORIGINS for e in selected[o]])
    save(directory/'frozen_inputs.json',frozen);snapshot(directory)
    labels,read_costs,checks=retained_labels(cohorts,selected,traces)
    differences={(origin,e['root_id']):features.feature_difference(e['candidate_after'],e['baseline_after'])
        for origin in ORIGINS for e in examples[origin]}
    histories={l['life']:l for l in source_run['lifecycles']};geometry={};groups=[];weights={};predictions={}
    for life in LIVES:
        for query in QUERIES:
            train={origin:[e for e in examples[origin] if e['life']==life and e['query']==query and e['split']=='TRAIN'] for origin in ORIGINS}
            for method in METHODS:
                tags=[('OLD',e) for e in train['OLD']]+([('NEW',e) for e in train['NEW']] if method=='UPDATED' else [])
                vectors=[differences[o,e['root_id']] for o,e in tags]
                key=(life,query,method)
                geometry[key]=geometry[life,query,'PRIOR'] if method=='REPLAY' else TrainingGeometry(vectors)
                groups.append(dict(life=life,query=query,method=method,training_roots=[e['root_id'] for _,e in tags],
                    training_differences=[sorted(d.items()) for d in vectors]))
                qdata=histories[life]['queries'][query];payload=read(SOURCE/qdata['models'][method]['model_ref'])
                weights[key]={int(row[0]):row[1:] for row in payload['weights']}
                for origin in ORIGINS:
                    predictions[origin,life,query,method]={r['root_id']:r['estimated_advantage'] for r in qdata['validation'][origin][method]}
    save(directory/'geometry_inputs.json',dict(groups=groups))
    rows=[];checks.update(frozen_predictions=True,source_mse_reproduced=True)
    for origin in ORIGINS:
        for example in selected[origin]:
            life,query,key=example['life'],example['query'],example['root_id'];difference=differences[origin,key]
            estimates={m:predictions[origin,life,query,m][key] for m in METHODS}
            for method in METHODS:
                tail=features.predict_difference(difference,weights[life,query,method])
                recomposed=utility([example['immediate_difference']+tail[0],*tail[1:]],query)
                checks['frozen_predictions']&=features.close(estimates[method],recomposed)
            rows.append(dict(origin=origin,**{k:example[k] for k in ('root_id','life','query','replica','slot','candidate_action','baseline_action')},
                labels=labels[origin,key],difference=sorted(difference.items()),
                label_diagnostics=label_diagnostics(labels[origin,key],estimates),
                geometry={m:geometry[life,query,m].measure(difference) for m in METHODS}))
    summary={o:{q:aggregate([r for r in rows if r['origin']==o and r['query']==q]) for q in QUERIES} for o in ORIGINS}
    source_analysis=read(SOURCE/'analysis.json')
    for origin in ORIGINS:
        for query in QUERIES:
            for method in METHODS:
                checks['source_mse_reproduced']&=features.close(summary[origin][query]['metrics'][method+'.squared_error'],
                    source_analysis['diagnostics'][query][origin]['VALIDATION'][method]['utility_mse'])
    geometry_counts=Counter()
    for key,obj in geometry.items():
        if key[2]!='REPLAY':geometry_counts.update(obj.counts)
    costs=dict(**read_costs,**geometry_counts,feature_differences_computed=len(differences),
        frozen_prediction_checks=len(rows)*len(METHODS),diagnostic_roots=len(rows),
        balanced_partitions_evaluated=len(rows)*35,new_environment_samples=0,new_model_samples=0,
        training_update_attempts=0,new_control_games=0)
    save(directory/'rows.json',dict(rows=rows))
    result=dict(schema='acfqp.transfer_diagnosis.v146.analysis',complete=all(checks.values()),checks=checks,
        settings=settings(),summary=summary,costs=costs,inherited_costs_ref=frozen['inherited_costs_ref'],seconds=perf_counter()-started)
    save(directory/'analysis.json',result)
    print(json.dumps(dict(complete=result['complete'],failed=[k for k,v in checks.items() if not v],costs=costs,seconds=result['seconds'])),flush=True)
    if not result['complete']:raise ValueError('retained-data diagnosis did not reproduce source evidence')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/controlled_predictive_transfer_diagnosis_v146')
    run(parser.parse_args().output)
