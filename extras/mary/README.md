# Perfil Skadi neste fork

O conteúdo de `Mary-Ghostty-portatil-2026-09-29.zip` foi extraído aqui sem
alterar os arquivos originais. O perfil reúne a paleta oceano/turquesa,
Adwaita Mono, imagem de fundo, shader de aurora e rastro, banner MARY e
prompt Bash animado com ble.sh. As licenças e os recursos estão incluídos.

## Animação atual: água em movimento e baleia nadando

Os ajustes ficam em `overrides/`, separados do pacote original e de seus
checksums. O instalador aplica esses arquivos depois dos recursos originais.
O título da janela fica fixo em **Skadi** (`title = Skadi`), inclusive quando
o shell ou outro programa tenta alterá-lo. Recarregar a configuração atualiza
também as janelas abertas.

`overrides/shaders/ocean-dots.glsl` mantém duas geometrias de pontos:

- **Água:** grade com deslocamento orbital horizontal e vertical, cristas
  propagando-se e variação suave do vento. `freeWaterVertex` calcula o mar
  livre; `waterVertex` acrescenta o escoamento ao redor da baleia.
- **Baleia:** corpo tridimensional próprio, amostrado por `whaleVertex`.
  Seus pontos ficam presos ao corpo enquanto ele avança, emerge para
  respirar e afunda. Ombros largos, cabeça/rostro baixos, afunilamento
  posterior, corcova e barbatana substituem o perfil elipsoidal inicial.
  `bodyRadii`, `spineOffset` e `dorsalFin` são compartilhados pelo desenho
  e pelo contato com a água. A animação atual não contém cauda.

A seção móvel do corpo afasta a água lateralmente. O contato é verificado
novamente depois das ondas para impedir que os pontos atravessem o corpo.
Há uma onda de proa e uma esteira em V; a passagem fecha conforme o volume
imerso aumenta e as ondulações restantes desaparecem. O movimento usa campos
analíticos de deslocamento e contato, calculados a cada quadro.

A natação combina pequenas acelerações com uma onda de flexão dorso-ventral
que se propaga da frente para trás. A cabeça fica mais estável, a traseira
flexiona mais, e o dorso se arqueia durante a submersão. Os pontos acompanham
essa deformação mantendo suas identidades no corpo.

O avanço usa 30–45 unidades por segundo, com oscilação de velocidade
limitada a 10%. Ao mergulhar, ganha até 30% de velocidade adicional e
continua avançando mesmo submersa. A cabeça começa a descer após o sopro,
com flexão sincronizada à natação.

### Ondas baseadas nas referências de Acerola

