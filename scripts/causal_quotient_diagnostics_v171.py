"""Heldout observed-transition/boundary diagnostics; never fit on these labels."""
from collections import Counter

from acfqp.domains import standard_2048 as ground
from acfqp.domains.g2048 import D4Transform
from acfqp.science.controlled_predictive_causal_quotient_v171 import state_key
from acfqp.science.controlled_predictive_program_consolidation_v161 import canonical_frame,INVERSE


def mean(values):
    values=[v for v in values if v is not None]
    return sum(values)/len(values) if values else None


def vector_mean(values):
    values=[v for v in values if v is not None]
    return [mean([v[k] for v in values]) for k in range(3)] if values else None


def prediction_report(models,rows):
    by_life={m.life:m for m in models};entries=[];counts=Counter()
    kernels={m.life:{(r['state'],r['action']):r for r in m.payload['rows']} for m in models}
    tails={m.life:{r['state']:r['component_mean'] for r in m.payload['tails']} for m in models}
    for row in rows:
        life=row['life'];model=by_life[life];board=tuple(row['root_board']);remaining=sum(row['scores'])
        key=state_key(board,counts);brier=[];immediate=[];tail=[];local=Counter()
        for step,action in enumerate(row['actions']):
            canonical,frame=canonical_frame(board);counts['diagnostic_board_transforms']+=8
            label=ground.transform_action_v1(ground.Swipe2048Action(action),D4Transform(frame)).value
            counts['diagnostic_action_transports']+=1
            next_board=list(row['choices'][step]['afterstate']);next_board[row['spawned_cells'][step]]=row['spawned_ranks'][step]
            next_key=state_key(next_board,counts);counts['diagnostic_model_rows_read']+=1
            kernel=kernels[life].get((key,label))
            if kernel is not None and kernel['count']>=8:
                probs={edge['next_state']:edge['count']/kernel['count'] for edge in kernel['outcomes']}
                brier.append(1+sum(p*p for p in probs.values())-2*probs.get(next_key,0.))
                pred=[sum(edge['count']*edge[field] for edge in kernel['outcomes'])/kernel['count'] for field in ('reward_mean','failure','success')]
                actual=[row['scores'][step]/2048.,float(next_key=='LOST'),float(next_key=='WON')]
                immediate.append([(a-b)**2 for a,b in zip(pred,actual)])
                local['transition_supported']+=1
            else:local['transition_missing']+=1
            if step:
                counts['diagnostic_tail_rows_read']+=1
                boundary=tails[life].get(key)
                if boundary is None:local['tail_missing']+=1
                else:
                    actual=[remaining/2048.,float(row['result']['status']=='LOST'),float(row['result']['status']=='WON')]
                    tail.append([(a-b)**2 for a,b in zip(boundary,actual)]);local['tail_supported']+=1
            legal=[]
            for label in ('DOWN','LEFT','RIGHT','UP'):
                _,_,active=ground.swipe_board_v1(canonical,ground.Swipe2048Action(label));counts['diagnostic_ground_legality_swipes']+=1
                if active:legal.append(label)
            choices=[]
            for depth in (1,3):
                candidates=[]
                for action_label in legal:
                    vector=model.q(key,action_label,depth);counts['diagnostic_Q_reads']+=1
                    if vector is not None:candidates.append((-(vector[0]-vector[1]+vector[2]),action_label))
                chosen=min(candidates)[1] if candidates else None
                actual=None if chosen is None else ground.transform_action_v1(ground.Swipe2048Action(chosen),INVERSE[D4Transform(frame)]).value
                if chosen is not None:counts['diagnostic_action_transports']+=1
                choices.append(actual)
            if all(c is not None for c in choices):
                local['composition_supported']+=1;local['composition_action_disagreements']+=choices[0]!=choices[1]
            else:local['composition_missing']+=1
            remaining-=row['scores'][step];board=tuple(next_board);key=next_key
            counts['diagnostic_label_steps']+=1
        entries.append(dict(branch_id=row['branch_id'],life=life,steps=len(row['actions']),counts=dict(local),
            transition_brier=mean(brier),immediate_component_mse=vector_mean(immediate),tail_component_mse=vector_mean(tail)))
    histories=[]
    for life in range(4):
        selected=[r for r in entries if r['life']==life];total=Counter()
        for r in selected:total.update(r['counts'])
        histories.append(dict(life=life,branches=len(selected),steps=sum(r['steps'] for r in selected),counts=dict(total),
            transition_brier=mean([r['transition_brier'] for r in selected]),
            immediate_component_mse=vector_mean([r['immediate_component_mse'] for r in selected]),
            tail_component_mse=vector_mean([r['tail_component_mse'] for r in selected])))
    return dict(schema='acfqp.causal_quotient.v171.prediction',per_branch=entries,per_history=histories,
        pooled=dict(transition_brier=mean([h['transition_brier'] for h in histories]),
            immediate_component_mse=vector_mean([h['immediate_component_mse'] for h in histories]),
            tail_component_mse=vector_mean([h['tail_component_mse'] for h in histories])),logical_work=dict(counts),
        scope='observed actions and fixed H2 continuation only; conditional supported predictions, coverage retained;branch then history equalweight')
