"""Separate execution and knowledge on the complete validated V226 cohort."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.science import retained_model_v227 as core
from acfqp.science import latent_route_task_v213 as task
from scripts.run_conditioned_mechanisms_v205 import save, exact_json, mean
from scripts.run_persistent_evidence_v221 import query_score

INPUT = ROOT/'reports/limited_source_v226'
OUTPUT = ROOT/'reports/retained_model_v227'
SOURCE_FILES = (
    'src/acfqp/science/retained_model_v227.py',
    'src/acfqp/science/limited_source_v226.py',
    'src/acfqp/science/mixture_confidence_v225.py',
    'src/acfqp/science/assignment_union_v222.py',
    'scripts/run_retained_model_v227.py',
    'scripts/analyze_retained_model_v227.py',
    'tests/test_retained_model_v227.py',
    'specs/RETAINED_MODEL_V227.md',
    'reports/v227_runtime_tmp/run_stage.py',
)


def load(name):
    return json.loads((INPUT/name).read_text())


def saved(value):
    return json.loads(json.dumps(exact_json(value)))


def equal(actual, expected, name, checks):
    if saved(actual) != expected:
        raise AssertionError(name)
    checks[name] += 1


def summarize(results, records, prior, checks, work):
    arms = {}
    for arm in core.ARMS:
        rows = [r for r in results if r['arm']==arm]
        late = [r for r in rows if r['index']>=15]
        retained = [r for r in records if r['arm']==arm]
        changed = lambda r: sum(r['query_post'][q]['policy'] != r['legacy_query_post'][q]['policy']
                                for q in r['query_post'])
        regret = lambda r, key: sum(F(q['regret']) for q in r[key].values())
        arms[arm] = dict(deepcopy(prior['arms'][arm]),
            legacy_late_post_regret=prior['arms'][arm]['late_post_regret'],
            late_post_regret=mean(float(q['regret']) for r in late for q in r['query_post'].values()),
            changed_targets=sum(bool(changed(r)) for r in rows),
            changed_queries=sum(changed(r) for r in rows),
            worse_targets=sum(regret(r,'query_post')>regret(r,'legacy_query_post') for r in rows),
            late_changed_targets=sum(bool(changed(r)) for r in late),
            retained_library_fallbacks=sum(r['fallback'] and r['knowledge_mode']=='library' for r in retained),
            late_retained_library_fallbacks=sum(r['fallback'] and r['knowledge_mode']=='library'
                and r['index']>=15 for r in retained))
    contrasts = {arm+'_legacy_minus_retained_regret':[] for arm in core.ARMS}
    for life in range(12):
        for arm in core.ARMS:
            rows = [r for r in results if r['life']==life and r['arm']==arm and r['index']>=15]
            contrasts[arm+'_legacy_minus_retained_regret'].append(mean(
                float(F(r['legacy_query_post'][q]['regret'])-r['query_post'][q]['regret'])
                for r in rows for q in r['query_post']))
    rng = random.Random(233900); samples = {key:[] for key in contrasts}
    for _ in range(5000):
        indices = [rng.randrange(12) for _ in range(12)]; work['bootstrap_index_draws'] += 12
        for key, values in contrasts.items():
            samples[key].append(mean(values[i] for i in indices)); work['bootstrap_mean_terms'] += 12
    bootstrap = {key:dict(mean=mean(values),ci=[sorted(samples[key])[124],sorted(samples[key])[4874]])
                 for key,values in contrasts.items()}
    conditions = dict(
        EXECUTION_AND_COST_UNCHANGED=checks['execution_plan']==1152 and checks['library_after']==1152,
        MODEL_SCOPE=all(r['knowledge_coverage'] and r['knowledge_true_candidate']
            and r['knowledge_true_candidate_coverage'] for r in results),
        CERTIFICATES_UNCHANGED=checks['terminal_flags']==1152 and checks['knowledge_query_ready']==1152,
        QUERY_RETENTION=arms['LOW_UNION']['late_post_regret']<arms['LOW_UNION']['legacy_late_post_regret']
            and arms['LOW_UNION']['late_post_regret']<=.05)
    return dict(complete=True,cohort_records=len(records),stage_environment_samples=0,
        arms=arms,contrasts=contrasts,bootstrap=bootstrap,conditions=conditions,
        historical_scientific_gate=dict(decision=prior['decision'],conditions=prior['conditions']),
        decision='MODEL_RETENTION_INTERFACE_VALIDATED' if all(conditions.values())
                 else 'MODEL_RETENTION_INTERFACE_NOT_VALIDATED')


def run():
    begun = perf_counter()
    analysis = load('analysis.json')
    if not (analysis['valid'] and analysis['complete']):
        raise AssertionError('V226 cohort has not passed independent validation')
    old_rows, libraries = load('records.json'), load('source_evidence.json')
    old_results, old_run, prior = load('results.json'), load('run.json'), load('summary.json')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    for name in SOURCE_FILES:
        dest = OUTPUT/'source_code'/name; dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    save(OUTPUT/'source_manifest.json',dict(source_files=list(SOURCE_FILES),
        retained_input='reports/limited_source_v226',records=len(old_rows),
        input_valid=analysis['valid'],input_complete=analysis['complete']))
    checks = Counter(); work = {a:Counter() for a in core.ARMS}
    seconds = dict.fromkeys(core.ARMS,0.); records = []
    core.clear_cache()
    for life in range(12):
        anchors = {a:libraries[life]['full' if a=='FULL_FIXED' else 'low'] for a in core.ARMS}
        states = {a:core.prepare(anchors[a],a,work[a]) for a in core.ARMS}
        for old in (r for r in old_rows if r['life']==life):
            started = perf_counter(); arm=old['arm']; state=states[arm]; member=core.empty()
            equal(state,old['library_before'],'library_before',checks)
            plan=core.make_plan(member,anchors[arm],old['case'],arm,work[arm],state)
            equal(plan,old['initial_plan'],'initial_plan',checks)
            equal(core.queries(plan),old['initial_query'],'initial_query',checks)
            spent=0
            for batch in old['batches']:
                choice=core.choose(member,anchors[arm],old['case'],arm,plan,spent,work[arm],state)
                equal(choice,batch['choice'],'batch_choice',checks)
                op=choice['operator']
                if op != batch['operator'] or sum(member[op].values()) != batch['draw_start']:
                    raise AssertionError('retained batch operator/start')
                for cat,k in batch['increments'].items():
                    member[op][cat] += k
                spent += sum(batch['increments'].values())
                equal(spent,batch['spent'],'batch_spent',checks)
                plan=core.make_plan(member,anchors[arm],old['case'],arm,work[arm],state)
                equal(plan,batch['plan'],'batch_plan',checks)
            equal(core.choose(member,anchors[arm],old['case'],arm,plan,spent,work[arm],state),
                  None,'terminal_stop_choice',checks)
            equal(member,old['member'],'member',checks)
            equal(spent,old['spent'],'target_fee',checks)
            finished=core.finish(member,anchors[arm],old['case'],arm,work[arm],state,plan)
            equal(finished['execution_plan'],old['terminal_plan'],'execution_plan',checks)
            names=('fallback','certified','identified','transferred','stop')
            equal({k:finished[k] for k in names},{k:old[k] for k in names},'terminal_flags',checks)
            equal(finished['knowledge_query_ready'],plan['query_ready'],'knowledge_query_ready',checks)
            event=core.advance(state,member,anchors[arm],arm,work[arm],
                               terminal_plan=finished['execution_plan'])
            equal(event,old['advance'],'advance',checks)
            equal(state,old['library_after'],'library_after',checks)
            query=finished.pop('queries')
            records.append(dict(life=life,index=old['index'],arm=arm,spent=spent,
                member_spent=spent,source_spent=0,terminal_query=query,advance=event,**finished))
            seconds[arm] += perf_counter()-started
        print(json.dumps(dict(life=life,replayed=len(records),seconds=perf_counter()-begun)),flush=True)
    # Freeze the complete model/query decisions before consulting true kernels.
    save(OUTPUT/'records.json',records)
    source_costs=old_run['source_costs']
    for arm in core.ARMS:
        equal(sum(r['spent'] for r in records if r['arm']==arm),prior['arms'][arm]['target_samples'],
              'arm_target_fee',checks)
        equal(sum(source_costs[arm]),prior['arms'][arm]['source_samples'],'arm_source_fee',checks)
    results=[]; lookup={(r['life'],r['index'],r['arm']):r for r in old_results}
    for row in records:
        cases,laws,identities=task.world(row['life']); case=cases[row['index']]; law=laws[row['index']]
        old=lookup[row['life'],row['index'],row['arm']]; knowledge=row['knowledge_plan']
        coverage=all(lo<=law[op][cat]<=hi for op,env in knowledge['envelopes'].items()
                     for cat,(lo,hi) in env['bounds'].items())
        true_candidate=knowledge['mode']!='library' or identities[row['index']] in knowledge['candidates']
        true_box=(knowledge['candidate_envelopes'].get(identities[row['index']])
                  if knowledge['mode']=='library' else knowledge['envelopes'])
        true_coverage=true_box is not None and all(lo<=law[op][cat]<=hi
            for op,env in true_box.items() for cat,(lo,hi) in env['bounds'].items())
        results.append(dict(life=row['life'],index=row['index'],arm=row['arm'],spent=row['spent'],
            **{k:row[k] for k in ('certified','identified','transferred','fallback','stop')},
            terminal=old['terminal'],query_post=query_score(row['terminal_query'],law,case),
            legacy_query_post=old['query_post'],knowledge_coverage=coverage,
            knowledge_true_candidate=true_candidate,knowledge_true_candidate_coverage=true_coverage))
    stats=Counter(); summary=summarize(results,records,prior,checks,stats)
    save(OUTPUT/'results.json',results); save(OUTPUT/'summary.json',summary)
    save(OUTPUT/'run.json',dict(phases=['protocol_frozen','retained_decisions_frozen','oracle_evaluated','complete'],
        stage_environment_samples=0,arm_costs=work,arm_seconds=seconds,replay_checks=checks,
        historical_source_costs=source_costs,bootstrap_costs=stats,seconds=perf_counter()-begun))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    run()
