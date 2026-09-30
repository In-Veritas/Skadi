# Skadi: a única onda é calculada continuamente pelo shader, sem redesenhar PS1.
# RGB reservado codifica posição dentro do trecho e identidade, nunca altura.
_mary_prompt_static='\[\e[38;2;77;126;154m\][\[\e[1;38;2;94;234;212m\]\u\[\e[0;38;2;77;126;154m\]@\[\e[1;38;2;103;185;255m\]\h\[\e[0m\] \[\e[38;2;140;213;231m\]\W\[\e[38;2;77;126;154m\]]\[\e[1;38;2;94;234;212m\]\$\[\e[0m\] '
PS1=$_mary_prompt_static

if [[ ${BLE_VERSION-} ]] && declare -F ble/prompt/print >/dev/null; then
    _mary_prompt_user=${USER:-${LOGNAME:-user}}
    _mary_prompt_identity="${_mary_prompt_user}@${HOSTNAME%%.*}"
    _mary_prompt_user_length=${#_mary_prompt_user}

    function ble/prompt/backslash:mary/identity {
        ble/prompt/unit/add-hash '$COLUMNS'
        ble/prompt/unit/add-hash '$PWD'
        local index char rank marker_blue animate=0 position length
        local directory=${PWD##*/}
        [[ $PWD == / ]] && directory=/
        [[ $PWD == "$HOME" ]] && directory='~'
        local content="$_mary_prompt_identity $directory"
        local count=${#content} path_start=$((${#_mary_prompt_identity} + 1))
        local host_start=$((_mary_prompt_user_length + 1))
        ((COLUMNS > count + 12)) && animate=1

        ble/prompt/process-prompt-string '\[\e[0m\]\[\e[38;2;77;126;154m\]['
        for ((index=0; index<count; index++)); do
            char=${content:index:1}
            marker_blue=-1
            position=0 length=1
            if ((index < _mary_prompt_user_length)); then
                ble/prompt/process-prompt-string '\[\e[1;38;2;94;234;212m\]'
                marker_blue=0 position=$index length=$_mary_prompt_user_length
            elif ((index == _mary_prompt_user_length)); then
                ble/prompt/process-prompt-string '\[\e[0;38;2;77;126;154m\]'
                marker_blue=96
            elif ((index >= path_start)); then
                ble/prompt/process-prompt-string '\[\e[0;38;2;140;213;231m\]'
                marker_blue=64 position=$((index - host_start)) length=$((count - host_start))
            else
                ble/prompt/process-prompt-string '\[\e[1;38;2;103;185;255m\]'
                marker_blue=32 position=$((index - host_start)) length=$((count - host_start))
            fi
            if ((animate && marker_blue >= 0)); then
                rank=0
                ((length > 1)) && rank=$(((position * 48 + (length - 1) / 2) / (length - 1)))
                ble/prompt/process-prompt-string "\[\e[0;38;2;$((32 + rank * 4));255;${marker_blue}m\]"
            fi
            ble/prompt/print "$char"
        done
        ble/prompt/process-prompt-string '\[\e[0m\]\[\e[38;2;77;126;154m\]]\[\e[1;38;2;94;234;212m\]\$\[\e[0m\] '
    }

    # O histórico recebe um prompt normal, completo e colorido.
    bleopt prompt_ps1_final="$_mary_prompt_static"
    PS1='\q{mary/identity}'
    # Cancela também o timer de versões anteriores ao recarregar a configuração.
    if declare -F ble/util/idle.cancel >/dev/null; then
        ble/util/idle.cancel mary/prompt-tick
    fi
fi

# A primeira alteração de texto inicia a saída do título sem consumir teclas.
# O observador é acionado pela edição existente do ble.sh, nunca por um timer.
if [[ ${BLE_VERSION-} && ! ${_skadi_intro_observer_registered-} ]]; then
    _skadi_intro_observer_registered=1
    function skadi/intro-on-edit {
        [[ ${_skadi_intro_dismissed-} || ! ${_ble_edit_str-} ]] && return 0
        _skadi_intro_dismissed=1
        local banner="${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/banner/mary.py"
        if [[ -r $banner ]]; then
            # O subshell evita notificações de job no prompt interativo.
            (python3 "$banner" --dismiss </dev/null >/dev/tty 2>/dev/null &)
        fi
        return 0
    }
    _ble_edit_dirty_observer+=(skadi/intro-on-edit)
fi
