"""Independently replay observed-state feedback programs and paired effects."""
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

prior = mobility.prior
LIVES, QUERIES = prior.LIVES, prior.QUERIES
BASE, MAX_STEPS, WORKERS = 162*100000000, 2000, 4
TRAIN_SUFFIXES, EVAL_SUFFIXES = 4, 16
MODES = ('H2', 'FIXED', 'FEEDBACK')
CONTRASTS = {'FEEDBACK-FIXED': ('FEEDBACK', 'FIXED'), 'FEEDBACK-H2': ('FEEDBACK', 'H2'), 'FIXED-H2': ('FIXED', 'H2')}
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


def candidate_contrast(candidate, roots, index, heldout, histories, left, right):
    local = []
    for life in histories:
        selected = [r for r in roots if r['life'] == life]
        vectors = []
        for root in selected:
            pairs = []
            for suffix in range(TRAIN_SUFFIXES):
                x = outcome_values(index.get((heldout, root['root_id'], suffix, left)))
                y = outcome_values(index.get((heldout, root['root_id'], suffix, right)))
                pairs.append([None if x[k] is None or y[k] is None else x[k]-y[k] for k in METRICS])
            vectors.append([mean(v[k] for v in pairs) for k in range(4)])
        complete = len(selected) == 4 and all(v[0] is not None for v in vectors)
        vector = [mean(v[k] for v in vectors) for k in range(4)] if complete else [None]*4
        local.append(dict(life=life, roots=len(selected), complete=complete, mean=vector[0], components=vector[1:]))
    return dict(complete=all(h['complete'] for h in local), mean=mean(h['mean'] for h in local),
        components=[mean(h['components'][k] for h in local) for k in range(3)], per_history=local)


def select_programs(candidates, roots, outcomes):
    """TRAIN feedback selects the candidate; its FIXED twin is never reselected."""
    index = {(r['heldout_life'], r['root_id'], r['suffix'], r['mode']): r for r in outcomes}
    result = []
    for cell in candidates:
        heldout, query = cell['heldout_life'], cell['query']
        histories = [life for life in LIVES if life != heldout]
        pool = [r for r in roots if r['life'] in histories and r['query'] == query]
        scores = []
        for candidate in cell['candidates']:
            fixed, feedback = (candidate['candidate_id']+suffix for suffix in ('_FIXED', '_FEEDBACK'))
            primary = candidate_contrast(candidate, pool, index, heldout, histories, feedback, 'H2')
            diagnostics = {name: candidate_contrast(candidate, pool, index, heldout, histories, left, right)
                for name, left, right in [('FIXED-H2', fixed, 'H2'), ('FEEDBACK-FIXED', feedback, fixed)]}
            scores.append(dict(**candidate, **primary, diagnostics=diagnostics))
        complete = bool(scores) and all(s['complete'] and all(d['complete'] for d in s['diagnostics'].values()) for s in scores)
        best = min(range(len(scores)), key=lambda i: (-scores[i]['mean'], i)) if complete else None
        result.append(dict(heldout_life=heldout, query=query, complete=complete, train_lives=histories,
            candidate_scores=scores, selected_program=cell['candidates'][best] if best is not None else None))
    return result


def summarize_eval(roots, outcomes):
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
            if complete and mode == 'FEEDBACK':
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
    return dict(root_rows=root_rows, comparisons=comparisons, modes=modes, program_diagnostics=diagnostics)


def frame(board):
    """Reconstruct orientation independently of the program implementation."""
    choices = [(ground.transform_board_v1(tuple(board), t), i, t) for i, t in enumerate(D4_ELEMENTS)]
    canonical, _, transform = min(choices, key=lambda x: (x[0], x[1]))
    return canonical, transform


def transport(transform, actions):
    inverse = {ground.transform_action_v1(a, transform).value: a.value for a in ground.Swipe2048Action}
    return [inverse[a] for a in actions]


def modal(counter):
    return min(counter, key=lambda key: (-counter[key], key))


