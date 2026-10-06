"""Verify V251 roster/fees/provenance and the frozen three-variant barrier."""
from collections import Counter
from copy import deepcopy
import gzip
import json
import pytest

from scripts import run_information_axes_v252 as runner


def baseline(tmp_path):
    directory = tmp_path/'baseline'
    directory.mkdir()
    runner.save(directory/'run.json', dict(complete=True))
    runner.save(directory/'analysis.json', dict(valid=True))
    anchors = {op: {cat: 0 for cat in runner.core.joint.ALPHABETS[op]} for op in runner.core.joint.OPERATORS}
    aa, bb = deepcopy(anchors), deepcopy(anchors)
    for op in aa:
        aa[op][next(iter(aa[op]))] = 384
        bb[op][next(iter(bb[op]))] = 128
    runner.save(directory/'source_evidence.json', [dict(life=life, a=[aa]*3, b=[bb]*3) for life in runner.LIVES])
    runner.save(directory/'probe_ledgers.json', [dict(life=life, arm=arm, paid_samples=3072+1152,
        released_samples=0, by_context=dict(A=3072, B=1152)) for life in runner.LIVES for arm in runner.ARMS])
    for life in runner.LIVES:
        for arm in runner.ARMS:
            with (gzip.open(directory/f'records_life_{life:02d}_{arm}.jsonl.gz','wt') as stream,
                  gzip.open(directory/f'profiles_life_{life:02d}_{arm}.jsonl.gz','wt') as profiles):
                history = 0
                for index in tuple(range(3,27))+tuple(range(30,78)):
                    spent = 32 if 54 <= index < 62 else 16
                    fees = dict(source_paid_samples=3456 if index < 30 else 4608,
                        history_paid_samples=history, ordinary_history_paid_samples=history,
                        actual_probe_paid_before=3072 if index < 30 else 4224,
                        pending_probe_reserved=1152 if index < 30 else 0,
                        released_probe_samples=0, probe_cap_samples=4224, probe_quota_samples=4224,
                        future_B_source_reserved=1152 if index < 30 else 0,
                        current_paid_samples=spent,new_paid_samples=spent,
                        total_reference_paid_samples=(3456+3072 if index<30 else 4608+4224)+history+spent,
                        life_budget_remaining_before=1000,life_budget_remaining_after=1000-spent)
                    row = dict(life=life,index=index,arm=arm,identity=0,
                        case=dict(stage='A' if index<30 else 'B' if index<54 else 'A_RETURN', context='A',id=f'{life}/{index}'),
                        terminal_plan=dict(evidence_counts={'paid':index},joint_constraints={},
                            query_evidence=dict(queries={'goal':dict(policy='SHORT',
                                comparisons=[dict(other='DETOUR_RETRY',certified=index>=62,profile_id=index)])})),
                        member={},spent=spent,budget_exhausted=False,member_cap_exhausted=False,**fees)
                    stream.write(json.dumps(row)+'\n')
                    profiles.write(json.dumps(dict(profile_id=index,certificate=dict(source_index=index,witness_kind='global_likelihood_dual')))+'\n')
                    history += spent
    return directory


def classification(status='unknown'):
    return dict(candidate=dict(kernel=None),canonical_inside=None,all_query_inside=None,
        all_execution_inside=None,query_regions={},execution_regions=[],status=status)


def test_complete_roster_native_counts_and_full_lifecycle_probe_fees(monkeypatch,tmp_path):
    directory=baseline(tmp_path)
    monkeypatch.setattr(runner,'BASELINE',directory)
    selected,fees=runner.endpoints()
    assert len(selected)==48
    assert Counter((r['life'],r['arm']) for r in selected)=={(life,arm):8 for life in runner.LIVES for arm in runner.ARMS}
    assert all(row['index']<62 and row['evidence_counts']['paid']==row['index'] for row in selected)
    assert all(set(row['retained_fees'])==set(runner.FEE_FIELDS) for row in selected)
    assert all(row['source_samples']==4608 and row['ordinary_target_samples']==72*16+8*16 for row in fees)
    assert all(row['a_probe_samples']==3072 and row['b_probe_samples']==1152 and row['probe_samples']==4224 for row in fees)
    assert all(row['total_samples']==4608+1280+4224 for row in fees)
    assert 'QUERY_FIXED' not in runner.ARMS


