# Mary — pacote portátil do Ghostty

Este pacote contém a configuração atual da Mary, exportada em 29/09/2026:

- Paleta azul/turquesa, fonte Adwaita Mono e tema Catppuccin Mocha.
- Imagem de fundo com 18% de opacidade, aurora, partículas e rastro do cursor.
- Abertura MARY na fonte ANSI Shadow, linha por linha, em cerca de 3 segundos.
- A abertura para ao digitar e preserva as teclas para o comando.
- Comandos com destaque de sintaxe no Bash, usando ble.sh.
- Prompt colorido com letras saltando em ordem; fica estável durante a digitação.

## Como levar para outro PC

1. Copie o arquivo `Mary-Ghostty-portatil-2026-09-29.zip` para o pendrive.
2. No outro PC, extraia o ZIP para uma pasta local.
3. Abra essa pasta com o Codex e cole o conteúdo de `PEDIDO-PARA-CODEX.txt`.

O Codex deve seguir `INSTRUCOES-PARA-CODEX.md`, conferir a máquina de destino,
fazer backup e mesclar a configuração com o que você já usa. Não é necessário
copiar seu `.bashrc` inteiro por cima do outro.

O material da Mary está incluído, assim como o ble.sh e as quatro variantes
da fonte Adwaita Mono. Ghostty, Bash, Python e utilitários do sistema precisam
estar instalados no destino; esses programas não estão dentro do ZIP.
O pacote foi preparado a partir de Linux + Ghostty 1.3.1 + Bash 5.3.20.
Outros sistemas/shells precisam de adaptação descrita nas instruções.

## Conferir a cópia

Dentro da pasta extraída:

```bash
python3 verificar-pacote.py
```

Essa verificação apenas lê os arquivos. Não instala nada nem modifica seu shell.

## O que existe em cada pasta

| Pasta | Conteúdo |
| --- | --- |
| `payload/config/ghostty` | Configuração visual, shaders, fundo, temas e banner |
| `payload/config/blesh` | Cores dos comandos e prompt animado |
| `payload/share/blesh` | ble.sh completo, incluindo documentação e licenças |
| `payload/share/fonts` | Adwaita Mono: normal, negrito, itálico e negrito-itálico |
| `integracao` | Dois trechos para carregar Mary no início/final do `.bashrc` |
| `referencia` | `.bashrc` de origem como exemplo, não como substituto |
| `licencas` | Licença do Ghostty, origem do tema-base |

Histórico do shell, chaves, credenciais, caches de execução e backups antigos
da configuração não fazem parte deste pacote.

## Ajustes depois da integração

- Abertura: `banner/mary.py`, `LINE_DELAY = 0.48` (segundos por linha).
- Prompt: `mary-shell/mary-prompt.sh`, `MARY_PROMPT_STEP_MS=180` (milissegundos).
- Fundo: `background-image-opacity = 0.18` no arquivo do Ghostty.
- Rastro/aurora: constantes no início de `shaders/aurora-trail.glsl`.
- Cores dos comandos: `mary-shell/init.sh`.

Valores maiores nos dois intervalos deixam as animações mais lentas.
No Ghostty Linux da origem, Ctrl+Shift+vírgula recarrega o visual. Abra uma nova
aba/janela para carregar alterações de Bash, banner e prompt.
