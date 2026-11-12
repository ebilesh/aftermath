import concurrent.futures
import tempfile
import unittest
from pathlib import Path
from backend.lab import Lab

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'test.db'; self.lab=Lab(self.path)
    def tearDown(self): self.tmp.cleanup()
    def drain(self,rid):
        for _ in range(100):
            r=self.lab.get(rid)
            if r['complete']: return r
            self.lab.restart(rid) if r['crashed'] else self.lab.step(rid)
        self.fail('Worker did not converge')
    def test_after_commit_restart_from_new_instance(self):
        r=self.lab.create(dict(duplicates=8,outage_steps=0,crash='after_commit'))
        r=self.lab.step(r['id'])
        self.assertEqual(len(r['credits']),1)
        self.assertEqual(r['jobs'][0]['state'],'pending')
        self.assertTrue(r['crashed'])
        self.lab=Lab(self.path) # reopen persisted state, no in-memory recovery
        r=self.drain(r['id'])
        self.assertEqual(len(r['credits']),1)
        self.assertEqual(sum(e['kind']=='duplicate_ignored' for e in r['events']),9)
    def test_before_commit_does_not_credit(self):
        r=self.lab.create(dict(duplicates=1,outage_steps=0,crash='before_commit'))
        r=self.lab.step(r['id']); self.assertEqual(r['credits'],[])
        self.assertEqual(len(self.drain(r['id'])['credits']),1)
    def test_outage_preserves_pending_work(self):
        r=self.lab.create(dict(duplicates=0,outage_steps=3,crash='none'))
        for _ in range(3):
            r=self.lab.step(r['id']); self.assertEqual(r['credits'],[]); self.assertEqual(r['jobs'][0]['state'],'pending')
        self.assertTrue(self.drain(r['id'])['complete'])
    def test_concurrent_workers_single_credit(self):
        r=self.lab.create(dict(duplicates=30,outage_steps=0,crash='none'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda _: self.lab.step(r['id']),range(31)))
        r=self.drain(r['id']); self.assertTrue(r['complete']); self.assertEqual(len(r['credits']),1)
        self.assertEqual(sum(e['kind']=='credited' for e in r['events']),1)
    def test_database_constraint_independent_of_worker(self):
        r=self.lab.create({}); self.drain(r['id'])
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError),self.lab.connect() as db:
            db.execute('INSERT INTO credits VALUES(?,?,?)',(r['id'],'another-signature',1))
    def test_identical_recipes_reproduce_logical_trace(self):
        traces=[]
        for _ in range(2):
            run=self.lab.create({'duplicates':3,'outage_steps':2,'crash':'after_commit'})
            run=self.drain(run['id'])
            traces.append([(event['tick'],event['kind']) for event in run['events']])
        self.assertEqual(traces[0],traces[1])

    def test_configuration_bounds(self):
        for config in ({'duplicates':51},{'duplicates':True},{'outage_steps':-1},{'crash':'random'}):
            with self.assertRaises(ValueError): self.lab.create(config)
    def test_recipe_matrix(self):
        for crash in ('none','before_commit','after_commit'):
            for duplicates in (0,1,10):
                r=self.lab.create(dict(crash=crash,duplicates=duplicates,outage_steps=2))
                r=self.drain(r['id']); self.assertTrue(r['invariant']); self.assertEqual(len(r['credits']),1)

if __name__=='__main__': unittest.main()
