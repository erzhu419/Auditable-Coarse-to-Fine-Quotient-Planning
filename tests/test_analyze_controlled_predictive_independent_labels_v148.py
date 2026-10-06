"""Finite estimator checks: no environment acquisition or label-dependent fit."""
from copy import deepcopy
import unittest

from scripts import analyze_controlled_predictive_independent_labels_v148 as audit


def root(life=0,query='risk1',origin='OLD',slot=0,same=False,old=2.,zero=0.,updated=1.,shared=-1.):
    return dict(root_id=f'{origin}:{life}:{query}:{slot}',origin=origin,life=life,query=query,replica=slot//4,slot=slot%4,
        example=dict(candidate_action='LEFT',baseline_action='LEFT' if same else 'DOWN',
                     target_total=[0. if same else old,0.,0.]),
        predictions={method:dict(estimated_advantage=value,selected_h1=value>0.) for method,value in
                     zip(audit.METHODS,(zero,updated,shared))})


class IndependentLabelAuditTests(unittest.TestCase):
    def test_settings_and_disjoint_paired_seed_schedule(self):
        from scripts import run_controlled_predictive_independent_labels_v148 as runner
        self.assertEqual(audit.expected_settings(),runner.settings())
        values=[]
        for life in audit.LIVES:
            for query in audit.QUERIES:
                for origin in ('OLD','NEW'):
                    for slot in range(16):
                        r=root(life,query,origin,slot)
                        actual=audit.suffix_seeds(r)
                        expected=[runner.suffix_seed(life,query,origin,slot//4,slot%4,s) for s in range(32)]
                        self.assertEqual(actual,expected);values.extend(actual)
        self.assertEqual(len(set(values)),256*32)
        self.assertTrue(all(14800000000<=v<14900000000 for v in values))

    def test_fresh_unbiased_correction_is_not_clipped(self):
        r=root(zero=0.,updated=0.,shared=0.)
        result=audit.root_diagnostics(r,[-1.,1.]*16)
        self.assertEqual(result['fresh']['mean'],0.)
        self.assertAlmostEqual(result['fresh']['sample_variance'],32/31)
        self.assertAlmostEqual(result['fresh']['mean_variance'],1/31)
        self.assertEqual(result['models']['UPDATED']['fresh']['mse'],0.)
        self.assertAlmostEqual(result['models']['UPDATED']['fresh']['corrected_mse'],-1/31)
        self.assertNotIn('sample_variance',result['old'])
        self.assertNotIn('corrected_mse',result['models']['UPDATED']['old'])

    def test_paired_mse_gain_and_gate_contrasts_keep_frozen_selection(self):
        result=audit.root_diagnostics(root(old=4.,zero=0.,updated=2.,shared=-1.),[-4.,-2.]*16)
        m=result['models']['UPDATED']
        self.assertEqual(m['old']['mse_gain_over_zero'],12.)
        self.assertEqual(m['fresh']['mse_gain_over_zero'],-16.)
        self.assertEqual(m['old']['gate_advantage_vs_h2'],4.)
        self.assertEqual(m['fresh']['gate_advantage_vs_h2'],-3.)
        self.assertEqual(m['fresh']['gate_advantage_vs_zero'],-3.)
        self.assertEqual(result['models']['SHARED']['fresh']['gate_advantage_vs_h2'],0.)
        self.assertFalse(result['sign_reproduced'])
        self.assertEqual((result['old_sign'],result['fresh_sign']),(1,-1))
        zero=result['models']['ZERO']['fresh'];model=result['models']['UPDATED']['fresh']
        self.assertAlmostEqual(zero['corrected_mse']-model['corrected_mse'],model['mse_gain_over_zero'])

    def test_same_action_keeps_exact_zero_without_physical_samples(self):
        result=audit.root_diagnostics(root(same=True,zero=0.,updated=0.,shared=0.),[])
        self.assertTrue(result['same_action']);self.assertTrue(result['fresh']['complete'])
        self.assertEqual(result['fresh']['n'],0);self.assertEqual(result['fresh']['mean_variance'],0.)
        self.assertEqual(result['fresh']['mean'],0.)
        self.assertEqual([b['n'] for b in result['blocks']],[0]*4)
        self.assertTrue(all(result['models'][m]['fresh']['mse']==0. for m in audit.METHODS))

    def test_full_roster_equal_history_weighting_retains_zero_roots(self):
        rows=[]
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        same=slot>life
                        r=root(life,query,origin,slot,same=same,updated=0. if same else 1.,shared=0.)
                        rows.append(audit.root_diagnostics(r,[] if same else [float(life+1)]*32))
        full=audit.aggregate(rows);secondary=audit.aggregate(rows,True)
        cell=full['OLD']['risk1'];self.assertTrue(cell['complete']);self.assertEqual(cell['roots'],64)
        self.assertEqual(cell['fresh_mean'],sum((life+1)**2/16 for life in audit.LIVES)/4)
        self.assertEqual(secondary['OLD']['risk1']['fresh_mean'],2.5)
        self.assertEqual(cell['models']['UPDATED']['fresh']['gate_advantage_vs_h2'],cell['fresh_mean'])
        self.assertEqual(len(cell['blocks']),4)
        self.assertTrue(all(block['mean']==cell['fresh_mean'] for block in cell['blocks']))

    def test_cutoff_blocks_complete_cohort_without_dropping_valid_blocks(self):
        rows=[]
        for origin in ('OLD','NEW'):
            for query in audit.QUERIES:
                for life in audit.LIVES:
                    for slot in range(16):
                        values=[1.]*32
                        if (origin,query,life,slot)==('NEW','risk8',2,7):values[3]=None
                        rows.append(audit.root_diagnostics(root(life,query,origin,slot),values))
        full=audit.aggregate(rows);cell=full['NEW']['risk8']
        self.assertFalse(cell['complete']);self.assertEqual(cell['roots'],64)
        self.assertIsNone(cell['fresh_mean']);self.assertIsNone(cell['models']['UPDATED']['fresh']['mse'])
        self.assertIsNone(cell['blocks'][0]['mean']);self.assertEqual(cell['blocks'][1]['mean'],1.)
        self.assertEqual(cell['models']['UPDATED']['old']['mse'],1.)

    def test_cohort_audit_detects_prediction_and_original_seed_changes(self):
        examples={o:[] for o in ('OLD','NEW')};originals={o:{} for o in examples}
        cohort=dict(roots=[],same_action_roots=[],excluded_same_action_roots=[])
        models={(l,q,m):{} for l in audit.LIVES for q in audit.QUERIES for m in audit.METHODS}
        for origin in examples:
            for ordinal in range(128):
                life,within=divmod(ordinal,32);query=list(audit.QUERIES)[within//16];slot=within%16
                same=origin=='OLD' and ordinal>=45;r=root(life,query,origin,slot,same=same)
                e=r['example'];e.update(root_id=r['root_id'],life=life,query=query,replica=slot//4,slot=slot%4,
                    split='TRAIN',candidate_after=[1]+[0]*15,baseline_after=([1]+[0]*15 if same else [0]*16),
                    immediate_difference=0.)
                examples[origin].append(deepcopy(e));original=dict(root_id=r['root_id'],life=life,query=query,
                    replica=slot//4,slot=slot%4,actions=sorted({e['candidate_action'],e['baseline_action']}),
                    suffix_seeds=[(143 if origin=='OLD' else 145)*100000000+ordinal*100+s for s in range(8)])
                originals[origin][r['root_id']]=original;r.update(original)
                r['original_suffix_seeds']=original['suffix_seeds'];r['suffix_seeds']=[] if same else audit.suffix_seeds(r)
                r['predictions']={m:audit.prior.expected_prediction(e,{},m) for m in audit.METHODS}
                cohort['same_action_roots' if same else 'roots'].append(r)
                if same:cohort['excluded_same_action_roots'].append(r['root_id'])
        self.assertTrue(all(audit.cohort_checks(cohort,examples,originals,models).values()))
        changed=deepcopy(cohort);changed['roots'][0]['predictions']['SHARED']['estimated_advantage']=1.
        self.assertFalse(audit.cohort_checks(changed,examples,originals,models)['frozen_predictions'])
        changed=deepcopy(cohort);changed['roots'][0]['original_suffix_seeds'][0]+=1
        self.assertFalse(audit.cohort_checks(changed,examples,originals,models)['source_root_identity'])


if __name__=='__main__':unittest.main()
