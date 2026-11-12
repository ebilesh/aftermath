"""Run a portable recipe against a fresh temporary SQLite database."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.lab import Lab

recipe=json.loads(Path(sys.argv[1] if len(sys.argv)>1 else 'experiments/ack-gap.json').read_text())
with tempfile.TemporaryDirectory() as tmp:
    lab=Lab(Path(tmp)/'lab.db'); run=lab.create(recipe)
    while not run['complete']:
        run=lab.restart(run['id']) if run['crashed'] else lab.step(run['id'])
    assert len(run['credits'])==1
    print(json.dumps({'config':run['config'],'credits':run['credits'],'trace':[{'tick':e['tick'],'kind':e['kind'],'detail':e['detail']} for e in run['events']]},indent=2))
