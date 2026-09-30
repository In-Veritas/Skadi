#!/usr/bin/env python3
"""Instala o perfil Skadi no Linux, preservando arquivos anteriores em backup."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

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
    visual = "font-family =\ncustom-shader =\nresize-overlay = never\n" + visual
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
    icon_target = data / "icons/hicolor/512x512/apps/com.mitchellh.ghostty.png"
    icon_bytes = icon.read_bytes()
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
    changes[desktop_target] = desktop.encode()
    login = next((user_dir / name for name in (".bash_profile", ".bash_login", ".profile")
                  if (user_dir / name).exists()), user_dir / ".profile")
    login_text = login.read_text() if login.exists() else ""
    if not re.search(r"(?:source|\.)\s+[^\n]*\.bashrc", login_text):
        login_text += '\n# Mary: carregar o Bash interativo também no login.\nif [ -n "$BASH_VERSION" ] && [ -r "$HOME/.bashrc" ]; then\n    . "$HOME/.bashrc"\nfi\n'
        changes[login] = login_text.encode()

    changes = {p: content for p, content in changes.items()
               if not p.exists() or p.read_bytes() != content}
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
        path.write_bytes(content)
    cache.mkdir(parents=True, exist_ok=True)
    subprocess.run(["bash", "-n", str(bashrc)], check=True)
    subprocess.run(["ghostty", "+validate-config", f"--config-file={config_file}"], check=True)
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
