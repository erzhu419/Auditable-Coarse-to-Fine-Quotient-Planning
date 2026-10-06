"""Complete-root loading and label-independent model candidate features."""
from collections import Counter
import gzip,json
from pathlib import Path
import numpy as np
import pytest
from acfqp.science import controlled_predictive_candidate_data_v100 as module
from acfqp.science.controlled_predictive_root_coverage_v98 import source_seed,branch_seed
WORK=Counter()

@pytest.fixture(scope='module',autouse=True)
def ledger(request):
    before=request.session.testsfailed
    yield
    p=Path(__file__).resolve().parents[1]/'reports/controlled_predictive_candidate_data_v100.checks.json'
    r=json.loads(p.read_text()) if p.exists() else {'attempts':[]}
    r['attempts'].append(dict(failures=request.session.testsfailed-before,mock_work=dict(WORK),new_environment_transitions=0,new_synthetic_transitions=0,neural_model_fits=0))
    p.write_text(json.dumps(r,indent=2)+'\n')

def write_rows(path, rows):
    with gzip.open(path, "wt") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def batch(folder, replicas):
    board, raw, accepted, records = [1] * 10 + [0] * 6, [], [], []
    work, planning, outcomes = Counter(), Counter(), Counter()
    partition = {name: dict(source_transitions=0, branch_transitions=0, total_transitions=0)
                 for name in ("training", "heldout", "unincorporated")}
    for cursor in (7, 8, 9):
        episode, qi = divmod(cursor, 2)
        query = tuple(module.QUERIES)[qi]
        root = dict(board=board, episode=episode, query=query, step=0,
                    source_seed=source_seed(9, episode, query))
        complete = cursor != 9
        disposition = ("training" if episode % 5 != 4 else "heldout") if complete else "unincorporated"
        size = replicas if complete else replicas // 2
        seed_base = branch_seed(9, episode, query)
        for replica in range(size):
            for index, option in enumerate(module.OPTIONS):
                seed = seed_base + replica
                steps = [dict(board=board, next_board=board, score=4 * (index + 1),
                    status="LOST" if step == 21 else "ACTIVE") for step in range(22)]
                ground, controller_work = {"sampled_transitions": 22, "environment_random_draws": 44}, {"model_uniform_draws": 88}
                raw.append(dict(root=root, option=option, replica=replica, env_seed=seed, model_seed=seed + 10 ** 12,
                    game=dict(seed=seed, initial_board=board, initial_spawns=[], final_board=board,
                        steps=steps, return_score=88 * (index + 1), status="LOST", work=ground),
                    planning_counts=controller_work, controller=dict(selected_option=option, initiation_step=0,
                        fragment_actions=0 if option == "H2" else int(option.split("_")[1]))))
                work.update(ground)
                planning.update(controller_work)
                outcomes["LOST"] += 1
        branch_steps = size * 5 * 22
        record = dict(cursor=cursor, episode=episode, query=query, replicas=replicas, root=root,
            branch_seed=seed_base, source_status="LOST", branch_trajectories=size * 5,
            branch_transitions=branch_steps, source_transitions=2, branch_cutoff_trajectories=0,
            complete_block=complete, disposition=disposition, paired_rows=replicas * 4 * 2 if complete else 0)
        records.append(record)
        for name, value in (("source_transitions", 2), ("branch_transitions", branch_steps), ("total_transitions", branch_steps + 2)):
            partition[disposition][name] += value
        if complete:
            accepted.append(dict(root, replicas=replicas, heldout=episode % 5 == 4,
                paired_rows=replicas * 8, source_transitions=2, branch_transitions=branch_steps))
    source_work = dict(sampled_transitions=6, environment_random_draws=24)
    counts = dict(complete_roots=2, training_roots=1, heldout_roots=1, paired_rows=replicas * 16,
        training_paired_rows=replicas * 8, heldout_paired_rows=replicas * 8,
        terminal_anchor_rows=replicas * 8, bootstrap_rows=replicas * 8)
    acquisition = dict(life=9, replicas=replicas, budget=6 + work["sampled_transitions"],
        used_transitions=6 + work["sampled_transitions"], start_cursor=7, next_cursor=10, episode_cutoff=6,
        root_records=records, completed_roots=accepted, counts=counts, cost_partition=partition,
        source=dict(ground_work=source_work, planning_counts={"model_uniform_draws": 24}),
        branches=dict(ground_work=dict(work), planning_counts=dict(planning), outcomes=dict(outcomes)))
    (folder / "construction.json").write_text(json.dumps(dict(acquisition=acquisition)))
    write_rows(folder / "branch_games.jsonl.gz", raw)
    return acquisition, raw



