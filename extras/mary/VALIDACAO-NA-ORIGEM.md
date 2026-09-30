# Verificação do pacote na origem — 29/09/2026

Conferido antes de compactar:

- Sintaxe dos módulos Bash e dos arquivos Python incluídos.
- Configuração do Ghostty válida em um diretório XDG temporário diferente.
- Caminhos efetivos de imagem e shader apontando para esse novo diretório.
- Inicialização do Bash usando apenas a cópia incluída do ble.sh.
- Pulo do banner preservando o comando digitado.
- Preservação de uma configuração preexistente do shell durante a integração.
- Prompt carregado com usuário e hostname de destino simulados.
- Destaque de sintaxe ativo e código de saída de `false` preservado como `1`.
- Módulos sem efeito em shells não interativos.

Esses testes usaram diretórios temporários, sem substituir os arquivos ativos
da Mary na máquina de origem. Os hashes de todos os arquivos do pacote estão
em `SHA256SUMS`; o verificador incluído confere a cópia após a transferência.

A máquina de destino ainda precisa da validação própria descrita em
`INSTRUCOES-PARA-CODEX.md`, incluindo renderização real, fontes, shell e versão
do Ghostty. Este teste local não comprova compatibilidade com qualquer sistema.
