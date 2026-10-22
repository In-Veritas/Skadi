#!/usr/bin/env python3
"""Exercise early typing through the user's actual Bash startup and ble.sh.

Input latency is measured at the PTY output, not at the monitor's next frame.
Requires pyte to check the rendered cells, including input before the intro.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import tty
import pyte

ROOT = Path(__file__).resolve().parents[1]


def run(scenario, baseline, terminal=False, snapshot=None):
    with tempfile.TemporaryDirectory(prefix='skadi-input-') as folder:
        work = Path(folder)
        config = work / 'config/ghostty'
        (config / 'mary-shell').mkdir(parents=True)
        (config / 'banner').mkdir()
        (work / 'cache').mkdir()
        (work / 'state').mkdir()
        (work / 'runtime').mkdir(mode=0o700)
        # Reuse the installed terminal/keymap caches without writing to them.
        # This measures normal window startup, not first-time ble.sh setup.
        cached = Path.home() / '.cache/blesh'
        if cached.is_dir():
            shutil.copytree(cached, work / 'cache/blesh', symlinks=True)
        source = Path.home() / '.config/ghostty' if baseline else ROOT / 'overrides'
        for name in ('start.bash', 'startup.bash', 'init.sh', 'mary-prompt.sh'):
            (config / 'mary-shell' / name).symlink_to(source / 'mary-shell' / name)
        (config / 'mary-shell/end.bash').symlink_to(
            Path.home() / '.config/ghostty/mary-shell/end.bash' if baseline
            else ROOT / 'overrides/mary-shell/end.bash')
        (config / 'banner/mary.py').symlink_to(source / 'banner/mary.py')
        trace, ready, result = (work / name for name in ('edits', 'ready', 'result'))
        rc = work / 'bashrc'
        rc.write_text(r'''source "$SKADI_TEST_BASHRC"
HISTFILE=/dev/null
function skadi/test/observe {
    printf '%s\t%s\0' "$EPOCHREALTIME" "$_ble_edit_str" >> "$SKADI_TEST_TRACE"
}
_ble_edit_dirty_observer+=(skadi/test/observe)
skadi/test/observe
function skadi/test/ready { printf '%s' "$EPOCHREALTIME" > "$SKADI_TEST_READY"; }
ble/util/idle.push skadi/test/ready
''')
        env = {**os.environ, 'XDG_CONFIG_HOME': str(config.parent),
               'XDG_CACHE_HOME': str(work / 'cache'),
               'XDG_STATE_HOME': str(work / 'state'),
               'XDG_RUNTIME_DIR': str(work / 'runtime'), 'TERM': 'xterm-256color',
               'TERM_PROGRAM': 'ghostty', 'HISTFILE': '/dev/null',
               'SKADI_TEST_BASHRC': str(Path.home() / '.bashrc'),
               'SKADI_TEST_TRACE': str(trace), 'SKADI_TEST_READY': str(ready)}
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 34, 100, 0, 0))

        def controlling_tty():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        start = time.monotonic()
        process = subprocess.Popen(['bash', '--noprofile', '--rcfile', str(rc), '-i'],
                                   stdin=slave, stdout=slave, stderr=slave, env=env,
                                   cwd='/tmp', preexec_fn=controlling_tty)
        output = bytearray()
        screen = pyte.Screen(100, 34)
        stream = pyte.ByteStream(screen)
        first_positions = []
        orphaned = False
        tracking = False
        reply_tail = b''
        terminal_reply_tail = b''

        def pump(duration=.01):
            nonlocal reply_tail, terminal_reply_tail, orphaned
            inputs = [master, sys.stdin.fileno()] if terminal else [master]
            readable = select.select(inputs, [], [], duration)[0]
            if terminal and sys.stdin.fileno() in readable:
                incoming = terminal_reply_tail + os.read(sys.stdin.fileno(), 65536)
                # Only forward protocol replies. A test window must not treat
                # typing intended for another window as an executable command.
                replies = re.compile(rb'\x1b\[(?:[?>]?[0-9;]*[cRn]|\?[0-9]+u|\??[0-9;]*\$y)'
                                     rb'|\x1bP[^\x1b]*\x1b\\'
                                     rb'|\x1b\][0-9;]+rgb:[^\x07\x1b]*(?:\x07|\x1b\\)')
                consumed = 0
                for match in replies.finditer(incoming):
                    os.write(master, match.group())
                    consumed = match.end()
                tail = incoming[consumed:]
                escape = tail.rfind(b'\x1b')
                terminal_reply_tail = tail[escape:] if escape >= 0 and len(tail) - escape < 4096 else b''
            if master in readable:
                data = os.read(master, 65536)
                output.extend(data)
                stream.feed(data)
                if tracking:
                    for row, line in enumerate(screen.display):
                        if 'Z' in line:
                            col = line.index('Z')
                            first_positions.append((row, col))
                            if not line[:col].endswith((']$ ', ']# ')):
                                orphaned = True
                if terminal:
                    os.write(sys.stdout.fileno(), data)
                    return
                data = reply_tail + data
                # Answer the terminal capabilities/cursor queries ble.sh uses.
                # These are terminal replies, never an extra user keystroke.
                query = re.compile(rb'\x1b\[([?>=]?)([0-9;]*)([cn])')
                last = 0
                for match in query.finditer(data):
                    prefix, number, kind = match.groups()
                    response = None
                    if kind == b'n' and number == b'6':
                        response = f'\x1b[{screen.cursor.y + 1};{screen.cursor.x + 1}R'.encode()
                    elif kind == b'c':
                        response = b'\x1b[>1;4000;0c' if prefix == b'>' else b'\x1b[?62;4;6;22c'
                    if response:
                        os.write(master, response)
                    last = match.end()
                suffix = data[last:]
                escape = suffix.rfind(b'\x1b')
                reply_tail = suffix[escape:] if escape >= 0 and len(suffix) - escape < 24 else b''

        def wait_until(predicate, timeout=3):
            deadline = time.monotonic() + timeout
            while not predicate():
                assert process.poll() is None, output.decode(errors='replace')[-2000:]
                assert time.monotonic() < deadline, (
                    'editor=' + repr(buffer()) + '\n' + re.sub(
                        rb'\x1b\].*?(?:\x07|\x1b\\)', b'', bytes(output),
                        flags=re.S).decode(errors='replace')[-2000:])
                pump()

        def buffer():
            if not trace.exists():
                return None
            records = trace.read_bytes().split(b'\0')
            return records[-2].split(b'\t', 1)[1].decode() if len(records) > 1 else None

        try:
            if scenario == 'early':
                wait_until(lambda: time.monotonic() - start >= .03, 9)
            elif scenario == 'animation':
                wait_until(lambda: b'\x1b]4;250;#120000\x1b\\' in output, 9)
            else:
                wait_until(ready.exists, 9)
            sent = time.monotonic()
            tracking = True
            os.write(master, b'Z')
            # A single key must become visible without a following key/Enter.
            wait_until(lambda: first_positions, 4)
            visible_ms = (time.monotonic() - sent) * 1000
            wait_until(lambda: buffer() == 'Z', 4)
            buffered_ms = (time.monotonic() - sent) * 1000
            wait_until(ready.exists)
            tracking = False
            # Bash uses the session's decimal separator (e.g. fr_FR uses ',').
            ready_ms = (float(ready.read_text().replace(',', '.'))
                        - (time.time() - (time.monotonic() - start))) * 1000
            if snapshot and scenario == 'animation':
                end = time.monotonic() + .25
                while time.monotonic() < end:
                    pump()
                subprocess.run(['spectacle', '--background', '--nonotify', '--output', str(snapshot)],
                               check=True, capture_output=True, timeout=15)
            os.write(master, 'ação'.encode())
            wait_until(lambda: buffer() == 'Zação')
            os.write(master, b'\x7f')
            wait_until(lambda: buffer() == 'Zaçã')
            os.write(master, b'o\x01\x04')
            wait_until(lambda: buffer() == 'ação')
            os.write(master, b'\x05\x15')
            wait_until(lambda: buffer() == '')
            command = 'printf %s ' + shlex.quote('ação-áéç 🐋') + ' > ' + shlex.quote(str(result))
            os.write(master, b'\x1b[200~' + command.encode() + b'\x1b[201~')
            wait_until(lambda: buffer() == command)
            os.write(master, b'\r')
            wait_until(result.exists)
            assert result.read_text() == 'ação-áéç 🐋'
            report = {'scenario': scenario,
                      'prompt_ready_ms': round(ready_ms, 1),
                      'first_key_visible_ms': round(visible_ms, 1),
                      'first_key_in_editor_ms': round(buffered_ms, 1),
                      'first_key_on_prompt': not orphaned,
                      'first_key_position_stable': len(set(first_positions)) == 1,
                      'first_key_positions': sorted(set(first_positions)),
                      'unicode_edit_and_paste': 'passed'}
            print(json.dumps(report), flush=True)
            os.write(master, b'exit\r')
            process.wait(timeout=3)
            assert process.returncode == 0
            return report
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--terminal', action='store_true')
    parser.add_argument('--launch-window', action='store_true')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--snapshot', type=Path)
    args = parser.parse_args()
    if args.launch_window:
        output = Path(tempfile.mkdtemp(prefix='skadi-input-native-'))
        binary = Path.home() / '.local/share/skadi/runtime/bin/ghostty'
        # +new-window uses the existing application's environment, so forward
        # an optional test dependency path explicitly with the child command.
        child = [sys.executable]
        if os.environ.get('PYTHONPATH'):
            child = ['/usr/bin/env', 'PYTHONPATH=' + os.environ['PYTHONPATH']] + child
        command = [str(binary), '+new-window', '--working-directory=/tmp', '--title=Skadi input test',
                   '-e', *child, str(Path(__file__).resolve()), '--terminal',
                   '--report', str(output / 'report.json'),
                   '--snapshot', str(output / 'first-key.png')]
        if args.baseline:
            command.append('--baseline')
        with (output / 'runtime.log').open('w') as log:
            subprocess.run(command, check=True, timeout=15, stdout=log, stderr=log)
        deadline = time.monotonic() + 40
        while not (output / 'report.json').exists():
            assert time.monotonic() < deadline, 'Test window did not finish: ' + str(output)
            time.sleep(.1)
        print('Report:', output / 'report.json')
        print((output / 'report.json').read_text())
        report = json.loads((output / 'report.json').read_text())
        assert report['passed'], report
    else:
        original = termios.tcgetattr(sys.stdin) if args.terminal else None
        reports = []
        error = None
        try:
            if args.terminal:
                tty.setraw(sys.stdin)
            for scenario in ('early', 'animation', 'ready'):
                reports.append(run(scenario, args.baseline, args.terminal, args.snapshot))
            if not args.baseline:
                for report in reports:
                    assert report['first_key_on_prompt'], report
                    assert report['first_key_position_stable'], report
                    assert report['prompt_ready_ms'] < 3000, report
                    if report['scenario'] != 'early':
                        assert report['first_key_visible_ms'] < 250, report
                        assert report['first_key_in_editor_ms'] < 250, report
        except BaseException as exc:
            error = repr(exc)
            raise
        finally:
            if original is not None:
                termios.tcsetattr(sys.stdin, termios.TCSANOW, original)
            if args.report:
                args.report.write_text(json.dumps({'passed': error is None and len(reports) == 3, 'error': error,
                                                   'scenarios': reports}, indent=2) + '\n')
