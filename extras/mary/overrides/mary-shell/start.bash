# Carregar após o teste de shell interativo no início do .bashrc.
if [[ $- == *i* && ${TERM_PROGRAM-} == ghostty && -t 0 && -t 1 ]]; then
    # Transporta uma seed de 24 bits ao shader pelos dois bits menos
    # significativos dos quatro últimos tons de cinza. Variação <= 3/255.
    # Ghostty ainda não fornece iDate; o estado fica na paleta desta superfície.
    if [[ ! ${_mary_ocean_seeded-} ]]; then
        _mary_ocean_seeded=1
        _mary_ocean_seed=$(( (RANDOM << 9) ^ RANDOM ))
        for ((_mary_color=252; _mary_color<=255; _mary_color++)); do
            _mary_gray=$(( (8 + 10 * (_mary_color - 232)) & ~3 ))
            _mary_bits=$(( (_mary_ocean_seed >> (6 * (_mary_color - 252))) & 63 ))
            printf '\e]4;%d;#%02x%02x%02x\e\\' "$_mary_color" \
                "$((_mary_gray | (_mary_bits & 3)))" \
                "$((_mary_gray | ((_mary_bits >> 2) & 3)))" \
                "$((_mary_gray | ((_mary_bits >> 4) & 3)))"
        done
        unset _mary_color _mary_gray _mary_bits
    fi
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
