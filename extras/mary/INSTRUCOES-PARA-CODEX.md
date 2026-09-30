# Integração da Mary na máquina de destino

Objetivo: reproduzir a configuração contida neste pacote na máquina em que
o usuário está pedindo a importação, preservando os ajustes não relacionados.
O pacote não deve modificar a máquina só por ser extraído.

## 1. Inspeção e requisitos

Leia as instruções locais aplicáveis e execute `python3 verificar-pacote.py`
na raiz extraída. Verifique sistema operacional, arquitetura, usuário, shell
de login, diretórios XDG, fontes, configuração atual e `ghostty --version`.
Leia o `.bashrc`, os arquivos de login e os includes já existentes.

Referência testada: Ghostty 1.3.1-arch2, Bash 5.3.20, Python 3.14.7 e
ble.sh 0.4.0-nightly+d81fd54. Os shaders usam uniforms de Ghostty 1.3.
Use Ghostty 1.3.1 ou versão posterior compatível; valide a versão encontrada
em vez de supor que versões antigas suportam todos os efeitos.
Para esta integração, use Bash moderno (4 ou superior; preferencialmente 5),
Python 3 com `termios`, locale UTF-8, `awk`, `tput`/terminfo e utilitários POSIX.
Verifique a detecção `TERM_PROGRAM=ghostty` numa sessão real.

- Linux com Bash: é o cenário de origem. Use o gerenciador de pacotes da
  distribuição de destino somente para requisitos ausentes.
- Zsh/Fish/outro shell: não faça `source` dos arquivos Bash nesse shell.
  Mantenha o shell global. Pode configurar só o Ghostty para abrir o Bash
  instalado, respeitando os arquivos de inicialização do usuário. Se for
  necessário manter o outro shell dentro do Ghostty, explique que o destaque
  e o prompt precisam ser portados; não declare esses componentes instalados
  apenas por copiar os arquivos.
- macOS: adapte o diretório de configuração efetivo e a instalação de fontes;
  use Bash moderno, não presuma compatibilidade com o Bash 3.2 do sistema.
  `window-theme = ghostty` é uma opção Linux; substitua por `dark` se preciso.
  A tecla de recarga também pode ser diferente. Confira os efeitos na GPU.
- Windows sem ambiente compatível: não execute os scripts Bash/Python POSIX
  diretamente. Identifique primeiro onde o Ghostty/ambiente Linux irá rodar.

O ZIP inclui os recursos visuais, fontes e o código portátil do ble.sh.
Não inclui binários de Ghostty/Bash/Python nem garante instalação totalmente
offline se a máquina ainda não tiver os requisitos.

## 2. Backup e destinos

Faça backup datado dos arquivos que serão alterados e registre os caminhos.
Não use o `.bashrc` de `referencia` como substituto do arquivo do usuário.
Não exporte nem substitua HOME/CODEX_HOME. Use variáveis próprias para destinos.

Para um Linux com convenções XDG normais, os destinos são:

| Origem neste pacote | Destino |
| --- | --- |
| `payload/config/ghostty` | `${XDG_CONFIG_HOME:-$HOME/.config}/ghostty` |
| `payload/config/blesh/*` | `${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/` |
| `payload/share/blesh` | `${XDG_DATA_HOME:-$HOME/.local/share}/mary/blesh` |
| `payload/share/fonts/mary-adwaita-mono` | `${XDG_DATA_HOME:-$HOME/.local/share}/fonts/mary-adwaita-mono` |
| `integracao/00-mary-start.bash` | `ghostty/mary-shell/start.bash` no diretório de configuração |
| `integracao/90-mary-end.bash` | `ghostty/mary-shell/end.bash` no diretório de configuração |

Mantenha o ble.sh deste pacote num diretório próprio, sem sobrescrever outra
instalação. Não copie caches ou diretórios `run`; eles são gerados no destino.
Crie o diretório de cache do usuário (`${XDG_CACHE_HOME:-$HOME/.cache}`) se
estiver faltando. Preserve o `XDG_RUNTIME_DIR` fornecido pelo sistema.
A primeira abertura do ble.sh pode levar mais tempo enquanto gera seus caches.
Preserve licenças, documentação e fontes. No Linux, atualize o cache de fontes
com `fc-cache` e confira `fc-match 'Adwaita Mono'` e as variantes Bold/Italic.

O prompt resolve o nome do usuário e o hostname no destino. A única adaptação
de código feita para o pacote foi substituir o fallback de usuário pessoal
por um fallback genérico. Não escreva `gabriel`/`archlinux` no prompt final.

## 3. Mesclagem do Ghostty

Use `payload/config/ghostty/config.ghostty` como a configuração desejada para
a aparência. Preserve atalhos, comandos, diretório inicial, SSH e outros ajustes
não relacionados que já estejam configurados no destino. Identifique conflitos
de fontes, cores, shaders, tema e includes; integre um resultado coerente.

