"""Summarize existing timing logs without launching Word or reading secrets."""
import argparse
from collections import Counter, defaultdict
import ctypes
from ctypes import wintypes
import json
import math
import os
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
SIZE_BANDS = (('under_32_KiB', 0, 32 * 1024), ('32_to_64_KiB', 32 * 1024, 64 * 1024),
              ('64_to_128_KiB', 64 * 1024, 128 * 1024),
              ('128_to_256_KiB', 128 * 1024, 256 * 1024),
              ('256_to_512_KiB', 256 * 1024, 512 * 1024),
              ('512_KiB_and_up', 512 * 1024, None))


def summary(values):
    if not values:
        return None
    ordered = sorted(values)
    return {'count': len(values), 'median_ms': statistics.median(values),
            'p95_ms': ordered[math.ceil(len(values) * .95) - 1],
            'max_ms': max(values), 'sum_ms': sum(values)}


def memory():
    class Status(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
            (name, ctypes.c_ulonglong) for name in (
                'total', 'available', 'page_total', 'page_available',
                'virtual_total', 'virtual_available', 'extended_available')]
    status = Status()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return {'total_gib': round(status.total / 2**30, 2),
            'available_gib': round(status.available / 2**30, 2),
            'load_percent': status.load}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--since', help='Local log timestamp, e.g. 2026-10-13 00:24:01')
    parser.add_argument('--until', help='Exclusive upper local timestamp')
    parser.add_argument('--include-requests', action='store_true', help='Include successful timing/size rows')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    logs = defaultdict(list)
    for path in (ROOT / 'logs').glob('*.log*'):
        if path.name.startswith(('server.log', 'compare-worker.log', 'convert-worker.log')):
            logs[path.name.split('.log')[0]].extend(path.read_text(encoding='utf-8', errors='replace').splitlines())
    starts = [line[:23] for line in logs['server'] if ' INFO listening on ' in line]
    since = (args.since or (max(starts) if starts else '')).replace(',', '.')
    until = args.until.replace(',', '.') if args.until else None
    requests = {}
    jobs = {}
    phases = defaultdict(list)
    phase_entries = []
    statuses = Counter()
    for name, lines in logs.items():
        for line in lines:
            timestamp = line[:23].replace(',', '.')
            if timestamp < since or (until and timestamp >= until):
                continue
            if name == 'server':
                match = re.search(r'INFO ([0-9a-f]{32}) POST /v1/(compare-pdf|compare|convert) (\d+) (\S+) (\d+)ms', line)
                if match:
                    ident, kind, status, code, elapsed = match.groups()
                    statuses[status + ':' + code] += 1
                    if status == '200':
                        requests.setdefault(ident, {}).update(kind=kind.replace('-', '_'), http_ms=int(elapsed),
                                                              at_local=line[:23])
                match = re.search(r'validation request=([0-9a-f]{32}) bytes=(\d+)', line)
                if match:
                    requests.setdefault(match[1], {})['input_bytes'] = int(match[2])
                match = re.search(r'(?:validation|job) request=([0-9a-f]{32}).*?(queue_ms|input_ms|ms)=(\d+)', line)
                if match:
                    ident, key, value = match.groups()
                    requests.setdefault(ident, {})['validation_ms' if key == 'ms' else key] = int(value)
                match = re.search(r'job request=([0-9a-f]{32}) id=([0-9a-f]{32})', line)
                if match:
                    jobs[match[2]] = match[1]
            else:
                match = re.search(r'job id=([0-9a-f]{32}) phase=(\w+) ms=(\d+)', line)
                if match:
                    phase_entries.append((match[1], match[2], int(match[3])))
    # Resolve worker timings after all job-to-request mappings have been read.
    for name in ('compare-worker', 'convert-worker'):
        for line in logs[name]:
            timestamp = line[:23].replace(',', '.')
            if timestamp < since or (until and timestamp >= until):
                continue
            match = re.search(r'job id=([0-9a-f]{32}) kind=(compare_pdf|compare|convert) word_ms=(\d+)', line)
            if match and match[1] in jobs:
                requests.setdefault(jobs[match[1]], {})['word_ms'] = int(match[3])
    for job, phase, elapsed in phase_entries:
        request = requests.get(jobs.get(job))
        if request and 'http_ms' in request:
            phases[(request['kind'], phase)].append(elapsed)
    successful = [row for row in requests.values() if 'http_ms' in row]
    report = {'since_local_log_time': since, 'logical_cpus': os.cpu_count(),
              'memory_snapshot': memory(), 'post_statuses': dict(statuses), 'endpoints': {}}
    for kind in ('compare', 'compare_pdf', 'convert'):
        rows = [row for row in successful if row['kind'] == kind]
        measured = [row for row in rows if 'word_ms' in row]
        report['endpoints'][kind] = {
            'timings': {key: summary([row[key] for row in rows if key in row])
                        for key in ('http_ms', 'word_ms', 'validation_ms', 'queue_ms', 'input_ms')},
            'word_share_of_http_percent': round(100 * sum(row['word_ms'] for row in measured)
                / sum(row['http_ms'] for row in measured), 1) if measured else None,
            'phases': {phase: summary(values) for (lane, phase), values in phases.items() if lane == kind}}
        sized = [row for row in rows if 'input_bytes' in row]
        report['endpoints'][kind]['input_size'] = {
            'measured_count': len(sized), 'missing_count': len(rows) - len(sized),
            'median_bytes': statistics.median(row['input_bytes'] for row in sized) if sized else None}
        report['endpoints'][kind]['size_bands'] = {
            label: summary([row['http_ms'] for row in sized
                            if row['input_bytes'] >= lower and (upper is None or row['input_bytes'] < upper)])
            for label, lower, upper in SIZE_BANDS}
    if until:
        report['until_local_log_time_exclusive'] = until
    if args.include_requests:
        report['successful_requests'] = successful
    report['input_size_definition'] = 'Compressed prepared DOCX bytes; compare routes sum original and revised. Logged after input validation/template detachment.'
    report['limitations'] = 'Existing successful requests; mixed document sizes; no controlled load test or CPU attribution.'
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)


if __name__ == '__main__':
    main()
