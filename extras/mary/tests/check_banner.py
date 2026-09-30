"""Teste PTY da intro assíncrona; recebe o caminho de banner/mary.py instalado."""
import fcntl
import importlib.util
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import tempfile

path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('banner', path)
banner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(banner)
assert banner.frame(0) == '\x1b]4;251;#110000\x1b\\'
assert banner.frame(1) == '\x1b]4;251;#11ffff\x1b\\'
assert banner.fade_frame(0) == '\x1b]4;250;#120000\x1b\\'
assert banner.fade_frame(1) == '\x1b]4;250;#12ffff\x1b\\'
for scenario in ('full', 'input', 'signal', 'resize'):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 34, 100, 0, 0))
    before = termios.tcgetattr(slave)
    proc = subprocess.Popen([sys.executable, str(path)], stdin=slave, stdout=slave, stderr=slave)
    start = time.monotonic()
    output = bytearray()
    acted = False
    while proc.poll() is None:
        elapsed = time.monotonic() - start
        assert elapsed < 7, scenario
        if scenario != 'full' and elapsed > .2 and not acted:
            acted = True
            if scenario == 'input': os.write(master, 'ação-áéç\n'.encode())
            if scenario == 'signal': proc.send_signal(signal.SIGTERM)
            if scenario == 'resize':
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 10, 24, 0, 0))
        if select.select([master], [], [], .005)[0]:
            output.extend(os.read(master, 65536))
    assert proc.returncode == 0, scenario
    assert termios.tcgetattr(slave) == before, scenario
    if scenario in ('full', 'resize'):
        assert 5.3 < time.monotonic() - start < 6.5, scenario
    if scenario == 'input':
        assert select.select([slave], [], [], .2)[0]
        assert os.read(slave, 100) == 'ação-áéç\n'.encode()
    if scenario == 'full':
        # Sem digitação, a revelação acaba mas o título não inicia a saída.
        count_at_prompt = output.count(b'\x1b]4;251;')
        while time.monotonic() - start < banner.REVEAL_END + .6:
            if select.select([master], [], [], .05)[0]:
                output.extend(os.read(master, 65536))
        assert output.count(b'\x1b]4;251;') > count_at_prompt + 200
        assert output.count(b'\x1b]4;250;') == 1
        assert banner.RESET.encode() not in output
        assert b'\x1b[?25h' in output
        assert banner.frame(banner.REVEAL_END / banner.DURATION).encode() in output
        # O hook de edição inicia --dismiss; o subprocesso não lê a entrada.
        os.write(master, 'echo ação\n'.encode())
        fade_start = time.monotonic()
        fade = subprocess.Popen([sys.executable, str(path), '--dismiss'],
                                stdin=subprocess.DEVNULL, stdout=slave, stderr=slave)
        assert select.select([slave], [], [], .2)[0]
        assert os.read(slave, 100) == 'echo ação\n'.encode()
        faded = bytearray()
        while fade.poll() is None or banner.fade_frame(1).encode() not in faded:
            assert time.monotonic() - fade_start < 2
            if select.select([master], [], [], .02)[0]:
                faded.extend(os.read(master, 65536))
        assert fade.returncode == 0
        assert .75 < time.monotonic() - fade_start < 1.4
        assert faded.count(b'\x1b]4;250;') >= 40
        assert b'\x1b]4;251;' not in faded
        assert banner.RESET.encode() not in faded
        assert termios.tcgetattr(slave) == before
    print(f'OK {scenario}: prompt/termios/entrada; {time.monotonic()-start:.2f}s', flush=True)
    os.close(master)
    os.close(slave)
print('OK: descida, prompt aos 5,4s, título permanente sem digitar, fade de 0,8s, entrada e resize')

# Exercise the actual Bash observer: empty edits do nothing; the first text
# launches exactly one fade even if subsequent edit notifications arrive.
with tempfile.TemporaryDirectory(prefix='skadi-intro-hook-') as folder:
    config = Path(folder) / 'ghostty/banner'
    config.mkdir(parents=True)
    (config / 'mary.py').symlink_to(path.resolve())
    master, slave = pty.openpty()
    def controlling_tty():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    script = r'''
BLE_VERSION=test XDG_CONFIG_HOME=$2
source "$1"
[[ ${_ble_edit_dirty_observer[*]} == skadi/intro-on-edit ]] || exit 1
_ble_edit_str=
skadi/intro-on-edit
[[ ! ${_skadi_intro_dismissed-} ]] || exit 2
_ble_edit_str=ação
skadi/intro-on-edit
skadi/intro-on-edit
[[ $_skadi_intro_dismissed == 1 ]] || exit 3
sleep 1.1
'''
    prompt = Path(__file__).resolve().parents[1] / 'overrides/mary-shell/mary-prompt.sh'
    proc = subprocess.Popen(['bash', '-c', script, 'check', str(prompt), folder],
                            stdin=slave, stdout=slave, stderr=slave,
                            preexec_fn=controlling_tty)
    output = bytearray()
    deadline = time.monotonic() + 3
    while proc.poll() is None:
        assert time.monotonic() < deadline
        if select.select([master], [], [], .02)[0]:
            output.extend(os.read(master, 65536))
    assert proc.returncode == 0, output
    assert output.count(banner.fade_frame(0).encode()) == 1, output
    assert output.count(banner.fade_frame(1).encode()) == 1, output
    assert b'\x1b]4;251;' not in output, output
    os.close(master)
    os.close(slave)
print('OK: observer real do Bash ignora buffer vazio e dispara fade uma única vez')
