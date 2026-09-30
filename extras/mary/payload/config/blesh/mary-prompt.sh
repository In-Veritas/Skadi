# Prompt Mary: usuário turquesa, hostname azul, uma letra sobe por vez.
# Tempo de cada etapa (subida/repouso), em milissegundos.
MARY_PROMPT_STEP_MS=180

_mary_prompt_static='\[\e[38;2;77;126;154m\][\[\e[1;38;2;94;234;212m\]\u\[\e[0;38;2;77;126;154m\]@\[\e[1;38;2;103;185;255m\]\h\[\e[0m\] \[\e[38;2;140;213;231m\]\W\[\e[38;2;77;126;154m\]]\[\e[1;38;2;94;234;212m\]\$\[\e[0m\] '
PS1=$_mary_prompt_static

if [[ ${BLE_VERSION-} ]] && declare -F ble/util/idle.push >/dev/null; then
    _mary_prompt_user=${USER:-${LOGNAME:-user}}
    _mary_prompt_identity="${_mary_prompt_user}@${HOSTNAME%%.*}"
    _mary_prompt_user_length=${#_mary_prompt_user}
    _mary_prompt_frame=0

    function mary/prompt-tick {
        if [[ ! $_ble_edit_str ]]; then
            ((_mary_prompt_frame = (_mary_prompt_frame + 1) %
                (2 * ${#_mary_prompt_identity} + 4)))
        fi
        ble/util/idle.sleep "$MARY_PROMPT_STEP_MS"
    }

    function ble/prompt/backslash:mary/identity {
        ble/prompt/unit/add-hash '$_mary_prompt_frame'
        ble/prompt/unit/add-hash '${_ble_edit_str:+typing}'
        ble/prompt/unit/add-hash '$COLUMNS'
        local active=-1 index char padding
        local count=${#_mary_prompt_identity}
        # Mantém a largura do prompt constante; digitação suspende o salto.
        if [[ ! $_ble_edit_str ]] && ((COLUMNS > count + 12 &&
                _mary_prompt_frame % 2 == 0 && _mary_prompt_frame / 2 < count)); then
            active=$((_mary_prompt_frame / 2))
            [[ ${_mary_prompt_identity:active:1} == @ ]] && active=-1
        fi

        # Linha reservada para o salto, sem tocar na saída dos comandos.
        printf -v padding '%*s' "$((count + 2))" ''
        if ((active >= 0)); then
            padding="${padding:0:active+1}${_mary_prompt_identity:active:1}${padding:active+2}"
        fi
        ble/prompt/process-prompt-string '\[\e[1;38;2;192;255;245m\]'
        ble/prompt/print "$padding"
        ble/prompt/process-prompt-string '\[\e[0m\]\n\[\e[38;2;77;126;154m\]['

        for ((index=0; index<count; index++)); do
            char=${_mary_prompt_identity:index:1}
            if ((index < _mary_prompt_user_length)); then
                ble/prompt/process-prompt-string '\[\e[1;38;2;94;234;212m\]'
            elif [[ $char == @ ]]; then
                ble/prompt/process-prompt-string '\[\e[0;38;2;77;126;154m\]'
            else
                ble/prompt/process-prompt-string '\[\e[1;38;2;103;185;255m\]'
            fi
            ((index == active)) && char=' '
            ble/prompt/print "$char"
        done
        ble/prompt/process-prompt-string '\[\e[0m\] \[\e[38;2;140;213;231m\]\W\[\e[38;2;77;126;154m\]]\[\e[1;38;2;94;234;212m\]\$\[\e[0m\] '
    }

    # O histórico recebe um prompt normal, completo e colorido.
    bleopt prompt_ps1_final="$_mary_prompt_static"
    PS1='\q{mary/identity}'
    ble/util/idle.cancel mary/prompt-tick
    ble/util/idle.push --sleep="$MARY_PROMPT_STEP_MS" mary/prompt-tick
fi
