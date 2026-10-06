"""Finite checks for disjoint suffix folds, tail calibration, gate values, and missing labels."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from scripts import analyze_controlled_predictive_crossfit_shrinkage_v150 as audit


def root(life=0,query='risk1',origin='OLD',slot=0,same=False,values=(0.,2.,-1.)):
    return dict(root_id=f'{origin}:{life}:{query}:{slot}',origin=origin,life=life,query=query,
        replica=slot//4,slot=slot%4,example=dict(candidate_action='LEFT',baseline_action='LEFT' if same else 'DOWN'),
        predictions={m:dict(estimated_advantage=value,selected_h1=value>0) for m,value in zip(audit.METHODS,values)})


def diagnostic(r,fresh,train32=3.):
    return audit.root_diagnostics(r,fresh,dict(TRAIN32=dict(target_total=[train32,0.,0.])))


class CrossfitAuditTests(unittest.TestCase):
    def test_settings_match_frozen_runner(self):
        from scripts import run_controlled_predictive_crossfit_shrinkage_v150 as runner
        self.assertEqual(audit.expected_settings(),runner.settings())

    def test_disjoint_fold_labels_reconstructed_from_components_and_immediate_removed_once(self):
        r=root();r.update(board=[0]*16,actions=['DOWN','LEFT'],suffix_seeds=list(range(32)))
        r['example'].update(root_id=r['root_id'],life=0,query='risk1',replica=0,slot=0,split='TRAIN',
            immediate_difference=.25,target_total=[99.,99.,99.],target_tail=[99.,99.,99.],suffixes=8)
        zero=root(slot=1,same=True,values=(0.,0.,0.));zero.update(board=[0]*16,actions=['LEFT'],suffix_seeds=[])
        zero['example'].update(root_id=zero['root_id'],life=0,query='risk1',replica=0,slot=1,split='TRAIN',
            immediate_difference=0.,target_total=[0.,0.,0.],target_tail=[0.,0.,0.],suffixes=8)
        cohort=dict(roots=[r],same_action_roots=[zero]);records=[]
        for suffix in range(32):
            branches={action:dict(root_board=r['board'],first_action=action,seed=suffix,
                result=dict(components=components,status='WON')) for action,components in
                (('LEFT',[float(suffix),1.,0.]),('DOWN',[0.,0.,1.]))}
            records.append(dict(root_id=r['root_id'],suffix=suffix,seed=suffix,continuation='H2',branches=branches))
        capsule=dict(training_cohort_ref='cohort',source_run_ref='source/run.json')
        source=dict(lifecycles=[dict(life=0,consequences_trace='rows')])
        with patch.object(audit,'read',side_effect=lambda p:cohort if str(p)=='cohort' else source), \
                patch.object(audit.old,'read_rows',return_value=iter(records)):
            folds,examples,reads,checks=audit.training_examples(capsule)
        self.assertEqual(examples[0]['target_tail'],[15.25,1.,-1.])
        for fold in folds:
            k=fold['fold'];heldout=list(range(8*k,8*k+8));train=[s for s in range(32) if s not in heldout]
            self.assertEqual(fold['train'][0]['target_tail'],[sum(train)/24-.25,1.,-1.])
            self.assertEqual(fold['heldout'][0]['target_tail'],[sum(heldout)/8-.25,1.,-1.])
            self.assertEqual(fold['train'][1]['suffixes'],0);self.assertEqual(fold['heldout'][1]['target_tail'],[0.,0.,0.])
        self.assertEqual(reads,dict(trace_files=1,paired_records=32,branch_results=64))
        self.assertTrue(checks['training_branch_identity']);self.assertFalse(checks['training_branch_roster'])

    def test_tail_calibration_clipping_zero_norm_and_immediate_independence(self):
        pred=[dict(root_id='a',predicted_tail=[2.,0.,0.])]
        example=dict(root_id='a',query='risk1',target_tail=[1.,0.,0.],immediate_difference=99.)
        result=audit.calibration_oracle([(0,pred,[example])]);self.assertEqual(result['beta'],.5)
        self.assertEqual(result['numerator'],2.);self.assertEqual(result['denominator'],4.)
        for target,beta in ((-1.,0.),(3.,1.)):
            example['target_tail'][0]=target
            self.assertEqual(audit.calibration_oracle([(0,pred,[example])])['beta'],beta)
        pred[0]['predicted_tail']=[0.,0.,0.]
        self.assertEqual(audit.calibration_oracle([(0,pred,[example])])['beta'],0.)

    def test_query_utility_calibration_and_positive_scaling_can_change_gate(self):
        prediction=dict(root_id='a',predicted_tail=[0.,.5,0.])
        example=dict(root_id='a',query='risk8',target_tail=[0.,.25,0.])
        result=audit.calibration_oracle([(0,[prediction],[example])]);self.assertEqual(result['beta'],.5)
        self.assertEqual(result['rows'][0]['x'],-4.);self.assertEqual(result['rows'][0]['y'],-2.)
        self.assertEqual(audit.scaled_weights({7:(-2.,0.,0.)},.25),{7:(-.5,0.,0.)})
        self.assertEqual(audit.scaled_weights({7:(-2.,0.,0.)},0.),{})
        cohort=dict(roots=[root(values=(1.,-1.,.5))],same_action_roots=[])
        self.assertEqual(audit.gate_changes(cohort)['total_vs_train32'],1)
        self.assertEqual(audit.gate_changes(cohort)['total_vs_zero'],0)
        cohort['roots'][0]['predictions']['CF']['selected_h1']=False
        self.assertEqual(audit.gate_changes(cohort)['total_vs_train32'],0)

    def test_fresh_seeds_unique_in_v150_namespace(self):
        values=[s for origin in ('OLD','NEW') for query in audit.QUERIES for life in audit.LIVES
            for slot in range(16) for s in audit.suffix_seeds(root(life,query,origin,slot))]
        self.assertEqual(len(set(values)),256*32)
        self.assertTrue(all(15000000000<=s<15100000000 for s in values))

    def test_mse_gain_gate_and_noise_correction(self):
        row=diagnostic(root(),[-4.,-2.]*16);contrast=audit.summarize_roots([row])['comparisons']['CF-TRAIN32']
        self.assertEqual(contrast['fresh']['mse_reduction'],21.);self.assertEqual(contrast['fresh']['gate_advantage'],3.)
        self.assertEqual(contrast['train32']['mse_reduction'],-15.)
        zero=diagnostic(root(values=(0.,0.,0.)),[-1.,1.]*16)
        self.assertAlmostEqual(zero['models']['CF']['fresh']['corrected_mse'],-1/31)
        self.assertEqual(audit.summarize_roots([zero])['comparisons']['CF-TRAIN32']['fresh']['mse_reduction'],0.)

    def test_same_action_zero_and_unacquired_labels_not_success(self):
        row=diagnostic(root(same=True,values=(0.,0.,0.)),[],0.)
        self.assertTrue(row['fresh']['complete']);self.assertEqual(row['fresh']['mean'],0.)
        missing=diagnostic(root(),[])
        self.assertEqual(missing['fresh']['n'],0)
        self.assertFalse(missing['fresh']['complete']);self.assertIsNone(missing['models']['CF']['fresh']['mse'])

    def test_equal_history_combined_weighting_and_cutoff_propagation(self):
        rows=[]
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        same=slot>life;value=float(life+1)*(1 if origin=='OLD' else 3)
                        rows.append(diagnostic(root(life,query,origin,slot,same,values=(0.,0. if same else 1.,0.)),
                            [] if same else [value]*32,0.))
        full=audit.aggregate(rows);secondary=audit.aggregate(rows,True)
        self.assertEqual(full['OLD']['risk1']['roots'],64);self.assertEqual(full['COMBINED']['risk1']['roots'],128)
        self.assertEqual(full['OLD']['risk1']['fresh_mean'],sum((life+1)**2/16 for life in audit.LIVES)/4)
        self.assertEqual(full['COMBINED']['risk1']['fresh_mean'],2*full['OLD']['risk1']['fresh_mean'])
        self.assertEqual(secondary['OLD']['risk1']['fresh_mean'],2.5)
        rows[0]=diagnostic(root(),[None]+[1.]*31)
        full=audit.aggregate(rows)
        self.assertFalse(full['OLD']['risk1']['complete']);self.assertFalse(full['COMBINED']['risk1']['complete'])
        self.assertIsNone(full['OLD']['risk1']['comparisons']['CF-TRAIN32']['fresh']['mse_reduction'])
        self.assertIsNotNone(full['OLD']['risk1']['blocks'][1]['models']['CF']['mse'])

    def test_cohort_audit_detects_model_and_training_seed_mutation(self):
        training=dict(roots=[],same_action_roots=[],excluded_same_action_roots=[])
        models={(l,q,m):{} for l in audit.LIVES for q in audit.QUERIES for m in audit.METHODS};ordinal=0
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        same=ordinal<83;r=root(life,query,origin,slot,same,values=(0.,0.,0.))
                        r['example'].update(root_id=r['root_id'],life=life,query=query,replica=slot//4,slot=slot%4,
                            immediate_difference=0.,candidate_after=[0]*16 if same else [1]+[0]*15,baseline_after=[0]*16)
                        r.update(actions=['LEFT'] if same else ['DOWN','LEFT'],suffix_seeds=[] if same else
                            [14800000000+ordinal*100+i for i in range(32)],original_suffix_seeds=[14300000000+ordinal*100+i for i in range(8)])
                        training['same_action_roots' if same else 'roots'].append(r)
                        if same:training['excluded_same_action_roots'].append(r['root_id'])
                        ordinal+=1
        cohort=deepcopy(training)
        for r in cohort['roots']+cohort['same_action_roots']:
            r['training_suffix_seeds']=r['suffix_seeds'];r['suffix_seeds']=[] if len(r['actions'])==1 else audit.suffix_seeds(r)
            r['predictions']={m:dict(root_id=r['root_id'],predicted_tail=[0.,0.,0.],estimated_advantage=0.,selected_h1=False) for m in audit.METHODS}
        self.assertTrue(all(audit.cohort_checks(cohort,training,models).values()))
        changed=deepcopy(cohort);changed['roots'][0]['predictions']['CF']['estimated_advantage']=1.
        self.assertFalse(audit.cohort_checks(changed,training,models)['frozen_predictions'])
        changed=deepcopy(cohort);changed['roots'][0]['training_suffix_seeds'][0]+=1
        self.assertFalse(audit.cohort_checks(changed,training,models)['source_root_identity'])


if __name__=='__main__':unittest.main()
