# Carregar após o teste de shell interativo no início do .bashrc.
if [[ $- == *i* && ${TERM_PROGRAM-} == ghostty && -t 0 && -t 1 ]]; then
    _mary_config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/ghostty"
    _mary_data_dir="${XDG_DATA_HOME:-$HOME/.local/share}/mary"

    if [[ ! ${__ghostty_mary_banner_shown-} &&
          -r "$_mary_config_dir/banner/mary.py" ]] && command -v python3 >/dev/null; then
        __ghostty_mary_banner_shown=1
        python3 "$_mary_config_dir/banner/mary.py"
    fi

    if [[ ! ${BLE_VERSION-} && -r "$_mary_data_dir/blesh/ble.sh" ]]; then
        source -- "$_mary_data_dir/blesh/ble.sh" --attach=none \
            --rcfile="$_mary_config_dir/mary-shell/init.sh"
    fi
fi