A fonte do banner é um arquivo de texto; FIGlet não precisa ser instalado.
O tema-base `Catppuccin Mocha` está incluído em `themes/`, além dos overrides
azuis/turquesa. Preserve o tema local incluído ou confirme um equivalente.
Evite duplicar a entrada `custom-shader`, que é cumulativa.

Se criar um arquivo auxiliar de configuração, confira a precedência de
`config-file` e a resolução dos caminhos relativos. Os caminhos da imagem e
do shader devem apontar para cópias permanentes no diretório do usuário,
nunca para o pendrive, Downloads, a pasta extraída ou a máquina de origem.
Se o caminho efetivo do Ghostty não seguir XDG, adapte também os dois arquivos
de integração Bash. Não altere o conteúdo da imagem nem a função que preserva
as teclas ao pular o banner.

## 4. Integração no Bash

Os dois trechos em `integracao/` são módulos de inicialização, não instaladores.
Eles funcionam apenas em Bash interativo, com TTY, dentro do Ghostty.

Depois de copiar os arquivos, adicione blocos identificados e idempotentes
no `.bashrc` existente:

Logo após o teste de shell interativo, antes dos demais ajustes de edição:

```bash
# >>> Mary: início
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/start.bash" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/start.bash"
fi
# <<< Mary: início
```

No final, depois dos frameworks/temas que configuram PS1 ou Readline:

```bash
# >>> Mary: final
if [[ -r "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/end.bash" ]]; then
    source "${XDG_CONFIG_HOME:-$HOME/.config}/ghostty/mary-shell/end.bash"
fi
# <<< Mary: final
```

O módulo inicial exibe o banner antes do editor, detecta ble.sh já carregado
e, se necessário, carrega a cópia incluída com `--attach=none` e seu arquivo
de configuração explícito. O módulo final aplica as cores, define o prompt
e anexa o editor apenas se ele ainda não estiver ativo.

Se o destino já carregar ble.sh em outro ponto, ajuste a ordem para haver
uma única inicialização. Se houver um framework que restaura PS1 a cada prompt,
desative só o componente de prompt conflitante no Ghostty. Não acumule timers
ou hooks duplicados. Preserve aliases, funções, histórico e configurações de
outros terminais. Não copie o histórico desta máquina.

Confira que o arquivo de login usado pelo Ghostty já chama `.bashrc`; adicione
essa integração somente se estiver faltando, preservando seu conteúdo.

## 5. Validação antes de concluir

1. Execute `bash -n` no `.bashrc` e nos módulos alterados.
2. Execute `ghostty +validate-config` no destino. Confira também o resultado
   efetivo com `ghostty +show-config`, incluindo caminhos do shader/imagem.
3. Faça um teste do banner em um PTY: deixe as 6 linhas aparecerem (~3 s),
   depois pule digitando uma palavra, inclusive acentos; os bytes digitados
   devem chegar intactos ao shell. O terminal deve recuperar eco e modo normal.
4. Em uma nova janela real, confirme título Mary, fundo, fonte, cores e rastro.
   Veja os logs do Ghostty para erros de shader: validar só o arquivo de
   configuração não compila o GLSL nem prova o resultado visual.
5. Confirme destaque de comandos válidos e inválidos, backspace, setas,
   histórico e execução de comandos; uma palavra parcialmente digitada não
   deve ser perdida. O prompt deve pausar quando existe texto em edição.
6. Confirme que as letras do usuário/host do destino saltam na ordem correta
   e que o prompt registrado no histórico visual fica completo ao executar.
7. Execute `false` e depois `printf '%s\n' "$?"`: deve mostrar `1`, mesmo
   com o prompt animado. Teste também redimensionamento e uma janela estreita.
8. Reabra a sessão para conferir persistência e ausência de inicializações
   duplicadas. Teste que sessões não interativas e outros terminais não mostram
   o banner nem passam a usar o prompt Mary.

Não encerre sessões com trabalho do usuário. Use uma sessão nova para validar.
Ao concluir, descreva o que foi instalado, adaptações necessárias, testes
realizados, localização dos backups e forma de ativar/desfazer.

## 6. Ajustes e reversão

- `banner/mary.py`: `LINE_DELAY=0.48` segundos por linha.
- `mary-shell/mary-prompt.sh`: `MARY_PROMPT_STEP_MS=180` milissegundos.
- `mary-shell/init.sh`: cores de comandos, argumentos e erros.
- Configuração do Ghostty: fundo em 18%, título, fonte, paleta e shaders.
- `shaders/aurora-trail.glsl`: cores/intensidades da aurora e duração do rastro.

Para desfazer, restaure os arquivos de configuração a partir dos backups,
remova apenas os blocos identificados da integração e abra outra sessão.
Os diretórios exclusivos `mary-shell` e `share/mary/blesh` podem ser removidos
depois de confirmar que não são mais referenciados. Não apague diretórios
inteiros de Ghostty, fontes ou ble.sh que contenham material anterior do usuário.
