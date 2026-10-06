"""Check the paired roster, retained fees, and candidate-free freeze barrier."""
from collections import Counter
import gzip
import json
import pytest

from scripts import run_endpoint_regions_v248 as runner


def baseline(tmp_path):
    directory = tmp_path/'baseline'
    directory.mkdir()
    prefix = [dict(life=life, source_paid_samples=4608, history_paid_samples=1000+life,
        total_prefix_paid_samples=5608+life) for life in runner.LIVES]
    runner.save(directory/'prefix_ledgers.json', prefix)
    runner.save(directory/'run.json', dict(complete=True))
    runner.save(directory/'analysis.json', dict(valid=True))
    for life in runner.LIVES:
        with (gzip.open(directory/f'records_life_{life:02d}.jsonl.gz', 'wt') as records,
              gzip.open(directory/f'profiles_life_{life:02d}.jsonl.gz', 'wt') as profiles):
            for index in range(54, 78):
                for arm in runner.ARMS:
                    spent = 32 if index < 62 else 16
                    row = dict(life=life, index=index, arm=arm, identity=0,
                        case=dict(stage='A_RETURN', context='A', id=f'{life}/{index}/{arm}'),
                        terminal_plan=dict(evidence_counts={'paid': index}, joint_constraints={},
                            query_evidence=dict(queries={'goal': dict(policy='SHORT',
                                comparisons=[dict(other='DETOUR_RETRY', certified=index >= 62, profile_id=index)])})),
                        member={}, spent=spent, source_paid_samples=4608, history_paid_samples=1000,
                        current_paid_samples=spent, total_reference_paid_samples=5608+spent,
                        life_budget_remaining_before=100, life_budget_remaining_after=100-spent,
                        budget_exhausted=False, member_cap_exhausted=False)
                    records.write(json.dumps(row)+'\n')
                profiles.write(json.dumps(dict(profile_id=index, certificate=dict(source_index=index)))+'\n')
    return directory


def classification(status='unknown'):
    return dict(candidate=dict(kernel=None), canonical_inside=None, all_query_inside=None,
        all_execution_inside=None, query_regions={}, execution_regions=[], status=status)


def test_roster_is_complete_paired_and_costs_include_successful_targets(monkeypatch, tmp_path):
    directory = baseline(tmp_path)
    monkeypatch.setattr(runner, 'BASELINE', directory)
    selected, fees = runner.endpoints()
    assert len(selected) == 48
    assert Counter((row['life'], row['arm']) for row in selected) == {
        (life, arm): 8 for life in runner.LIVES for arm in runner.ARMS}
    assert all(row['index'] < 62 for row in selected)
    assert all(row['new_return_samples'] == 8*32+16*16 for row in fees)
    assert all(row['total_samples'] == 5608+row['life']+512 for row in fees)


def test_roster_requires_same_paired_identities(monkeypatch, tmp_path):
    directory = baseline(tmp_path)
    path = directory/'records_life_00.jsonl.gz'
    records = list(runner.rows(path))
    for row in records:
        if row['arm'] == 'JOINT_PREDICTION' and row['index'] in (61, 62):
            row['terminal_plan']['query_evidence']['queries']['goal']['comparisons'][0]['certified'] = row['index'] == 61
    with gzip.open(path, 'wt') as stream:
        stream.writelines(json.dumps(row)+'\n' for row in records)
    monkeypatch.setattr(runner, 'BASELINE', directory)
    with pytest.raises(ValueError, match='same paired'):
        runner.endpoints()


def test_bad_endpoint_union_does_not_double_count_two_variants():
    records = [dict(life=life, index=index, arm=arm, variant=variant,
        **classification('full_region_bad_witness' if index == 54 else 'unknown'))
        for life in runner.LIVES for index in range(54, 62) for arm in runner.ARMS for variant in runner.VARIANTS]
    summary = runner.summarize(records, [])
    assert summary['records'] == 96 and summary['endpoints'] == 48
    assert summary['status_counts']['full_region_bad_witness'] == 12
    assert all(row['distinct_full_bad_endpoints'] == 3 and row['same_evidence_query_certificate_ceiling'] == 69
               for row in summary['arm_full_bad_endpoint_unions'])
    assert all(row['pairs'] == 24 and not row['status_changes'] for row in summary['paired_arm_statuses'])
    assert all(row['pairs'] == 24 and not row['status_changes'] for row in summary['within_arm_variant_statuses'])


def test_all_endpoints_freeze_before_any_classification_and_both_variants_are_saved(monkeypatch, tmp_path):
    directory = baseline(tmp_path)
    output, calls = tmp_path/'output', []
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'BASELINE', directory)
    monkeypatch.setattr(runner, 'OUTPUT', output)
    monkeypatch.setattr(runner, 'capture', lambda: calls.append('source_captured'))

    def classify(counts, constraints, case, certificate):
        protocol = runner.read(output/'run.json')
        assert calls[0] == 'source_captured'
        assert len(protocol['roster']) == len(runner.read(output/'endpoints.json')) == 48
        assert protocol['phases'] == ['protocol_frozen', 'roster_frozen'] and not protocol['complete']
        assert counts['paid'] == certificate['source_index']
        calls.append(case['id'])
        return dict(variants={variant: classification() for variant in runner.VARIANTS},
                    empirical_rows={}, distances={variant: {} for variant in runner.VARIANTS})

    monkeypatch.setattr(runner.core, 'classify', classify)
    result = runner.run()
    assert len(calls) == 49 and result['records'] == 96
    records = runner.read(output/'records.json')
    assert Counter(row['variant'] for row in records) == {'RETAINED': 48, 'R_CENTERED': 48}
    assert result['new_observations'] == result['new_optimizer_calls'] == result['new_query_certificates'] == 0
    assert runner.read(output/'run.json')['complete']
