"""Real process death at the durable commit-to-acknowledgement boundary."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from backend.lab import Lab

ROOT=Path(__file__).resolve().parents[1]
class ProcessRecoveryTests(unittest.TestCase):
    def test_kill_after_commit_restart_exactly_one_credit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'lab.db'; ready=Path(tmp)/'committed'
            lab=Lab(path)
            run=lab.create({'duplicates':4,'outage_steps':0,'crash':'none'})
            command=[sys.executable,'-m','backend.worker','--db',str(path),'--run',run['id']]
            child=subprocess.Popen(command+['--pause-after-credit',str(ready)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                deadline=time.monotonic()+10
                while not ready.exists():
                    if child.poll() is not None: self.fail('Worker exited before checkpoint: '+child.communicate()[1])
                    if time.monotonic()>deadline: self.fail('Worker never reached committed checkpoint')
                    time.sleep(.01)
                durable=Lab(path).get(run['id'])
                self.assertEqual(len(durable['credits']),1)
                self.assertTrue(all(j['state']=='pending' for j in durable['jobs']))
                self.assertFalse(any(e['kind']=='acknowledged' for e in durable['events']))
                child.kill() # actual OS process termination, not an injected exception
                child.communicate(timeout=5)
                self.assertNotEqual(child.returncode,0)
            finally:
                if child.poll() is None: child.kill(); child.communicate(timeout=5)
            restarted=subprocess.run(command+['--drain'],cwd=ROOT,capture_output=True,text=True,timeout=10,check=True)
            result=json.loads(restarted.stdout)
            self.assertTrue(result['complete'])
            final=Lab(path).get(run['id'])
            self.assertEqual(len(final['credits']),1)
            self.assertEqual(sum(e['kind']=='credited' for e in final['events']),1)
            self.assertEqual(sum(e['kind']=='duplicate_ignored' for e in final['events']),5)
            self.assertTrue(all(j['state']=='acked' for j in final['jobs']))
