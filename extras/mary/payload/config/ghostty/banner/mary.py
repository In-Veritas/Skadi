#!/usr/bin/env python3
"""MARY / ANSI Shadow: reveal rows; typing skips without consuming input."""

from pathlib import Path
import select
import shutil
import signal
import sys
import termios

# Intervalo entre linhas, em segundos (6 linhas = aproximadamente 3 segundos).
LINE_DELAY = 0.48
RESET = '\033[0m'
COMPACT = (
    r' __  __',
    r"|  \/  | __ _ _ __ _   _",
    r"| |\/| |/ _` | '__| | | |",
    r'| |  | | (_| | |  | |_| |',
    r'|_|  |_|\__,_|_|   \__, |',
    r'                   |___/',
)


def render_rows(columns):
    data = Path(__file__).with_name('mary-ansi-shadow.txt').read_text().splitlines()
    width = max(map(len, data))
    if columns < width + 2:
        text = COMPACT if columns >= 27 else ('Mary',)
        return ['\033[38;2;94;234;212m' + row + RESET for row in text]
    margin = ' ' * min(6, max(1, (columns - width) // 2))
    rows = []
    for index, row in enumerate(data):
        amount = index / max(1, len(data) - 1)
        red = round(95 + (45 - 95) * amount)
        green = round(180 + (225 - 180) * amount)
        blue = round(255 + (200 - 255) * amount)
        rows.append(f'{margin}\033[1;38;2;{red};{green};{blue}m{row}{RESET}')
    return rows


def interrupt(_signal, _frame):
    raise KeyboardInterrupt


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return
    columns, _ = shutil.get_terminal_size()
    rows = render_rows(columns)
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    immediate = termios.tcgetattr(fd)
    immediate[3] &= ~(termios.ICANON | termios.ECHO)
    immediate[6][termios.VMIN] = 1
    immediate[6][termios.VTIME] = 0
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, interrupt)
    started = False
    try:
        # TCSANOW restores settings without flushing queued keystrokes.
        termios.tcsetattr(fd, termios.TCSANOW, immediate)
        for row in rows:
            if select.select([fd], [], [], 0)[0]:
                break
            if not started:
                print()
                started = True
            print(row, flush=True)
            # Wait like sleep(), but wake up immediately when input arrives.
            # No read() call: Bash receives every byte the user typed.
            if select.select([fd], [], [], LINE_DELAY)[0]:
                break
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, original)
        if started:
            print(RESET + '\n', end='', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, termios.error):
        # An unavailable terminal or banner must never block the shell.
        sys.exit(0)
