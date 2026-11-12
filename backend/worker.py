"""One real worker process per attempt, or drain until completion for experiments."""
import argparse
import importlib
import json
import time
from pathlib import Path
from .lab import Lab


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--db',required=True)
    parser.add_argument('--run',required=True)
    parser.add_argument('--drain',action='store_true')
    parser.add_argument('--handler',help='Import path module:Factory; factory takes no arguments')
    parser.add_argument('--pause-after-credit',type=Path,help='TEST ONLY: write readiness file after commit, block before ack')
    args=parser.parse_args()
    handler=None
    if args.handler:
        module,factory=args.handler.split(':',1)
        handler=getattr(importlib.import_module(module),factory)()
    lab=Lab(args.db,handler=handler)
    def checkpoint():
        if args.pause_after_credit:
            args.pause_after_credit.write_text('credit committed; acknowledgement pending')
            while True: time.sleep(.05)
    try:
        while True:
            run=lab.get(args.run)
            if run['crashed']:
                print(json.dumps(run)); return
            run=lab.step(args.run,after_credit=checkpoint)
            if not args.drain or run['complete'] or run['crashed']:
                print(json.dumps(run)); return
    except (ValueError,KeyError) as exc:
        print(json.dumps({'error':str(exc)})); raise SystemExit(1)

if __name__=='__main__': main()
