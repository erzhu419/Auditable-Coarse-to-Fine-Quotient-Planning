"""Finite alias, paired-seed and uncertainty checks; no planner or environment."""
from copy import deepcopy
import math
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts import analyze_controlled_predictive_module_replication_v152 as audit


def logical_fixture():
    indexed={};valid={}
    for life in audit.LIVES:
        for query in audit.QUERIES:
            for checkpoint in audit.CHECKPOINTS:
                for method,offset in zip(audit.METHODS,(0.,-1.,1.,2.)):
                    for replica in range(audit.REPLICAS):
                        key=life,query,checkpoint,method,replica
                        value=life+replica+(offset if method=='ALT' else offset*checkpoint)
                        indexed[key]=dict(result=dict(score=2048,steps=200,status='WON',utility=value,components=[1.,0.,1.]))
                        valid[key]=True
    return indexed,valid


class ModuleReplicationAuditTests(unittest.TestCase):
    def test_settings_and_full_rosters_match_runner_without_alias_work_duplication(self):
        from scripts import run_controlled_predictive_module_replication_v152 as runner
        self.assertEqual(audit.expected_settings(),runner.settings())
        physical,logical=runner.rosters()
        self.assertTrue(all(audit.logical_roster_checks(physical,logical).values()))
        self.assertEqual(sum(row['method']=='H2' for row in physical),128)
        self.assertEqual(len(logical)-len(physical),1408)
        changed=deepcopy(logical);row=next(r for r in changed if r['method']=='ALT')
        row['physical_id']=f"{row['life']}:{row['query']}:-1:H2:{row['replica']}"
        self.assertFalse(audit.logical_roster_checks(physical,changed)['logical_roster'])
        self.assertFalse(audit.logical_roster_checks(physical+[deepcopy(physical[0])],logical)['physical_roster'])
        seeds={runner.evaluation_seed(l,r) for l in audit.LIVES for r in range(16)}
        self.assertEqual(len(seeds),64)
        self.assertTrue(all(audit.BASE+90000000<=seed<audit.BASE+94000000 for seed in seeds))

    def test_source_model_copy_binding_and_zero_checkpoint_audit(self):
        temp=Path(__file__).resolve().parents[1]/'reports/v152_runtime_tmp';temp.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(prefix='analyzer_source_',dir=temp) as name:
            directory=Path(name);source=directory/'source';source.mkdir()
            snapshots=[dict(life=l) for l in audit.LIVES];capsule=dict(source_run_ref=str(source/'run.json'),snapshots=snapshots,models=[])
            lifecycles=[]
            for life in audit.LIVES:
                records=[]
                for checkpoint in audit.CHECKPOINTS:
                    groups={q:{} for q in audit.QUERIES}
                    for query in audit.QUERIES:
                        for duration in (1,8):
                            state=dict(radix=11,updates=checkpoint*32,frozen=True,weights=[] if checkpoint==0 else [[-1,float(checkpoint),0.,0.]])
                            payload=dict(schema='acfqp.root_consequences.v151',**state)
                            relative=f'{life}_{query}_{checkpoint}_{duration}.json'
                            (source/relative).write_text(json.dumps(payload));(directory/relative).write_text(json.dumps(payload))
                            groups[query][str(duration)]=dict(model_ref=relative,frozen_state=deepcopy(state))
                            capsule['models'].append(dict(life=life,query=query,checkpoint=checkpoint,duration=duration,
                                source_model_ref=str(source/relative),model_ref=relative,frozen_state=deepcopy(state),model_bytes=(directory/relative).stat().st_size))
                    records.append(dict(checkpoint=checkpoint,models=groups))
                lifecycles.append(dict(life=life,checkpoints=records))
            (source/'run.json').write_text(json.dumps(dict(status='complete',lifecycles=lifecycles)))
            (source/'analysis.json').write_text(json.dumps(dict(complete=True,primary_complete=True)))
            (source/'source_capsule.json').write_text(json.dumps(dict(snapshots=snapshots)))
            models,checks,work=audit.source_models(capsule,directory)
            self.assertEqual(len(models),80);self.assertTrue(all(checks.values()),checks)
            self.assertEqual(work['source_model_files_read'],80);self.assertEqual(work['frozen_model_files_read'],80)
            changed=capsule['models'][0];path=directory/changed['model_ref'];payload=json.loads(path.read_text())
            payload['weights']=[[-1,1.,0.,0.]];path.write_text(json.dumps(payload))
            _,damaged,_=audit.source_models(capsule,directory)
            self.assertFalse(damaged['frozen_model_copies']);self.assertFalse(damaged['zero_checkpoint_models'])

    def test_physical_alias_keys_keep_target_query_and_checkpoint_zero(self):
        self.assertEqual(audit.physical_key(2,'risk8',4,'H2',11),(2,'risk8',-1,'H2',11))
        self.assertEqual(audit.physical_key(2,'risk8',4,'ALT',11),(2,'risk1',-1,'H2',11))
        self.assertEqual(audit.physical_key(2,'risk8',0,'LEARN8',11),(2,'risk8',-1,'H2',11))
        self.assertEqual(audit.physical_key(2,'risk8',4,'LEARN8',11),(2,'risk8',4,'LEARN8',11))
        values={audit.physical_key(l,q,c,m,r) for l in audit.LIVES for q in audit.QUERIES
            for c in audit.CHECKPOINTS for m in audit.METHODS for r in range(audit.REPLICAS)}
        self.assertEqual(len(values),1152)

    def test_checkpoint_zero_alias_requires_frozen_empty_model(self):
        payload=dict(frozen=True,updates=0,weights=[])
        self.assertTrue(audit.zero_checkpoint_valid(payload))
        for change in (dict(frozen=False),dict(updates=1),dict(weights=[[-1,1.,0.,0.]])):
            self.assertFalse(audit.zero_checkpoint_valid(dict(payload,**change)))

    def test_alias_recomposes_alt_utility_without_counting_a_new_game(self):
        result=dict(score=2048,steps=100,status='LOST',components=[1.,1.,0.],utility=0.,environment_counts=dict(sampled_transitions=100))
        res=audit.logical_result(result,'risk8')
        self.assertEqual(res['utility'],-7.);self.assertEqual(res['components'],[1.,1.,0.])
        self.assertNotIn('environment_counts',res);self.assertEqual(result['utility'],0.)
        result.update(status='CUTOFF',utility=None,components=[1.,0.,0.])
        self.assertIsNone(audit.logical_result(result,'risk8')['utility'])

    def test_all_checkpoints_increments_blocks_and_zero_variance(self):
        indexed,valid=logical_fixture();result=audit.aggregate(indexed,valid)
        self.assertTrue(result['primary_complete'])
        self.assertEqual(set(result['learning_curves']),{'0','1','2','3','4'})
        cell=result['learning_curves']['4']['comparisons']['LEARN8-H2']['risk8']
        self.assertEqual(cell['mean'],8.);self.assertEqual(cell['conditional_seed_se'],0.)
        self.assertEqual(cell['conditional_seed_ci95'],[8.,8.]);self.assertEqual(cell['positive'],4)
        self.assertEqual([b['mean'] for b in cell['blocks']],[8.]*4)
        self.assertEqual(result['checkpoint_increments']['3->4']['LEARN8']['risk8']['mean'],2.)
        self.assertEqual(result['checkpoint_increments']['0->4']['LEARN8']['risk8']['mean'],8.)
        self.assertEqual(result['checkpoint_increments']['0->4']['H2']['risk8']['conditional_seed_ci95'],[0.,0.])
        self.assertEqual(result['learning_curves']['4']['methods']['LEARN8']['risk8']['games'],64)

    def test_conditional_seed_variance_uses_four_fixed_histories_and_paired_deltas(self):
        indexed,valid=logical_fixture()
        for life in audit.LIVES:
            for replica in range(16):
                baseline=indexed[life,'risk1',4,'H2',replica]['result']['utility']
                indexed[life,'risk1',4,'LEARN8',replica]['result']['utility']=baseline+replica*(life+1)
        cell=audit.paired_contrast(indexed,valid,lambda l,r:((l,'risk1',4,'LEARN8',r),(l,'risk1',4,'H2',r)))
        # Sample variance of 0..15 is 68/3; each history scales it by (life+1)^2.
        se=math.sqrt((68/3)*30/16/16)
        self.assertAlmostEqual(cell['mean'],18.75);self.assertAlmostEqual(cell['conditional_seed_se'],se)
        self.assertAlmostEqual(cell['conditional_seed_ci95'][0],18.75-1.96*se)
        self.assertAlmostEqual(cell['conditional_seed_ci95'][1],18.75+1.96*se)

    def test_cutoff_invalidates_full_contrast_interval_but_retains_other_blocks(self):
        indexed,valid=logical_fixture();indexed[2,'risk8',3,'LEARN8',5]['result'].update(status='CUTOFF',utility=None)
        result=audit.aggregate(indexed,valid);cell=result['learning_curves']['3']['comparisons']['LEARN8-H2']['risk8']
        self.assertFalse(result['primary_complete']);self.assertFalse(cell['complete'])
        self.assertIsNone(cell['mean']);self.assertIsNone(cell['conditional_seed_se']);self.assertIsNone(cell['conditional_seed_ci95'])
        self.assertTrue(cell['blocks'][0]['complete']);self.assertFalse(cell['blocks'][1]['complete'])
        self.assertEqual(cell['blocks'][2]['mean'],6.)
        self.assertFalse(result['checkpoint_increments']['3->4']['LEARN8']['risk8']['complete'])
        self.assertTrue(result['checkpoint_increments']['0->4']['LEARN8']['risk8']['complete'])


if __name__=='__main__':unittest.main()
