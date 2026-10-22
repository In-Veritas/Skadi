#!/usr/bin/env python3
"""Intro visual em segundo plano, sem bloquear o shell nem tocar na entrada."""

import os
import subprocess
import sys
import time
import shutil

DURATION = 13.6
REVEAL_END = 9.6
FADE_DURATION = 0.8
FIRST_EVENT_END = 72.0
FPS = 60
RESET = '\033]104;249;250;251\033\\'


def frame(progress):
    step = round(max(0.0, min(1.0, progress)) * 65535)
    return f'\033]4;251;#11{step:04x}\033\\'


def fade_frame(progress):
    step = round(max(0.0, min(1.0, progress)) * 65535)
    return f'\033]4;250;#12{step:04x}\033\\'


def whale_frame(elapsed):
    step = round(max(0.0, min(1.0, elapsed / FIRST_EVENT_END)) * 65535)
    return f'\033]4;249;#13{step:04x}\033\\'


def emit(text):
    os.write(sys.stdout.fileno(), text.encode())


def continue_intro(start):
    # A primeira baleia tem relógio próprio, inclusive após dispensar o título.
    # O título permanece até o primeiro texto digitado.
    # Nenhum subprocesso lê stdin ou escreve texto/cursor sobre o prompt.
    revealed = False
    while True:
        elapsed = time.monotonic() - start
        if not revealed:
            emit(frame(min(elapsed, REVEAL_END) / DURATION))
            revealed = elapsed >= REVEAL_END
        emit(whale_frame(elapsed))
        if elapsed >= FIRST_EVENT_END:
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


def main():
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return
    start = time.monotonic()
    # Prepare o espaço antes de o Bash desenhar o prompt. Depois deste ponto,
    # somente o editor controla texto, cursor e termios. A animação nunca
    # espera uma tecla: ble.sh e o restante do .bashrc já podem inicializar.
    lines = shutil.get_terminal_size().lines
    emit(fade_frame(0) + frame(0) + whale_frame(0)
         + '\r\n' * max(1, min(lines - 2, round(lines * .36))))
    subprocess.Popen([sys.executable, __file__, '--continue', str(start)],
                     stdin=subprocess.DEVNULL, stdout=sys.stdout,
                     stderr=subprocess.DEVNULL, start_new_session=True,
                     close_fds=True)


if __name__ == '__main__':
    try:
        if len(sys.argv) == 3 and sys.argv[1] == '--continue':
            continue_intro(float(sys.argv[2]))
        elif len(sys.argv) == 2 and sys.argv[1] == '--animate':
            continue_intro(time.monotonic())
        elif len(sys.argv) == 2 and sys.argv[1] == '--dismiss':
            dismiss_title()
        else:
            main()
    except (OSError, ValueError):
        sys.exit(0)
