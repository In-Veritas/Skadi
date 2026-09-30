"""Exercise the real Bash prompt's static shader markers and editing fallbacks."""
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = r'''
function emit { printf '%s\0%s\0' "$1" "$2"; }
function ble/util/idle.push { emit TIMER push; }
function ble/util/idle.cancel { emit CANCEL "$1"; }
function ble/util/idle.sleep { emit TIMER sleep; }
function ble/prompt/unit/add-hash { emit HASH "$1"; }
function ble/prompt/process-prompt-string { emit STYLE "$1"; }
function bleopt { emit OPTION "$1"; }
function ble/prompt/print { emit CHAR "$1"; }
BLE_VERSION=test HOSTNAME=host HOME=/home/test
USER=$4 PWD=$2 COLUMNS=$3
source "$1"
emit BEGIN idle
ble/prompt/backslash:mary/identity
_ble_edit_str='typing a long command'
emit BEGIN typing
ble/prompt/backslash:mary/identity
'''
COLORS = re.compile(r"38;2;(\d+);(\d+);(\d+)m")


def render(directory, columns=120, user="alice"):
    result = subprocess.run(
        ["bash", "-c", SCRIPT, "check", str(ROOT / "overrides/mary-shell/mary-prompt.sh"),
         directory, str(columns), user],
        check=True, capture_output=True, env={**os.environ, "LC_ALL": "C.UTF-8"},
    )
    fields = result.stdout.decode().split("\0")
    assert fields.pop() == ""
    assert len(fields) % 2 == 0
    events = list(zip(fields[::2], fields[1::2]))
    assert not any(kind == "TIMER" for kind, _ in events), events
    assert ("CANCEL", "mary/prompt-tick") in events
    begin = [index for index, event in enumerate(events) if event[0] == "BEGIN"]
    assert len(begin) == 2
    idle, typing = events[begin[0] + 1:begin[1]], events[begin[1] + 1:]
    assert idle == typing, "Typing must not change or stop the shader animation"
    assert [value for kind, value in idle if kind == "HASH"] == ["$COLUMNS", "$PWD"]
    color = None
    cells = []
    for kind, value in idle:
        if kind == "STYLE":
            matches = COLORS.findall(value)
            if matches:
                color = tuple(map(int, matches[-1]))
        elif kind == "CHAR":
            assert len(value) == 1, (directory, value)
            cells.append((value, color))
    return cells


def marker_rank(color, kind):
    red, green, blue = color
    assert green == 255 and blue == kind * 32, color
    assert 32 <= red <= 224 and (red - 32) % 4 == 0, color
    return (red - 32) // 4


def check(directory, expected, user="alice"):
    cells = render(directory, user=user)
    identity = f"{user}@host "
    assert "".join(char for char, _ in cells) == identity + expected
    username = cells[:len(user)]
    separator = cells[len(user)]
    host = cells[len(user) + 1:len(identity)]
    path = cells[len(identity):]
    assert separator == ("@", (32, 255, 96)), separator
    host_ranks = [marker_rank(color, 1) for _, color in host]
    path_ranks = [marker_rank(color, 2) for _, color in path]
    combined = host_ranks + path_ranks
    assert combined == sorted(combined) and combined[0] == 0 and combined[-1] == 48
    assert host_ranks[-1] < path_ranks[0], (host_ranks, path_ranks)
    for part, kind in ((username, 0),):
        ranks = [marker_rank(color, kind) for _, color in part]
        assert ranks == sorted(ranks) and ranks[0] == 0, ranks
        if len(ranks) > 1:
            assert ranks[-1] == 48, ranks
    narrow = render(directory, columns=8, user=user)
    assert "".join(char for char, _ in narrow) == identity + expected
    assert all(color[1] != 255 for _, color in narrow), narrow
    assert narrow[len(user)] == ("@", (77, 126, 154))
    assert all(color == (94, 234, 212) for _, color in narrow[:len(user)])
    assert all(color == (103, 185, 255) for _, color in narrow[len(user) + 1:len(identity)])
    assert all(color == (140, 213, 231) for _, color in narrow[len(identity):])


check("/tmp/ocean", "ocean")
check("/tmp/maré azul", "maré azul", user="álïce")
check("/home/test", "~")
check("/", "/")
check("/tmp/a", "a", user="a")
# Prompt text must remain literal: paths must not be interpreted as shell code
# or as ble.sh prompt escapes when printed character by character.
check("/tmp/$(echo unsafe)\\q{test}", "$(echo unsafe)\\q{test}")
print("OK: marcadores estáticos, sem timer, usuário/@/host/caminho, digitação contínua, "
      "Unicode, home/root e fallback estreito.")
