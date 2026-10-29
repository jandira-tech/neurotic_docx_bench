"""Deterministic validation of immutable manifests and Word failure evidence."""
from __future__ import annotations
from pathlib import Path


def manifest_hashes_text(text: str) -> dict[str, str]:
    hashes = {}
    for line in text.splitlines():
        if not line:
            continue
        if len(line) < 67 or line[64:66] not in ('  ', ' *'):
            raise ValueError('Malformed SHA256 manifest line')
        digest, name = line[:64], line[66:]
        if any(c not in '0123456789abcdef' for c in digest) or name in hashes:
            raise ValueError('Invalid digest or duplicate manifest path')
        hashes[name] = digest
    return hashes


def word_output_confirmed(pdf: Path | None, lines: list[dict], original: str,
                          renamed: str, kind: str) -> bool:
    return pdf is not None and any(line.get('kind') == kind
        and line.get('original_filename') in (original, renamed)
        and line.get('status') in ('ok', 'skipped') and line.get('path_out') == str(pdf)
        for line in lines)


def word_log_evidence(text: str, original: str, path: str) -> list[dict]:
    return [{'path': path, 'line': line} for line in text.splitlines()
            if original in line and 'FAIL' in line]


def word_failure_reason(lines: list[dict], original: str, renamed: str,
                        kind: str, evidence: list[dict]) -> str:
    failed = [line for line in lines if line.get('original_filename') in (original, renamed)
              and line.get('kind') == kind and line.get('status') == 'failed']
    reason = str(failed[-1].get('error') or '') if failed else ''
    for item in evidence:
        if not reason and ' — ' in item['line']:
            reason = item['line'].split(' — ', 1)[1]
    if not reason:
        raise ValueError(f'Missing per-document Word failure reason: {original}')
    if not evidence:
        raise ValueError(f'Missing per-document Word log evidence: {original}')
    return reason