def generation_cell(rows, heldout_life, query):
    """Rebuild window labels using physical swipes, independent of learned code."""
    counts = Counter(source_rows_examined=len(rows)); groups = {}; games = []
    for row in rows:
        if row['life'] == heldout_life or row['query'] != query:
            continue
        n = row['result']['steps']; boards = []; board = tuple(row['initial_board'])
        counts.update(source_games=1, source_state_reconstructions=n)
        for step, action in enumerate(row['actions']):
            boards.append(board)
            after, _, _ = ground.swipe_board_v1(board, ground.Swipe2048Action(action))
            board = list(after); board[row['spawned_cells'][step]] = row['spawned_ranks'][step]; board = tuple(board)
        for start in range(n-3):
            _, transform = frame(boards[start])
            word = tuple(ground.transform_action_v1(ground.Swipe2048Action(a), transform).value for a in row['actions'][start:start+4])
            observed = ground.transform_board_v1(boards[start+1], transform)
            groups.setdefault(word[0], []).append((word[1:], observed))
            counts.update(fragment_windows=1, board_transforms=8, action_transports=4, postspawn_board_transforms=1)
        games.append(dict(life=row['life'], query=query, replica=row['replica'], seed=row['seed'], steps=n, status=row['result']['status']))
    eligible = []
    for first, windows in groups.items():
        fixed = modal(Counter(suffix for suffix, _ in windows)); probe = fixed[0]
        branches = {True: Counter(), False: Counter()}
        for suffix, board in windows:
            _, score, changed = ground.swipe_board_v1(board, ground.Swipe2048Action(probe))
            branches[bool(changed and score > 0)][suffix] += 1
            counts.update(probe_checks=1, learned_swipe_calls=1, learned_line_rewrites=4)
        if branches[True] and branches[False]:
            true, false = modal(branches[True]), modal(branches[False])
            if true != false:
                eligible.append(dict(first_action=first, probe_action=probe, fixed_suffix=list(fixed), true_suffix=list(true),
                    false_suffix=list(false), occurrences=len(windows), condition_counts={'true':sum(branches[True].values()),'false':sum(branches[False].values())}))
    counts.update(first_action_groups=len(groups), eligible_groups=len(eligible))
    selected = sorted(eligible, key=lambda row: (-row['occurrences'], row['first_action']))[:2]
    candidates = [dict(candidate_id=f'P{i}', **candidate) for i, candidate in enumerate(selected)]
    return dict(heldout_life=heldout_life, query=query, training_lives=sorted({r['life'] for r in games}),
        candidates=candidates, source_games=games, counts=dict(counts))


