"""Monitor readiness and summarize real request timings without reading API secrets."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from word_endpoint.processes import process_name


def health(base: str) -> dict:
    try:
        with urllib.request.urlopen(base + '/ready', timeout=5) as response:
            return {'http_status': response.status, 'body': json.load(response)}
    except urllib.error.HTTPError as error:
        with error:
            try:
                body = json.load(error)
            except ValueError:
                body = None
            return {'http_status': error.code, 'body': body}
    except Exception as error:
        return {'error': type(error).__name__ + ': ' + str(error)}


def processes() -> dict:
    result = {}
    for label, relative in (('server', 'logs/server.pid'), ('tunnel', 'logs/tunnel.pid'),
                            ('compare', 'work/compare.word.pid'), ('convert', 'work/convert.word.pid')):
        try:
            pid = int((ROOT / relative).read_text().strip())
            result[label] = {'pid': pid, 'image': process_name(pid)}
        except (OSError, ValueError) as error:
            result[label] = {'error': type(error).__name__}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--minutes', type=int, default=30)
    parser.add_argument('--interval', type=int, default=10)
    parser.add_argument('--base', default='http://127.0.0.1:8787')
    args = parser.parse_args()
    if not 1 <= args.interval <= args.minutes <= 120:
        parser.error('Require 1 <= interval <= minutes <= 120')
    began = datetime.now().astimezone()
    destination = ROOT / 'reports' / f'endpoint-monitor-{began:%Y%m%d-%H%M%S}.json'
    report = {'began_local': began.isoformat(), 'duration_minutes': args.minutes,
              'interval_minutes': args.interval, 'checkpoints': [], 'health_samples': [],
              'limitations': 'Loopback readiness and recorded process images; passive request timings from actual logs. No authenticated synthetic requests or public reachability probe. Mixed document sizes; no traffic means no interval speed estimate.'}
    began_clock = time.monotonic()
    next_checkpoint = 0
    deadline = args.minutes * 60
    since = (began - timedelta(minutes=args.interval)).strftime('%Y-%m-%d %H:%M:%S.%f')[:23]
    while True:
        elapsed = time.monotonic() - began_clock
        now = datetime.now().astimezone()
        sample = {'at_local': now.isoformat(), 'elapsed_seconds': round(elapsed),
                  'readiness': health(args.base), 'processes': processes()}
        report['health_samples'].append(sample)
        if elapsed >= next_checkpoint:
            audit = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/performance-audit.py'),
                                    '--since', since], cwd=ROOT, capture_output=True,
                                   text=True, encoding='utf-8', errors='replace', timeout=30)
            checkpoint = dict(sample)
            checkpoint['interval_since_local'] = since
            checkpoint['timings'] = json.loads(audit.stdout) if audit.returncode == 0 else {'error': audit.stderr}
            report['checkpoints'].append(checkpoint)
            medians = {name: row['timings']['http_ms'] for name, row in checkpoint['timings'].get('endpoints', {}).items()}
            print(json.dumps({'checkpoint_minutes': round(elapsed / 60), 'at': now.isoformat(),
                              'readiness': sample['readiness'], 'http_timings': medians,
                              'report': str(destination)}), flush=True)
            since = now.strftime('%Y-%m-%d %H:%M:%S.%f')[:23]
            next_checkpoint = min(next_checkpoint + args.interval * 60, deadline)
        else:
            print(json.dumps({'heartbeat_minutes': round(elapsed / 60),
                              'readiness': sample['readiness']}), flush=True)
        destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
        if elapsed >= deadline:
            report['completed_local'] = datetime.now().astimezone().isoformat()
            destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
            print('Monitoring complete: ' + str(destination), flush=True)
            return
        time.sleep(min(60, max(0, next_checkpoint - (time.monotonic() - began_clock))))


if __name__ == '__main__':
    main()
