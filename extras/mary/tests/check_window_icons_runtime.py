#!/usr/bin/env python3
"""Validate the compiled Skadi window-icon lifecycle in the real KDE panel.

Requires the selected assets to be installed. Opens a separate test instance,
captures two screenshots, then terminates it and removes its temporary launcher.
Existing Skadi processes and panel configuration are never changed.
"""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from window_icons import ROOT, plan_window_icons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve()
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    output = Path(tempfile.mkdtemp(prefix="skadi-native-icons-"))
    identity = "org.skadi.WindowIconTest.p" + str(os.getpid())
    launcher = data / 'applications/com.mitchellh.ghostty.desktop'
    launcher_exec = next(line for line in launcher.read_text().splitlines() if line.startswith('Exec='))
    installed = plan_window_icons(data, launcher_exec)
    if any(not path.is_file() or path.read_bytes() != content for path, content in installed.items()):
        raise RuntimeError('Install the selected icon catalogue before running this test')
    changes = {data / "applications" / (identity + ".desktop"): (
        "[Desktop Entry]\nType=Application\nName=Skadi icon test\nNoDisplay=true\n"
        f"StartupWMClass={identity}\nExec=/usr/bin/true\n"
        f"Icon={ROOT}/design/skadi-icons/caudas-v2/anel/06-gravura.png\n"
    ).encode()}
    previous = {path: path.read_bytes() if path.exists() else None for path in changes}
    process = None
    report = {"output": str(output), "application_id": identity}
    # A cancelled tool call must still remove the temporary test launcher.
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)

    def refresh():
        subprocess.run(["kbuildsycoca6"], check=True, capture_output=True)

    def capture(name):
        subprocess.run(["spectacle", "--background", "--nonotify", "--output", str(output / name)], check=True, timeout=15)

    def window(label, duration):
        subprocess.run([
            str(binary), "+new-window", "--class=" + identity,
            "--title=Skadi icon test " + label, "-e", "/bin/sleep", str(duration),
        ], check=True, capture_output=True, timeout=15)

    try:
        for path, content in changes.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        refresh()
        with (output / "runtime.log").open("w") as log:
            process = subprocess.Popen([
                str(binary), "--config-default-files=false", "--initial-window=false",
                "--quit-after-last-window-closed=false", "--gtk-single-instance=true",
                "--class=" + identity, "--window-width=40", "--window-height=10",
                "--working-directory=/tmp", "--shell-integration=none",
            ], stdout=log, stderr=log)
            object_path = "/" + identity.replace(".", "/")
            for _ in range(40):
                if process.poll() is not None:
                    raise RuntimeError("Test process exited before registering D-Bus")
                ready = subprocess.run([
                    "gdbus", "call", "--session", "--dest", identity,
                    "--object-path", object_path, "--method", "org.gtk.Actions.List",
                ], capture_output=True, timeout=3)
                if ready.returncode == 0:
                    break
                time.sleep(0.25)
            else:
                raise RuntimeError("Test process did not register D-Bus")
            window("original (closes first)", 8)
            window("selected 1", 40)
            window("selected 2", 40)
            window("selected 3", 40)
            time.sleep(3)
            capture("four-windows.png")
            time.sleep(6)
            window("selected 4 (after original closed)", 40)
            time.sleep(3)
            capture("after-original-closed.png")
            process.terminate()
            process.wait(timeout=10)
        text = (output / "runtime.log").read_text()
        actual = re.findall(r"Skadi window icon: (skadi-fluke-\d+-[a-f0-9]+)", text)
        selected = installed[data / "skadi/window-icons/icons.txt"].decode().splitlines()
        passed = len(actual) == 4 and len(set(actual)) == 4 and set(actual) <= set(selected)
        report.update({"selected": selected, "actual": actual, "passed": passed})
        if not report["passed"]:
            raise AssertionError(f"Window assignments differ: {actual!r}")
        print(json.dumps(report, indent=2), flush=True)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for path, content in previous.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(content)
        refresh()
        report["test_assets_restored"] = True
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print("Report:", output / "report.json", flush=True)


if __name__ == "__main__":
    main()