def replay_branch(row, max_steps=MAX_STEPS):
    result = row['result']; n = result['steps']; query = row['query']; program = row['module']['program']; arm = row['arm']
    checks = dict(branch_arrays=n>0 and all(len(row[k])==n for k in ('actions','choices','scores','spawned_cells','spawned_ranks')),
        branch_settings=row['p_four']==.1 and row['max_steps']==max_steps, branch_actions=True, branch_rng=True,
        branch_terminal=True, branch_returns=True, branch_environment=True, branch_phases=True,
        branch_program_attempt=True, branch_program_work=True, branch_program_orientation=True,
        branch_feedback_event=True, branch_feedback_observed_state=True, branch_program_exit=True,
        branch_h2_choice=True, branch_policy_totals=True,
        branch_no_learning=not any(result['learning_counts'].values()),
        branch_seconds=math.isfinite(result['seconds']) and math.isfinite(result['decision_seconds']) and 0<=result['decision_seconds']<=result['seconds'])
    if not checks['branch_arrays']: return checks, 0
    board = tuple(row['root_board']); status, exits, swipes = prior.previous.legal_exits(board); replayed = swipes
    checks['branch_terminal'] &= status=='ACTIVE'
    environment = Counter(ground_state_status_calls=1, ground_status_internal_swipe_calls=swipes, ground_swipe_calls=swipes)
    phases = {p: Counter() for p in ('prefix','continuation')}; teachers = {q: Counter() for q in QUERIES}
    if program is None:
        module = dict(program=None, arm=arm, canonical_board=None, transform=None, actual_word=[], actual_probe=None,
            actual_true_suffix=[], actual_false_suffix=[], prefix_steps=0, attempts=0, predicate=None, exit_reason='baseline', exit_step=0)
        setup = Counter()
        checks['branch_program_orientation'] &= arm=='H2'
    else:
        canonical, transform = frame(board)
        first = transport(transform, [program['first_action']])
        fixed = transport(transform, program['fixed_suffix'])
        feedback = arm=='FEEDBACK'
        module = dict(program=program, arm=arm, canonical_board=list(canonical), transform=transform.value,
            actual_word=first if feedback else first+fixed,
            actual_probe=transport(transform, [program['probe_action']])[0] if feedback else None,
            actual_true_suffix=transport(transform, program['true_suffix']) if feedback else [],
            actual_false_suffix=transport(transform, program['false_suffix']) if feedback else [],
            prefix_steps=0, attempts=0, predicate=None, exit_reason=None, exit_step=None)
        setup = Counter(program_board_transforms=8, program_action_transports=8 if feedback else 4)
        checks['branch_program_orientation'] &= arm in ('FIXED','FEEDBACK')
    checks['branch_program_orientation'] &= Counter(result['program_setup_counts'])==setup
    rng = random.Random(row['seed']); score_total = 0
    for step, choice in enumerate(row['choices']):
        attempt = None; event = None; expected_prefix = module['exit_reason'] is None; prefix_work = Counter()
        if expected_prefix:
            if arm=='FEEDBACK' and module['prefix_steps']==1:
                probe = module['actual_probe']; after, score, legal = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(probe)); replayed += 1
                predicate = bool(legal and score>0)
                suffix = module['actual_true_suffix'] if predicate else module['actual_false_suffix']
                event = dict(probe_action=probe, afterstate=list(after), score=score, legal=bool(legal), predicate=predicate, selected_suffix=list(suffix))
                module['predicate'] = predicate; module['actual_word'] += suffix
                prefix_work.update(feedback_probe_checks=1,feedback_learned_swipe_calls=1,feedback_learned_line_rewrites=4)
                checks['branch_feedback_observed_state'] &= choice.get('feedback_event')==event
            action = module['actual_word'][module['prefix_steps']]; legal = action in exits
            if legal: after, score = exits[action]
            else: after, score, _ = ground.swipe_board_v1(tuple(board), ground.Swipe2048Action(action)); replayed += 1
            attempt = dict(index=module['prefix_steps'], action=action, legal=legal, afterstate=list(after), score=score)
            module['attempts'] += 1
            prefix_work.update(program_action_checks=1, program_learned_swipe_calls=1, program_learned_line_rewrites=4)
            if not legal:
                module.update(exit_reason='illegal', exit_step=step); expected_prefix = False
        phase = 'prefix' if expected_prefix else 'continuation'; work = Counter(choice['work']); phases[phase].update(work)
        checks['branch_phases'] &= choice['step']==step and choice['phase']==phase and choice.get('module_decision') is None
        checks['branch_program_attempt'] &= choice['program_action_attempt']==attempt
        checks['branch_feedback_event'] &= choice.get('feedback_event')==event
        if expected_prefix:
            checks['branch_program_work'] &= choice['policy_key']=='PROGRAM' and work==prefix_work
            checks['branch_actions'] &= choice['action']==attempt['action'] and choice['afterstate']==attempt['afterstate'] and choice['score']==attempt['score']
        else:
            native = {k[len(f'policy_{query}_'):]: v for k, v in work.items() if k.startswith(f'policy_{query}_')}
            expected = Counter(forced_decisions=1); expected.update(prefix_work)
            expected.update({f'policy_{query}_{k}':v for k,v in native.items()})
            checks['branch_h2_choice'] &= choice['policy_key']==query and work==expected
            checks['branch_h2_choice'] &= prior.planning.planning_counts_valid(native,'H2','SINGLE',1,len(exits)) and prior.local.compact_choice_valid(choice,exits,query)
            add_checks(checks, prior.h1.root_choice_checks(board,choice,query)); replayed += 4
        prior.add_policy_work(teachers,work)
        action = choice['action']; checks['branch_actions'] &= status=='ACTIVE' and action in exits and row['actions'][step]==action
        if action not in exits: return checks, replayed
        after, score = exits[action]; score_total += score; checks['branch_actions'] &= row['scores'][step]==score
        empty = [i for i,v in enumerate(after) if not v]
        cell = empty[int(rng.random()*len(empty))]; rank = 1 if rng.random()<.9 else 2
        checks['branch_rng'] &= (row['spawned_cells'][step],row['spawned_ranks'][step])==(cell,rank)
        board = list(after); board[cell] = rank; status, exits, swipes = prior.previous.legal_exits(tuple(board)); replayed += swipes
        environment.update(ground_explicit_swipe_calls=1,ground_swipe_calls=1+swipes,environment_random_draws=2,sampled_transitions=1,
                           ground_state_status_calls=1,ground_status_internal_swipe_calls=swipes)
        if phase=='prefix':
            module['prefix_steps'] += 1
            reason = 'terminal' if status!='ACTIVE' else 'budget' if module['prefix_steps']==4 else None
            if reason is not None: module.update(exit_reason=reason, exit_step=step+1)
    final = 'CUTOFF' if status=='ACTIVE' else status
    if module['exit_reason'] is None: module.update(exit_reason='cutoff',exit_step=n)
    components = [score_total/2048.,float(final=='LOST'),float(final=='WON')]
    checks['branch_program_exit'] &= row['module']==module
    checks['branch_terminal'] &= row['final_board']==board and result['status']==final and n<=max_steps and (final!='CUTOFF' or n==max_steps)
    checks['branch_returns'] &= result['score']==score_total and result['components']==components and result['utility']==(None if final=='CUTOFF' else prior.utility(components,query))
    checks['branch_environment'] &= Counter(result['environment_counts'])==environment
    checks['branch_policy_totals'] &= Counter(result['prefix_counts'])==phases['prefix'] and Counter(result['continuation_counts'])==phases['continuation'] and Counter(result['policy_counts'])==sum(phases.values(),Counter())
    checks['branch_policy_totals'] &= set(result['policy_counts_by_query'])==set(QUERIES) and all(Counter(result['policy_counts_by_query'][q])==teachers[q] for q in QUERIES)
    return checks, replayed


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
                    modes.extend((candidate['candidate_id']+'_'+arm,arm,candidate) for arm in ('FIXED','FEEDBACK'))
                suffixes=TRAIN_SUFFIXES
            else:
                program=frozen[heldout,root['query']]['selected_program']
                modes=[('H2','H2',None),('FIXED','FIXED',program),('FEEDBACK','FEEDBACK',program)]
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
    expected={r['branch_id']:r for r in roster};seen=[];outcomes=[];paired_first={}
    checks=dict(branch_roster=True,branch_identity=True,branch_program_binding=True,compact_outcomes=True,
                branch_physical_accounting=True,branch_shared_first_prefix=True,branch_rule_frozen=lifecycle['rule_before']==lifecycle['rule_after']==source['rule'])
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
            paired_first.setdefault(key,{})[row['arm']] = (row['actions'][0],row['scores'][0],
                row['choices'][0]['afterstate'],row['spawned_cells'][0],row['spawned_ranks'][0])
        outcomes.append(compact_outcome(row));add_cost(cost,row['result'],'physical_branches')
        for q in QUERIES:totals[q].update(row['result']['policy_counts_by_query'][q])
    checks['branch_roster'] &= len(seen)==len(set(seen))==len(roster) and set(seen)==set(expected)
    checks['branch_shared_first_prefix'] &= all(set(pair)=={'FIXED','FEEDBACK'} and pair['FIXED']==pair['FEEDBACK'] for pair in paired_first.values())
    checks['compact_outcomes'] &= read(directory/lifecycle['outcomes_ref'])==outcomes
    checks['branch_physical_accounting'] &= lifecycle['physical_branches']==cost['physical_branches'] and all(
        Counter(lifecycle[k])==cost[k] for k in ('environment_counts','policy_counts','program_setup_counts','statuses'))
    add_checks(checks,teacher_checks(lifecycle,source,totals))
    print(json.dumps(dict(event='audited_branches',life=life,phase=phase,branches=len(outcomes))),flush=True)
    return dict(life=life,phase=phase,checks=checks,outcomes=outcomes,costs=cost)


