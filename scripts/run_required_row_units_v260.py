"""Fresh A/B/A comparison of predictably declared required-row acquisition units."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from copy import deepcopy
from fractions import Fraction as F
import gzip
import json
from pathlib import Path
import random
import shutil
import sys
from time import perf_counter, process_time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT)]
from acfqp.science import required_row_units_v260 as core
from acfqp.science import joint_unresolved_trajectory_v255 as allocation
from acfqp.science import oracle_gap_acquisition_v231 as acquisition
from acfqp.science import scoped_route_task_v228 as task
from scripts.run_conditioned_mechanisms_v205 import draw,exact_json,save
from scripts.run_reuse_rebuild_lifecycle_v242 import evaluate,aggregate
from scripts.run_persistent_evidence_v221 import query_score
from scripts.run_oracle_gap_lifecycle_v231 import oracle_goal
from scripts.run_shared_probe_timing_v249 import activate_cold_caches

OUTPUT = ROOT/'reports/required_row_units_v260'
LIVES,ARMS = (0,1,2),core.ARMS
TARGETS = tuple(range(3,27))+tuple(range(30,78))
TOTAL_CAPS,SOURCE_COST,MEMBER_CAP,MEMBER_BATCH,SHARED_BATCH = (14144,17072,17168),4608,384,16,256
SOURCE_BASE,SHARED_BASE,MEMBER_BASE,EXECUTION_BASE,MIX_BASE = 318000,319000,320000,321000,322000
PUBLIC_COSTS = (('low','17/20'),('low','19/20'),('high','17/20'),('high','19/20'))
MODEL_SCOPES = ('initialization','begin_b','type_selection','row_pool_updates','trajectory_updates','query_previews','planning','execution_choice')
FILE_KINDS = ('tapes','rounds','sources','batches','previews','checks','phases','profiles','decisions','records')


def filename(kind,life,arm):
    return OUTPUT/f'{kind}_life_{life:02d}_{arm}.jsonl.gz'


def rows(path):
    with gzip.open(path,'rt') as stream:
        yield from (json.loads(line) for line in stream)


def write_row(stream,row):
    begun = perf_counter()
    stream.write(json.dumps(exact_json(row),separators=(',',':'))+'\n')
    stream.flush()
    return perf_counter()-begun


def retain_plan(plan,stream,ids,identity):
    saved = deepcopy({key:value for key,value in plan.items() if key!='query_evidence'})
    decisions = {}
    for query,decision in plan['query_evidence']['queries'].items():
        retained = {key:value for key,value in decision.items() if key!='comparisons'}
        if 'comparisons' in decision:
            retained['comparisons'] = []
            for certificate in decision['comparisons']:
                costs = plan['case']['operating'],str(F(plan['case']['retry_cost']))
                references = 'admitted_unit_ids' if certificate['score_source']=='actual_declared_required_row_units' else 'admitted_round_ids'
                key = (plan['case']['context'],identity,costs,query,certificate['chosen'],certificate['other'],tuple(certificate[references]))
                if key not in ids:
                    ids[key] = len(ids)
                    write_row(stream,dict(profile_id=ids[key],case=dict(context=plan['case']['context'],operating=costs[0],retry_cost=costs[1]),
                        query_identity=identity,certificate=certificate))
                retained['comparisons'].append(dict(profile_id=ids[key],other=certificate['other'],certified=certificate['certified']))
        decisions[query] = retained
    saved['query_evidence'] = dict(queries=decisions,all_ready=plan['query_evidence']['all_ready'],threshold=4320)
    return saved


def available_budget(cap,fees,remaining_targets):
    future_b_source = max(0,1152-max(0,fees['source']-3456))
    return cap-sum(fees.values())-future_b_source-2*remaining_targets


def realized(policy,outcomes,case):
    short_cost,detour_cost = core.native.mechanics.robust.learning.COST_PRIOR[case['operating']]
    if policy=='WAIT':
        reward,last = F(0),'ABORT'
    elif policy=='SHORT':
        reward,last = -short_cost,outcomes[core.trajectory.S]
    else:
        reward,last = -detour_cost,outcomes[core.trajectory.D]
        if last=='RECOVERY':
            if policy=='DETOUR_RETRY':
                reward -= F(case['retry_cost'])
                last = outcomes[core.trajectory.R]
            else:
                last = 'ABORT'
    failure,delivery = int(last=='LOST'),int(last=='DELIVERY')
    return dict(reward=reward,failure=failure,delivery=delivery,terminal='WON' if delivery else 'LOST' if failure else 'ABORT',
        goal_utility=reward+4*delivery,risk_utility=reward-4*failure+4*delivery)


class Simulator:
    """Only this sampling object accesses probabilities before final scoring."""
    def __init__(self,life,laws,work):
        self.life,self._laws,self.work = life,laws,work
        self.generators,self.offsets = {},Counter()

    def observe(self,phase,context,identity,operator,index=None):
        op_index = core.OPERATORS.index(operator)
        if phase in ('SOURCE','SHARED'):
            base = SOURCE_BASE if phase=='SOURCE' else SHARED_BASE
            slot = (0 if context=='A' else 3)+identity
            seed,law_index = base+(self.life*6+slot)*3+op_index,identity if context=='A' else 27+identity
        else:
            base = MEMBER_BASE if phase=='MEMBER' else EXECUTION_BASE
            seed,law_index = base+(self.life*78+index)*3+op_index,index
        key = phase,context,identity,operator,index
        if key not in self.generators:
            self.generators[key] = random.Random(seed)
        start = self.offsets[key]
        increments,progress = dict.fromkeys(core.ALPHABETS[operator],0),dict(draw_end=start,n=start)
        draw(self.generators[key],self._laws[law_index],operator,increments,1,self.work,progress)
        self.offsets[key] = progress['draw_end']
        return dict(seed=seed,draw_start=start,draw_end=progress['draw_end'],outcome=next(cat for cat,count in increments.items() if count))


class Lifecycle:
    def __init__(self,life,arm,bundle,streams):
        self.life,self.arm,self.bundle,self.streams = life,arm,bundle,streams
        self.work,self.cache,self.profile_ids = Counter(),{},{}
        self.normalizers = activate_cold_caches()
        self.timings = dict.fromkeys(MODEL_SCOPES,0.)
        self.acquisition_seconds,self.observation_seconds,self.output_seconds = 0.,0.,0.
        self.fees,self.remaining = dict.fromkeys(('source','shared','member','execution'),0),72
        self.step,self.round_id,self.batch_id,self.check_id = 0,0,0,0
        self.cursors = {'A':0,'B':0}
        self.simulator = Simulator(life,bundle['laws'],self.work)
        self.state = self.timed('initialization',core.prepare,life,arm,self.work)
        self.records,self.auxiliary_records = [],0
        self.unit_accounting = dict.fromkeys(('source_complete_units','source_tail_samples',
            'shared_complete_units','shared_partial_units','shared_tail_samples'),0)
        self.shared_primitive_samples_by_operator = dict.fromkeys(core.OPERATORS,0)
        self.shared_declared_row_sets = Counter()

    def timed(self,scope,function,*args,acquisition_call=False):
        begun = process_time()
        result = function(*args)
        elapsed = process_time()-begun
        self.timings[scope] += elapsed
        if acquisition_call:
            self.acquisition_seconds += elapsed
        return result

    def write(self,kind,row):
        self.output_seconds += write_row(self.streams[kind],row)

    def retain(self,plan,identity):
        begun = perf_counter()
        saved = retain_plan(plan,self.streams['profiles'],self.profile_ids,identity)
        self.output_seconds += perf_counter()-begun
        return saved

    def budget(self):
        future = max(0,1152-max(0,self.fees['source']-3456))
        return dict(cap=TOTAL_CAPS[self.life],fees=deepcopy(self.fees),paid=sum(self.fees.values()),
            future_B_source_reserved=future,remaining_targets=self.remaining,execution_reserved=2*self.remaining,
            available=available_budget(TOTAL_CAPS[self.life],self.fees,self.remaining))

    def primitive(self,phase,context,identity,operator,index=None,round_id=None,batch_id=None,role=None,cursor_before=None):
        begun = perf_counter()
        observed = self.simulator.observe(phase,context,identity,operator,index)
        self.observation_seconds += perf_counter()-begun
        self.step += 1
        self.fees[{'SOURCE':'source','SHARED':'shared','MEMBER':'member','EXECUTION':'execution'}[phase]] += 1
        if phase=='SHARED':
            self.shared_primitive_samples_by_operator[operator] += 1
        increments = dict.fromkeys(core.ALPHABETS[operator],0)
        increments[observed['outcome']] = 1
        self.timed('row_pool_updates',core.observe_row,self.state,context,identity,operator,increments)
        row = dict(life=self.life,arm=self.arm,phase=phase,context=context,identity=identity,index=index,
            step_index=self.step,operator=operator,round_id=round_id,batch_id=batch_id,role=role,cursor_before=cursor_before,**observed)
        self.write('tapes',row)
        return row

    def conditional_batch(self,phase,context,index,amount,eligible,prior_check_id=None,
            declared_rows_by_type=None,preview_ids_by_type=None):
        begun_step,before_cursor,before_budget = self.step,self.cursors[context],self.budget()
        target,batch_id,before_round = self.step+amount,self.batch_id,self.round_id
        masks = [list(core.OPERATORS) for _ in range(3)] if declared_rows_by_type is None else deepcopy(declared_rows_by_type)
        tails,complete,partial = 0,0,0
        while self.step<target:
            cursor = self.cursors[context]
            identity,next_cursor = self.timed('type_selection',allocation.select_type,cursor,eligible)
            self.cursors[context] = next_cursor
            declared = tuple(masks[identity])
            maximum_calls = len(declared)
            if target-self.step<maximum_calls:
                row = self.primitive(phase,context,identity,core.trajectory.S,batch_id=batch_id,role='tail_S',cursor_before=cursor)
                self.timed('trajectory_updates',core.observe_tail,self.state,context,identity,row['outcome'])
                tails += 1
                self.work['standalone_S_tails'] += 1
                self.unit_accounting['source_tail_samples' if phase=='SOURCE' else 'shared_tail_samples'] += 1
                continue
            self.round_id += 1
            unit_start,primitives,outcomes = self.step+1,[],{}
            unit_budget = self.budget()
            for operator in (core.trajectory.S,core.trajectory.D):
                if operator in declared:
                    row = self.primitive(phase,context,identity,operator,round_id=self.round_id,batch_id=batch_id,
                        role='S' if operator==core.trajectory.S else 'D',cursor_before=cursor)
                    primitives.append(row['step_index'])
                    outcomes[operator] = row['outcome']
            if core.trajectory.R in declared:
                if outcomes[core.trajectory.D]=='RECOVERY':
                    row = self.primitive(phase,context,identity,core.trajectory.R,round_id=self.round_id,batch_id=batch_id,
                        role='R',cursor_before=cursor)
                    primitives.append(row['step_index'])
                    outcomes[core.trajectory.R] = row['outcome']
                else:
                    outcomes[core.trajectory.R] = None
            all_rows = declared==core.OPERATORS
            record = dict(life=self.life,arm=self.arm,phase=phase,context=context,identity=identity,
                round_id=self.round_id,batch_id=batch_id,start_step=unit_start,end_step=self.step,
                declared_rows=list(declared),all_rows_declared=all_rows,maximum_calls_reserved=maximum_calls,
                budget_before=unit_budget,primitive_steps=primitives,outcomes=outcomes)
            self.timed('trajectory_updates',core.observe_unit,self.state,record)
            self.write('rounds',record)
            self.work['declared_observation_units'] += 1
            if all_rows:
                complete += 1
                self.work['complete_conditional_rounds'] += 1
                self.unit_accounting['source_complete_units' if phase=='SOURCE' else 'shared_complete_units'] += 1
            else:
                partial += 1
                self.work['partial_required_row_units'] += 1
                self.unit_accounting['shared_partial_units'] += 1
            if phase=='SHARED':
                self.shared_declared_row_sets['|'.join(declared)] += 1
        self.write('batches',dict(life=self.life,arm=self.arm,phase=phase,context=context,index=index,batch_id=batch_id,
            prior_check_id=prior_check_id,eligible_types_frozen=list(eligible),start_step=begun_step,end_step=self.step,
            actual_samples=amount,cursor_before=before_cursor,cursor_after=self.cursors[context],
            declared_rows_by_type=masks,preview_ids_by_type=deepcopy(preview_ids_by_type),
            observation_units=self.round_id-before_round,complete_rounds=complete,partial_units=partial,
            standalone_S_tails=tails,budget_before=before_budget,budget_after=self.budget()))
        self.batch_id += 1
        return batch_id

    def source(self,context,index):
        amount = 3456 if context=='A' else 1152
        batch = self.conditional_batch('SOURCE',context,index,amount,[0,1,2])
        self.timed('initialization',core.freeze_sources,self.state,context)
        self.write('sources',dict(life=self.life,arm=self.arm,context=context,index=index,batch_id=batch,
            source_counts=deepcopy(self.state['a' if context=='A' else 'b']['sources']),actual_samples=amount,
            source_round_ids=[row['round_id'] for row in self.state['round_log'] if row['phase']=='SOURCE' and row['context']==context],
            cursor=self.cursors[context],budget=self.budget()))

    def preview_check(self,stage,context,index):
        check_id,readiness,refs = self.check_id,[True]*3,[]
        masks,refs_by_type = [],[]
        for identity in range(3):
            plans,type_refs = [],[]
            for cost_index,(operating,retry) in enumerate(PUBLIC_COSTS):
                case = dict(id=f'v260_l{self.life}_{stage}_t{identity}_c{cost_index}',context=context,stage=stage,operating=operating,retry_cost=retry)
                plan = self.timed('query_previews',core.make_plan,core.empty(),case,self.state,identity,index,self.cache,self.work)
                retained = self.retain(plan,identity)
                record = dict(life=self.life,arm=self.arm,stage=stage,context=context,index=index,check_id=check_id,
                    identity=identity,cost_index=cost_index,preview_id=check_id*12+identity*4+cost_index,
                    plan=retained,budget=self.budget())
                self.write('previews',record)
                readiness[identity] = readiness[identity] and core.ready(plan)
                refs.append(record['preview_id'])
                type_refs.append(record['preview_id'])
                plans.append(plan)
            masks.append(list(self.timed('type_selection',core.declared_rows_for_plans,plans)) if self.arm==ARMS[0] else list(core.OPERATORS))
            refs_by_type.append(type_refs)
        meta = dict(life=self.life,arm=self.arm,stage=stage,context=context,index=index,check_id=check_id,
            preview_ids=refs,preview_ids_by_type=refs_by_type,declared_rows_by_type=masks,
            ready_by_type=readiness,all_ready=all(readiness),cursor=self.cursors[context],budget=self.budget())
        self.write('checks',meta)
        self.check_id += 1
        self.auxiliary_records += 12
        return meta

    def shared_phase(self,stage,context,index):
        budget_before,shared_before = self.budget(),self.fees['shared']
        check = self.preview_check(stage,context,index)
        initial_check,check_ids,batch_ids = check['check_id'],[check['check_id']],[]
        while not check['all_ready'] and self.budget()['available']>0:
            eligible = allocation.eligible_types('DIRECT_JOINT_UNRESOLVED',check['ready_by_type'])
            amount = min(SHARED_BATCH,self.budget()['available'])
            batch_ids.append(self.conditional_batch('SHARED',context,index,amount,eligible,check['check_id'],
                check['declared_rows_by_type'],check['preview_ids_by_type']))
            check = self.preview_check(stage,context,index)
            check_ids.append(check['check_id'])
        self.write('phases',dict(life=self.life,arm=self.arm,stage=stage,context=context,index=index,
            initial_check_id=initial_check,final_check_id=check['check_id'],check_ids=check_ids,batch_ids=batch_ids,
            paid_samples=self.fees['shared']-shared_before,final_ready_by_type=check['ready_by_type'],
            stop_reason='all_ready' if check['all_ready'] else 'budget_exhausted',budget_before=budget_before,budget_after=self.budget()))

    def execute(self,index,case,identity,mix):
        before = self.budget()
        begun = process_time()
        seed = MIX_BASE+self.life*78+index
        coin = F(random.Random(seed).random())
        cumulative,selected = F(0),None
        for policy,weight in mix:
            cumulative += F(weight)
            if coin<cumulative:
                selected = policy
                break
        self.timings['execution_choice'] += process_time()-begun
        primitives,outcomes = [],{}
        if selected!='WAIT':
            operator = core.trajectory.S if selected=='SHORT' else core.trajectory.D
            row = self.primitive('EXECUTION',case['context'],identity,operator,index=index,role=selected)
            primitives.append(row['step_index'])
            outcomes[operator] = row['outcome']
            if selected=='DETOUR_RETRY' and row['outcome']=='RECOVERY':
                row = self.primitive('EXECUTION',case['context'],identity,core.trajectory.R,index=index,role=selected)
                primitives.append(row['step_index'])
                outcomes[core.trajectory.R] = row['outcome']
        self.remaining -= 1
        return dict(mix_seed=seed,mix_coin=coin,selected_policy=selected,primitive_steps=primitives,outcomes=outcomes,
            actual_samples=len(primitives),realized=realized(selected,outcomes,case),released_execution_reserve=2-len(primitives),
            budget_before=before,budget_after=self.budget())

    def target(self,index):
        case,identity = self.bundle['cases'][index],self.bundle['identities'][index]
        member,spent,batches = core.empty(),0,[]
        budget_before,model_before,acq_before = self.budget(),sum(self.timings.values()),self.acquisition_seconds
        bank = self.state['a' if case['context']=='A' else 'b']
        pooled_before = deepcopy(bank['pools'][identity])
        plan = self.timed('planning',core.make_plan,member,case,self.state,identity,index,self.cache,self.work)
        initial = self.retain(plan,identity)
        while not (plan['utility_lower']>=2 or plan['goal_impossible']) and spent+MEMBER_BATCH<=MEMBER_CAP and self.budget()['available']>=MEMBER_BATCH:
            choice = self.timed('planning',acquisition.choose,member,plan,spent,self.work,acquisition_call=True)
            operator,start = choice['operator'],sum(member[choice['operator']].values())
            increments = dict.fromkeys(core.ALPHABETS[operator],0)
            primitive_steps = []
            for _ in range(MEMBER_BATCH):
                observed = self.primitive('MEMBER',case['context'],identity,operator,index=index,role='member')
                increments[observed['outcome']] += 1
                primitive_steps.append(observed['step_index'])
            for category,count in increments.items():
                member[operator][category] += count
            spent += MEMBER_BATCH
            plan = self.timed('planning',core.make_plan,member,case,self.state,identity,index,self.cache,self.work)
            batches.append(dict(operator=operator,choice=choice,draw_start=start,draw_end=start+MEMBER_BATCH,
                increments=increments,primitive_steps=primitive_steps,spent=spent,plan=self.retain(plan,identity)))
        terminal = batches[-1]['plan'] if batches else initial
        completed = core.ready(plan)
        mix = deepcopy(plan['mix']) if completed else [('WAIT',F(1))]
        pooled_terminal,budget_terminal = deepcopy(bank['pools'][identity]),self.budget()
        self.write('decisions',dict(life=self.life,arm=self.arm,index=index,identity=identity,
            terminal_plan=terminal,executed_mix=mix,member=deepcopy(member),pooled_after_terminal=pooled_terminal,budget=budget_terminal))
        actual = self.execute(index,case,identity,mix)
        execution_resolved = plan['utility_lower']>=2 or plan['goal_impossible']
        reason = 'joint_ready' if completed else 'direct_unresolved_no_shared_budget' if execution_resolved else 'member_cap' if spent==MEMBER_CAP else 'budget_exhausted'
        row = dict(life=self.life,arm=self.arm,index=index,identity=identity,case=deepcopy(case),initial_plan=initial,
            batches=batches,terminal_plan=terminal,member=deepcopy(member),spent=spent,
            pooled_before=pooled_before,pooled_after_terminal=pooled_terminal,pooled_after_execution=deepcopy(bank['pools'][identity]),
            source_paid_samples=self.fees['source'],shared_paid_before=budget_before['fees']['shared'],
            history_paid_samples=budget_before['fees']['member'],execution_paid_before=budget_before['fees']['execution'],
            budget_before=budget_before,budget_terminal=budget_terminal,budget_after=self.budget(),
            budget_exhausted=budget_terminal['available']<MEMBER_BATCH,member_cap_exhausted=spent==MEMBER_CAP,
            execution_certified=plan['utility_lower']>=2,execution_resolved=execution_resolved,goal_impossible=plan['goal_impossible'],
            query_certified=plan['query_ready'],joint_completed=completed,fallback=not completed,stop_reason=reason,
            executed_mix=mix,actual_execution=actual,model_seconds=sum(self.timings.values())-model_before,
            acquisition_seconds=self.acquisition_seconds-acq_before)
        self.write('records',row)
        self.records.append(row)


def run_life_arm(life,arm,bundle):
    begun = perf_counter()
    with ExitStack() as stack:
        streams = {kind:stack.enter_context(gzip.open(filename(kind,life,arm),'wt')) for kind in FILE_KINDS}
        job = Lifecycle(life,arm,bundle,streams)
        job.source('A',3)
        job.shared_phase('A','A',3)
        for index in TARGETS:
            if index==30:
                job.timed('begin_b',core.begin_b,job.state,bundle['metadata']['changed_operator'],bundle['metadata']['b_to_a'],job.work)
                job.source('B',30)
                job.shared_phase('B','B',30)
            if index==54:
                job.shared_phase('A_RETURN','A',54)
            job.target(index)
            print(f'life={life} arm={arm} index={index} paid={job.step} joint={job.records[-1]["joint_completed"]}',flush=True)
    artifact = dict(life=life,arm=arm,records=job.records,auxiliary_records=job.auxiliary_records,
        fees=job.fees,primitive_samples=job.step,remaining_targets=job.remaining,cursors=job.cursors,
        unit_accounting=job.unit_accounting,shared_primitive_samples_by_operator=job.shared_primitive_samples_by_operator,
        shared_declared_row_sets=job.shared_declared_row_sets,
        final_state=job.state,timings=job.timings,acquisition_seconds=job.acquisition_seconds,
        observation_seconds=job.observation_seconds,output_seconds=job.output_seconds,worker_wall_seconds=perf_counter()-begun,
        work=job.work,profiles=len(job.profile_ids),cache_statistics=dict(direct_score_prefixes=len(job.cache),
            normalizers={name:function.cache_info()._asdict() for name,function in job.normalizers.items()}))
    save(OUTPUT/f'worker_artifacts_life_{life:02d}_{arm}.json',{key:value for key,value in artifact.items() if key!='records'})
    return artifact


def score_execution_plan(plan,case,law):
    """Posthoc numerical claims on every plan, including uncertified mixes."""
    pure = core.native.mechanics.vectors(case,law)
    actual = [sum(F(weight)*pure[policy][component] for policy,weight in plan['mix']) for component in range(3)]
    utility,risk,optimum = actual[0]+4*actual[2],actual[1],oracle_goal(case,law)
    upper,lower,risk_upper,box = (F(plan[key]) for key in ('goal_upper','utility_lower','risk_upper','box_goal_upper'))
    return dict(actual_utility=utility,actual_risk=risk,true_optimum=optimum,
        goal_upper=upper,box_goal_upper=box,utility_lower=lower,risk_upper=risk_upper,
        execution_certified=lower>=2,execution_resolved=lower>=2 or plan['goal_impossible'],goal_impossible=plan['goal_impossible'],
        query_certified=plan['query_ready'],joint_completed=plan['query_ready'] and (lower>=2 or plan['goal_impossible']),
        false_execution_certificate=lower>=2 and (utility<2 or risk>F(1,20)),
        false_impossible_certificate=plan['goal_impossible'] and optimum>=2,
        false_goal_upper=optimum>upper,false_utility_lower=utility<lower,false_risk_upper=risk>risk_upper,
        risk_violation=risk>F(1,20),new_impossible_vs_box=plan['goal_impossible'] and box>=2,nonlooser_goal_upper=upper<=box)


def score_execution_history(row,law):
    points = [(row['initial_plan'],0)]+[(batch['plan'],batch['spent']) for batch in row['batches']]
    return [dict(life=row['life'],arm=row['arm'],index=row['index'],identity=row['identity'],
        prefix_position=position,spent=spent,is_terminal=position==len(points)-1,
        **score_execution_plan(plan,row['case'],law)) for position,(plan,spent) in enumerate(points)]


def score_preview(row,law):
    plan = row['plan']
    queries = query_score(plan['queries'],law,plan['case'])
    return dict(life=row['life'],arm=row['arm'],preview_id=row['preview_id'],check_id=row['check_id'],index=row['index'],
        stage=row['stage'],context=row['context'],identity=row['identity'],cost_index=row['cost_index'],queries=queries,
        false_query_certificates=sum(decision['certified'] and queries[query]['regret']>F(1,20) for query,decision in plan['query_evidence']['queries'].items()),
        **score_execution_plan(plan,plan['case'],law))


def stage_aggregate(results):
    result = aggregate(results)
    result.update(execution_resolved=sum(row['execution_certified'] or row['goal_impossible'] for row in results),
        execution_unresolved=sum(not (row['execution_certified'] or row['goal_impossible']) for row in results),
        query_unresolved=sum(not row['query_certified'] for row in results),
        query_only_unresolved=sum(not row['query_certified'] and (row['execution_certified'] or row['goal_impossible']) for row in results),
        execution_only_unresolved=sum(row['query_certified'] and not (row['execution_certified'] or row['goal_impossible']) for row in results),
        both_unresolved=sum(not row['query_certified'] and not (row['execution_certified'] or row['goal_impossible']) for row in results),
        new_impossible_vs_box=sum(row['new_impossible_vs_box'] for row in results),
        executed_risk_violations=sum(row['executed']['violation'] for row in results),
        actual_execution_samples=sum(row['actual_execution']['actual_samples'] for row in results),
        realized_delivery=sum(row['actual_execution']['realized']['delivery'] for row in results),
        realized_failure=sum(row['actual_execution']['realized']['failure'] for row in results),
        realized_reward=sum(F(row['actual_execution']['realized']['reward']) for row in results),
        realized_goal_utility=sum(F(row['actual_execution']['realized']['goal_utility']) for row in results))
    return result


EXECUTION_ERRORS = ('false_execution_certificate','false_impossible_certificate','false_goal_upper',
    'false_utility_lower','false_risk_upper','risk_violation')


def summarize(results,auxiliary,execution_history,artifacts):
    methods,lives = {},[]
    for arm in ARMS:
        own = [row for row in results if row['arm']==arm]
        jobs = [item for item in artifacts if item['arm']==arm]
        fees = {kind:sum(job['fees'][kind] for job in jobs) for kind in ('source','shared','member','execution')}
        methods[arm] = dict(stage_aggregate(own),fees=fees,total_samples=sum(fees.values()),
            unit_accounting={field:sum(job['unit_accounting'][field] for job in jobs)
                for field in ('source_complete_units','source_tail_samples','shared_complete_units','shared_partial_units','shared_tail_samples')},
            shared_primitive_samples_by_operator={op:sum(job['shared_primitive_samples_by_operator'][op] for job in jobs) for op in core.OPERATORS},
            shared_declared_row_sets=dict(sum((Counter(job['shared_declared_row_sets']) for job in jobs),Counter())),
            aux_false_query_certificates=sum(row['false_query_certificates'] for row in auxiliary if row['arm']==arm),
            auxiliary_execution_errors={field:sum(row[field] for row in auxiliary if row['arm']==arm) for field in EXECUTION_ERRORS},
            history_execution_errors={field:sum(row[field] for row in execution_history if row['arm']==arm) for field in EXECUTION_ERRORS},
            execution_history_snapshots=sum(row['arm']==arm for row in execution_history),
            new_impossible_prefixes_vs_box=sum(row['new_impossible_vs_box'] for row in execution_history if row['arm']==arm),
            aux_new_impossible_vs_box=sum(row['new_impossible_vs_box'] for row in auxiliary if row['arm']==arm),
            all_goal_uppers_nonlooser_than_box=all(row['nonlooser_goal_upper'] for row in auxiliary+execution_history if row['arm']==arm),
            auxiliary_records=sum(job['auxiliary_records'] for job in jobs),
            late_b=stage_aggregate([row for row in own if 42<=row['index']<54]),
            a_return=stage_aggregate([row for row in own if row['stage']=='A_RETURN']),
            stages={stage:stage_aggregate([row for row in own if row['stage']==stage]) for stage in task.STAGES},
            model_seconds=sum(sum(job['timings'].values()) for job in jobs))
        for job in jobs:
            selected = [row for row in own if row['life']==job['life']]
            lives.append(dict(life=job['life'],arm=arm,fees=job['fees'],total_samples=sum(job['fees'].values()),
                unit_accounting=job['unit_accounting'],shared_primitive_samples_by_operator=job['shared_primitive_samples_by_operator'],
                shared_declared_row_sets=job['shared_declared_row_sets'],
                cap=TOTAL_CAPS[job['life']],stages={stage:stage_aggregate([row for row in selected if row['stage']==stage]) for stage in task.STAGES}))
    required = methods[ARMS[0]]
    controls = [methods[arm] for arm in ARMS[1:]]
    errors = ('false_query_certificates','false_execution_certificates','false_impossible_certificates','false_goal_uppers',
        'risk_violations','executed_risk_violations','aux_false_query_certificates')
    conditions = dict(late_b_quality=required['late_b']['query_certified']>=27,a_return_quality=required['a_return']['query_certified']>=54,
        matched_late_b_quality=all(required['late_b']['query_certified']>=control['late_b']['query_certified'] for control in controls),
        matched_a_return_quality=all(required['a_return']['query_certified']>=control['a_return']['query_certified'] for control in controls),
        matched_joint_quality=all(required['joint_completed']>=control['joint_completed'] for control in controls),
        actual_acquisition_saving=all(required['total_samples']<control['total_samples'] for control in controls),
        per_life_budgets=all(row['total_samples']<=row['cap'] for row in lives),
        valid_certificates_and_execution=all(method[field]==0 for method in methods.values() for field in errors)
            and all(value==0 for method in methods.values() for scope in ('auxiliary_execution_errors','history_execution_errors')
                for value in method[scope].values())
            and all(method['all_goal_uppers_nonlooser_than_box'] for method in methods.values()))
    paired = []
    for control in ARMS[1:]:
        before = {(row['life'],row['index']):row for row in results if row['arm']==control}
        for life in LIVES:
            own = [row for row in results if row['life']==life and row['arm']==ARMS[0]]
            paired.append(dict(life=life,control=control,
                control_minus_required_rows_samples=next(row['total_samples'] for row in lives if row['life']==life and row['arm']==control)-next(row['total_samples'] for row in lives if row['life']==life and row['arm']==ARMS[0]),
                query_gains=sum(row['query_certified'] and not before[life,row['index']]['query_certified'] for row in own),
                query_losses=sum(not row['query_certified'] and before[life,row['index']]['query_certified'] for row in own),
                execution_resolved_gains=sum((row['execution_certified'] or row['goal_impossible'])
                    and not (before[life,row['index']]['execution_certified'] or before[life,row['index']]['goal_impossible']) for row in own),
                execution_resolved_losses=sum(not (row['execution_certified'] or row['goal_impossible'])
                    and (before[life,row['index']]['execution_certified'] or before[life,row['index']]['goal_impossible']) for row in own),
                impossibility_gains=sum(row['goal_impossible'] and not before[life,row['index']]['goal_impossible'] for row in own),
                impossibility_losses=sum(not row['goal_impossible'] and before[life,row['index']]['goal_impossible'] for row in own),
                joint_gains=sum(row['joint_completed'] and not before[life,row['index']]['joint_completed'] for row in own),
                joint_losses=sum(not row['joint_completed'] and before[life,row['index']]['joint_completed'] for row in own)))
    return dict(complete=True,records=len(results),methods=methods,life_summaries=lives,paired=paired,
        conditions=conditions,stage_condition_met=all(conditions.values()),
        physical_source_samples=sum(job['fees']['source'] for job in artifacts),
        new_environment_observations=sum(sum(job['fees'].values()) for job in artifacts),
        model_seconds=sum(sum(job['timings'].values()) for job in artifacts),
        model_timings={scope:sum(job['timings'][scope] for job in artifacts) for scope in MODEL_SCOPES},
        acquisition_seconds=sum(job['acquisition_seconds'] for job in artifacts),acquisition_seconds_scope='subset_of_planning_process_CPU',
        model_seconds_scope='summed_process_CPU_all_initialization_pool_trajectory_query_plan_acquisition_and_execution_choice_once',
        observation_seconds=sum(job['observation_seconds'] for job in artifacts),output_seconds=sum(job['output_seconds'] for job in artifacts),
        auxiliary_records=sum(job['auxiliary_records'] for job in artifacts),
        execution_history_snapshots=len(execution_history),
        all_goal_uppers_nonlooser_than_box=all(method['all_goal_uppers_nonlooser_than_box'] for method in methods.values()),
        cache_statistics=[dict(life=job['life'],arm=job['arm'],profiles=job['profiles'],**job['cache_statistics']) for job in artifacts],
        work=[dict(life=job['life'],arm=job['arm'],**job['work']) for job in artifacts],
        actual_execution=True,realized_failures_are_certificate_errors=False,
        scientific_gate_changed=False,qualification_only=True,known_interface=True)


def capture():
    from scripts import audit_required_row_units_v260
    paths = {'src/acfqp/science/required_row_units_v260.py','scripts/run_required_row_units_v260.py',
        'scripts/audit_required_row_units_v260.py','tests/test_required_row_units_v260_core.py',
        'tests/test_required_row_units_v260_runner.py','tests/test_required_row_units_v260_audit.py','specs/REQUIRED_ROW_UNITS_V260.md'}
    for module in tuple(sys.modules.values()):
        source = getattr(module,'__file__',None)
        if source:
            path = Path(source).resolve()
            if path.is_relative_to(ROOT/'src') or path.is_relative_to(ROOT/'scripts'):
                paths.add(path.relative_to(ROOT).as_posix())
    for relative in sorted(paths):
        destination = OUTPUT/'source_code'/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/relative,destination)
    save(OUTPUT/'source_manifest.json',sorted(paths))


def run():
    begun = perf_counter()
    baseline = ROOT/'reports/continuous_row_cs_v259'
    read = lambda path:json.loads(path.read_text())
    if not read(baseline/'run.json')['complete'] or not read(baseline/'analysis.json')['valid'] or read(baseline/'summary.json')['stage_condition_met']:
        raise ValueError('V259 complete independently valid negative lifecycle is required')
    OUTPUT.mkdir(parents=True,exist_ok=False)
    worlds = {life:task.world(life) for life in LIVES}
    protocol = dict(lives=LIVES,arms=ARMS,targets=TARGETS,total_caps=TOTAL_CAPS,source_budget=SOURCE_COST,
        source_A_budget=3456,source_B_budget=1152,source_seed_base=SOURCE_BASE,shared_seed_base=SHARED_BASE,
        member_seed_base=MEMBER_BASE,execution_seed_base=EXECUTION_BASE,mix_seed_base=MIX_BASE,
        shared_batch=SHARED_BATCH,member_batch=MEMBER_BATCH,member_cap=MEMBER_CAP,
        shared_before_indexes=[3,30,54],query_streams=216,query_threshold=4320,query_delta='1/20',execution_delta='1/20',
        confidence_scope='per_life_fixed_arm_query_plus_execution_1/10_not_whole_cohort',
        execution_pool_event=720,execution_member_event=8640,execution_utility_threshold=2,execution_risk_limit='1/20',
        execution_cs_method_by_arm=dict(REQUIRED_ROWS_REUSE='continuous_compatible_jeffreys_prefixes',
            CONTINUOUS_REUSE='continuous_compatible_jeffreys_prefixes',TRAJECTORY_REBUILD='separate_native_source_pool_member_regions'),
        continuous_active_pool_streams=12,continuous_reserved_pool_streams=18,member_streams=216,
        continuous_compatibility='canonical_A_stream_for_unchanged_rows_B_changed_native_stream_no_new_events',
        execution_reserve='2_per_remaining_unexecuted_target_including_current',
        direct_unit='same_actual_unit_with_predeclared_rows_covering_fixed_comparison_required_rows',
        direct_point='native_current_context_raw_joint_mean_of_ALL_predeclared_units_only',
        shared_unit_by_arm=dict(REQUIRED_ROWS_REUSE='batch_frozen_uncertified_query_required_rows_union_ALL_if_any_cost_execution_unresolved',
            CONTINUOUS_REUSE='ALL_S_D_conditional_R',TRAJECTORY_REBUILD='ALL_S_D_conditional_R'),
        unit_reservation='declared_row_count_before_any_unit_observation_conditional_R_only_if_declared_and_D_RECOVERY',
        batch_tail='native_only_S_when_remaining_below_declared_maximum_not_query_or_point_evidence',
        transfer='same_whole_declared_unit_only_when_all_fixed_comparison_required_rows_unchanged',
        member_rule='old_V231_choose_only_while_execution_unresolved_query_markers_remain_actual',
        shared_preview='full_execution_and_direct_query_plan_empty_member_upcoming_real_target_index',
        type_ready='all_four_public_costs_execution_certified_or_goal_impossible_AND_query_ready',
        goal_upper='V258_full_original_risk_constrained_D_joint_CS_dual_and_minimum_with_original_box',
        preview_execution_validity='posthoc_all_numeric_goal_upper_utility_lower_risk_upper_and_impossibility_claims',
        target_execution_validity='all_initial_member_and_terminal_numeric_claims_after_global_freeze',
        execution_feedback='native_row_pool_after_terminal_freeze_not_member_or_direct_rounds',
        truth_scoring='only_after_all_648_targets_auxiliary_checks_and_actual_executions_frozen',
        comparison_scope='required_rows_vs_continuous_reuse_isolates_shared_unit_declaration_rebuild_is_strong_reference',
        prerequisites=dict(v259_complete=True,v259_independent_valid=True,v259_stage_negative=True),
        scientific_gate_changed=False,known_interface=True,qualification_only=True)
    capture()
    save(OUTPUT/'cases.json',[dict(life=life,cases=worlds[life][0]) for life in LIVES])
    save(OUTPUT/'interfaces.json',[dict(life=life,identities=worlds[life][2],metadata={key:worlds[life][3][key] for key in ('changed_operator','b_to_a','stage_ranges')}) for life in LIVES])
    save(OUTPUT/'run.json',dict(protocol,complete=False,phases=['protocol_and_public_roster_frozen','source_captured']))
    with ProcessPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(run_life_arm,life,arm,dict(cases=worlds[life][0],laws=worlds[life][1],identities=worlds[life][2],metadata={key:worlds[life][3][key] for key in ('changed_operator','b_to_a')})) for life in LIVES for arm in ARMS]
        artifacts = [future.result() for future in futures]
    save(OUTPUT/'run.json',dict(protocol,complete=False,phases=['protocol_and_public_roster_frozen','source_captured','all_648_targets_auxiliary_and_executions_frozen']))
    results,auxiliary,execution_history,scoring_seconds = [],[],[],0.
    for job in artifacts:
        life,arm = job['life'],job['arm']
        with (gzip.open(filename('results',life,arm),'wt') as stream,
              gzip.open(filename('execution_history_results',life,arm),'wt') as history_stream):
            for row in job['records']:
                started = perf_counter()
                history = score_execution_history(row,worlds[life][1][row['index']])
                result = dict(evaluate(row,worlds[life][1][row['index']]),actual_execution=row['actual_execution'],
                    new_impossible_vs_box=history[-1]['new_impossible_vs_box'])
                scoring_seconds += perf_counter()-started
                write_row(stream,result)
                results.append(result)
                for point in history:
                    write_row(history_stream,point)
                    execution_history.append(point)
        with gzip.open(filename('preview_results',life,arm),'wt') as stream:
            for row in rows(filename('previews',life,arm)):
                started = perf_counter()
                score = score_preview(row,worlds[life][1][row['identity'] if row['context']=='A' else 27+row['identity']])
                scoring_seconds += perf_counter()-started
                write_row(stream,score)
                auxiliary.append(score)
    summary = dict(summarize(results,auxiliary,execution_history,artifacts),elapsed_seconds=perf_counter()-begun,scoring_seconds=scoring_seconds,
        worker_wall_seconds={f'{job["life"]}:{job["arm"]}':job['worker_wall_seconds'] for job in artifacts})
    save(OUTPUT/'summary.json',summary)
    save(OUTPUT/'run.json',dict(protocol,complete=True,phases=['protocol_and_public_roster_frozen','source_captured','all_648_targets_auxiliary_and_executions_frozen','posthoc_truth_scored','complete']))
    print(json.dumps(exact_json(summary)),flush=True)
    return summary


if __name__=='__main__':
    run()
