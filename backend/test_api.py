"""Exercise real HTTP request parsing and subprocess worker without binding a port."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend.lab import Lab
from backend.server import Handler

class MemoryConnection:
    def __init__(self,data): self.input=io.BytesIO(data); self.output=bytearray()
    def makefile(self,*args): return self.input
    def sendall(self,data): self.output.extend(data)

class ApiTests(unittest.TestCase):
    def request(self,path,body=None):
        payload=json.dumps(body).encode() if body is not None else b''
        method='POST' if body is not None else 'GET'
        req=f'{method} {path} HTTP/1.0\r\nHost: localhost\r\nContent-Length: {len(payload)}\r\n\r\n'.encode()+payload
        conn=MemoryConnection(req)
        with patch.object(Handler,'log_message'): Handler(conn,('127.0.0.1',1234),None)
        head,result=bytes(conn.output).split(b'\r\n\r\n',1)
        return int(head.split()[1]),json.loads(result)
    def test_http_to_worker_to_database_recovery(self):
        with tempfile.TemporaryDirectory() as tmp,patch('backend.server.lab',Lab(Path(tmp)/'api.db')):
            code,run=self.request('/api/runs',{'duplicates':3,'outage_steps':1,'crash':'after_commit'})
            self.assertEqual(code,200)
            rid=run['id']
            for _ in range(12):
                if run['complete']: break
                action='restart' if run['crashed'] else 'step'
                code,run=self.request(f'/api/runs/{rid}/{action}',{})
                self.assertEqual(code,200,run)
            self.assertTrue(run['complete'])
            code,saved=self.request(f'/api/runs/{rid}')
            self.assertEqual(code,200)
            self.assertEqual(len(saved['credits']),1)
            self.assertEqual(sum(e['kind']=='worker_crashed' for e in saved['events']),1)
    def test_inspector_unavailable_response(self):
        with patch('backend.server.urllib.request.urlopen',side_effect=TimeoutError):
            code,result=self.request('/api/inspect',{'signature':'1'*64,'cluster':'devnet'})
        self.assertEqual(code,502)
        self.assertIn('unavailable',result['error'])
        self.assertNotIn('result',result)
