"""Audit supported consequence leaves while preserving unseen source assignments."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
import math
from pathlib import Path
import random
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4_ELEMENTS
from scripts import analyze_controlled_predictive_module_mobility_v160 as mobility
from scripts import analyze_controlled_predictive_feedback_program_v162 as feedback

prior = mobility.prior
LIVES, QUERIES = prior.LIVES, prior.QUERIES
BASE, MAX_STEPS, WORKERS = 164*100000000, 2000, 4
TRAIN_SUFFIXES, EVAL_SUFFIXES = 4, 16
MODES = ('H2', 'MODAL', 'LEARNED', 'MATCH_MODAL', 'GLOBAL', 'FIXED')
CONTRASTS = {'LEARNED-MODAL': ('LEARNED', 'MODAL'), 'LEARNED-MATCH_MODAL': ('LEARNED', 'MATCH_MODAL'),
    'LEARNED-GLOBAL': ('LEARNED', 'GLOBAL'), 'LEARNED-H2': ('LEARNED', 'H2'),
    'MATCH_MODAL-MODAL': ('MATCH_MODAL', 'MODAL'), 'LEARNED-FIXED': ('LEARNED', 'FIXED')}
MAPPINGS = ('AA', 'AB', 'BA', 'BB')
METRICS = ('utility', 'reward', 'failure', 'success')
read, mean, close, add_checks = prior.read, prior.mean, prior.close, prior.add_checks
moments, root_pool, history_pool = mobility.moments, mobility.root_pool, mobility.history_pool


def compact_outcome(row):
    keys = ('branch_id', 'root_id', 'life', 'query', 'replica', 'slot', 'suffix', 'mode', 'seed', 'phase', 'heldout_life', 'arm')
    return dict(**{key: row[key] for key in keys if key in row},
        **{key: row['result'][key] for key in ('score', 'steps', 'status', 'components', 'utility')}, module=row['module'])


def outcome_values(row):
    if row is None or row['status'] not in ('WON', 'LOST'):
        return {key: None for key in METRICS}
    return dict(zip(METRICS, [row['utility'], *row['components']]))


def mapped_program(candidate, code):
    program = dict(candidate)
    suffixes = {'A': candidate['true_suffix'], 'B': candidate['false_suffix']}
    program.update(true_suffix=list(suffixes[code[0]]), false_suffix=list(suffixes[code[1]]))
    return program



def summarize_eval(roots, outcomes, programs):
    """Paired suffix uncertainty, equal roots within each fixed history."""
    index = {(r['root_id'], r['suffix'], r['mode']): r for r in outcomes}
    root_rows = []
    for root in roots:
        item = {k: root[k] for k in ('root_id', 'life', 'query', 'replica', 'slot')}
        modes = {mode: [outcome_values(index.get((root['root_id'], s, mode))) for s in range(EVAL_SUFFIXES)] for mode in MODES}
        item['modes'] = {mode: {key: moments(v[key] for v in values) for key in METRICS} for mode, values in modes.items()}
        item['contrasts'] = {name: {key: moments(None if a[key] is None or b[key] is None else a[key]-b[key]
            for a, b in zip(modes[left], modes[right])) for key in METRICS} for name, (left, right) in CONTRASTS.items()}
        item['complete'] = all(m['complete'] for mode in item['modes'].values() for m in mode.values())
        root_rows.append(item)
    comparisons, modes, diagnostics = [], [], []
    for query in QUERIES:
        selected = [r for r in root_rows if r['query'] == query]
        for kind, names, target in (('contrasts', CONTRASTS, comparisons), ('modes', MODES, modes)):
            for name in names:
                histories = [dict(life=life, roots=sum(r['life'] == life for r in selected),
                    metrics={key: root_pool([r[kind][name][key] for r in selected if r['life'] == life]) for key in METRICS}) for life in LIVES]
                metrics = {key: history_pool([h['metrics'][key] for h in histories]) for key in METRICS}
                target.append(dict(query=query, **{('contrast' if kind == 'contrasts' else 'mode'): name},
                    roots=len(selected), complete=all(m['complete'] for m in metrics.values()), metrics=metrics, per_history=histories))
        for mode in MODES:
            rows = [index.get((r['root_id'], s, mode)) for r in selected for s in range(EVAL_SUFFIXES)]
            complete = bool(rows) and all(row is not None for row in rows)
            predicates = Counter(str(row['module']['predicate']).lower() for row in rows if row is not None)
            root_predicates = [{index[r['root_id'], suffix, mode]['module']['predicate'] for suffix in range(EVAL_SUFFIXES)
                if (r['root_id'], suffix, mode) in index} for r in selected]
            divergence = 0
            if complete and mode not in ('H2', 'FIXED'):
                for row in rows:
                    module = row['module']; program = module['program']
                    chosen = program['true_suffix'] if module['predicate'] is True else program['false_suffix']
                    divergence += int(module['predicate'] is not None and chosen != program['fixed_suffix'])
            diagnostics.append(dict(query=query, mode=mode, complete=complete, branches=len(rows),
                mean_prefix_steps=mean(r['module']['prefix_steps'] for r in rows) if complete else None,
                mean_attempts=mean(r['module']['attempts'] for r in rows) if complete else None,
                exit_counts=dict(Counter(r['module']['exit_reason'] for r in rows)) if complete else {},
                predicate_counts=dict(predicates), roots_with_both_predicates=sum(True in p and False in p for p in root_predicates),
                selected_suffix_differs_fixed=divergence if complete else None))
    frozen={(p['heldout_life'],p['query']):p for p in programs}
    provenance=[]
    for query in QUERIES:
        histories=[]
        for life in LIVES:
            cell=frozen.get((life,query));selected=[r for r in roots if r['life']==life and r['query']==query]
            rows=[index.get((root['root_id'],suffix,'LEARNED')) for root in selected for suffix in range(EVAL_SUFFIXES)]
            counts=Counter(terminal_supported=0,source_prior=0,none=0)
            complete=cell is not None and bool(rows) and all(row is not None for row in rows)
            if complete:
                identifier=cell['programs']['LEARNED']['candidate_id']
                score=next(c for c in cell['candidate_scores'] if c['candidate_id']==identifier)
                for row in rows:
                    predicate=row['module']['predicate']
                    if predicate is None:kind='none'
                    else:
                        evidence=score['predicate_evidence']['true' if predicate else 'false']
                        kind='terminal_supported' if evidence['provenance']=='terminal_estimated' else 'source_prior'
                    counts[kind]+=1
            histories.append(dict(life=life,complete=complete,branches=len(rows),branch_counts=dict(counts),
                selected_program_all_predicates_identified=cell['selected_program_all_predicates_identified'] if cell is not None else None))
        provenance.append(dict(query=query,complete=all(h['complete'] for h in histories),
            branches=sum(h['branches'] for h in histories),branch_counts={key:sum(h['branch_counts'][key] for h in histories) for key in ('terminal_supported','source_prior','none')},
            per_history=histories))
    return dict(root_rows=root_rows, comparisons=comparisons, modes=modes, program_diagnostics=diagnostics,
        learned_provenance_diagnostics=provenance)


frame, transport, generation_cell, replay_branch = feedback.frame, feedback.transport, feedback.generation_cell, feedback.replay_branch


def source_seed(life, query, phase, replica):
    offset = 10000000 if phase=='TRAIN_SOURCE' else 90000000
    return BASE+offset+life*1000000+list(QUERIES).index(query)*100000+replica


def branch_seed(root, suffix, phase, heldout_life):
    if phase=='SCREEN':
        return BASE+20000000+heldout_life*1000000+root['life']*100000+list(QUERIES).index(root['query'])*10000+root['replica']*1000+root['slot']*100+suffix
    return BASE+50000000+root['life']*1000000+list(QUERIES).index(root['query'])*100000+root['replica']*1000+root['slot']*100+suffix


def expected_roots(boards, row):
    if row['phase']=='TRAIN_SOURCE' and row['replica']>=2:
        return []
    n=len(boards)
    return [dict(root_id=f'{row["phase"]}:{row["life"]}:{row["query"]}:{row["replica"]}:{slot}',
        phase=row['phase'],life=row['life'],query=row['query'],replica=row['replica'],slot=slot,
        source_id=row['source_id'],source_seed=row['seed'],source_step=((2*slot+1)*n)//4,
        source_steps=n,board=boards[((2*slot+1)*n)//4]) for slot in range(2)]


def branch_roster(roots, phase, candidates=None, programs=None):
    cells={(r['heldout_life'],r['query']):r for r in candidates or []}
    frozen={(r['heldout_life'],r['query']):r for r in programs or []}
    schedule=[]
    for root in roots:
        folds=[life for life in LIVES if life!=root['life']] if phase=='SCREEN' else [root['life']]
        for heldout in folds:
            if phase=='SCREEN':
                modes=[('H2','H2',None)]
                for candidate in cells[heldout,root['query']]['candidates']:
                    modes.extend((candidate['candidate_id']+'_'+action,'FEEDBACK',mapped_program(candidate,action*2)) for action in ('A','B'))
                suffixes=TRAIN_SUFFIXES
            else:
                cell=frozen[heldout,root['query']]['programs']
                modes=[('H2','H2',None)]+[(mode,'FIXED' if mode=='FIXED' else 'FEEDBACK',cell[mode]['program']) for mode in MODES[1:]]
                suffixes=EVAL_SUFFIXES
            for suffix in range(suffixes):
                for mode,arm,program in modes:
                    branch_id=(f'{root["root_id"]}:fold{heldout}:{suffix}:{mode}' if phase=='SCREEN' else f'{root["root_id"]}:{suffix}:{mode}')
                    schedule.append(dict(branch_id=branch_id,root_id=root['root_id'],life=root['life'],query=root['query'],
                        replica=root['replica'],slot=root['slot'],suffix=suffix,mode=mode,arm=arm,phase=phase,
                        heldout_life=heldout,seed=branch_seed(root,suffix,phase,heldout),program=program))
    return schedule


def teacher_checks(lifecycle, source, totals):
    checks=dict(teacher_bank=set(lifecycle['teacher_bank'])==set(QUERIES),teacher_totals=True)
    for query in QUERIES:
        teacher=lifecycle['teacher_bank'][query]
        checks['teacher_bank'] &= prior.h1.teacher_analysis.teacher_loads_valid(teacher['loads'],source,'SINGLE',query)
        checks['teacher_bank'] &= teacher['parent_before']==teacher['parent_after']==prior.planning.previous.model_state(source,query,'PARENT',0)
        checks['teacher_bank'] &= teacher['leaf_before']==teacher['leaf_after']==prior.planning.expected_model_state(source,query,'SINGLE')
        checks['teacher_totals'] &= Counter(teacher['total_counts'])==totals[query]
    return checks


def new_cost():
    return dict(physical_games=0,physical_branches=0,environment_counts=Counter(),policy_counts=Counter(),
                program_setup_counts=Counter(),statuses=Counter(),decision_seconds=0.,analysis_replay_swipes=0)


def add_cost(cost,result,kind):
    cost[kind]+=1;cost['statuses'][result['status']]+=1
    cost['decision_seconds']+=result['decision_seconds']
    for name in ('environment_counts','policy_counts','program_setup_counts'):
        cost[name].update(result.get(name,{}))


def aggregate_costs(costs):
    result=new_cost()
    for cost in costs:
        for name in ('physical_games','physical_branches','decision_seconds','analysis_replay_swipes'):
            result[name]+=cost[name]
        for name in ('environment_counts','policy_counts','program_setup_counts','statuses'):
            result[name].update(cost[name])
    result['new_environment_samples']=result['environment_counts'].get('sampled_transitions',0)
    return result


def audit_source(lifecycle, source, directory):
    life,phase=lifecycle['life'],lifecycle['phase'];directory=Path(directory)
    rows=list(prior.old.read_rows(directory/lifecycle['source_trace']));roots=[]
    checks=dict(source_roster=len(rows)==8,source_identity=True,source_roots=True,
                source_physical_accounting=True)
    cost=new_cost();totals={q:Counter() for q in QUERIES}
    for i,row in enumerate(rows):
        query=list(QUERIES)[i//4];replica=i%4
        checks['source_identity'] &= all(row[k]==v for k,v in dict(life=life,phase=phase,query=query,
            replica=replica,source_id=f'{phase}:{life}:{query}:{replica}',method='H2',duration=0,max_steps=MAX_STEPS,seed=source_seed(life,query,phase,replica)).items())
        local,swipes,boards=prior.replay_game(row,{})
        add_checks(checks,local);cost['analysis_replay_swipes']+=swipes
        selected=expected_roots(boards,row);checks['source_roots'] &= row['roots']==selected
        roots.extend(selected);add_cost(cost,row['result'],'physical_games')
        prior.add_policy_work(totals,row['result']['policy_counts'])
    checks['source_roots'] &= lifecycle['roots']==roots
    checks['source_physical_accounting'] &= lifecycle['physical_games']==cost['physical_games'] and all(
        Counter(lifecycle[k])==cost[k] for k in ('environment_counts','policy_counts','statuses'))
    add_checks(checks,teacher_checks(lifecycle,source,totals))
    print(json.dumps(dict(event='audited_source',life=life,phase=phase,games=len(rows))),flush=True)
    return dict(life=life,phase=phase,checks=checks,rows=rows,roots=roots,costs=cost)


def audit_branches(lifecycle, source, roots, candidates, programs, directory):
    life,phase=lifecycle['life'],lifecycle['phase'];directory=Path(directory)
    roots=[r for r in roots if r['life']==life]
    root_map={r['root_id']:r for r in roots};roster=branch_roster(roots,phase,candidates,programs)
    expected={r['branch_id']:r for r in roster};seen=[];outcomes=[];paired_first={};paired_conditions={}
    checks=dict(branch_roster=True,branch_identity=True,branch_program_binding=True,compact_outcomes=True,
                branch_physical_accounting=True,branch_shared_first_prefix=True,branch_shared_predicate=True,branch_none_outcomes=True,branch_rule_frozen=lifecycle['rule_before']==lifecycle['rule_after']==source['rule'])
    cost=new_cost();totals={q:Counter() for q in QUERIES}
    for row in prior.old.read_rows(directory/lifecycle['branch_trace']):
        seen.append(row['branch_id']);plan=expected.get(row['branch_id'])
        if plan is None:
            checks['branch_roster']=False;continue
        root=root_map[row['root_id']]
        checks['branch_identity'] &= all(row.get(k)==v for k,v in plan.items() if k!='program') and row['root_board']==root['board']
        checks['branch_program_binding'] &= row['module']['program']==plan['program']
        local,swipes=replay_branch(row);add_checks(checks,local);cost['analysis_replay_swipes']+=swipes
        if row['arm'] != 'H2':
            key=(row['root_id'],row['heldout_life'],row['suffix'],row['module']['program']['candidate_id'])
            paired_first.setdefault(key,{})[row['mode']] = (row['actions'][0],row['scores'][0],
                row['choices'][0]['afterstate'],row['spawned_cells'][0],row['spawned_ranks'][0])
            if phase=='SCREEN':
                paired_conditions.setdefault(key,[]).append((row['module']['predicate'],row['result']['components'],row['result']['status'],row['result']['utility']))
        outcomes.append(compact_outcome(row));add_cost(cost,row['result'],'physical_branches')
        for q in QUERIES:totals[q].update(row['result']['policy_counts_by_query'][q])
    checks['branch_roster'] &= len(seen)==len(set(seen))==len(roster) and set(seen)==set(expected)
    checks['branch_shared_first_prefix'] &= all((phase!='SCREEN' or len(pair)==2) and all(value==next(iter(pair.values())) for value in pair.values()) for pair in paired_first.values())
    checks['branch_shared_predicate'] &= all(len(pair)==2 and pair[0][0]==pair[1][0] for pair in paired_conditions.values())
    checks['branch_none_outcomes'] &= all(pair[0]==pair[1] for pair in paired_conditions.values() if pair[0][0] is None)
    checks['compact_outcomes'] &= read(directory/lifecycle['outcomes_ref'])==outcomes
    checks['branch_physical_accounting'] &= lifecycle['physical_branches']==cost['physical_branches'] and all(
        Counter(lifecycle[k])==cost[k] for k in ('environment_counts','policy_counts','program_setup_counts','statuses'))
    add_checks(checks,teacher_checks(lifecycle,source,totals))
    print(json.dumps(dict(event='audited_branches',life=life,phase=phase,branches=len(outcomes))),flush=True)
    return dict(life=life,phase=phase,checks=checks,outcomes=outcomes,costs=cost)


def independent_selection(candidates, roots, outcomes):
    """Derive map consequences from paid A/B vectors using full-roster weights."""
    indexed={(r['heldout_life'],r['root_id'],r['suffix'],r['mode']):r for r in outcomes}
    result=[]
    for cell in candidates:
        heldout,query=cell['heldout_life'],cell['query'];histories=[l for l in LIVES if l!=heldout]
        roster=[r for r in roots if r['life'] in histories and r['query']==query]
        root_counts=Counter(r['life'] for r in roster);work=Counter(weight_updates=0,terminal_supported_assignments=0,retained_source_assignments=0);scores=[]
        for candidate in cell['candidates']:
            identifier=candidate['candidate_id']; issues=[] if all(root_counts[life]==4 for life in histories) else ['root_roster']
            support=Counter(true=0,false=0,none=0);paired={r['root_id']:[] for r in roster}
            for root in roster:
                for suffix in range(TRAIN_SUFFIXES):
                    physical=[indexed.get((heldout,root['root_id'],suffix,mode)) for mode in ('H2',identifier+'_A',identifier+'_B')]
                    work['candidate_pairs_examined']+=1;issue=None
                    if any(row is None for row in physical):issue='missing_pair'
                    elif any(row['status'] not in ('WON','LOST') or row['utility'] is None for row in physical):issue='nonterminal_pair'
                    elif physical[1]['module']['predicate']!=physical[2]['module']['predicate']:issue='predicate_mismatch'
                    elif physical[1]['module']['predicate'] is None and any(physical[1][key]!=physical[2][key] for key in ('components','status','utility')):issue='none_outcome_mismatch'
                    if issue is not None:
                        if issue not in issues:issues.append(issue)
                        continue
                    baseline,left,right=physical;predicate=left['module']['predicate']
                    support['none' if predicate is None else 'true' if predicate else 'false']+=1
                    paired[root['root_id']].append((predicate,baseline['components'],left['components'],right['components']))
            mapping_scores=[]
            if not issues:
                for code in MAPPINGS:
                    histories_scored=[]
                    for life in histories:
                        local=[r for r in roster if r['life']==life];vectors=[]
                        for root in local:
                            differences=[]
                            for predicate,baseline,left,right in paired[root['root_id']]:
                                choose_b=predicate is not None and code[0 if predicate else 1]=='B'
                                vector=right if choose_b else left
                                differences.append([value-base for value,base in zip(vector,baseline)])
                                work['mapping_vector_selections']+=1
                            vectors.append([mean(d[k] for d in differences) for k in range(3)])
                            work['mapping_root_means']+=1
                        vector=[mean(v[k] for v in vectors) for k in range(3)]
                        histories_scored.append(dict(life=life,roots=len(local),train_gain=prior.utility(vector,query),component_delta=vector))
                        work['mapping_history_means']+=1
                    vector=[mean(h['component_delta'][k] for h in histories_scored) for k in range(3)]
                    mapping_scores.append(dict(mapping_code=code,mapping={'true':code[0],'false':code[1]},
                        train_gain=prior.utility(vector,query),component_delta=vector,history_gains=histories_scored))
                    work['mapping_scores']+=1
            evidence={}
            for label,condition,prior_assignment in [('true',True,'A'),('false',False,'B')]:
                amount=support[label];supported=not issues and amount>0
                vector=None;delta=None
                if supported:
                    history_vectors=[]
                    for life in histories:
                        root_vectors=[]
                        for root in (r for r in roster if r['life']==life):
                            vectors=[]
                            for predicate,baseline,left,right in paired[root['root_id']]:
                                vectors.append([a-b for a,b in zip(left,right)] if predicate is condition else [0.,0.,0.])
                                work['evidence_vector_selections']+=1
                            root_vectors.append([mean(v[k] for v in vectors) for k in range(3)])
                            work['evidence_root_means']+=1
                        history_vectors.append([mean(v[k] for v in root_vectors) for k in range(3)])
                        work['evidence_history_means']+=1
                    vector=[mean(v[k] for v in history_vectors) for k in range(3)];delta=prior.utility(vector,query)
                    work['evidence_estimates']+=1
                if not issues:
                    work['terminal_supported_assignments' if supported else 'retained_source_assignments']+=1
                evidence[label]=dict(support=amount,provenance='terminal_estimated' if supported else 'source_prior' if amount==0 else 'terminal_incomplete',
                    component_delta_A_minus_B=vector,utility_delta_A_minus_B=delta,prior_assignment=prior_assignment,
                    allowed_assignments=['A','B'] if supported else [prior_assignment] if not issues else [])
            allowed=[code for code in MAPPINGS if code[0] in evidence['true']['allowed_assignments'] and code[1] in evidence['false']['allowed_assignments']]
            ordered=sorted(mapping_scores,key=lambda row:(-row['train_gain'],MAPPINGS.index(row['mapping_code'])))
            learned_ordered=[m for m in ordered if m['mapping_code'] in allowed]
            global_ordered=[m for m in ordered if m['mapping_code'] in ('AA','BB')]
            scores.append(dict(candidate_id=identifier,complete=not issues,condition_counts=dict(support),issues=issues,
                mapping_scores=mapping_scores,learned_mapping=learned_ordered[0]['mapping_code'] if learned_ordered else None,
                global_mapping=global_ordered[0]['mapping_code'] if global_ordered else None,predicate_evidence=evidence,
                allowed_mapping_codes=allowed,all_predicates_identified=not issues and bool(support['true'] and support['false'])))
        complete=bool(scores) and all(item['complete'] for item in scores);programs={}
        if complete:
            work['learned_branch_tables']=1
            candidate_by_id={c['candidate_id']:c for c in cell['candidates']}
            score_by_id={score['candidate_id']:{m['mapping_code']:m for m in score['mapping_scores']} for score in scores}
            modal_index=max(range(len(scores)),key=lambda i:score_by_id[scores[i]['candidate_id']]['AB']['train_gain'])
            learned_index=max(range(len(scores)),key=lambda i:score_by_id[scores[i]['candidate_id']][scores[i]['learned_mapping']]['train_gain'])
            modal,learned=scores[modal_index],scores[learned_index]
            decisions=[('MODAL',modal,'AB'),('LEARNED',learned,learned['learned_mapping']),
                ('MATCH_MODAL',learned,'AB'),('GLOBAL',learned,learned['global_mapping'])]
            for mode,chosen,code in decisions:
                mapping_score=score_by_id[chosen['candidate_id']][code]
                programs[mode]=dict(candidate_id=chosen['candidate_id'],mapping=dict(mapping_score['mapping']),
                    program=mapped_program(candidate_by_id[chosen['candidate_id']],code),train_gain=mapping_score['train_gain'])
            programs['FIXED']=dict(candidate_id=learned['candidate_id'],mapping=None,program=dict(candidate_by_id[learned['candidate_id']]),train_gain=None)
        result.append(dict(heldout_life=heldout,query=query,complete=complete,train_lives=histories,
            candidate_scores=scores,programs=programs,learning_counts=dict(work),
            all_predicates_identified=complete and all(c['all_predicates_identified'] for c in scores),
            selected_program_all_predicates_identified=complete and scores[learned_index]['all_predicates_identified']))
    return result


def compact_roster_valid(rows, expected):
    index={r['branch_id']:r for r in expected}
    return len(rows)==len(index)==len({r['branch_id'] for r in rows}) and all(
        row['branch_id'] in index and all(index[row['branch_id']].get(k)==v for k,v in row.items()) for row in rows)


def settings_valid(settings):
    expected=dict(lifecycles=list(LIVES),queries=QUERIES,source_replicas=4,source_games=64,train_roots=32,eval_roots=64,
        word_length=4,candidate_limit=2,train_suffixes=4,eval_suffixes=16,screening_branch_cap=1920,
        evaluation_branches=6144,physical_branch_cap=8064,maximum_environment_transitions=16256000,
        max_steps=2000,p_four=.1,workers=4,version_base=BASE,new_parameter_updates=0)
    return all(settings.get(k)==v for k,v in expected.items())


def parallel_audit(function,lifecycles,sources,*args):
    results=[]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        tasks=[pool.submit(function,lifecycle,sources[lifecycle['life']],*args) for lifecycle in lifecycles]
        for task in as_completed(tasks):results.append(task.result())
    results.sort(key=lambda r:r['life']);return results


def analyze(directory):
    started=perf_counter();directory=Path(directory).resolve()
    run,capsule,frozen=(read(directory/name) for name in ('run.json','source_capsule.json','frozen_inputs.json'))
    inherited={ref['path']:read(ref['path']) for ref in capsule['cost_refs']}
    source_run,source_analysis=read(capsule['source_run_ref']),read(capsule['source_analysis_ref'])
    source_capsule=read(Path(capsule['source_run_ref']).parent/'source_capsule.json')
    held_run,held_analysis=read(capsule['inherited_v163_run_ref']),read(capsule['inherited_v163_analysis_ref'])
    source_roster=[dict(phase=phase,life=life,query=query,replica=replica,seed=source_seed(life,query,phase,replica))
        for phase in ('TRAIN_SOURCE','EVAL_SOURCE') for life in LIVES for query in QUERIES for replica in range(4)]
    checks=dict(settings=settings_valid(run['settings']),frozen_inputs=frozen['status']=='frozen' and frozen['settings']==run['settings']
        and frozen['phases']=={} and frozen['phase_order']==[] and frozen['source_roster']==source_roster,
        inherited_costs=run['inherited_cost_refs']==capsule['cost_refs']==frozen['inherited_cost_refs'],
        inherited_fields=all(all(k in inherited[ref['path']] for k in ref['fields']) for ref in capsule['cost_refs']),
        source_complete=source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete'],
        source_binding=capsule['snapshots']==source_capsule['snapshots'],
        inherited_physical_cost=capsule['inherited_v162_environment_samples']==source_analysis['costs']['new_environment_samples']==2586113
            and capsule['inherited_v161_environment_samples']==source_capsule['inherited_v161_environment_samples']==2554756
            and capsule['inherited_v160_environment_samples']==source_capsule['inherited_v160_environment_samples']==2958948
            and capsule['inherited_v158_environment_samples']==source_capsule['inherited_v158_environment_samples']==4026405,
        inherited_v163_hold=held_run['status']=='incomplete_training' and held_analysis['complete'] and not held_analysis['primary_complete']
            and held_analysis['status']=='incomplete_training' and set(held_run['phases'])=={'TRAIN_SOURCE','SCREEN'}
            and held_run['phase_order']==['TRAIN_SOURCE','SCREEN','PROGRAMS_FROZEN']
            and capsule['inherited_v163_environment_samples']==held_analysis['costs']['new_environment_samples']==996655,
        phase_order=run['phase_order']==(['TRAIN_SOURCE','SCREEN','PROGRAMS_FROZEN'] if run['status']=='incomplete_training' else
            ['TRAIN_SOURCE','SCREEN','PROGRAMS_FROZEN','EVAL_SOURCE','EVAL']),phase_lifecycle_roster=True)
    sources={s['life']:s for s in capsule['snapshots']}
    checks['learned_rewrite_matches_physics']=all(source['rule']['program']==dict(pack=True,merge_relation='equal',rank_increment=1,consumption='once',reward_rule='output_value') and source['rule']['goal_rank']==11 for source in sources.values())
    for phase,record in run['phases'].items():
        checks['phase_lifecycle_roster'] &= len(record['lifecycles'])==4 and [r['life'] for r in record['lifecycles']]==list(LIVES)
        checks['phase_lifecycle_roster'] &= all(r['phase']==phase for r in record['lifecycles'])
    train=parallel_audit(audit_source,run['phases']['TRAIN_SOURCE']['lifecycles'],sources,directory)
    train_rows=[r for life in train for r in life['rows']];train_roots=[r for life in train for r in life['roots']]
    for life in train:add_checks(checks,life['checks'])
    checks['train_root_roster']=len(train_roots)==32 and len({r['root_id'] for r in train_roots})==32 and read(directory/'train_roots.json')==train_roots
    candidates=[generation_cell(train_rows,heldout,query) for heldout in LIVES for query in QUERIES]
    checks['generated_candidates']=read(directory/'generated_candidates.json')==candidates
    checks['generation_excludes_heldout']=all(c['training_lives']==[l for l in LIVES if l!=c['heldout_life']] and
        len(c['source_games'])==12 and len(c['candidates'])<=2 for c in candidates)
    screening_inputs=read(directory/'screening_inputs.json')
    checks['screening_frozen_inputs']=screening_inputs['roots']==train_roots and screening_inputs['candidates']==candidates and compact_roster_valid(
        screening_inputs['branch_roster'],branch_roster(train_roots,'SCREEN',candidates))
    screen=parallel_audit(audit_branches,run['phases']['SCREEN']['lifecycles'],sources,
        train_roots,candidates,None,directory)
    screen_rows=[r for life in screen for r in life['outcomes']]
    for life in screen:add_checks(checks,life['checks'])
    programs=independent_selection(candidates,train_roots,screen_rows)
    checks['frozen_programs']=mobility.arithmetic.equivalent(read(directory/'frozen_programs.json'),programs)
    screening_count=len(branch_roster(train_roots,'SCREEN',candidates))
    checks['screening_roster_complete']=len(screen_rows)==len({r['branch_id'] for r in screen_rows})==screening_count and screening_count<=1920
    checks['symbolic_learning_only']=all(p['learning_counts']['weight_updates']==0 and p['learning_counts'].get('learned_branch_tables',0)==int(p['complete']) for p in programs)
    checks['selection_excludes_heldout']=all(p['train_lives']==[l for l in LIVES if l!=p['heldout_life']] for p in programs)
    all_results=train+screen;metrics=None;primary_complete=False
    if run['status']=='incomplete_training':
        checks['training_stop']=not all(p['complete'] for p in programs) and set(run['phases'])=={'TRAIN_SOURCE','SCREEN'}
    else:
        checks['training_selection_complete']=all(p['complete'] for p in programs)
        evaluation_source=parallel_audit(audit_source,run['phases']['EVAL_SOURCE']['lifecycles'],sources,directory)
        eval_roots=[r for life in evaluation_source for r in life['roots']]
        for life in evaluation_source:add_checks(checks,life['checks'])
        checks['eval_root_roster']=len(eval_roots)==64 and len({r['root_id'] for r in eval_roots})==64 and read(directory/'eval_roots.json')==eval_roots
        evaluation_inputs=read(directory/'evaluation_inputs.json')
        checks['evaluation_frozen_inputs']=evaluation_inputs['roots']==eval_roots and mobility.arithmetic.equivalent(evaluation_inputs['programs'],programs) and compact_roster_valid(
            evaluation_inputs['branch_roster'],branch_roster(eval_roots,'EVAL',programs=programs))
        evaluation=parallel_audit(audit_branches,run['phases']['EVAL']['lifecycles'],sources,eval_roots,None,programs,directory)
        eval_rows=[r for life in evaluation for r in life['outcomes']]
        for life in evaluation:add_checks(checks,life['checks'])
        checks['eval_roster_complete']=len(eval_rows)==len({r['branch_id'] for r in eval_rows})==6144
        metrics=summarize_eval(eval_roots,eval_rows,programs)
        checks['summary_values']=mobility.arithmetic.equivalent(read(directory/'summary.json'),metrics)
        primary_complete=all(r['complete'] for r in metrics['comparisons'] if r['contrast']=='LEARNED-MODAL')
        all_results+=evaluation_source+evaluation
    costs=aggregate_costs(r['costs'] for r in all_results)
    generation_analysis_replay_swipes=sum(c['counts']['source_state_reconstructions']+c['counts'].get('probe_checks',0) for c in candidates)
    costs['analysis_replay_swipes']+=generation_analysis_replay_swipes
    costs.update(new_parameter_updates=0,inherited_v163_environment_samples=996655,inherited_v162_environment_samples=2586113,inherited_v161_environment_samples=2554756,inherited_v160_environment_samples=2958948,inherited_v158_environment_samples=4026405,
        generation_counts=dict(sum((Counter(c['counts']) for c in candidates),Counter())),
        generation_analysis_replay_swipes=generation_analysis_replay_swipes,
        program_learning_counts=dict(sum((Counter(p['learning_counts']) for p in programs),Counter())),
        physical_phase_costs={phase:aggregate_costs(r['costs'] for r in all_results if r['phase']==phase) for phase in run['phases']},
        teacher_accounting=[dict(phase=phase,life=row['life'],query=query,**teacher)
            for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()])
    checks['full_physical_roster']=costs['physical_games']==(32 if run['status']=='incomplete_training' else 64) and costs['physical_branches']==(
        screening_count if run['status']=='incomplete_training' else screening_count+6144)
    complete=all(checks.values()) and run['status'] in ('complete','incomplete_training')
    return dict(schema='acfqp.supported_program.v164.analysis',complete=complete,primary_complete=complete and primary_complete,
        status=run['status'],checks=checks,candidates=candidates,programs=programs,metrics=metrics,costs=costs,
        inherited_cost_refs=capsule['cost_refs'],seconds=perf_counter()-started,
        uncertainty='Pointwise paired-suffix intervals conditional on fixed roots, four histories, and trained selections; cross-fold training overlaps.',
        limitations='Unseen predicate leaves retain the source AB assignment with unknown terminal delta; operational completeness does not identify every leaf. Four-map TRAIN fits reuse paid suffix pairs, while EVAL is separately sampled. This bounded grammar has no population-history interval.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_supported_program_v164')
    directory=parser.parse_args().input
    result=analyze(directory)
    (directory/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
                         failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
