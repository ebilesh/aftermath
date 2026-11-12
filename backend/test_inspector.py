import io
import json
import unittest
from unittest.mock import patch
from backend.server import inspect

class InspectorTests(unittest.TestCase):
    @patch('backend.server.urllib.request.urlopen')
    def test_read_only_finalized_v0_contract(self,request):
        request.return_value.__enter__.return_value=io.BytesIO(json.dumps({'result':{'slot':123,'meta':{'err':None,'fee':5000}}}).encode())
        result=inspect('1'*64,'devnet')
        req=request.call_args.args[0]
        payload=json.loads(req.data)
        self.assertEqual(req.full_url,'https://api.devnet.solana.com')
        self.assertEqual(payload['method'],'getTransaction')
        self.assertEqual(payload['params'][1],{'encoding':'jsonParsed','commitment':'finalized','maxSupportedTransactionVersion':0})
        self.assertEqual(result['result']['slot'],123)
    @patch('backend.server.urllib.request.urlopen')
    def test_null_is_not_failure(self,request):
        request.return_value.__enter__.return_value=io.BytesIO(b'{"result":null}')
        self.assertIsNone(inspect('1'*64,'mainnet-beta')['result'])
    @patch('backend.server.urllib.request.urlopen')
    def test_rpc_errors_are_not_success(self,request):
        request.return_value.__enter__.return_value=io.BytesIO(b'{"error":{"code":429}}')
        with self.assertRaises(ValueError): inspect('1'*64,'devnet')
    @patch('backend.server.urllib.request.urlopen')
    def test_reject_invalid_inputs_without_network(self,request):
        for sig,cluster in [('bad','devnet'),('0'*88,'devnet'),('1'*64,'https://untrusted.example')]:
            with self.assertRaises(ValueError): inspect(sig,cluster)
        request.assert_not_called()
