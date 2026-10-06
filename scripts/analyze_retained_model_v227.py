"""Independent execution/model split on the already verified V226 cohort."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts import analyze_limited_source_v226 as prior

OUTPUT = ROOT/'reports/retained_model_v227'
INPUT = ROOT/'reports/limited_source_v226'
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
ARMS, OPERATORS, SUPPORT = prior.ARMS, prior.OPERATORS, prior.SUPPORT
empty, queries, same = prior.empty, prior.queries, prior.same
query_score, world, settled = prior.query_score, prior.world, prior.settled


def finish(member,anchors,case,arm,state,plan,work):
    fallback = len(plan['candidates']) != 1 and not plan['query_ready']
    execution = (prior.make_plan(member,anchors,case,arm,state,work,force_member=True)
                 if fallback else plan)
    certified = execution['utility_lower'] >= 2
    identified = len(execution['candidates']) == 1 and certified
    transferred = (certified and execution['mode'] == 'library'
                   and (identified or execution['query_ready']))
    stop = ('member_budget' if fallback else 'query_set' if transferred and not identified
            else 'identified' if identified else 'member_certified' if certified else 'budget')
    knowledge = plan if plan['mode'] == 'library' and plan['candidates'] else execution
    return dict(execution_plan=execution,knowledge_plan=knowledge,queries=queries(knowledge),
                fallback=fallback,certified=certified,identified=identified,
                transferred=transferred,stop=stop,knowledge_mode=knowledge['mode'],
                knowledge_candidates=list(knowledge['candidates']),
                knowledge_query_ready=knowledge['query_ready'])


def retained_member(row):
    member = empty()
    for batch in row['batches']:
        for category,count in batch['increments'].items():
            member[batch['operator']][category] += count
    return member


def covered(block,law):
    return all(lo <= law[operator][category] <= hi for operator in OPERATORS
               for category,(lo,hi) in block[operator]['bounds'].items())


def summarize(results,records,old,counts,work):
    arms = {}
    for arm in ARMS:
        rows = [row for row in results if row['arm'] == arm]
        late = [row for row in rows if row['index'] >= 15]
        retained = [row for row in records if row['arm'] == arm]
        def changed(row):
            return sum(row['query_post'][query]['policy'] != row['legacy_query_post'][query]['policy']
                       for query in row['query_post'])
        def regret(row,key):
            return sum(F(query['regret']) for query in row[key].values())
        arms[arm] = dict(deepcopy(old['arms'][arm]),
            legacy_late_post_regret=old['arms'][arm]['late_post_regret'],
            late_post_regret=settled.mean(float(query['regret']) for row in late
                                        for query in row['query_post'].values()),
            changed_targets=sum(bool(changed(row)) for row in rows),
            changed_queries=sum(changed(row) for row in rows),
            worse_targets=sum(regret(row,'query_post') > regret(row,'legacy_query_post') for row in rows),
            late_changed_targets=sum(bool(changed(row)) for row in late),
            retained_library_fallbacks=sum(row['fallback'] and row['knowledge_mode'] == 'library'
                                           for row in retained),
            late_retained_library_fallbacks=sum(row['fallback'] and row['knowledge_mode'] == 'library'
                                                and row['index'] >= 15 for row in retained))
    contrasts = {arm+'_legacy_minus_retained_regret': [] for arm in ARMS}
    for life in range(12):
        for arm in ARMS:
            rows = [row for row in results if row['life'] == life and row['arm'] == arm and row['index'] >= 15]
            contrasts[arm+'_legacy_minus_retained_regret'].append(settled.mean(
                float(F(row['legacy_query_post'][query]['regret'])-row['query_post'][query]['regret'])
                for row in rows for query in row['query_post']))
    randomizer = random.Random(233900)
    samples = {key: [] for key in contrasts}
    for _ in range(5000):
        indices = [randomizer.randrange(12) for _ in range(12)]
        work['bootstrap_index_draws'] += 12
        for key,values in contrasts.items():
            samples[key].append(settled.mean(values[index] for index in indices))
            work['bootstrap_mean_terms'] += 12
    bootstrap = {key: dict(mean=settled.mean(values),
                           ci=[sorted(samples[key])[124],sorted(samples[key])[4874]])
                 for key,values in contrasts.items()}
    conditions = dict(
        EXECUTION_AND_COST_UNCHANGED=counts['execution_plan'] == 1152 and counts['library_after'] == 1152,
        MODEL_SCOPE=all(row['knowledge_coverage'] and row['knowledge_true_candidate']
                        and row['knowledge_true_candidate_coverage'] for row in results),
        CERTIFICATES_UNCHANGED=counts['terminal_flags'] == 1152 and counts['knowledge_query_ready'] == 1152,
        QUERY_RETENTION=arms['LOW_UNION']['late_post_regret'] < arms['LOW_UNION']['legacy_late_post_regret']
                        and arms['LOW_UNION']['late_post_regret'] <= .05)
    return dict(complete=True,cohort_records=len(records),stage_environment_samples=0,
        arms=arms,contrasts=contrasts,bootstrap=bootstrap,conditions=conditions,
        historical_scientific_gate=dict(decision=old['decision'],conditions=old['conditions']),
        decision='MODEL_RETENTION_INTERFACE_VALIDATED' if all(conditions.values())
                 else 'MODEL_RETENTION_INTERFACE_NOT_VALIDATED')


def analyze():
    started = perf_counter()
    checks,work,replay_counts = [],Counter(),Counter()
    def check(name,value):
        checks.append(dict(name=name,passed=bool(value)))
    def read(folder,name):
        return json.loads((folder/name).read_text())
    try:
        verified = read(INPUT,'analysis.json')
        check('previous_full_cohort_independently_verified',verified['valid'] and verified['complete'])
        old_rows,libraries = read(INPUT,'records.json'),read(INPUT,'source_evidence.json')
        old_results,old_run,old_summary = (read(INPUT,name) for name in ('results.json','run.json','summary.json'))
        check('fixed_retained_input_and_source_manifest',read(OUTPUT,'source_manifest.json') == dict(
            source_files=list(SOURCE_FILES),retained_input='reports/limited_source_v226',
            records=1152,input_valid=True,input_complete=True))
        original = {(row['life'],row['index'],row['arm']): row for row in old_rows}
        saved = read(OUTPUT,'records.json')
        lookup = {(row['life'],row['index'],row['arm']): row for row in saved}
        check('complete_unchanged_retained_four_arm_cohort',len(saved) == len(lookup) == len(original) == 1152
              and lookup.keys() == original.keys())
        frozen = []
        for life in range(12):
            anchors = {arm: libraries[life]['full' if arm == 'FULL_FIXED' else 'low'] for arm in ARMS}
            states = {arm: prior.prepare(anchors[arm],arm) for arm in ARMS}
            flags = dict(member=True,execution=True,knowledge=True,state=True,fees=True,certificates=True)
            for old in (row for row in old_rows if row['life'] == life):
                arm,index = old['arm'],old['index']
                row,state = lookup[life,index,arm],states[arm]
                flags['state'] &= same(old['library_before'],state)
                member = retained_member(old)
                flags['member'] &= same(old['member'],member)
                spent = sum(sum(counts.values()) for counts in member.values())
                flags['fees'] &= old['spent'] == spent and row['spent'] == spent
                flags['fees'] &= row['member_spent'] == spent and row['source_spent'] == 0
                # V226 already verified all prefixes and acquisition plans. Only
                # the new terminal split and rolling-state use are reconstructed.
                plan = prior.make_plan(member,anchors[arm],old['case'],arm,state,work)
                legacy_preplan = old['batches'][-1]['plan'] if old['batches'] else old['initial_plan']
                flags['execution'] &= same(legacy_preplan,plan)
                split = finish(member,anchors[arm],old['case'],arm,state,plan,work)
                flags['execution'] &= same(old['terminal_plan'],split['execution_plan'])
                flags['execution'] &= same(row['execution_plan'],split['execution_plan'])
                flags['knowledge'] &= same(row['knowledge_plan'],split['knowledge_plan'])
                flags['knowledge'] &= same(row['terminal_query'],split['queries'])
                for field in ('knowledge_mode','knowledge_candidates','knowledge_query_ready'):
                    flags['knowledge'] &= row[field] == split[field]
                flags['certificates'] &= split['knowledge_query_ready'] == plan['query_ready']
                for field in ('fallback','certified','identified','transferred','stop'):
                    flags['certificates'] &= row[field] == split[field] == old[field]
                event = prior.advance(state,member,anchors[arm],arm,split['execution_plan'])
                flags['state'] &= same(old['advance'],event) and same(row['advance'],event)
                flags['state'] &= same(old['library_after'],state)
                expected = dict(life=life,index=index,arm=arm,spent=spent,member_spent=spent,
                    source_spent=0,execution_plan=split['execution_plan'],knowledge_plan=split['knowledge_plan'],
                    terminal_query=split['queries'],advance=event,
                    **{field: split[field] for field in ('fallback','certified','identified','transferred','stop',
                                                        'knowledge_mode','knowledge_candidates','knowledge_query_ready')})
                flags['knowledge'] &= same(row,expected)
                frozen.append(expected)
                for name in ('library_before','initial_plan','initial_query','terminal_stop_choice','member',
                             'target_fee','execution_plan','terminal_flags','knowledge_query_ready','advance','library_after'):
                    replay_counts[name] += 1
                for name in ('batch_choice','batch_plan','batch_spent'):
                    replay_counts[name] += len(old['batches'])
            for name,value in flags.items():
                check(f'life_{life}_retained_{name}',value)
        for arm in ARMS:
            check(arm+'_unchanged_retained_fees',
                  sum(row['spent'] for row in frozen if row['arm'] == arm) == old_summary['arms'][arm]['target_samples']
                  and sum(old_run['source_costs'][arm]) == old_summary['arms'][arm]['source_samples'])
            replay_counts['arm_source_fee'] += 1
            replay_counts['arm_target_fee'] += 1
        # Oracle evaluation follows the complete fixed-count reconstruction.
        original_results = {(row['life'],row['index'],row['arm']): row for row in old_results}
        worlds = [world(life) for life in range(12)]
        results = []
        for row in frozen:
            life,index,arm = row['life'],row['index'],row['arm']
            cases,laws,identities = worlds[life]
            old,knowledge = original_results[life,index,arm],row['knowledge_plan']
            is_library = knowledge['mode'] == 'library'
            true_candidate = not is_library or identities[index] in knowledge['candidates']
            true_box = (knowledge['candidate_envelopes'].get(identities[index])
                        if is_library else knowledge['envelopes'])
            results.append(dict(life=life,index=index,arm=arm,spent=row['spent'],
                **{field: row[field] for field in ('certified','identified','transferred','fallback','stop')},
                terminal=old['terminal'],query_post=query_score(row['terminal_query'],laws[index],cases[index]),
                legacy_query_post=old['query_post'],knowledge_coverage=covered(knowledge['envelopes'],laws[index]),
                knowledge_true_candidate=true_candidate,
                knowledge_true_candidate_coverage=true_box is not None and covered(true_box,laws[index])))
        check('independent_retained_queries_and_actual_candidate_scope',same(read(OUTPUT,'results.json'),results))
        stats = Counter()
        expected = summarize(results,frozen,old_summary,replay_counts,stats)
        check('descriptive_paired_query_statistics_and_unchanged_scientific_gate',same(read(OUTPUT,'summary.json'),expected))
        run = read(OUTPUT,'run.json')
        check('complete_retained_replay_comparisons',run['replay_checks'] == dict(replay_counts))
        check('zero_source_and_target_environment_samples',run['stage_environment_samples'] == 0
              and all(run['arm_costs'][arm].get(key,0) == 0 for arm in ARMS
                      for key in ('controlled_samples','controlled_resets','environment_random_draws')))
        check('retained_historical_fees_are_preserved',same(run['historical_source_costs'],old_run['source_costs']))
        check('fixed_descriptive_bootstrap_work',run['bootstrap_costs'] == dict(stats))
        check('all_terminal_decisions_frozen_before_oracle_scoring',run['phases'] == [
            'protocol_frozen','retained_decisions_frozen','oracle_evaluated','complete'])
        complete = True
    except Exception as error:
        check('reconstruction',False)
        checks[-1]['error'] = f'{type(error).__name__}: {error}'
        complete = False
    output = dict(valid=complete and all(item['passed'] for item in checks),complete=complete,
                  checks=checks,stage_environment_samples=0,costs=dict(work),seconds=perf_counter()-started)
    (OUTPUT/'analysis.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(dict(valid=output['valid'],complete=complete,checks=len(checks))))
    return output


if __name__=='__main__':
    raise SystemExit(0 if analyze()['valid'] else 1)
