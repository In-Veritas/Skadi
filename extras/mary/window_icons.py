#!/usr/bin/env python3
"""Install the selected Skadi window icons and, optionally, a compiled runtime."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
COLLECTION = ROOT / "design/skadi-icons/2026-10-18-caudas-100"
WINDOW_ID = "com.mitchellh.ghostty.window"


def plan_window_icons(data, launcher_exec):
    """Return installable files; leave the original launcher/icon untouched."""
    selection = json.loads((COLLECTION / "selection.json").read_text())
    if selection.get("collection") != "skadi-caudas-100-2026-10-18":
        raise ValueError("Unrecognized icon collection")
    ids = selection["selected_ids"]
    if not 1 <= len(ids) <= 100 or len(set(ids)) != len(ids):
        raise ValueError("Select between one and 100 unique icons")
    if any(type(i) is not int or not 1 <= i <= 100 for i in ids):
        raise ValueError("Invalid icon ID")
    expected = [f"icons/skadi-{i:03d}.png" for i in ids]
    if selection["selected_files"] != expected:
        raise ValueError("Icon IDs and paths disagree")
    if not launcher_exec.startswith("Exec=") or "\n" in launcher_exec:
        raise ValueError("Expected one desktop Exec line")
    changes, names = {}, []
    for i, filename in zip(ids, expected):
        content = (COLLECTION / filename).read_bytes()
        name = f"skadi-fluke-{i:03d}-{hashlib.sha256(content).hexdigest()[:16]}"
        # Unique names have no competing small icons in system themes, so one
        # master per name suffices. GTK scales it for each display and panel.
        changes[data / "icons/hicolor/512x512/apps" / (name + ".png")] = content
        names.append(name)
    directory = data / "skadi/window-icons"
    changes[directory / "icons.txt"] = ("\n".join(names) + "\n").encode()
    changes[directory / "selection.json"] = (json.dumps(selection, indent=2) + "\n").encode()
    # Plasma prefers a desktop entry's icon over per-window textures. An
    # iconless entry makes it fall back to each GTK window's own themed icon.
    changes[data / "applications" / (WINDOW_ID + ".desktop")] = (
        "[Desktop Entry]\nType=Application\nName=Skadi\nNoDisplay=true\n"
        "Terminal=false\nDBusActivatable=false\n"
        f"StartupWMClass={WINDOW_ID}\n{launcher_exec}\n"
    ).encode()
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-dir", type=Path, default=Path.home())
    parser.add_argument("--app-build", type=Path)
    args = parser.parse_args()
    user_dir = args.user_dir.resolve()
    isolated = user_dir != Path.home()
    data = user_dir / ".local/share" if isolated else Path(os.environ.get("XDG_DATA_HOME", user_dir / ".local/share"))
    if not data.is_absolute():
        parser.error("XDG_DATA_HOME must be absolute")
    runtime = data / "skadi/runtime"
    binary = runtime / "bin/ghostty"
    desktop = data / "applications/com.mitchellh.ghostty.desktop"
    if desktop.exists():
        match = re.search(r"^Exec=.*$", desktop.read_text(), re.M)
        if not match:
            parser.error("The Skadi launcher is missing its Exec line")
        launcher_exec = match.group()
    elif isolated:
        launcher_exec = "Exec=ghostty +new-window"
    else:
        parser.error("Install the Skadi profile before installing window icons")
    changes = plan_window_icons(data, launcher_exec)
    if args.app_build:
        build = args.app_build.resolve()
        built_binary = build / "bin/ghostty"
        if not built_binary.is_file() or not (build / "share/ghostty").is_dir():
            parser.error("--app-build requires bin/ghostty and share/ghostty")
        subprocess.run([str(built_binary), "+validate-config"], check=True)
        changes[binary] = built_binary.read_bytes()
        for directory in ("ghostty", "locale", "terminfo"):
            for source in sorted((build / "share" / directory).rglob("*")):
                if source.is_file():
                    changes[runtime / "share" / source.relative_to(build / "share")] = source.read_bytes()
    changes = {p: content for p, content in changes.items() if not p.exists() or p.read_bytes() != content}
    if not changes:
        print("Ícones por janela já instalados; nenhum arquivo alterado.")
        return
    backup = data / "mary/backups" / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-window-icons")
    backup.mkdir(parents=True)
    manifest = []
    for index, path in enumerate(changes):
        entry = {"path": str(path), "backup": str(index) if path.exists() else None}
        if path.exists():
            shutil.copy2(path, backup / str(index))
        manifest.append(entry)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Backup e lista de arquivos: {backup}", flush=True)
    for path, content in changes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".skadi-new")
        temporary.write_bytes(content)
        if path == binary:
            temporary.chmod(0o755)
        temporary.replace(path)
    if not isolated:
        for command in (["gtk-update-icon-cache", "-f", "-t", str(data / "icons/hicolor")], ["kbuildsycoca6"]):
            if shutil.which(command[0]):
                subprocess.run(command, check=True)
    print("Seleção de caudas instalada. As janelas existentes mantêm sua sessão.")


if __name__ == "__main__":
    main()
