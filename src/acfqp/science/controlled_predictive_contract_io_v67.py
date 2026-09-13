"""Serialize predictive contracts and the literal states still required above H1."""
from dataclasses import asdict
from collections import defaultdict


def load_state_index(payload):
    """Recover executable encoder-key routing without concrete H1 members."""
    cells={cell:(layer,status) for cell,layer,status in payload['cells']}
    index={(layer,status):cell for cell,(layer,status) in cells.items() if status!='ACTIVE'}
    for cell,board in payload['literal_boards']:
        index[cells[cell][0],tuple(board)]=cell
    if payload['rule']['variant']=='BASELINE':
        return index
    rows=defaultdict(dict)
    for cell,action,outcomes in payload['rows']:
        rows[cell][action]=outcomes
    for cell,(layer,status) in cells.items():
        if layer!=1 or status!='ACTIVE':
            continue
        contract=[]
        for action in ('UP','DOWN','LEFT','RIGHT'):
            if action not in rows[cell]:
                continue
            outcomes=rows[cell][action]
            reward=round(outcomes[0][2]*2048)
            won=round(10*sum(p for p,target,_ in outcomes if cells[target][1]=='WON'))
            lost=round(10*sum(p for p,target,_ in outcomes if cells[target][1]=='LOST'))
            contract.append((action,reward,won,lost))
        if payload['rule']['variant']=='CONTRACT':
            key=('ACTION_CONTRACT',tuple(contract))
        else:
            key=('REWARD_ONLY_CONTRACT',tuple((a,r) for a,r,_,_ in contract))
        index[1,key]=cell
    return index


def model_payload(build, compiled):
    return dict(schema='acfqp.action_contract_model.v67',rule=asdict(build.rule),
        cells=[[cell,row.layer,row.terminal] for cell,row in sorted(compiled.cells.items())],
        rows=[[cell,action,[[o.probability,o.next_state,o.reward] for o in outcomes]]
              for (cell,action),outcomes in sorted(compiled.rows.items())],
        roots=list(compiled.roots),
        literal_boards=[[compiled.state_to_cell[state],list(board)] for state,board in sorted(build.boards.items())],
        contract_cell_index='For H1 contract cells, action reward and terminal probabilities in rows define the encoding key; no concrete members are stored.')