def mock_prefix(board,query,option,replica,seed,rule):
    oi=module.OPTIONS.index(option); final=list(board);final[0]=oi+1
    duration=0 if option=='H2' else int(option.split('_')[1])
    WORK['mock_prefixes']+=1
    return dict(option=option,replica=replica,spawn_seed=seed,planning_seed=seed+10**12,
        initial_board=list(board),final_board=final,status='ACTIVE',steps_count=4,
        steps=[dict(status='ACTIVE') for _ in range(4)],direct=[oi*.1,0,0],
        controller=dict(events=[{}],initiation_step=0,fragment_actions=duration),
        action_paths=['fragment']*duration+['H2']*(4-duration),
        model_work=dict(synthetic_transitions=4,spawn_uniform_draws=8),planning_counts=dict(model_uniform_draws=16))

@pytest.mark.parametrize('replicas',[4,8])
def test_complete_blocks_labels_and_separate_feature_streams(tmp_path,monkeypatch,replicas):
    acq,raw=batch(tmp_path,replicas);monkeypatch.setattr(module,'_simulate_prefix',mock_prefix)
    output=tmp_path/'new';output.mkdir()
    records,log=module.load_batch(tmp_path,output,None,9)
    assert len(records)==2 and log['counts']['excluded_roots']==1
    assert log['counts']['training_roots']==log['counts']['heldout_roots']==1
    assert not any(r['query']=='risk_goal' and r['episode']==4 for r in records)
    assert log['model_prefix_trajectories']==320 and log['new_model_work']['synthetic_transitions']==1280
    assert log['inherited_acquisition']['used_transitions']==acq['used_transitions']
    for r in records:
        assert np.asarray(r['features']).shape==(5,121)
        assert r['utilities']==pytest.approx([88*i/2048 for i in range(5)])
        assert r['prefix_seed']!=next(g['env_seed'] for g in raw if g['root']['query']==r['query'])
    for r in raw: r['game']['return_score']+=1000*module.OPTIONS.index(r['option'])
    write_rows(tmp_path/'branch_games.jsonl.gz',raw)
    out2=tmp_path/'changed';out2.mkdir()
    changed,_=module.load_batch(tmp_path,out2,None,9)
    assert [r['features'] for r in changed]==[r['features'] for r in records]
    assert [r['utilities'] for r in changed]!=[r['utilities'] for r in records]


def test_scalar_selector_no_fake_rfs_and_prefix_zero_neural_calls(monkeypatch):
    monkeypatch.setattr(module,'_simulate_prefix',mock_prefix)
    board=[1]*10+[0]*6
    selector=module.CandidateSelector(None,None,42,replicas=2);work=Counter()
    event=selector.select(board,'reward',work=work)
    assert event['option']=='SNAKE_4' and event['score_semantics']=='prefix_utility'
    assert event['predicted_advantage'] is None
    assert all(set(p)=={'value'} for p in event['predictions'].values())
    assert selector.last_log['value_counts']=={'prefix_only_decisions':1}
    assert work['candidate_trajectories']==10 and all(selector.last_log['wiring'].values())
