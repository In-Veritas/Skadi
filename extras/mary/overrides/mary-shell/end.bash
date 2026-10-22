# Carregar no final do .bashrc, depois dos demais ajustes de PS1/Readline.
if [[ $- == *i* && ${TERM_PROGRAM-} == ghostty && -t 0 && -t 1 ]]; then
    _mary_config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/ghostty"

    if [[ ${BLE_VERSION-} && -r "$_mary_config_dir/mary-shell/init.sh" ]]; then
        source "$_mary_config_dir/mary-shell/init.sh"
    fi
    if [[ -r "$_mary_config_dir/mary-shell/mary-prompt.sh" ]]; then
        source "$_mary_config_dir/mary-shell/mary-prompt.sh"
    fi
    if [[ ${BLE_VERSION-} && ! ${_ble_attached-} ]]; then
        ble-attach
    fi
    if [[ ${BLE_VERSION-} && ${_skadi_intro_pending-} ]]; then
        # Idle roda depois da primeira renderização e da entrada já enfileirada.
        ble/util/idle.push skadi/startup/ready
        # Enter antecipado pode iniciar um comando antes do primeiro idle.
        blehook PREEXEC+=skadi/startup/ready
    fi
fi
