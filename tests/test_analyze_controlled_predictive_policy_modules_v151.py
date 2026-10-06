"""Small independent-audit fixtures; no scientific sampling or native planners."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from scripts import analyze_controlled_predictive_policy_modules_v151 as audit


class PolicyModuleAuditTests(unittest.TestCase):
    def test_settings_match_frozen_runner(self):
        from scripts import run_controlled_predictive_policy_modules_v151 as runner
        self.assertEqual(audit.expected_settings(),runner.settings())

    def test_real_runner_warm_fit_schema_and_cumulative_counts_match_independent_oracle(self):
        from scripts import run_controlled_predictive_policy_modules_v151 as runner
        from acfqp.science.controlled_predictive_policy_modules_v151 import RootConsequences
        temp=Path(__file__).resolve().parents[1]/'reports/v151_runtime_tmp';temp.mkdir(parents=True,exist_ok=True)
        examples=[dict(root_id='one',board=[1,1]+[0]*14,triplet_ids=['one:0'],targets={'1':[1.,-.25,.25],'8':[2.,-.5,.5]})]
        models={d:RootConsequences() for d in (1,8)};weights={d:{} for d in (1,8)};counts={d:Counter() for d in (1,8)};updates={d:0 for d in (1,8)}
        with TemporaryDirectory(prefix='analyzer_fit_',dir=temp) as location:
            directory=Path(location)
            for checkpoint,rows in enumerate(([],examples,examples)):
                folder=directory/str(checkpoint);folder.mkdir();fitted=runner.fit_models(models,rows,folder,directory)
                for d in (1,8):
                    prior_weights,prior_updates,prior_counts=deepcopy(weights[d]),updates[d],Counter(counts[d])
                    checks,weights[d],updates[d],counts[d]=audit.audit_model(fitted[str(d)],directory,rows,weights[d],updates[d],counts[d],d,initial=checkpoint==0)
                    self.assertTrue(all(checks.values()),checks)
                    if checkpoint==2:
                        changed=deepcopy(fitted[str(d)]);changed['fit_counts']['update_calls']+=1
                        damaged,_,_,_=audit.audit_model(changed,directory,rows,prior_weights,prior_updates,prior_counts,d)
                        self.assertFalse(damaged['model_work'])
                    models[d].predict([1,1]+[0]*14);counts[d].update(audit.prediction_work([1,1]+[0]*14))
            log=temp/'analyzer_fit_work.json';old=json.loads(log.read_text()) if log.exists() else {}
            attempts=old.get('attempts',[old] if old else []);attempts.append(dict(real_training_updates=128,oracle_lms_updates=192,
                real_root_predictions_outside_fit=6,new_environment_samples=0,native_planner_calls=0))
            log.write_text(json.dumps(dict(attempts=attempts))+'\n')

    def test_branch_replay_accepts_budget_cutoff_and_rejects_policy_or_rng_change(self):
        from acfqp.science.controlled_predictive_policy_modules_v151 import run_module_branch
        class Planner:
            def __init__(self,actions):self.actions=iter(actions);self.counts=Counter()
            def choose(self,board,query):self.counts['choose_calls']+=1;return dict(action=next(self.actions))
        row=run_module_branch([1,1]+[0]*14,dict(risk1=Planner(['DOWN']),risk8=Planner(['LEFT'])),'risk1',1,123,max_steps=2)
        with patch.object(audit.planning,'planning_counts_valid',return_value=True):
            checks,swipes=audit.replay_branch(row,2);self.assertTrue(all(checks.values()),checks)
            changed=deepcopy(row);changed['policy_keys'][1]='risk8'
            self.assertFalse(audit.replay_branch(changed,2)[0]['branch_policy_schedule'])
            changed=deepcopy(row);changed['spawned_ranks'][0]=3
            self.assertFalse(audit.replay_branch(changed,2)[0]['branch_rng'])
        self.assertEqual(row['result']['status'],'CUTOFF');self.assertIsNone(row['result']['utility'])
        temp=Path(__file__).resolve().parents[1]/'reports/v151_runtime_tmp';temp.mkdir(parents=True,exist_ok=True)
        (temp/'analyzer_branch_work.json').write_text(json.dumps(dict(new_environment_samples=2,native_planner_calls=0,
            environment_counts=row['result']['environment_counts'],analysis_replay_swipes=3*swipes))+'\n')

    def test_commitment_audit_detects_early_release_and_omitted_work(self):
        board=[1,1]+[0]*14;weights={-1:(1.,0.,0.)};remaining=0
        with patch.object(audit.planning,'planning_counts_valid',return_value=True), \
                patch.object(audit.local,'compact_choice_valid',return_value=True), \
                patch.object(audit.h1,'root_choice_checks',return_value={}):
            for step in range(8):
                boundary=step==0;work=Counter(choose_calls=1,module_policy_decisions=1,policy_risk8_choose_calls=1)
                if boundary:
                    work.update(boundary_decisions=1,module_accepts=1)
                    work.update({f'learner_{k}':v for k,v in audit.prediction_work(board).items()})
                else:work['committed_module_decisions']=1
                decision=dict(step=step,boundary=boundary,target_query='risk1',other_query='risk8',duration=8,
                    policy_key='risk8',selected_other=True,remaining_before=8-step,remaining_after=7-step,
                    predicted_components=[1.,0.,0.] if boundary else None,estimated_advantage=1. if boundary else None)
                choice=dict(work=dict(work),module_decision=decision)
                checks,after=audit.gate_checks(board,choice,'risk1','LEARN8',weights,remaining,step,8)
                self.assertTrue(all(checks.values()),checks)
                if step==1:
                    changed=deepcopy(choice);changed['module_decision']['remaining_after']=0
                    self.assertFalse(audit.gate_checks(board,changed,'risk1','LEARN8',weights,remaining,step,8)[0]['module_commitment'])
                    changed=deepcopy(choice);changed['work'].pop('committed_module_decisions')
                    self.assertFalse(audit.gate_checks(board,changed,'risk1','LEARN8',weights,remaining,step,8)[0]['module_work'])
                remaining=after
        self.assertEqual(remaining,0)

    def test_root_features_keep_bias_multiplicity_and_d4_invariance(self):
        board=[1,2,3,4,5,6,7,8,9,10,0,1,2,3,4,5]
        vector=audit.features(board)
        self.assertEqual(sum(vector.values()),41);self.assertEqual(vector[-1],1)
        rotated=[board[4*(3-column)+row] for row in range(4) for column in range(4)]
        self.assertEqual(vector,audit.features(rotated))
        counts=audit.prediction_work(board)
        self.assertEqual(counts['feature_rank_reads'],64)
        self.assertEqual(counts['component_weight_reads'],3*len(vector))
        self.assertEqual(audit.predict(board,{key:(1.,-1.,2.) for key in vector}),[41.,-41.,82.])

    def test_warm_lms_uses_total_components_and_replays_accumulated_roots(self):
        board=[1]+[0]*15;example=dict(board=board,target=[2.,-1.,1.]);vector=audit.features(board)
        one=audit.fit_oracle([example],passes=1,alpha=.1)
        for predicted,expected in zip(audit.predict(board,one['weights']),[.2,-.1,.1]):
            self.assertAlmostEqual(predicted,expected)
        before=deepcopy(one['weights']);two=audit.fit_oracle([example],one['weights'],passes=1,alpha=.1)
        self.assertEqual(one['weights'],before)
        for predicted,expected in zip(audit.predict(board,two['weights']),[.38,-.19,.19]):
            self.assertAlmostEqual(predicted,expected)
        self.assertEqual(two['updates'],1)
        self.assertEqual(two['counts']['update_calls'],1)
        self.assertEqual(two['counts']['root_updates'],1)
        self.assertEqual(two['counts']['weight_address_updates'],len(vector))
        self.assertEqual(two['counts']['allocated_weight_addresses'],0)

    def test_curves_preserve_all_checkpoints_paired_seeds_and_cutoffs(self):
        indexed={};valid={}
        for batch in range(5):
            for life in audit.LIVES:
                for query in audit.QUERIES:
                    for method,offset in zip(audit.METHODS,(0.,-1.,1.,2.)):
                        for replica in range(4):
                            key=life,query,batch,method,replica
                            indexed[key]=dict(result=dict(status='WON',utility=life+replica+offset*batch,score=2048,steps=200))
                            valid[key]=True
        result=audit.full_game_comparison(indexed,valid)
        self.assertEqual(set(result),{'0','1','2','3','4'})
        cell=result['4']['comparisons']['LEARN8-LEARN1']['risk1']
        self.assertTrue(cell['complete']);self.assertEqual(cell['mean'],4.);self.assertEqual(cell['positive'],4)
        self.assertEqual(result['0']['comparisons']['LEARN1-H2']['risk8']['mean'],0.)
        key=2,'risk1',3,'LEARN8',1;indexed[key]['result'].update(status='CUTOFF',utility=None)
        changed=audit.full_game_comparison(indexed,valid)
        self.assertFalse(changed['3']['comparisons']['LEARN8-H2']['risk1']['complete'])
        self.assertIsNone(changed['3']['comparisons']['LEARN8-H2']['risk1']['mean'])
        self.assertEqual(changed['4']['comparisons']['LEARN8-H2']['risk1']['mean'],8.)


if __name__=='__main__':unittest.main()
