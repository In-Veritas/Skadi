# Prepare o editor antes de iniciar a intro. Nenhuma tecla é lida aqui:
# o próprio TTY conserva a entrada até o Bash/ble.sh assumir a edição.
function skadi/startup/prepare {
    local rows=${LINES:-24} padding
    _skadi_startup_tty=$(stty -g) || return
    stty -echo || return
    _skadi_intro_pending=1
    # O título fica oculto durante a preparação; o mar ainda não começou.
    printf '\e]4;250;#12ffff\e\\\e]4;251;#110000\e\\\e]4;249;#130000\e\\'
    local offset=$(((rows * 36 + 50) / 100))
    ((offset > rows - 2)) && offset=$((rows - 2))
    ((offset < 1)) && offset=1
    printf -v padding '%*s' "$offset" ''
    printf '%s' "${padding// /$'\r\n'}"
    # Recupera o eco se a configuração for interrompida ou ble.sh não carregar.
    # Preserva tanto PROMPT_COMMAND escalar quanto o formato de array do Bash.
    PROMPT_COMMAND+=(skadi/startup/first-prompt)
}

function skadi/startup/first-prompt {
    [[ ${_skadi_startup_tty-} ]] || return 0
    if [[ ! ${_ble_attached-} && ! ${_ble_base_attach_from_prompt-} ]]; then
        stty "$_skadi_startup_tty"
        skadi/startup/ready
    fi
    unset _skadi_startup_tty
    return 0
}

function skadi/startup/ready {
    [[ ${_skadi_intro_pending-} ]] || return 0
    unset _skadi_intro_pending
    if declare -F blehook >/dev/null; then
        blehook PREEXEC-=skadi/startup/ready
    fi
    # Uma tecla recebida durante a preparação dispensa o título sem fazê-lo
    # reaparecer. O worker só controla a paleta, nunca o texto ou o cursor.
    if [[ ! ${_skadi_intro_dismissed-} ]]; then
        printf '\e]4;250;#120000\e\\'
    fi
    local banner="${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/banner/mary.py"
    (python3 "$banner" --animate </dev/null >/dev/tty 2>/dev/null &)
    return 0
}
