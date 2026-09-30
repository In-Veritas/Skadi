#!/usr/bin/env python3
"""Título no alto, prompt liberado e revelação do mar em segundo plano."""

import os
import select
import signal
import subprocess
import sys
import termios
import time
import shutil

DURATION = 13.6
REVEAL_END = 9.6
FADE_DURATION = 0.8
PROMPT_AT = 5.4
FPS = 60
RESET = '\033]104;250;251\033\\'


def frame(progress):
    step = round(max(0.0, min(1.0, progress)) * 65535)
    return f'\033]4;251;#11{step:04x}\033\\'


def fade_frame(progress):
    step = round(max(0.0, min(1.0, progress)) * 65535)
    return f'\033]4;250;#12{step:04x}\033\\'


def emit(text):
    os.write(sys.stdout.fileno(), text.encode())


def continue_intro(start):
    # Só a revelação tem prazo. O título permanece até o primeiro texto digitado.
    # Nenhum subprocesso lê stdin ou escreve texto/cursor sobre o prompt.
    while True:
        elapsed = time.monotonic() - start
        emit(frame(min(elapsed, REVEAL_END) / DURATION))
        if elapsed >= REVEAL_END:
            break
        deadline = start + (int(elapsed * FPS) + 1) / FPS
        time.sleep(max(0.0, deadline - time.monotonic()))


def dismiss_title():
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        emit(fade_frame(elapsed / FADE_DURATION))
        if elapsed >= FADE_DURATION:
            break
        deadline = start + (int(elapsed * FPS) + 1) / FPS
        time.sleep(max(0.0, deadline - time.monotonic()))


def interrupt(_signal, _frame):
    raise KeyboardInterrupt


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return
    fd = sys.stdin.fileno()
    original = termios.tcgetattr(fd)
    immediate = termios.tcgetattr(fd)
    immediate[3] &= ~(termios.ICANON | termios.ECHO)
    immediate[6][termios.VMIN] = 1
    immediate[6][termios.VTIME] = 0
    previous_signals = {}
    for signum in (signal.SIGTERM, signal.SIGHUP):
        previous_signals[signum] = signal.signal(signum, interrupt)
    handed_off = False
    try:
        termios.tcsetattr(fd, termios.TCSANOW, immediate)
        emit('\033[?25l' + fade_frame(0) + frame(0))
        start = time.monotonic()
        while True:
            elapsed = time.monotonic() - start
            emit(frame(elapsed / DURATION))
            if elapsed >= PROMPT_AT:
                break
            deadline = start + (int(elapsed * FPS) + 1) / FPS
            if select.select([fd], [], [], max(0.0, deadline - time.monotonic()))[0]:
                # Digitação antecipada adianta o prompt, sem consumir bytes.
                start = time.monotonic() - PROMPT_AT
                break
        # O prompt fica abaixo do título parado no alto.
        lines = shutil.get_terminal_size().lines
        emit('\r\n' * max(1, min(lines - 2, round(lines * .36))))
        subprocess.Popen([sys.executable, __file__, '--continue', str(start)],
                         stdin=subprocess.DEVNULL, stdout=sys.stdout,
                         stderr=subprocess.DEVNULL, start_new_session=True,
                         close_fds=True)
        handed_off = True
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, original)
        for signum, handler in previous_signals.items():
            signal.signal(signum, handler)
        if not handed_off:
            emit(RESET)
        emit('\033[?25h')


if __name__ == '__main__':
    try:
        if len(sys.argv) == 3 and sys.argv[1] == '--continue':
            continue_intro(float(sys.argv[2]))
        elif len(sys.argv) == 2 and sys.argv[1] == '--dismiss':
            dismiss_title()
        else:
            main()
    except (OSError, ValueError, termios.error):
        sys.exit(0)
