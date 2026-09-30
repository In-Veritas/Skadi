#!/usr/bin/env python3
"""Confere a integridade do pacote sem instalar nem modificar arquivos."""
import hashlib
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
manifest = root / 'SHA256SUMS'
failures = []
checked = 0
try:
    entries = manifest.read_text(encoding='utf-8').splitlines()
except OSError as error:
    sys.exit('Não foi possível ler SHA256SUMS: ' + str(error))

for line in entries:
    expected, name = line.split('  ', 1)
    target = root / name
    if root not in target.resolve().parents or target.is_symlink():
        failures.append(name + ': caminho inválido')
        continue
    try:
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
    except OSError:
        failures.append(name + ': ausente ou ilegível')
        continue
    checked += 1
    if actual != expected:
        failures.append(name + ': conteúdo diferente do original')

if failures:
    print('\n'.join(failures), file=sys.stderr)
    sys.exit(1)
print(f'OK: {checked} arquivos conferidos. Nenhuma instalação foi executada.')
