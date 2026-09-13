import json

from acfqp.science.controlled_predictive_contract_io_v67 import load_state_index


def test_restore_h1_contract_routing_from_rows_without_board_members():
    board=[2,2,3,4]*4
    payload=dict(rule=dict(variant='CONTRACT'),
        cells=[[0,2,'ACTIVE'],[1,1,'ACTIVE'],[2,0,'LOST'],[3,0,'CUTOFF']],
        literal_boards=[[0,board]],
        rows=[[0,'LEFT',[[1.,1,0.]]],
              [1,'DOWN',[[1.,3,8/2048]]],
              [1,'UP',[[.9,2,4/2048],[.1,3,4/2048]]]])
    restored=load_state_index(json.loads(json.dumps(payload)))
    assert restored=={
        (2,tuple(board)):0,
        (1,('ACTION_CONTRACT',(('UP',4,0,9),('DOWN',8,0,0)))):1,
        (0,'LOST'):2,(0,'CUTOFF'):3}