def independent_selection(candidates, roots, outcomes):
    """Rebuild three paired training contrasts directly from terminal records."""
    indexed={(r['heldout_life'],r['root_id'],r['suffix'],r['mode']):r for r in outcomes}
    cells=[]
    for cell in candidates:
        heldout=cell['heldout_life']; query=cell['query']; histories=[l for l in LIVES if l!=heldout]
        scores=[]
        for candidate in cell['candidates']:
            fb, fixed=candidate['candidate_id']+'_FEEDBACK', candidate['candidate_id']+'_FIXED'
            contrasts={}
            for name,left,right in [('FEEDBACK-H2',fb,'H2'),('FIXED-H2',fixed,'H2'),('FEEDBACK-FIXED',fb,fixed)]:
                rows=[]
                for life in histories:
                    local=[r for r in roots if r['life']==life and r['query']==query]; paired=[]
                    for root in local:
                        values=[]
                        for suffix in range(TRAIN_SUFFIXES):
                            x=indexed.get((heldout,root['root_id'],suffix,left)); y=indexed.get((heldout,root['root_id'],suffix,right))
                            if x is None or y is None or x['status'] not in ('WON','LOST') or y['status'] not in ('WON','LOST'):
                                values.append(None)
                            else:
                                values.append([x['utility']-y['utility'],*[a-b for a,b in zip(x['components'],y['components'])]])
                        paired.append([mean(v[k] if v is not None else None for v in values) for k in range(4)])
                    complete=len(local)==4 and all(v[0] is not None for v in paired)
                    vector=[mean(v[k] for v in paired) for k in range(4)] if complete else [None]*4
                    rows.append(dict(life=life,roots=len(local),complete=complete,mean=vector[0],components=vector[1:]))
                contrasts[name]=dict(complete=all(r['complete'] for r in rows),mean=mean(r['mean'] for r in rows),
                    components=[mean(r['components'][k] for r in rows) for k in range(3)],per_history=rows)
            scores.append(dict(**candidate,**contrasts['FEEDBACK-H2'],diagnostics={k:contrasts[k] for k in ('FIXED-H2','FEEDBACK-FIXED')}))
        complete=bool(scores) and all(r['complete'] and all(d['complete'] for d in r['diagnostics'].values()) for r in scores)
        selected=None
        if complete:
            selected=cell['candidates'][0]; best=scores[0]['mean']
            for i,score in enumerate(scores[1:],1):
                if score['mean']>best: best=score['mean']; selected=cell['candidates'][i]
        cells.append(dict(heldout_life=heldout,query=query,complete=complete,train_lives=histories,candidate_scores=scores,selected_program=selected))
    return cells


