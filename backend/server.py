import json
import os
import re
import subprocess
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from .lab import Lab

lab = Lab(os.environ.get('AFTERMATH_DB','aftermath.sqlite3'))
ROOT = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'

def inspect(signature, cluster):
    if not re.fullmatch(r'[1-9A-HJ-NP-Za-km-z]{64,88}', signature): raise ValueError('Enter a base58 Solana transaction signature (64–88 characters).')
    if cluster not in ('devnet','mainnet-beta'): raise ValueError('Unknown cluster')
    payload = dict(jsonrpc='2.0',id=1,method='getTransaction',params=[signature,dict(encoding='jsonParsed',commitment='finalized',maxSupportedTransactionVersion=0)])
    req = urllib.request.Request(f'https://api.{cluster}.solana.com',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=12) as response: data = json.load(response)
    if 'error' in data: raise ValueError('Solana RPC rejected the request. Try again later or use another cluster.')
    return dict(cluster=cluster,signature=signature,commitment='finalized',result=data.get('result'))

class Handler(BaseHTTPRequestHandler):
    def send_json(self,data,status=200):
        body=json.dumps(data).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path=='/api/runs': return self.send_json(lab.list())
        if self.path.startswith('/api/runs/'):
            try: return self.send_json(lab.get(self.path.split('/')[-1]))
            except KeyError: return self.send_json({'error':'Run not found'},404)
        target = ROOT / self.path.split('?')[0].lstrip('/')
        if not target.resolve().is_relative_to(ROOT.resolve()): return self.send_json({'error':'Invalid path'},400)
        if not target.is_file(): target=ROOT/'index.html'
        if not target.exists(): return self.send_json({'error':'Build frontend first: npm run build'},503)
        import mimetypes
        body=target.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(target)[0] or 'application/octet-stream'); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=4096: raise ValueError('Request must contain 1–4096 bytes')
            data=json.loads(self.rfile.read(size))
            if not isinstance(data,dict): raise ValueError('Expected an object')
            if self.path=='/api/runs': result=lab.create(data)
            elif self.path=='/api/inspect': result=inspect(data.get('signature',''),data.get('cluster','devnet'))
            else:
                parts=self.path.split('/')
                if len(parts)!=5 or parts[1:3]!=['api','runs'] or parts[4] not in ('step','restart'): return self.send_json({'error':'Route not found'},404)
                if parts[4]=='restart': result=lab.restart(parts[3])
                else:
                    lab.get(parts[3]) # fail missing IDs before launching the child
                    child=subprocess.run([sys.executable,'-m','backend.worker','--db',lab.path,'--run',parts[3]],capture_output=True,text=True,timeout=30,cwd=ROOT.parents[1])
                    if child.returncode:
                        try: message=json.loads(child.stdout)['error']
                        except (ValueError,KeyError): message='Worker failed; inspect persisted state before retrying.'
                        raise ValueError(message)
                    result=json.loads(child.stdout)
            self.send_json(result)
        except KeyError: self.send_json({'error':'Run not found'},404)
        except (ValueError,TypeError) as e: self.send_json({'error':str(e)},400)
        except Exception: self.send_json({'error':'RPC unavailable. Check connectivity and try again.'},502)

if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
