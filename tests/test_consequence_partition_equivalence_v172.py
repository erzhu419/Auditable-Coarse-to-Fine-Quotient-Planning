"""Gauge invariance is narrower than equivalence of arbitrary coefficient edits."""
from copy import deepcopy

from scripts import reconcile_controlled_predictive_consequence_partition_v172 as reconcile

ROWS = []


def payload():
    return dict(leaves=[dict(leaf_id=7,connected_components=[['DOWN','LEFT','RIGHT'],['UP']],
        coefficients={'DOWN':[2.,.5,-.5],'LEFT':[-1.,.25,.75],'RIGHT':[-1.,-.75,-.25],'UP':[0.,0.,0.]},
        loss=3.,root_ids=['root'],pair_root_ids={'DOWN|LEFT':['root']})],nodes=[dict(kind='leaf',leaf_id=7)],fit_counts={'leaf_fits':1})


def shifted_payload():
    original = payload(); shifted = deepcopy(original)
    for action in ('DOWN','LEFT','RIGHT'):
        shifted['leaves'][0]['coefficients'][action] = [v+s for v,s in zip(original['leaves'][0]['coefficients'][action],[3.,-2.,1.])]
    shifted['leaves'][0]['coefficients']['UP'] = [9.,8.,7.]
    return original,shifted


def test_common_component_gauge_preserves_frozen_fields_and_legal_subset_choices():
    original,shifted = shifted_payload(); before = deepcopy(shifted)
    normalized,offsets = reconcile.normalize_payload(shifted)
    assert reconcile.audit._equal(normalized,original) and shifted==before
    # Current legal actions omit RIGHT: centering their subset would be wrong.
    choice = dict(life=0,mode='ONE_LATE',canonical_action='DOWN',decision=dict(leaf=7,canonical_action='DOWN',work={'reads':2},
        predicted_pairs={'DOWN|LEFT':[3.,.25,-1.25]},predicted_components={action:[v+(0.2 if k==0 else 0.) for k,v in enumerate(shifted['leaves'][0]['coefficients'][action])] for action in ('DOWN','LEFT')}))
    expected = deepcopy(choice)
    expected['decision']['predicted_components'] = {action:[v+(0.2 if k==0 else 0.) for k,v in enumerate(original['leaves'][0]['coefficients'][action])] for action in ('DOWN','LEFT')}
    assert reconcile.audit._equal(reconcile.normalize_choices([choice],{(0,'ONE_LATE'):offsets}),[expected])
    assert choice['decision']['predicted_components']['DOWN'][0]==5.2 and ROWS==[]


def test_nonconstant_tamper_and_action_change_are_not_reconciled():
    original,shifted = shifted_payload(); shifted['leaves'][0]['coefficients']['DOWN'][0] += .4
    normalized,_ = reconcile.normalize_payload(shifted)
    assert not reconcile.audit._equal(normalized,original)
    assert reconcile.first_difference(normalized,original)['path'].startswith('payload.leaves[0].coefficients')
    assert not reconcile.audit._equal({'canonical_action':'LEFT','predicted_pairs':[3.]},{'canonical_action':'DOWN','predicted_pairs':[3.]})
