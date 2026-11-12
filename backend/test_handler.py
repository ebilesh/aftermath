import tempfile
import unittest
from pathlib import Path
from backend.lab import Lab
from examples.custom_handler import MerchantHandler

class HandlerTests(unittest.TestCase):
    def test_custom_handler_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            lab=Lab(Path(tmp)/'test.db',handler=MerchantHandler())
            run=lab.create({'duplicates':2,'outage_steps':0,'crash':'after_commit'})
            while not run['complete']:
                run=lab.restart(run['id']) if run['crashed'] else lab.step(run['id'])
            self.assertEqual(len(run['credits']),1)
            self.assertTrue(run['credits'][0]['signature'].startswith('example:'))
    def test_rejected_input_rolls_back_and_can_retry(self):
        for change in ({'recipient':'wrong'},{'lamports':1},{'finalized':False},{'err':'InstructionError'}):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as tmp:
                tx=dict(signature='example-tx',recipient='merchant-demo',lamports=25000000,finalized=True,err=None)
                tx.update(change)
                lab=Lab(Path(tmp)/'test.db',handler=MerchantHandler(lambda _:tx))
                run=lab.create({'duplicates':0,'outage_steps':0,'crash':'none'})
                with self.assertRaises(ValueError): lab.step(run['id'])
                saved=lab.get(run['id'])
                self.assertEqual(saved['credits'],[])
                self.assertEqual(saved['jobs'][0]['state'],'pending')
                lab.handler=MerchantHandler()
                self.assertTrue(lab.step(run['id'])['complete'])
