"""Estimator checks catch label reuse, weighting, sign and cutoff errors without sampling."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from scripts import analyze_controlled_predictive_label_precision_v149 as audit


def root(life=0,query='risk1',origin='OLD',slot=0,same=False,values=(0.,1.,2.,-1.)):
    return dict(root_id=f'{origin}:{life}:{query}:{slot}',origin=origin,life=life,query=query,
        replica=slot//4,slot=slot%4,example=dict(candidate_action='LEFT',baseline_action='LEFT' if same else 'DOWN'),
        predictions={m:dict(estimated_advantage=value,selected_h1=value>0) for m,value in zip(audit.METHODS,values)})


def diagnostic(r,fresh,train8=4.,train32=3.):
    targets={m:dict(target_total=[value,0.,0.]) for m,value in (('TRAIN8',train8),('TRAIN32',train32))}
    return audit.root_diagnostics(r,fresh,targets)


class LabelPrecisionAuditTests(unittest.TestCase):
    def test_settings_match_frozen_runner(self):
        from scripts import run_controlled_predictive_label_precision_v149 as runner
        self.assertEqual(audit.expected_settings(),runner.settings())

    def test_reconstruct_nested_labels_from_branch_components_subtracts_immediate_once(self):
        r=root();r.update(board=[0]*16,actions=['DOWN','LEFT'],suffix_seeds=list(range(32)))
        r['example'].update(root_id=r['root_id'],life=0,query='risk1',replica=0,slot=0,split='TRAIN',
            immediate_difference=.25,target_total=[99.,99.,99.],target_tail=[99.,99.,99.],suffixes=8)
        zero=root(slot=1,same=True,values=(0.,0.,0.,0.));zero.update(board=[0]*16,actions=['LEFT'],suffix_seeds=[])
        zero['example'].update(root_id=zero['root_id'],life=0,query='risk1',replica=0,slot=1,split='TRAIN',
            immediate_difference=0.,target_total=[0.,0.,0.],target_tail=[0.,0.,0.],suffixes=8)
        cohort=dict(roots=[r],same_action_roots=[zero]);records=[]
        for suffix in range(32):
            branches={}
            for action,components in (('LEFT',[float(suffix),1.,0.]),('DOWN',[0.,0.,1.])):
                branches[action]=dict(root_board=r['board'],first_action=action,seed=suffix,
                    result=dict(components=components,status='LOST' if action=='LEFT' else 'WON',steps=2,
                        seconds=0.,decision_seconds=0.,environment_counts=dict(sampled_transitions=2),policy_counts={}))
            records.append(dict(root_id=r['root_id'],suffix=suffix,seed=suffix,continuation='H2',branches=branches))
        capsule=dict(training_cohort_ref='cohort',source_run_ref='source/run.json')
        source=dict(lifecycles=[dict(life=0,consequences_trace='rows')])
        with patch.object(audit,'read',side_effect=lambda p:cohort if str(p)=='cohort' else source), \
                patch.object(audit.old,'read_rows',return_value=iter(records)):
            examples,views,reads,checks=audit.training_examples(capsule)
        self.assertEqual(examples['TRAIN8'][0]['target_total'],[3.5,1.,-1.])
        self.assertEqual(examples['TRAIN8'][0]['target_tail'],[3.25,1.,-1.])
        self.assertEqual(examples['TRAIN32'][0]['target_tail'],[15.25,1.,-1.])
        self.assertEqual(examples['TRAIN32'][1]['suffixes'],0)
        self.assertEqual(examples['TRAIN32'][1]['target_tail'],[0.,0.,0.])
        self.assertEqual(views['TRAIN8'],dict(paired_records=8,physical_branches=16,sampled_transitions=32))
        self.assertEqual(views['TRAIN32'],dict(paired_records=32,physical_branches=64,sampled_transitions=128))
        self.assertEqual(reads,dict(trace_files=1,paired_records=32,branch_results=64))
        self.assertTrue(checks['training_branch_identity']);self.assertTrue(checks['training_labels_terminal'])
        self.assertFalse(checks['training_branch_roster'])  # The finite fixture is intentionally smaller than the experiment.

    def test_seed_schedule_disjoint_from_training_and_nested_blocks(self):
        values=[]
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        seeds=audit.suffix_seeds(root(life,query,origin,slot));values.extend(seeds)
                        self.assertEqual(seeds,list(range(seeds[0],seeds[0]+32)))
        self.assertEqual(len(set(values)),256*32)
        self.assertTrue(all(14900000000<=value<15000000000 for value in values))

    def test_mse_gain_sign_gate_and_nested_training_diagnostics(self):
        row=diagnostic(root(),[-4.,-2.]*16)
        self.assertEqual(row['models']['TRAIN8']['train8']['mse'],4.)
        self.assertEqual(row['models']['TRAIN8']['train32']['mse'],1.)
        self.assertEqual(row['models']['TRAIN8']['fresh']['mse'],25.)
        self.assertEqual(row['models']['TRAIN32']['fresh']['mse'],4.)
        result=audit.summarize_roots([row]);contrast=result['comparisons']['TRAIN32-TRAIN8']
        self.assertEqual(contrast['fresh']['mse_reduction'],21.)
        self.assertEqual(contrast['fresh']['gate_advantage'],3.)
        self.assertEqual(contrast['train8']['mse_reduction'],-21.)
        self.assertEqual(contrast['train8']['gate_advantage'],-4.)
        self.assertEqual(result['blocks'][0]['comparisons']['TRAIN32-TRAIN8']['mse_reduction'],21.)

    def test_noise_correction_unclipped_and_cancels_between_methods(self):
        row=diagnostic(root(values=(0.,0.,0.,0.)),[-1.,1.]*16)
        self.assertAlmostEqual(row['fresh']['mean_variance'],1/31)
        self.assertAlmostEqual(row['models']['TRAIN32']['fresh']['corrected_mse'],-1/31)
        self.assertNotIn('corrected_mse',row['models']['TRAIN32']['train32'])
        self.assertEqual(audit.summarize_roots([row])['comparisons']['TRAIN32-TRAIN8']['fresh']['mse_reduction'],0.)

    def test_same_action_exact_zero_keeps_all_roots_without_samples(self):
        row=diagnostic(root(same=True,values=(0.,0.,0.,0.)),[],0.,0.)
        self.assertTrue(row['fresh']['complete']);self.assertEqual(row['fresh']['n'],0)
        self.assertEqual(row['fresh']['mean'],0.);self.assertEqual(row['fresh']['mean_variance'],0.)
        self.assertTrue(all(block['n']==0 and block['mean']==0 for block in row['blocks']))

    def test_equal_history_and_combined_weighting_keep_exact_zero_roots(self):
        rows=[]
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        same=slot>life;value=float(life+1)*(1 if origin=='OLD' else 3)
                        r=root(life,query,origin,slot,same,values=(0.,0.,0. if same else 1.,0.))
                        rows.append(diagnostic(r,[] if same else [value]*32,0.,0.))
        full=audit.aggregate(rows);secondary=audit.aggregate(rows,True)
        self.assertEqual(full['OLD']['risk1']['roots'],64);self.assertEqual(full['COMBINED']['risk1']['roots'],128)
        self.assertEqual(full['OLD']['risk1']['fresh_mean'],sum((life+1)**2/16 for life in audit.LIVES)/4)
        self.assertEqual(full['COMBINED']['risk1']['fresh_mean'],2*full['OLD']['risk1']['fresh_mean'])
        self.assertEqual(secondary['OLD']['risk1']['fresh_mean'],2.5)
        self.assertEqual(full['OLD']['risk1']['models']['TRAIN8']['fresh']['gate_advantage_vs_h2'],full['OLD']['risk1']['fresh_mean'])

    def test_cohort_checks_detect_frozen_prediction_and_training_seed_changes(self):
        training=dict(roots=[],same_action_roots=[],excluded_same_action_roots=[])
        models={(l,q,m):{} for l in audit.LIVES for q in audit.QUERIES for m in audit.METHODS}
        ordinal=0
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        same=ordinal<83;r=root(life,query,origin,slot,same,values=(0.,0.,0.,0.))
                        r['example'].update(root_id=r['root_id'],life=life,query=query,replica=slot//4,slot=slot%4,
                            immediate_difference=0.,candidate_after=[0]*16 if same else [1]+[0]*15,baseline_after=[0]*16)
                        r.update(actions=['LEFT'] if same else ['DOWN','LEFT'],
                            suffix_seeds=[] if same else [14800000000+ordinal*100+i for i in range(32)],
                            original_suffix_seeds=[14300000000+ordinal*100+i for i in range(8)])
                        training['same_action_roots' if same else 'roots'].append(r)
                        if same:training['excluded_same_action_roots'].append(r['root_id'])
                        ordinal+=1
        cohort=deepcopy(training)
        for r in cohort['roots']+cohort['same_action_roots']:
            r['training_suffix_seeds']=r['suffix_seeds'];r['suffix_seeds']=[] if len(r['actions'])==1 else audit.suffix_seeds(r)
            r['predictions']={m:dict(root_id=r['root_id'],predicted_tail=[0.,0.,0.],estimated_advantage=0.,selected_h1=False) for m in audit.METHODS}
        self.assertTrue(all(audit.cohort_checks(cohort,training,models).values()))
        changed=deepcopy(cohort);changed['roots'][0]['predictions']['TRAIN32']['estimated_advantage']=1.
        self.assertFalse(audit.cohort_checks(changed,training,models)['frozen_predictions'])
        changed=deepcopy(cohort);changed['roots'][0]['training_suffix_seeds'][0]+=1
        self.assertFalse(audit.cohort_checks(changed,training,models)['source_root_identity'])
        changed=deepcopy(cohort);changed['roots'][0]['suffix_seeds'][0]=changed['roots'][0]['training_suffix_seeds'][0]
        self.assertFalse(audit.cohort_checks(changed,training,models)['independent_suffix_seeds'])

    def test_cutoff_blocks_claim_without_dropping_roots_or_complete_blocks(self):
        rows=[]
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        fresh=[1.]*32
                        if (origin,query,life,slot)==('NEW','risk8',2,7):fresh[3]=None
                        rows.append(diagnostic(root(life,query,origin,slot),fresh))
        full=audit.aggregate(rows);cell=full['NEW']['risk8']
        self.assertFalse(cell['complete']);self.assertEqual(cell['roots'],64)
        self.assertIsNone(cell['comparisons']['TRAIN32-TRAIN8']['fresh']['mse_reduction'])
        self.assertIsNone(cell['blocks'][0]['models']['TRAIN32']['mse'])
        self.assertEqual(cell['blocks'][1]['models']['TRAIN32']['mse'],4.)
        self.assertEqual(cell['models']['TRAIN8']['train8']['mse'],4.)
        self.assertFalse(full['COMBINED']['risk8']['complete'])


if __name__=='__main__':unittest.main()
