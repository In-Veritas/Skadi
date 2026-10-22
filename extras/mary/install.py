#!/usr/bin/env python3
"""Instala o perfil Skadi no Linux, preservando arquivos anteriores em backup."""

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from window_icons import plan_window_icons

ROOT = Path(__file__).resolve().parent


def block(text, name, body):
    start, end = f"# >>> Mary: {name}", f"# <<< Mary: {name}"
    text = re.sub(re.escape(start) + r"\n.*?" + re.escape(end) + r"\n?",
                  "", text, flags=re.S)
    return text, f"{start}\n{body}\n{end}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-dir", type=Path, default=Path.home(),
                        help="diretório do usuário (alternativo para teste isolado)")
    parser.add_argument("--app-build", type=Path, help="prefixo compilado (zig-out) para instalar o executável Skadi")
    args = parser.parse_args()
    user_dir = args.user_dir.resolve()
    isolated = user_dir != Path.home()
    config = (user_dir / ".config" if isolated else
              Path(os.environ.get("XDG_CONFIG_HOME", user_dir / ".config")))
    data = (user_dir / ".local/share" if isolated else
            Path(os.environ.get("XDG_DATA_HOME", user_dir / ".local/share")))
    cache = (user_dir / ".cache" if isolated else
             Path(os.environ.get("XDG_CACHE_HOME", user_dir / ".cache")))
    if sys.platform != "linux" or not all(p.is_absolute() for p in (config, data, cache)):
        sys.exit("Este instalador requer Linux e diretórios XDG absolutos.")
    subprocess.run([sys.executable, str(ROOT / "verificar-pacote.py")], check=True)
    ghostty_dir = config / "ghostty"
    bashrc = user_dir / ".bashrc"
    original = bashrc.read_text() if bashrc.exists() else ""
    cleaned, end = block(original, "final", '''if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/end.bash" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/end.bash"
fi''')
    cleaned, start = block(cleaned, "início", '''if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/start.bash" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/start.bash"
fi''')
    # O guard padrão do Ubuntu; outros layouts recebem o módulo no começo.
    # O próprio módulo verifica Bash interativo + Ghostty + TTY antes de agir.
    guard = re.search(r"case \$- in\n.*?\nesac\n", cleaned, re.S)
    offset = guard.end() if guard else 0
    updated = cleaned[:offset] + start + cleaned[offset:]
    updated = updated.rstrip() + "\n\n" + end
    subprocess.run(["bash", "-n"], input=updated, text=True, check=True)
    if re.search(r"(?:source|\.)\s+[^\n]*(?:ble\.sh|blesh)", cleaned):
        sys.exit("Integração ble.sh existente: revise a ordem antes de instalar.")

    changes = {}
    executable_paths = set()
    runtime = data / "skadi/runtime"
    runtime_binary = runtime / "bin/ghostty"
    if args.app_build:
        build = args.app_build.resolve()
        binary = build / "bin/ghostty"
        if not binary.is_file() or not (build / "share/ghostty").is_dir():
            sys.exit("--app-build deve apontar para um prefixo compilado com bin/ghostty e share/ghostty.")
        subprocess.run([str(binary), "+validate-config"], check=True)
        changes[runtime_binary] = binary.read_bytes()
        for directory in ("ghostty", "locale", "terminfo"):
            for source in sorted((build / "share" / directory).rglob("*")):
                if source.is_file():
                    changes[runtime / "share" / source.relative_to(build / "share")] = source.read_bytes()
        executable_paths.add(runtime_binary)
    native = args.app_build is not None or runtime_binary.exists()
    def native_exec(text):
        # Desktop Entry escaping; retain the command's existing arguments.
        quoted = str(runtime_binary).replace("\\", "\\\\").replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')
        return re.sub(r'^Exec=(?:"[^"]*"|\S+)', lambda _: f'Exec="{quoted}"', text, flags=re.M)
    if native:
        service_id = "com.mitchellh.ghostty.service"
        bus_source = Path("/usr/share/dbus-1/services") / service_id
        bus = bus_source.read_text() if bus_source.exists() else (
            "[D-BUS Service]\nName=com.mitchellh.ghostty\nExec=ghostty --gtk-single-instance=true --initial-window=false\n")
        # A distro systemd unit would otherwise launch the old system binary.
        bus = re.sub(r"^SystemdService=.*\n?", "", bus, flags=re.M)
        changes[data / "dbus-1/services" / service_id] = native_exec(bus).encode()

    for source in (ROOT / "payload/config/ghostty").rglob("*"):
        if source.is_file() and source.name != "config.ghostty":
            changes[ghostty_dir / source.relative_to(ROOT / "payload/config/ghostty")] = source.read_bytes()
    for source in (ROOT / "payload/config/blesh").glob("*"):
        changes[ghostty_dir / "mary-shell" / source.name] = source.read_bytes()
    for source, target in (("00-mary-start.bash", "start.bash"), ("90-mary-end.bash", "end.bash")):
        changes[ghostty_dir / "mary-shell" / target] = (ROOT / "integracao" / source).read_bytes()
    # Ajustes do fork ficam separados do pacote original e de seus checksums.
    for source in (ROOT / "overrides").rglob("*"):
        if source.is_file():
            changes[ghostty_dir / source.relative_to(ROOT / "overrides")] = source.read_bytes()
    for directory, target in (("blesh", data / "mary/blesh"),
                              ("fonts", data / "fonts")):
        for source in (ROOT / "payload/share" / directory).rglob("*"):
            if source.is_file():
                changes[target / source.relative_to(ROOT / "payload/share" / directory)] = source.read_bytes()

    visual = (ROOT / "payload/config/ghostty/config.ghostty").read_text()
    visual = visual.replace("title = Mary", "title = Skadi")
    visual = visual.replace("theme = Catppuccin Mocha", f"theme = {ghostty_dir}/themes/Catppuccin Mocha")
    visual = visual.replace("background-image = backgrounds/", f"background-image = {ghostty_dir}/backgrounds/")
    visual = visual.replace("custom-shader = shaders/", f"custom-shader = {ghostty_dir}/shaders/")
    visual = visual.replace("aurora-trail.glsl", "ocean-dots.glsl")
    # Fundo uniforme permite compor o pequeno salto sobre o mar procedural.
    visual = visual.replace("background-image-opacity = 0.18", "background-image-opacity = 0")
    # Listas cumulativas precisam de reset para substituir efeitos/fontes anteriores.
    visual = ("font-family =\ncustom-shader =\nresize-overlay = never\n"
              "working-directory = home\nwindow-inherit-working-directory = false\n") + visual
    changes[ghostty_dir / "mary.ghostty"] = visual.encode()
    config_file = ghostty_dir / "config.ghostty"
    # Ghostty prefere config.ghostty quando os dois nomes existem.
    if not config_file.exists() and (ghostty_dir / "config").exists():
        config_file = ghostty_dir / "config"
    current = config_file.read_text() if config_file.exists() else ""
    current, include = block(current, "aparência", f"config-file = {ghostty_dir}/mary.ghostty")
    changes[config_file] = (current.rstrip() + "\n\n" + include).lstrip("\n").encode()
    changes[bashrc] = updated.encode()
    # Mantém a identidade do aplicativo para que janelas e atalhos fixados
    # usem o mesmo ícone. O PNG escolhido é copiado sem modificar a arte.
    icon = ROOT / "design/skadi-icons/caudas-v2/anel/06-gravura.png"
    icon_bytes = icon.read_bytes()
    # O lançador pode manter imagens em memória pelo caminho, mesmo após
    # reconstruir o índice. Um nome por conteúdo invalida também esse cache.
    icon_name = "skadi-" + hashlib.sha256(icon_bytes).hexdigest()[:16] + ".png"
    icon_target = data / "icons/hicolor/512x512/apps" / icon_name
    changes[icon_target] = icon_bytes
    # A busca do tema prefere o tamanho exato do sistema a um ícone local
    # de 512 px. Cubra também os tamanhos pequenos e as variantes HiDPI.
    # GTK/KDE fazem a redução do PNG original, sem alterar a ilustração.
    for size in (16, 24, 32, 48, 64, 128, 256, 512, 1024):
        for scale in ("", "@2"):
            directory = f"{size}x{size}{scale}/apps"
            changes[data / "icons/hicolor" / directory / "com.mitchellh.ghostty.png"] = icon_bytes
    desktop_id = "com.mitchellh.ghostty.desktop"
    desktop_target = data / "applications" / desktop_id
    desktop_source = next((p for p in (
        desktop_target,
        Path("/usr/local/share/applications") / desktop_id,
        Path("/usr/share/applications") / desktop_id,
    ) if p.exists()), None)
    if desktop_source:
        desktop = desktop_source.read_text()
    else:
        desktop = (ROOT.parents[1] / "dist/linux/app.desktop.in").read_text()
        desktop = desktop.replace("@NAME@", "Skadi").replace("@APPID@", "com.mitchellh.ghostty")
        desktop = desktop.replace("@GHOSTTY@", "ghostty")
    desktop = re.sub(r"^Name=.*$", "Name=Skadi", desktop, count=1, flags=re.M)
    desktop = re.sub(r"^Icon=.*$", lambda _: f"Icon={icon_target}", desktop, count=1, flags=re.M)
    if native:
        desktop = native_exec(desktop)
        desktop = re.sub(r"^TryExec=.*$", lambda _: f"TryExec={runtime_binary}", desktop, flags=re.M)
    # Desktop/taskbar launches must not inherit the last active terminal's
    # directory. Send an explicit absolute home directory over the same IPC
    # used by Dolphin. Disable desktop D-Bus activation: it skips Exec and
    # would lose this per-launch working-directory override.
    home_arg = str(user_dir).replace("\\", "\\\\").replace('"', '\\"')
    home_arg = home_arg.replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    launcher_exec = f'Exec=ghostty +new-window "--working-directory={home_arg}"'
    if native:
        launcher_exec = native_exec(launcher_exec)
    desktop = re.sub(r"^Exec=.*$", lambda _: launcher_exec, desktop, flags=re.M)
    if re.search(r"^DBusActivatable=", desktop, flags=re.M):
        desktop = re.sub(r"^DBusActivatable=.*$", "DBusActivatable=false", desktop, flags=re.M)
    else:
        desktop = desktop.replace("[Desktop Entry]\n", "[Desktop Entry]\nDBusActivatable=false\n", 1)
    changes[desktop_target] = desktop.encode()
    changes.update(plan_window_icons(data, launcher_exec))
    # KTerminalLauncherJob supplies the folder as the process working directory.
    # +new-window forwards it over D-Bus to an already running Skadi instance.
    terminal_desktop_id = "com.mitchellh.ghostty.terminal.desktop"
    terminal_exec = "Exec=ghostty +new-window"
    if native:
        terminal_exec = native_exec(terminal_exec)
    changes[data / "applications" / terminal_desktop_id] = (
        "[Desktop Entry]\nType=Application\nName=Skadi\nNoDisplay=true\n"
        f"{terminal_exec}\nIcon={icon_target}\n"
        "Terminal=false\nStartupNotify=true\n"
        "StartupWMClass=com.mitchellh.ghostty\nCategories=System;TerminalEmulator;\n"
    ).encode()
    # Hide the generic Ghostty service menu shipped by system packages. The
    # native Dolphin terminal action will use Skadi and keeps its real shortcut.
    service_mask = data / "kio/servicemenus" / desktop_id
    changes[service_mask] = b"[Desktop Entry]\nHidden=true\n"
    executable_paths.add(service_mask)
    dolphinrc = user_dir / ".config/dolphinrc"
    dolphin_config = dolphinrc.read_text() if dolphinrc.exists() else ""
    context_menu = re.search(r"(?ms)^\[ContextMenu\]\n.*?(?=^\[|\Z)", dolphin_config)
    if context_menu:
        context_block = context_menu.group(0)
        if re.search(r"(?m)^ShowOpenTerminal=", context_block):
            context_block = re.sub(r"(?m)^ShowOpenTerminal=.*$", "ShowOpenTerminal=true", context_block)
        else:
            context_block += "ShowOpenTerminal=true\n"
        dolphin_config = dolphin_config[:context_menu.start()] + context_block + dolphin_config[context_menu.end():]
    else:
        dolphin_config += "\n[ContextMenu]\nShowOpenTerminal=true\n"
    changes[dolphinrc] = dolphin_config.encode()
    dolphin_ui = user_dir / ".local/share/kxmlgui5/dolphin/dolphinui.rc"
    if dolphin_ui.exists():
        ui_root = ET.fromstring(dolphin_ui.read_text())
    else:
        namespace = "https://www.kde.org/standards/kxmlgui/1.0"
        ET.register_namespace("", namespace)
        ui_root = ET.Element(f"{{{namespace}}}gui", {"name": "dolphin", "version": "1"})
    ui_namespace = ui_root.tag.split("}")[0] + "}" if "}" in ui_root.tag else ""
    if ui_namespace:
        ET.register_namespace("", ui_namespace[1:-1])
    properties = next((element for element in ui_root
                       if element.tag.split("}")[-1] == "ActionProperties"
                       and element.get("scheme", "Default") == "Default"), None)
    if properties is None:
        properties = ET.SubElement(ui_root, f"{ui_namespace}ActionProperties", {"scheme": "Default"})
    properties.set("scheme", "Default")
    action = next((element for element in properties if element.tag.split("}")[-1] == "Action"
                   and element.get("name") == "open_terminal_here"), None)
    if action is None:
        action = ET.SubElement(properties, f"{ui_namespace}Action", {"name": "open_terminal_here"})
    action.set("text", "Open in Skadi")
    action.set("shortcut", "Alt+Shift+F4")
    changes[dolphin_ui] = ET.tostring(ui_root, encoding="utf-8", xml_declaration=True)
    kdeglobals = user_dir / ".config/kdeglobals"
    kde_config = kdeglobals.read_text() if kdeglobals.exists() else ""
    terminal_application = terminal_exec.removeprefix("Exec=")
    general = re.search(r"(?ms)^\[General\]\n.*?(?=^\[|\Z)", kde_config)
    if general:
        general_block = general.group(0)
        for key, value in (("TerminalApplication", terminal_application),
                           ("TerminalService", terminal_desktop_id)):
            if re.search(rf"(?m)^{key}=", general_block):
                general_block = re.sub(rf"(?m)^{key}=.*$", f"{key}={value}", general_block)
            else:
                general_block += f"{key}={value}\n"
        kde_config = kde_config[:general.start()] + general_block + kde_config[general.end():]
    else:
        kde_config += (f"\n[General]\nTerminalApplication={terminal_application}\n"
                       f"TerminalService={terminal_desktop_id}\n")
    changes[kdeglobals] = kde_config.encode()
    login = next((user_dir / name for name in (".bash_profile", ".bash_login", ".profile")
                  if (user_dir / name).exists()), user_dir / ".profile")
    login_text = login.read_text() if login.exists() else ""
    if not re.search(r"(?:source|\.)\s+[^\n]*\.bashrc", login_text):
        login_text += '\n# Mary: carregar o Bash interativo também no login.\nif [ -n "$BASH_VERSION" ] && [ -r "$HOME/.bashrc" ]; then\n    . "$HOME/.bashrc"\nfi\n'
        changes[login] = login_text.encode()

    changes = {p: content for p, content in changes.items()
               if not p.exists() or p.read_bytes() != content
               or (p in executable_paths and not p.stat().st_mode & 0o100)}
    if not changes:
        print("Skadi já instalado; nenhum arquivo alterado.")
        return
    backup = data / "mary/backups" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
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
        if path == runtime_binary:
            # Updating a running executable requires replacing its inode.
            temporary = path.with_name(path.name + ".skadi-new")
            temporary.write_bytes(content)
            temporary.chmod(0o755)
            temporary.replace(path)
        else:
            path.write_bytes(content)
        if path in executable_paths:
            path.chmod(path.stat().st_mode | 0o100)
    cache.mkdir(parents=True, exist_ok=True)
    subprocess.run(["bash", "-n", str(bashrc)], check=True)
    subprocess.run([str(runtime_binary) if native else "ghostty", "+validate-config", f"--config-file={config_file}"], check=True)
    if not isolated and shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(data / "fonts/mary-adwaita-mono")], check=True)
    if not isolated:
        for command in (["update-desktop-database", str(data / "applications")],
                        ["gtk-update-icon-cache", "-f", "-t", str(data / "icons/hicolor")],
                        ["kbuildsycoca6", "--noincremental"]):
            if shutil.which(command[0]):
                subprocess.run(command, check=False)
    print(f"Skadi instalado. Backup e lista de arquivos: {backup}")


if __name__ == "__main__":
    main()
