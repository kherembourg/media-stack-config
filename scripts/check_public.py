#!/usr/bin/env python3
"""Guard the curated public tree. Heuristics complement, not replace, manual review."""
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SENSITIVE = re.compile(r"^(?:api[_-]?key|password|passwd|username|sessionSecret|clientId|serverId|machineId|vapidPrivate|token|secret)$", re.I)
TOKENS = re.compile(r"(?:gh[pousr]_)[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]+|\b[0-9a-fA-F]{32,64}\b")
PRIVATE_PATH = re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+/|\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b")
ASSIGNMENT = re.compile(r"^\s*(?:[\w.-]+\.)?(key|api[_-]?key|password|passwd|username|token|secret)\s*[:=]\s*(.*?)\s*$", re.I | re.M)


def placeholder(value):
    return not value or value.startswith(("{{HOMEPAGE_", "${"))


def json_secrets(value):
    if isinstance(value, dict):
        return any((SENSITIVE.fullmatch(k) and not placeholder(str(v or ""))) or json_secrets(v) for k, v in value.items())
    if isinstance(value, list):
        return any(json_secrets(v) for v in value)
    return False


def issues(path, text):
    found = []
    if TOKENS.search(text): found.append("token/private-key/high-entropy identifier pattern")
    if PRIVATE_PATH.search(text): found.append("personal absolute path or private network address")
    if re.search(r"\w+://[^\s/@]+:[^\s/@]+@", text): found.append("credentials embedded in URL")
    if path.endswith('.json') and json_secrets(json.loads(text)): found.append("credential/identity field in JSON")
    if path.endswith('.xml'):
        root = ET.fromstring(text)
        if any(SENSITIVE.fullmatch(e.tag) and (e.text or '').strip() for e in root.iter()): found.append("credential/identity field in XML")
    if path.endswith(('.yaml', '.yml', '.conf')):
        for _, value in ASSIGNMENT.findall(text):
            if not placeholder(value.strip('"\'')): found.append("non-placeholder credential assignment")
    return found


def check():
    names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    failures = []
    allowed = {'.gitignore', '.env.example', 'README.md', 'compose.yml'}
    prefixes = ('docs/', 'preferences/', 'config/homepage/', 'scripts/', '.github/workflows/')
    for name in sorted(set(filter(None, names))):
        p = ROOT / name
        if p.is_symlink() or (name not in allowed and not name.startswith(prefixes)) or p.suffix not in {'.md', '.json', '.xml', '.conf', '.yaml', '.yml', '.py', '.example', ''} and name != '.gitignore':
            failures.append((name, ['unexpected file type/location']))
            continue
        problems = issues(name, p.read_text())
        if problems: failures.append((name, problems))
    for name, problems in failures: print(f'{name}: {", ".join(problems)}')
    if failures: raise SystemExit(1)
    print('Public-tree checks passed (manual review is still required).')


if __name__ == '__main__':
    assert issues('example.conf', 'Password=' + 'not-public')
    assert issues('example.json', json.dumps({'apiKey': 'not-public'}))
    assert issues('README.md', 'ghp_' + 'x' * 36)
    assert not issues('services.yaml', 'key: "{{HOMEPAGE_FILE_SERVICE_KEY}}"')
    check()
