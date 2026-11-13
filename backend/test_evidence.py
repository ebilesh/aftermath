import unittest
from backend.evidence import validate_signature, summarize, SYSTEM_PROGRAM

class EvidenceTests(unittest.TestCase):
    def test_signature_is_decoded_not_just_length_checked(self):
        validate_signature('1'*64)
        for value in ('1'*65, 'z'*88, '0'*88, None, 123):
            with self.subTest(value=value), self.assertRaises(ValueError): validate_signature(value)
    def instruction(self, program=SYSTEM_PROGRAM):
        return {'programId':program,'parsed':{'type':'transfer','info':{'source':'sender','destination':'recipient','lamports':9007199254740993}}}
    def transaction(self,err=None):
        return {'slot':1,'transaction':{'message':{'instructions':[self.instruction()]}},'meta':{'err':err,'innerInstructions':[{'index':0,'instructions':[self.instruction()]}]}}
    def test_outer_and_inner_integer_evidence(self):
        result=summarize(self.transaction())
        self.assertEqual([x['scope'] for x in result['transfers']],['outer','inner:0'])
        self.assertEqual(result['transfers'][0]['lamports'],'9007199254740993')
        self.assertTrue(all(x['applied'] for x in result['transfers']))
    def test_failed_transaction_does_not_report_applied_transfer(self):
        result=summarize(self.transaction({'InstructionError':[1,'failure']}))
        self.assertEqual(result['status'],'failed')
        self.assertFalse(any(x['applied'] for x in result['transfers']))
    def test_missing_execution_metadata_is_unknown(self):
        tx=self.transaction();tx['meta']={}
        result=summarize(tx)
        self.assertEqual(result['status'],'unknown');self.assertFalse(result['transfers'][0]['applied'])
    def test_other_program_not_treated_as_sol_transfer(self):
        tx=self.transaction();tx['transaction']['message']['instructions']=[self.instruction('token-program')];tx['meta']['innerInstructions']=[]
        self.assertEqual(summarize(tx)['transfers'],[])
    def test_missing_and_malformed_are_distinct(self):
        self.assertEqual(summarize(None)['status'],'not_found')
        with self.assertRaises(ValueError):summarize({})
