"""Deterministic durable payment worker. All amounts are integer lamports."""
from contextlib import contextmanager
import json
import sqlite3
import uuid
from pathlib import Path
from .handlers import SimulatedPaymentHandler

SCHEMA = '''
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, config TEXT NOT NULL, tick INTEGER NOT NULL DEFAULT 0, outage INTEGER NOT NULL DEFAULT 0, crashed INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), state TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS credits(run_id TEXT PRIMARY KEY REFERENCES runs(id), signature TEXT UNIQUE NOT NULL, lamports INTEGER NOT NULL CHECK(lamports > 0));
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id), tick INTEGER NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
'''
class Lab:
    def __init__(self, path, handler=None):
        self.path = str(Path(path).resolve())
        self.handler = handler or SimulatedPaymentHandler()
        with self.connect() as db: db.executescript(SCHEMA)
    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()
    def event(self, db, rid, kind, detail):
        tick = db.execute('SELECT tick FROM runs WHERE id=?', (rid,)).fetchone()[0]
        db.execute('INSERT INTO events(run_id,tick,kind,detail) VALUES(?,?,?,?)', (rid,tick,kind,detail))
    def create(self, config):
        duplicates = config.get('duplicates', 3)
        outage = config.get('outage_steps', 1)
        crash = config.get('crash', 'after_commit')
        if type(duplicates) is not int or not 0 <= duplicates <= 50 or type(outage) is not int or not 0 <= outage <= 20 or crash not in ('none','before_commit','after_commit'):
            raise ValueError('Invalid experiment configuration')
        config = dict(duplicates=duplicates, outage_steps=outage, crash=crash)
        rid = uuid.uuid4().hex[:12]
        with self.connect() as db:
            db.execute('INSERT INTO runs(id,config,outage) VALUES(?,?,?)', (rid,json.dumps(config),outage))
            db.executemany('INSERT INTO jobs(run_id) VALUES(?)', [(rid,)]*(duplicates+1))
            self.event(db,rid,'created',f'{duplicates+1} simulated notifications queued for order {rid}; 25000000 lamports')
        return self.get(rid)
    def get(self, rid):
        with self.connect() as db:
            row = db.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
            if row is None: raise KeyError(rid)
            result = dict(row); result['config'] = json.loads(result['config'])
            result['events'] = [dict(x) for x in db.execute('SELECT * FROM events WHERE run_id=? ORDER BY id',(rid,))]
            result['jobs'] = [dict(x) for x in db.execute('SELECT * FROM jobs WHERE run_id=? ORDER BY id',(rid,))]
            result['credits'] = [dict(x) for x in db.execute('SELECT * FROM credits WHERE run_id=?',(rid,))]
            result['invariant'] = len(result['credits']) <= 1
            result['complete'] = all(j['state']=='acked' for j in result['jobs'])
            return result
    def list(self):
        with self.connect() as db: ids = [r[0] for r in db.execute('SELECT id FROM runs ORDER BY rowid DESC LIMIT 100')]
        return [self.get(rid) for rid in ids]
    def step(self, rid, after_credit=None):
        # Verification and credit are serialized; acknowledgement is a separate commit.
        job_id = None
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            run = db.execute('SELECT * FROM runs WHERE id=?',(rid,)).fetchone()
            if run is None: raise KeyError(rid)
            if run['crashed']: raise ValueError('Worker stopped. Restart it before advancing.')
            db.execute('UPDATE runs SET tick=tick+1 WHERE id=?',(rid,))
            job = db.execute("SELECT * FROM jobs WHERE run_id=? AND state!='acked' ORDER BY id LIMIT 1",(rid,)).fetchone()
            if not job:
                pass
            elif run['outage']:
                db.execute('UPDATE runs SET outage=outage-1 WHERE id=?',(rid,))
                self.event(db,rid,'rpc_unavailable','Injected verification outage; notification stays pending. No credit written.')
            else:
                config = json.loads(run['config'])
                already_crashed = db.execute("SELECT 1 FROM events WHERE run_id=? AND kind='worker_crashed'",(rid,)).fetchone()
                crash = config['crash'] if not already_crashed else 'none'
                payment = self.handler.verify(rid)
                if (type(payment.lamports) is not int or payment.lamports != 25000000
                        or not isinstance(payment.signature,str) or not payment.signature):
                    raise ValueError('Handler must return a verified matching 25000000-lamport payment')
                self.event(db,rid,'verified',payment.evidence)
                if crash == 'before_commit':
                    db.execute('UPDATE runs SET crashed=1 WHERE id=?',(rid,))
                    self.event(db,rid,'worker_crashed','Injected stop before ledger credit. Notification remains pending.')
                else:
                    inserted = db.execute('INSERT OR IGNORE INTO credits VALUES(?,?,?)',(rid,payment.signature,payment.lamports)).rowcount
                    if not inserted:
                        existing=db.execute('SELECT * FROM credits WHERE run_id=?',(rid,)).fetchone()
                        if existing is None or existing['signature'] != payment.signature or existing['lamports'] != payment.lamports:
                            raise ValueError('Payment conflicts with an existing order or signature')
                    self.event(db,rid,'credited' if inserted else 'duplicate_ignored','Ledger credit committed.' if inserted else 'Unique order/signature constraint prevented a second credit.')
                    if crash == 'after_commit':
                        db.execute('UPDATE runs SET crashed=1 WHERE id=?',(rid,))
                        self.event(db,rid,'worker_crashed','Injected stop after ledger credit, before acknowledgement. Replay will encounter the existing credit.')
                    else:
                        job_id=job['id']
        # Durable seam: the ledger transaction has COMMITTED, the job is still pending.
        # A subprocess integration test kills the process while this hook blocks.
        if job_id is not None:
            if after_credit is not None: after_credit()
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                changed=db.execute("UPDATE jobs SET state='acked' WHERE id=? AND state='pending'",(job_id,)).rowcount
                if changed: self.event(db,rid,'acknowledged',f'Notification {job_id} acknowledged.')
        return self.get(rid)
    def restart(self,rid):
        with self.connect() as db:
            if not db.execute('SELECT 1 FROM runs WHERE id=?',(rid,)).fetchone(): raise KeyError(rid)
            db.execute('UPDATE runs SET crashed=0 WHERE id=?',(rid,))
            self.event(db,rid,'restarted','Worker resumed from durable pending notifications.')
        return self.get(rid)