def test_require_same_paired_failure_roster(monkeypatch,tmp_path):
    directory=baseline(tmp_path)
    path=directory/'records_life_00_QUERY_SHARED.jsonl.gz'
    records=list(runner.rows(path))
    for row in records:
        if row['index'] in (61,62):
            row['terminal_plan']['query_evidence']['queries']['goal']['comparisons'][0]['certified']=row['index']==61
    with gzip.open(path,'wt') as stream:
        stream.writelines(json.dumps(row)+'\n' for row in records)
    monkeypatch.setattr(runner,'BASELINE',directory)
    with pytest.raises(ValueError,match='same paired'):
        runner.endpoints()


def test_three_variant_union_and_all_pairwise_statuses_do_not_promote_rejections():
    records=[dict(life=life,index=index,arm=arm,variant=variant,
        **classification('full_region_bad_witness' if index==54 else 'paid_constraints_reject_candidate'))
        for life in runner.LIVES for index in range(54,62) for arm in runner.ARMS for variant in runner.VARIANTS]
    summary=runner.summarize(records,[])
    assert summary['records']==144 and summary['endpoints']==48
    assert summary['status_counts']['full_region_bad_witness']==18
    assert summary['status_counts']['paid_constraints_reject_candidate']==126
    assert all(item['distinct_full_bad_endpoints']==3 and item['same_evidence_query_certificate_ceiling']==69
        for item in summary['arm_full_bad_endpoint_unions'])
    assert len(summary['paired_arm_statuses'])==3 and len(summary['within_arm_variant_statuses'])==6
    assert all(item['pairs']==24 and not item['status_changes'] for item in summary['within_arm_variant_statuses'])
    assert summary['diagnostic_only'] and not summary['scientific_gate_changed']
    assert 'stage_condition_met' not in summary


def test_roster_and_source_freeze_before_144_classifications_with_per_arm_profiles(monkeypatch,tmp_path):
    directory=baseline(tmp_path)
    output,calls=tmp_path/'output',[]
    monkeypatch.setattr(runner,'ROOT',tmp_path)
    monkeypatch.setattr(runner,'BASELINE',directory)
    monkeypatch.setattr(runner,'OUTPUT',output)
    monkeypatch.setattr(runner,'capture',lambda:calls.append('source_captured'))
    def classify(counts,constraints,case,certificate):
        protocol=runner.read(output/'run.json')
        assert calls[0]=='source_captured'
        assert len(protocol['roster'])==len(runner.read(output/'endpoints.json'))==48
        assert protocol['phases']==['protocol_frozen','roster_frozen'] and not protocol['complete']
        assert counts['paid']==certificate['source_index']
        calls.append(case['id'])
        return dict(variants={variant:classification() for variant in runner.VARIANTS},
            empirical_rows={},distances={variant:{} for variant in runner.VARIANTS})
    monkeypatch.setattr(runner.core,'classify',classify)
    result=runner.run()
    assert len(calls)==49 and result['records']==144
    records=runner.read(output/'records.json')
    assert Counter(row['variant'] for row in records)==dict.fromkeys(runner.VARIANTS,48)
    assert all(row['profile_provenance']['file']==f'profiles_life_{row["life"]:02d}_{row["arm"]}.jsonl.gz' for row in records)
    assert all(row['profile_provenance']['profile_id']==row['profile_id'] and row['profile_provenance']['family']=='S_D_FULL_R' for row in records)
    assert result['new_observations']==result['new_optimizer_calls']==result['new_query_certificates']==result['posthoc_scoring_calls']==0
    assert runner.read(output/'run.json')['complete']
