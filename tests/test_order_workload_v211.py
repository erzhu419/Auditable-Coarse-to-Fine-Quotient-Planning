from scripts import order_workload_v211 as workload
from acfqp.science import mechanism_switch_task_v205 as task

def test_interleaved_roster_retains_known_weather_transfer():
    roster=task.roster();original=workload.sequence(roster,'original');changed=workload.sequence(roster,'interleaved')
    assert {c['id'] for c in original}=={c['id'] for c in changed} and len(changed)==12
    assert [c['weather'] for c in changed[:3]]==['wet','normal','blocked']
    assert all(c['weather'] in {x['weather'] for x in changed[:8]} for c in changed[8:])
    assert all(c['weather']!='normal' and c['operating']=='low' for c in changed[8:])

def test_sampling_stream_is_context_paired_not_position_paired():
    roster=task.roster();original=workload.sequence(roster,'original');changed=workload.sequence(roster,'interleaved')
    streams={c['id']:tuple(workload.sample_seed(3,c,i,roster) for i in range(3)) for c in original}
    assert streams=={c['id']:tuple(workload.sample_seed(3,c,i,roster) for i in range(3)) for c in changed}
    assert len({seed for row in streams.values() for seed in row})==36
