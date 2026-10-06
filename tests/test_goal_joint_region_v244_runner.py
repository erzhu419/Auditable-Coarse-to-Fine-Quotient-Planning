"""V244 roster selection and interpretation regressions."""
from copy import deepcopy
from scripts import run_goal_joint_region_v244 as runner


def prior_row(life, index, *, arm='ONE_WAY', stage='A_RETURN', certified=False):
    return dict(life=life, index=index, arm=arm, case=dict(stage=stage),
        terminal_plan=dict(query_evidence=dict(queries=dict(goal=dict(policy='SHORT',
            comparisons=[dict(other='DETOUR_RETRY', certified=certified, profile_id=index)])))))


def test_all_prior_unknowns_and_no_cross_arm_or_later_stage(monkeypatch):
    data = []
    for life in range(3):
        data.extend(prior_row(life, index) for index in range(54, 62))
        data.extend([prior_row(life, 62, arm='TWO_WAY'), prior_row(life, 63, stage='B'),
                     prior_row(life, 64, certified=True)])
    monkeypatch.setattr(runner, 'rows', lambda path: iter(deepcopy([
        row for row in data if row['life'] == int(path.name.split('_')[2].split('.')[0])])))
    selected = runner.endpoints()
    assert len(selected) == 24
    assert all(row['arm'] == 'ONE_WAY' and row['case']['stage'] == 'A_RETURN' for row, _ in selected)
    assert [(row['life'], row['index']) for row, _ in selected] == sorted(
        (row['life'], row['index']) for row, _ in selected)


def test_rejecting_one_candidate_never_issues_a_query_certificate():
    rejected = dict(life=0, status='paid_constraints_reject_candidate', canonical_inside=True,
        all_query_inside=False, all_execution_inside=True,
        query_regions={'S': dict(exact_inside=False)}, execution_regions=[])
    summary = runner.summarize([rejected])
    assert summary['status_counts']['full_region_bad_witness'] == 0
    assert summary['canonical_admitted'] == 1
    assert summary['new_query_certificates'] == summary['new_optimizer_calls'] == summary['new_observations'] == 0
    assert summary['query_rejection_counts'] == {'S': 1}