Foram lidas as legendas e descrições e inspecionados quadros de storyboard de
[How Games Fake Water](https://www.youtube.com/watch?v=PH9q0HNBjT4) e
[I Tried Simulating The Entire Ocean](https://www.youtube.com/watch?v=yPfagLeUa7k).
O YouTube retornou HTTP 403 para os arquivos de vídeo; não houve reprodução
integral. O código de referência dos vídeos é [Water](https://github.com/GarrettGunnell/Water).

O campo atual usa seis bandas: ondas longas com maior amplitude e ondulações
curtas menores. O perfil exponencial dá cristas mais estreitas e vales mais
largos; a derivada de uma banda desloca a amostragem das seguintes. As fases
permanecem contínuas enquanto a energia muda suavemente com o vento. A
velocidade angular segue `omega² = g*k`, com gravidade em unidades da cena.
O deslocamento lateral aproxima os pontos nas cristas. Inclinação aproximada
e compressão modulam a luz azul-turquesa e um destaque discreto nas cristas.

É uma adaptação analítica para o shader de pontos, **não uma FFT, JONSWAP ou
simulação hidrodinâmica completa**. A deformação entre bandas torna a normal
uma aproximação. As ideias de dispersão e deslocamento também são descritas
em [GPU Gems, capítulo 1](https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models).

O benchmark atualizado na Intel UHD Graphics a 1000×700, sem readback,
mediu 11,84 / 16,50 / 11,77 ms por quadro nas três fases com baleia
(84 / 61 / 85 fps). Não é garantia de FPS mínimo em outras resoluções.

O sopro tem maior altura e dispersão, mantendo os pontos pequenos. Usa 288 partículas: 96 gotículas balísticas e 192 pontos de vapor.
São emitidos por dois pontos próximos no alto da cabeça, preservando a
posição e a velocidade no instante da emissão. As gotículas caem; o vapor
sobe com arrasto, expande, segue o vento e se dissolve. O raio projetado do
sopro fica abaixo de 0,65 pixel nas cenas testadas, menor que os pontos da
água e do corpo. Vapor e gotículas têm perfis de transparência diferentes.

Referência de comportamento: [NOAA — Whale Behaviors](https://stellwagen.noaa.gov/visit/whalewatching/whale-behaviors.html),
seções sobre exposição do dorso e expiração. A referência orienta o movimento;
os desenhos são gerados pelo shader.

Uma seed de 24 bits é gerada na abertura de cada Bash interativo no Ghostty.
Ela coordena direção, velocidade e amplitude das ondas, posição, distância,
tamanho e orientação dos encontros. O vento muda suavemente a cada 28 s.
O primeiro encontro começa entre 8 e 27 s; os seguintes começam a intervalos
entre 53 e 91 s. A baleia respira e submerge em cerca de 16 s; a esteira
diminui até 29 s depois do início do encontro.

A perspectiva rasante permanece: `SEA_HORIZON = 0.60`, com horizonte a 40%
da altura desde o topo. `SEA_OPACITY = 0.24` controla a intensidade dos pontos.
Uma única crista de até 3 pixels segue um ciclo contínuo de 12 segundos:
usuário, brilho do `@`, nome da máquina, caminho e retorno ao usuário.
Cada letra sobe e desce suavemente ao longo de 1,2 s. O `@` começa a
acender aos 2,6 s, enquanto a última letra desce; segura branco/turquesa
intenso entre 3,6 e 3,8 s e apaga até 5 s. Só então a onda segue pelo
host e pelo caminho, compartilhando uma frente contínua mais lenta.
O shader usa `iTime` e interpolação subpixel, sem timer Bash nem redesenho
do prompt por quadro. A animação continua enquanto se digita, inclusive com
cursor em outra linha. O histórico recebe as cores normais e janelas estreitas
usam prompt estático. A fluidez acompanha a renderização do Ghostty
(`custom-shader-animation = true`), sem depender da atualização do ble.sh.
O `@` também tem um halo turquesa suave no fundo, sincronizado com o pulso.
O rastro ao digitar é compacto e desaparece em 550 ms; a tinta da letra
recém-escrita clareia por até 420 ms. As faces semânticas do ble.sh identificam
comandos e palavras-chave para um realce discreto de toda a palavra na linha
ativa, preservando o histórico. Shader, paleta de sintaxe e módulo do prompt
devem ser usados juntos.

### Transporte da seed nesta versão do Ghostty

O renderer desta versão não atualiza `iDate`. O módulo
`overrides/mary-shell/start.bash` envia a seed pela paleta da superfície:
usa os dois bits inferiores de cada componente RGB nos tons 252–255.
A diferença visual nesses quatro cinzas é de no máximo 3/255 por componente.
O shader recupera os bits por `iPalette`; a seed não muda a cada quadro.
Reexecutar `.bashrc` na mesma sessão não gera outra seed. Uma aplicação que
redefina esses quatro tons também altera os bits recebidos pelo shader.

### Validação e ativação

```sh
python3 extras/mary/tests/render_shader.py --output-dir /tmp/mary-anatomy-qa
```

Requer Mesa EGL/GLES e Pillow. O teste verifica compilação, mudanças de seed,
reprodução do mesmo quadro, movimento orbital da água, avanço da baleia,
ausência de água dentro do corpo em cinco fases, fechamento após a submersão,
salto de 3 pixels do prompt e quatro sessões distintas. Também verifica
assimetria anatômica, flexão maior atrás, 288 partículas pequenas, subida do
vapor, queda das gotas e término da emissão.
A folha de comparação e o GIF gerados são apenas registros de QA; o terminal
executa o shader procedural diretamente.

Para ativar a versão atual, recarregue com `Ctrl+Shift+,` e abra uma nova
janela para inicializar sua seed. Backup anterior à ondulação das letras, ao título detalhado e à saída de quatro segundos:
`~/.local/share/mary/backups/20260930-000653-183138`.
O `manifest.json` identifica os arquivos e as cópias anteriores.

## Abertura e fluidez

O shell fica livre desde 5,4 segundos; o título espera a primeira digitação:

- 0–5 s: Skadi desce lentamente e para no primeiro terço da tela (centro a 25%).
- 5,4 s: aparece o prompt abaixo do título; já é possível digitar e executar.
- 5,8–9,2 s: o mar nasce por colunas verticais, da esquerda para a direita;
  em cada coluna os pontos surgem de cima para baixo, mantendo suas órbitas.
- Após a revelação: Skadi permanece no alto, ondulando, até começar a digitar.
- Ao primeiro texto: Skadi sobe e desaparece em 0,8 segundo; o mar continua.

O título **Skadi** usa o ASCII fornecido pelo usuário, preservado em
`overrides/banner/skadi.txt`. Cada caractere é desenhado com Adwaita Mono,
a fonte incluída no pacote. Uma onda atravessa o desenho e coordena o
movimento vertical, as cores azul/turquesa/branco e as transformações suaves
entre caracteres de formato semelhante (`o/O/0`, `8/B`, `d/q/b`). Os espaços
ficam vazios e as trocas usam crossfade para evitar piscadas. O gerador
`python3 extras/mary/tools/build_title.py` atualiza as tabelas do shader a
partir do ASCII; Pillow só é necessário para regenerá-las.
Os caminhos internos `mary` continuam compatíveis com instalações existentes
e com o arquivo original, cujo conteúdo e checksums foram preservados.
A saída final sobe e perde opacidade durante 0,8 segundo. O shader compõe o título
sobre o fundo sem substituir os pixels do texto. Cada ponto recebe seu
instante de nascimento pela posição de repouso e pela fração dentro da
coluna. O fade de cada ponto dura 240 ms; colunas vizinhas se sobrepõem
para evitar blocos aparecendo juntos. A formação do mar caiu de 5,5 para
3,4 segundos. O mar não reinicia ao final.
`overrides/banner/mary.py` libera o processo principal aos 5,4 s e entrega o
restante a um processo curto em segundo plano, que só emite OSC de paleta:
nunca lê stdin nem altera posição do cursor ou conteúdo do terminal.
O progresso usa 16 bits nos canais verde/azul da cor 251 (vermelho=17), com
atualização alvo de 60 Hz até 9,6 s. A cor 250 (vermelho=18) controla
o fade independente. Um observador de edição do ble.sh inicia uma única
saída ao primeiro texto, sem ler stdin nem manter um processo esperando. Os índices
252–255 seguem exclusivos da seed. Resize não interrompe a sequência;
digitar antes da hora adianta a liberação do prompt sem consumir as teclas.

O perfil define `resize-overlay = never`, ocultando o indicador de dimensões
que pode surgir quando a janela ajusta o tamanho na abertura. O prompt ativo
não tem mais uma quebra de linha extra: tem a mesma altura do prompt final
gravado no histórico, evitando o salto ao executar/redesenhar comandos.

O shader pré-calcula os parâmetros comuns das ondas por fragmento, inverte
a projeção para buscar nove vizinhos da malha livre e restringe a busca da
baleia/água deslocada à vizinhança projetada. O sopro usa um limite espacial
que acompanha a expansão das partículas, preservando as 288 partículas.
Os testes verificam contato, movimento, seed, ordem das colunas, visibilidade
do texto durante a intro, espera por digitação, fade independente e resize.

Na Intel UHD Graphics (CML GT2), o benchmark EGL a 1000×700 com readback
passou de 62–71 ms por quadro para 24–46 ms nas três fases com baleia
(aproximadamente 22–41 quadros/s). Separando o desenho sincronizado na GPU da cópia das imagens e do Pillow,
as três fases mediram 9,18 / 14,21 / 9,12 ms por quadro (109 / 70 / 110 fps).
Portanto o shader ficou abaixo do orçamento de 16,67 ms nessas amostras a
1000×700. Isso não garante um mínimo de 60 fps em toda resolução, carga ou
composição da janela. A intro envia controles a 60 Hz, e o timer do
renderizador do fork segue em 8 ms.

```sh
python3 extras/mary/install.py --user-dir /tmp/mary-opening-stage
python3 extras/mary/tests/check_banner.py /tmp/mary-opening-stage/.config/ghostty/banner/mary.py
python3 extras/mary/tests/render_shader.py --benchmark
python3 extras/mary/tests/render_shader.py --skip-animation
```

## Instalar

No Linux, com Ghostty, Bash 4+, Python 3 e fontconfig instalados:

```sh
python3 extras/mary/install.py
```

Execute como seu usuário, sem `sudo`. O instalador verifica o pacote, copia
os recursos para os diretórios XDG do usuário, cria um backup datado e
acrescenta blocos identificados ao `.bashrc`. O perfil visual fica em
`~/.config/ghostty/mary.ghostty`, incluído pela configuração principal.
Os recursos passam a usar caminhos permanentes; o ZIP não é necessário
depois da instalação. Atalhos, aliases e a inicialização do Conda são
preservados. A aparência Skadi substitui fontes e shaders anteriores.

Abra uma nova janela do Ghostty para ativar todos os componentes. Compilar
este fork não instala automaticamente arquivos no diretório do usuário;
execute o instalador também quando usar um binário compilado do fork.

O instalador pode ser executado novamente sem duplicar os blocos. Para
testar cópias de configurações sem alterar o usuário atual, use
`--user-dir /tmp/mary-teste`. Esse modo não atualiza o cache de fontes.
Em máquinas com outros frameworks ou configurações complexas, siga também
as instruções de mesclagem de [INSTRUCOES-PARA-CODEX.md](INSTRUCOES-PARA-CODEX.md).

## Instalação nesta máquina — 29/09/2026

- Ubuntu 26.04, Bash 5.3.9, locale UTF-8.
- Ghostty instalado: `1.3.0-dev+0000000`. Embora anterior à referência
  `1.3.1` do pacote, aceitou todas as opções e executou o shader em uma
  janela real sem registrar erros de compilação GLSL.
- Código deste fork: `1.3.2-dev`. O núcleo não foi alterado nem recompilado;
  não há Zig instalado no PATH.
- Backup: `/home/veritas/.local/share/mary/backups/20260929-172807-617987`.
  `manifest.json` relaciona cada destino à sua cópia anterior; `null`
  identifica um arquivo que não existia antes da instalação.
- `.profile` já carregava `.bashrc` e foi preservado.

Verificações concluídas: integridade dos 356 arquivos, sintaxe Bash,
`ghostty +validate-config`, configuração efetiva, quatro variantes da fonte,
idempotência do instalador, banner completo e interrompido com entrada UTF-8,
restauração de termios, carregamento do ble.sh, preservação de `$?` após
`false`, digitação parcial, histórico/seta para cima/backspace, janela estreita,
identidade local e isolamento de outros terminais e shells não interativos.
A janela de teste confirmou `TERM_PROGRAM=ghostty` e fechou automaticamente.
Os logs gráficos apresentaram avisos GTK/Adwaita, sem erros do shader.
A aparência e a animação não foram inspecionadas visualmente quadro a quadro.

## Desfazer nesta máquina

Para restaurar os dois arquivos anteriores à instalação:

```sh
cp ~/.local/share/mary/backups/20260929-172807-617987/348 ~/.config/ghostty/config.ghostty
cp ~/.local/share/mary/backups/20260929-172807-617987/349 ~/.bashrc
```

Isso restaura o estado anterior, incluindo o `.bashrc` completo. Caso tenha
feito alterações posteriores nesses arquivos, preserve-as e remova apenas os
blocos `Mary: início`, `Mary: final` e `Mary: aparência` em vez de restaurar
as cópias inteiras. Abra uma nova janela. Os recursos deixam de ser carregados
e podem permanecer no disco; o manifesto lista os arquivos adicionados caso
queira removê-los individualmente.

Teste da crista única e da passagem pelo caminho: `python3 extras/mary/tests/check_prompt.py`.

### Ícone do Skadi

O instalador aplica `design/skadi-icons/caudas-v2/anel/06-gravura.png`
sem alterar a imagem. O lançador local passa a se chamar Skadi, mantendo
a identidade `com.mitchellh.ghostty` para os atalhos e janelas existentes.
O ícone e o lançador entram no mesmo backup das demais configurações.
A instalação cobre tamanhos de 16 a 1024 px e variantes HiDPI: substituir
apenas 512 px deixa o GTK escolher os ícones pequenos antigos do sistema.

O lançador usa um nome de ícone derivado do conteúdo da imagem, evitando
que a busca do KDE mantenha uma versão anterior em cache após a troca.