def compact_roster_valid(rows, expected):
    index={r['branch_id']:r for r in expected}
    return len(rows)==len(index)==len({r['branch_id'] for r in rows}) and all(
        row['branch_id'] in index and all(index[row['branch_id']].get(k)==v for k,v in row.items()) for row in rows)


def settings_valid(settings):
    expected=dict(lifecycles=list(LIVES),queries=QUERIES,source_replicas=4,source_games=64,train_roots=32,eval_roots=64,
        word_length=4,candidate_limit=2,train_suffixes=4,eval_suffixes=16,screening_branch_cap=1920,
        evaluation_branches=3072,physical_branch_cap=4992,maximum_environment_transitions=10112000,
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
    source_roster=[dict(phase=phase,life=life,query=query,replica=replica,seed=source_seed(life,query,phase,replica))
        for phase in ('TRAIN_SOURCE','EVAL_SOURCE') for life in LIVES for query in QUERIES for replica in range(4)]
    checks=dict(settings=settings_valid(run['settings']),frozen_inputs=frozen['status']=='frozen' and frozen['settings']==run['settings']
        and frozen['phases']=={} and frozen['phase_order']==[] and frozen['source_roster']==source_roster,
        inherited_costs=run['inherited_cost_refs']==capsule['cost_refs']==frozen['inherited_cost_refs'],
        inherited_fields=all(all(k in inherited[ref['path']] for k in ref['fields']) for ref in capsule['cost_refs']),
        source_complete=source_run['status']=='complete' and source_analysis['complete'] and source_analysis['primary_complete'],
        source_binding=capsule['snapshots']==source_capsule['snapshots'],
        inherited_physical_cost=capsule['inherited_v161_environment_samples']==source_analysis['costs']['new_environment_samples']==2554756
            and capsule['inherited_v160_environment_samples']==source_capsule['inherited_v160_environment_samples']==2958948
            and capsule['inherited_v158_environment_samples']==source_capsule['inherited_v158_environment_samples']==4026405,
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
        checks['eval_roster_complete']=len(eval_rows)==len({r['branch_id'] for r in eval_rows})==3072
        metrics=summarize_eval(eval_roots,eval_rows)
        checks['summary_values']=mobility.arithmetic.equivalent(read(directory/'summary.json'),metrics)
        primary_complete=all(r['complete'] for r in metrics['comparisons'] if r['contrast']=='FEEDBACK-FIXED')
        all_results+=evaluation_source+evaluation
    costs=aggregate_costs(r['costs'] for r in all_results)
    generation_analysis_replay_swipes=sum(c['counts']['source_state_reconstructions']+c['counts'].get('probe_checks',0) for c in candidates)
    costs['analysis_replay_swipes']+=generation_analysis_replay_swipes
    costs.update(new_parameter_updates=0,inherited_v161_environment_samples=2554756,inherited_v160_environment_samples=2958948,inherited_v158_environment_samples=4026405,
        generation_counts=dict(sum((Counter(c['counts']) for c in candidates),Counter())),
        generation_analysis_replay_swipes=generation_analysis_replay_swipes,
        physical_phase_costs={phase:aggregate_costs(r['costs'] for r in all_results if r['phase']==phase) for phase in run['phases']},
        teacher_accounting=[dict(phase=phase,life=row['life'],query=query,**teacher)
            for phase,data in run['phases'].items() for row in data['lifecycles'] for query,teacher in row['teacher_bank'].items()])
    checks['full_physical_roster']=costs['physical_games']==(32 if run['status']=='incomplete_training' else 64) and costs['physical_branches']==(
        screening_count if run['status']=='incomplete_training' else screening_count+3072)
    complete=all(checks.values()) and run['status'] in ('complete','incomplete_training')
    return dict(schema='acfqp.feedback_program.v162.analysis',complete=complete,primary_complete=complete and primary_complete,
        status=run['status'],checks=checks,candidates=candidates,programs=programs,metrics=metrics,costs=costs,
        inherited_cost_refs=capsule['cost_refs'],seconds=perf_counter()-started,
        uncertainty='Pointwise paired-suffix intervals conditional on fixed roots, four histories, and trained selections; cross-fold training overlaps.',
        limitations='Four primitive actions, one merge predicate, and global per-query selection are a bounded feedback grammar, not general strategy learning. Training cutoff stops evaluation; no population-history interval.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input','--directory',dest='input',type=Path,default=ROOT/'reports/controlled_predictive_feedback_program_v162')
    directory=parser.parse_args().input
    result=analyze(directory)
    (directory/'analysis.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps(dict(complete=result['complete'],primary_complete=result['primary_complete'],checks=len(result['checks']),
                         failed=[k for k,v in result['checks'].items() if not v],seconds=result['seconds'])),flush=True)
    raise SystemExit(0 if result['complete'] else 1)
