"""Renderização de QA do shader Mary: requer Mesa EGL/GLES e Pillow.

Uso: python3 extras/mary/tests/render_shader.py --output-dir /tmp/mary-qa
Não abre janelas nem altera configurações do usuário.
"""
import argparse
import ctypes as C
import os
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=Path('/tmp/mary-qa'))
parser.add_argument('--skip-animation', action='store_true', help='Executa verificações e quadros sem exportar GIF')
parser.add_argument('--shader', type=Path, help='Shader alternativo para comparar desempenho')
parser.add_argument('--benchmark', action='store_true', help='Mede quadros completos com leitura GPU sincronizada')
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parents[1]
os.environ['EGL_PLATFORM'] = 'surfaceless'
E = C.CDLL('libEGL.so.1')
G = C.CDLL('libGLESv2.so.2')

def bind(lib, name, ret, args):
    f = getattr(lib, name)
    f.restype = ret
    f.argtypes = args
    return f
I = C.c_int
U = C.c_uint
F = C.c_float
P = C.c_void_p
get = bind(E, 'eglGetDisplay', P, [P])
init = bind(E, 'eglInitialize', U, [P, P, P])
choose = bind(E, 'eglChooseConfig', U, [P, P, P, I, P])
api = bind(E, 'eglBindAPI', U, [U])
context = bind(E, 'eglCreateContext', P, [P, P, P, P])
surface = bind(E, 'eglCreatePbufferSurface', P, [P, P, P])
current = bind(E, 'eglMakeCurrent', U, [P, P, P, P])
d = get(None)
assert init(d, None, None)
assert api(12448)
attrs = (I * 13)(12324, 8, 12323, 8, 12322, 8, 12321, 8, 12339, 1, 12352, 64, 12344)
config = P()
n = I()
assert choose(d, attrs, C.byref(config), 1, C.byref(n)) and n.value
ctx = context(d, config, None, (I * 3)(12440, 3, 12344))
w, h = (1000, 700)
surf = surface(d, config, (I * 5)(12375, w, 12374, h, 12344))
assert current(d, surf, surf, ctx)
create = bind(G, 'glCreateShader', U, [U])
source = bind(G, 'glShaderSource', None, [U, I, P, P])
compile_ = bind(G, 'glCompileShader', None, [U])
status = bind(G, 'glGetShaderiv', None, [U, U, P])
log = bind(G, 'glGetShaderInfoLog', None, [U, I, P, P])

def shader(kind, text):
    sh = create(kind)
    st = C.c_char_p(text.encode())
    source(sh, 1, C.byref(st), None)
    compile_(sh)
    ok = I()
    status(sh, 35713, C.byref(ok))
    if not ok.value:
        buf = C.create_string_buffer(10000)
        log(sh, 10000, None, buf)
        raise RuntimeError(buf.value.decode())
    return sh
vertex = shader(35633, '#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2); gl_Position=vec4(p*2.0-1.0,0,1);}')
header = """#version 300 es
precision highp float;
precision highp int;
uniform sampler2D iChannel0;
uniform int maryTestMode;
uniform vec3 iResolution, iBackgroundColor, iPalette[256];
uniform float iTime, iTimeCursorChange, iTimeFocus;
uniform vec4 iCurrentCursor, iPreviousCursor;
uniform int iFocus, iCursorVisible;
out vec4 outputColor;
"""
body = (args.shader or root / 'overrides/shaders/ocean-dots.glsl').read_text()
fragment = shader(35632, header + body + """
void main() {
    prepareOcean(sessionSeed());
    OceanEvent e = sceneEvent(iTime, sessionSeed());
    if (maryTestMode == 1) {
        vec2 world = e.origin + e.side * GRID;
        vec3 free = freeWaterVertex(world, sessionSeed());
        vec3 point = waterVertex(world, e, sessionSeed());
        outputColor = vec4(0.5 + (point.x - free.x) / 256.0,
                           0.5 + (point.z - free.z) / 256.0,
                           0.5 + (point.y - free.y) / 256.0, 1.0);
    } else if (maryTestMode == 2) {
        outputColor = vec4((mod(iTime, EVENT_SECONDS) - e.age) / 32.0,
                          CAMERA / (CAMERA + e.origin.y),
                          0.5 + e.origin.x / 4000.0, 1.0);
    } else if (maryTestMode == 3) {
        vec2 world = vec2(72.0, 300.0);
        vec3 point = freeWaterVertex(world, sessionSeed());
        outputColor = vec4(0.5 + (point.x - world.x) / 64.0,
                           0.5 + (point.z - world.y) / 64.0,
                           0.5 + point.y / 64.0, 1.0);
    } else if (maryTestMode == 4) {
        vec2 center = projectPoint(whaleVertex(0.0, 0.0, e));
        outputColor = vec4(center / iResolution.xy, e.exposure, 1.0);
    } else if (maryTestMode == 5) {
        vec2 uv = gl_FragCoord.xy / iResolution.xy * 2.0 - 1.0;
        vec2 world = e.center + e.forward * uv.x * e.size * 1.2
                              + e.side * uv.y * e.size * 0.6;
        vec3 p = waterVertex(world, e, sessionSeed());
        vec2 delta = p.xz - e.center;
        float x = dot(delta, e.forward);
        float z = dot(delta, e.side);
        float section = bodySection(x, p.y, e);
        z -= spineOffset(x / e.size, e).x;
        outputColor = vec4(section > 0.01 && abs(z) + 0.25 < section ? 1.0 : 0.0,
                           0.0, 0.0, 1.0);
    } else if (maryTestMode == 6) {
        float rear = spineOffset(-0.7, e).y - e.bodyY + e.pitch * 0.7 * e.size;
        float head = spineOffset(0.7, e).y - e.bodyY - e.pitch * 0.7 * e.size;
        outputColor = vec4(0.5 + rear / e.size, 0.5 + head / e.size, 0.0, 1.0);
    } else if (maryTestMode == 7) {
        outputColor = vec4(bodyRadii(0.25, e).x / e.size,
                           bodyRadii(-0.75, e).x / e.size,
                           dorsalFin(-0.42, e) / e.size, 1.0);
    } else if (maryTestMode == 8) {
        int index = min(SPRAY_COUNT - 1, int(gl_FragCoord.x / iResolution.x * float(SPRAY_COUNT)));
        SprayPoint particle = sprayParticle(index, e);
        outputColor = vec4(particle.radius / 2.0, particle.visibility, particle.vapor, 1.0);
    } else if (maryTestMode == 9) {
        SprayPoint drop = sprayParticle(0, e);
        SprayPoint mist = sprayParticle(1, e);
        outputColor = vec4(0.5 + drop.position.y / 256.0,
                           0.5 + mist.position.y / 256.0, mist.visibility, 1.0);
    } else if (maryTestMode == 14) {
        float kind = gl_FragCoord.y < iResolution.y / 3.0 ? 0.0 :
                     (gl_FragCoord.y < iResolution.y * 2.0 / 3.0 ? 3.0 : 2.0);
        vec3 marker = vec3(1.0, gl_FragCoord.x / iResolution.x, kind);
        outputColor = vec4(promptLift(marker) / 3.0, promptPulse(marker), 0.0, 1.0);
    } else if (maryTestMode == 13) {
        outputColor = vec4(introTitle(gl_FragCoord.xy, introProgress()), 1.0);
    } else if (maryTestMode == 12) {
        vec2 pixel = gl_FragCoord.xy;
        float horizon = iResolution.y * SEA_HORIZON;
        float depth = clamp((horizon - pixel.y) / horizon, 0.025, 1.0);
        float nearRow = floor(CAMERA / GRID * (1.0 / depth - 1.0));
        vec3 ocean = vec3(0.0);
        if (pixel.y < horizon + 3.0) {
            for (int j = -5; j <= 5; j++) {
                float row = nearRow + float(j);
                float d = CAMERA / (CAMERA + row * GRID);
                float col = round((pixel.x - iResolution.x * 0.5) / (GRID * d));
                for (int i = -3; i <= 3; i++) {
                    vec2 world = vec2(col + float(i), row) * GRID;
                    ocean = max(ocean, drawWaterPoint(pixel, world, e, sessionSeed()));
                }
            }
        }
        outputColor = vec4(iBackgroundColor + ocean, 1.0);
    } else if (maryTestMode == 11) {
        float x = (gl_FragCoord.x / iResolution.x - 0.5) * 1600.0;
        outputColor = vec4(introWaterVisibility(vec2(x, 600.0)),
                           introWaterVisibility(vec2(x, 1200.0)),
                           introWaterVisibility(vec2(x, 0.0)), 1.0);
    } else if (maryTestMode == 10) {
        OceanEvent next = e;
        next.age += 0.05;
        poseWhale(next);
        float speed = dot(next.center - e.center, e.forward) / 0.05;
        outputColor = vec4(speed / 80.0, e.exposure, 0.0, 1.0);
    } else {
        mainImage(outputColor, gl_FragCoord.xy);
    }
}
""")
program = bind(G, 'glCreateProgram', U, [])()
attach = bind(G, 'glAttachShader', None, [U, U])
attach(program, vertex)
attach(program, fragment)
bind(G, 'glLinkProgram', None, [U])(program)
stat = I()
bind(G, 'glGetProgramiv', None, [U, U, P])(program, 35714, C.byref(stat))
assert stat.value
bind(G, 'glUseProgram', None, [U])(program)
loc = bind(G, 'glGetUniformLocation', I, [U, C.c_char_p])
f1 = bind(G, 'glUniform1f', None, [I, F])
i1 = bind(G, 'glUniform1i', None, [I, I])
f3 = bind(G, 'glUniform3f', None, [I, F, F, F])
f4 = bind(G, 'glUniform4f', None, [I, F, F, F, F])

def at(name):
    return loc(program, name.encode())
f3(at('iResolution'), w, h, 1)
f3(at('iBackgroundColor'), 8 / 255, 25 / 255, 37 / 255)
f4(at('iCurrentCursor'), 600, 570, 10, 26)
i1(at('iCursorVisible'), 1)
i1(at('iFocus'), 1)
i1(at('iChannel0'), 0)
tex = U()
bind(G, 'glGenTextures', None, [I, P])(1, C.byref(tex))
bind(G, 'glBindTexture', None, [U, U])(3553, tex)
param = bind(G, 'glTexParameteri', None, [U, U, I])
param(3553, 10241, 9729)
param(3553, 10240, 9729)
upload = bind(G, 'glTexImage2D', None, [U, I, I, I, I, I, U, U, P])
read = bind(G, 'glReadPixels', None, [I, I, I, I, U, U, P])
draw = bind(G, 'glDrawArrays', None, [U, I, I])
bind(G, 'glViewport', None, [I, I, I, I])(0, 0, w, h)
font = ImageFont.truetype(str(root / 'payload/share/fonts/mary-adwaita-mono/AdwaitaMono-Regular.ttf'), 20)


def render(t, mode=0, terminal=None):
    if terminal is None:
        terminal = Image.new('RGB', (w, h), (8, 25, 37))
    raw = terminal.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes()
    upload(0x0DE1, 0, 0x1907, w, h, 0, 0x1907, 0x1401, raw)
    f1(at('iTime'), t)
    i1(at('maryTestMode'), mode)
    draw(4, 0, 3)
    pixels = C.create_string_buffer(w * h * 4)
    read(0, 0, w, h, 0x1908, 0x1401, pixels)
    return Image.frombytes('RGBA', (w, h), pixels.raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM)


from PIL import ImageChops, ImageStat


def set_seed(seed):
    for index in range(4):
        gray = (208 + index * 10) & ~3
        bits = (seed >> (index * 6)) & 63
        rgb = [gray | ((bits >> (channel * 2)) & 3) for channel in range(3)]
        f3(at(f'iPalette[{252 + index}]'), *(value / 255 for value in rgb))


if args.benchmark:
    set_seed(192837)
    onset = render(0, 2).getpixel((0, 0))[0] / 255 * 32
    for phase in (3, 6, 10):
        render(onset + phase)
        start = time.perf_counter()
        for frame in range(12):
            render(onset + phase + frame / 120)
        elapsed = time.perf_counter() - start
        print(f'fase={phase}: {elapsed / 12 * 1000:.2f} ms/quadro; {12 / elapsed:.1f} quadros/s (QA com readback)', flush=True)
        finish = bind(G, 'glFinish', None, [])
        finish()
        start = time.perf_counter()
        for frame in range(24):
            f1(at('iTime'), onset + phase + frame / 120)
            draw(4, 0, 3)
            finish()
        elapsed = time.perf_counter() - start
        print(f'fase={phase}: {elapsed / 24 * 1000:.2f} ms/quadro; {24 / elapsed:.1f} quadros/s (desenho sincronizado, sem readback)', flush=True)
    raise SystemExit(0)

# Intro: mar oculto durante a descida, revelação ordenada e término completo.
set_seed(192837)
def opening(seconds):
    step = round(seconds / 13.6 * 65535)
    f3(at('iPalette[251]'), 17 / 255, (step >> 8) / 255, (step & 255) / 255)
opening(4.5)
assert render(1, 11).convert('RGB').getbbox() is None
# Coluna central no meio da revelação: alto visível, baixo ainda oculto.
columns = 42
middle_row = (560 / 1160 - .025) / .975
opening(5.8 + 3.15 * (20 + middle_row * .8 + .1) / columns + .12)
order = render(1, 11)
assert order.getpixel((100, 0))[0] > order.getpixel((900, 0))[0]
assert order.getpixel((500, 0))[1] > order.getpixel((500, 0))[0] > order.getpixel((500, 0))[2]
assert 0 < order.getpixel((500, 0))[0] < 255
for seconds in (.5, 2.0, 5.0, 6.5, 7.5, 9.3, 10.5, 12.0, 13.5):
    opening(seconds)
    render(1).save(args.output_dir / f'intro-{seconds:.1f}.png')
# Ondulação real por letra durante a pausa do título, sem deslocar o prompt.
letter_tops = [[] for _ in range(5)]
title_frames = []
for seconds in (5.5, 6.0, 6.5, 7.0):
    opening(seconds)
    title = render(seconds, 13).convert('RGB')
    title_frames.append(title)
    unit = min(w * .84 / 50, h / 65)
    for letter, (start, end) in enumerate(((0,11), (11,22), (22,32), (32,43), (43,50))):
        left = round(w / 2 + (start - 25) * unit)
        right = round(w / 2 + (end - 25) * unit)
        crop = title.crop((left, 85, right, 255))
        box = crop.point(lambda value: 255 if value > 80 else 0).getbbox()
        assert box is not None
        letter_tops[letter].append(box[1])
assert all(max(tops) - min(tops) >= 2 for tops in letter_tops), letter_tops
assert ImageChops.difference(title_frames[0], title_frames[-1]).getbbox()
title_frames[1].save(args.output_dir / 'skadi-title.png')

# Texto permanece legível durante a revelação.
opening(8.5)
terminal = Image.new('RGB', (w, h), (8, 25, 37))
ImageDraw.Draw(terminal).text((45, 250), '$ echo posso digitar', fill=(212, 238, 245), font=font)
with_prompt = render(1, terminal=terminal)
ink_pixels = [(x, y) for y in range(250, 280) for x in range(45, 300)
              if terminal.getpixel((x, y))[0] > 200]
assert ink_pixels
for position in ink_pixels:
    assert max(abs(a - b) for a, b in zip(with_prompt.getpixel(position), terminal.getpixel(position))) <= 1
with_prompt.save(args.output_dir / 'intro-prompt.png')
opening(13.6)
assert render(1, 11).convert('RGB').getextrema() == ((255, 255),) * 3
# O título continua visível mesmo muito depois da revelação terminar.
assert render(120, 13).convert('RGB').getbbox()
f3(at('iPalette[250]'), 18 / 255, 128 / 255, 0)
assert render(120, 13).convert('RGB').getbbox()
f3(at('iPalette[250]'), 18 / 255, 1, 1)
assert render(120, 13).convert('RGB').getbbox() is None
finished = render(1)
f3(at('iPalette[251]'), 198 / 255, 198 / 255, 198 / 255)
normal = render(1)
finished.save(args.output_dir / 'intro-finished.png')
normal.save(args.output_dir / 'intro-normal.png')
difference = ImageChops.difference(finished, normal).convert('RGB')
assert max(v[1] for v in difference.getextrema()) <= 1, difference.getextrema()

set_seed(192837)
before, after = render(27.999), render(28.001)
assert max(ImageStat.Stat(ImageChops.difference(before, after)).mean) < 0.5
assert render(30).tobytes() == render(30).tobytes()
first = render(0)
set_seed(918273)
assert ImageChops.difference(first, render(0)).convert('RGB').getbbox()
set_seed(192837)
assert first.tobytes() == render(0).tobytes()

# Valida a busca inversa contra uma busca larga, incluindo as novas cristas.
for check_time in (0, 4):
    difference = ImageChops.difference(render(check_time), render(check_time, 12)).convert('RGB')
    assert max(ImageStat.Stat(difference).mean) < .06, ImageStat.Stat(difference).mean
    assert max(v[1] for v in difference.getextrema()) < 16, difference.getextrema()

# A mesma textura estática anima pelo tempo, sem atualizações de PS1.
for marker_type, peak in ((0, .6), (32, 5.6), (64, 5.6), (96, 3.7)):
    terminal = Image.new('RGB', (w, h), (8, 25, 37))
    ImageDraw.Draw(terminal).text((44, 130), '@', (32, 255, marker_type), font=font)
    masks, brightness = [], []
    for seconds in (0, peak):
        frame = render(seconds, terminal=terminal).convert('RGB')
        threshold = ((126 if seconds == 0 else 255) + 25) / 2 if marker_type == 96 else 100
        pixels = [(x, y) for y in range(125, 161) for x in range(44, 58)
                  if frame.getpixel((x, y))[1] > threshold]
        masks.append(set(pixels))
        brightness.append(sum(frame.getpixel(p)[1] for p in pixels))
    if marker_type == 96:
        assert masks[0] == masks[1], '@ must stay on its baseline'
        assert brightness[1] > brightness[0] * 1.5
    else:
        assert min(y for _, y in masks[0]) - min(y for _, y in masks[1]) == 3
    # Cursor em outra linha, no início ou oculto não revela cores marcadoras.
    expected = render(peak, terminal=terminal)
    f4(at('iCurrentCursor'), 0, 300, 10, 26)
    i1(at('iCursorVisible'), 0)
    assert expected.tobytes() == render(peak, terminal=terminal).tobytes()
    f4(at('iCurrentCursor'), 600, 570, 10, 26)
    i1(at('iCursorVisible'), 1)

# Brilho da tinta: curto, localizado e independente da cor de sintaxe.
terminal = Image.new('RGB', (w, h), (8, 25, 37))
painter = ImageDraw.Draw(terminal)
painter.rectangle((590, 138, 597, 149), fill=(150, 190, 200))
f4(at('iPreviousCursor'), 590, 570, 10, 26)
f1(at('iTimeCursorChange'), 10)
rest = render(11, terminal=terminal)
f1(at('iTimeCursorChange'), 10.98)
bright = render(11, terminal=terminal)
assert bright.getpixel((594, 143))[0] > rest.getpixel((594, 143))[0] + 5
assert bright.getpixel((594, 170)) == rest.getpixel((594, 170)), 'halo must stay compact'
f1(at('iTimeCursorChange'), 10.5)
assert render(11, terminal=terminal).getpixel((594, 143)) == rest.getpixel((594, 143))
f1(at('iTimeCursorChange'), 0)
f4(at('iPreviousCursor'), 0, 0, 0, 0)

# Todas as letras de comandos reconhecidos ganham realce, histórico não.
for color in ((95,233,211), (104,212,254), (131,185,254)):
    terminal = Image.new('RGB', (w,h), (8,25,37))
    painter = ImageDraw.Draw(terminal)
    for x in (420, 435, 450):
        painter.rectangle((x,138,x+6,149), fill=color)
        painter.rectangle((x,100,x+6,111), fill=color)
    lit = render(11, terminal=terminal)
    for x in (420, 435, 450):
        assert lit.getpixel((x+3,143))[0] > color[0]
        assert lit.getpixel((x+3,105))[:3] == color

# O halo do @ alcança o fundo fora da tinta, sem deslocar a letra.
terminal = Image.new('RGB', (w,h), (8,25,37))
ImageDraw.Draw(terminal).rectangle((45,140,48,149), fill=(32,255,96))
base = render(2.95)
lit = render(2.95, terminal=terminal)
assert lit.getpixel((42,144))[1] > base.getpixel((42,144))[1]
assert lit.getpixel((30,144)) == base.getpixel((30,144))
lit.save(args.output_dir / 'at-halo.png')

# Ordem temporal e continuidade a 60 Hz usando o próprio shader.
last = None
for frame_number in range(721):
    t = frame_number / 60
    state = render(t, 14).convert('RGB')
    # No espaço de imagem: caminho em cima, @ no meio, usuário embaixo.
    user = [state.getpixel((x, h-1))[1] for x in range(0,w,20)]
    at_glow = state.getpixel((0,h//2))
    path = [state.getpixel((x,0))[1] for x in range(0,w,20)]
    assert at_glow[0] == 0
    phase = t % 12
    if phase >= 3.2:
        assert max(user) == 0
    if phase < 5.0:
        assert max(path) == 0
    if phase < 2.6 or phase >= 5.0:
        assert at_glow[1] == 0
    if 3.6 <= phase <= 3.8:
        assert at_glow[1] == 255  # breve patamar máximo
    if 2.7 <= phase <= 3.0:
        assert max(user) > 0 and at_glow[1] > 0  # última letra descendo
    if 5.1 <= phase <= 5.5:
        assert max(path) > 0 and at_glow[1] == 0  # só passa depois de apagar
    values = user + [at_glow[1]] + path
    if last is not None:
        assert max(abs(a-b) for a,b in zip(last, values)) <= 20, (t, values)
    last = values
assert max(last) == 0

# Movimento próprio da água em três eixos, mesmo sem baleia presente.
orbital = [render(t, 3).getpixel((0, 0)) for t in (0, 1, 2, 3, 4, 5, 6)]
ranges = [max(p[channel] for p in orbital) - min(p[channel] for p in orbital)
          for channel in range(3)]
assert ranges[0] + ranges[1] > 5 and ranges[2] > 5, orbital

# Contato com corpo separado: a água abre, não penetra e fecha depois.
metadata = render(0, 2).getpixel((0, 0))
delay = metadata[0] / 255 * 32
rest = render(0, 1).getpixel((0, 0))
pushed = render(delay + 7, 1).getpixel((0, 0))
returned = render(delay + 30, 1).getpixel((0, 0))
assert abs(pushed[0] - rest[0]) + abs(pushed[1] - rest[1]) > 4, (rest, pushed)
assert returned == rest, (rest, returned)
for phase in (3, 6, 9, 12, 15):
    assert render(delay + phase, 5).getchannel('R').getbbox() is None, phase
start, end = render(delay + 4, 4).getpixel((0,0)), render(delay + 12, 4).getpixel((0,0))
assert abs(end[0] - start[0]) > 10, (start, end)

# Não freia ao respirar nem ao desaparecer: avanço contínuo nas duas direções.
for seed in (192837, 918273, 432198, 712345):
    set_seed(seed)
    onset = render(0, 2).getpixel((0, 0))[0] / 255 * 32
    motion = [render(onset + phase, 10).getpixel((0, 0))
              for phase in (3, 5, 6, 7, 8, 10, 12, 14, 16)]
    assert min(p[0] / 255 * 80 for p in motion) > 26, motion
    assert motion[-1][0] > motion[2][0], motion
    assert motion[4][1] > motion[5][1] > motion[6][1] > motion[7][1], motion
set_seed(192837)

# Forma assimétrica e flexão real: a traseira muda de curvatura mais que a cabeça.
poses = [render(delay + phase, 6).getpixel((0, 0)) for phase in (4, 5, 6, 7, 8, 9, 10)]
rear_range = max(p[0] for p in poses) - min(p[0] for p in poses)
head_range = max(p[1] for p in poses) - min(p[1] for p in poses)
assert rear_range > max(6, head_range * 2), poses
widths = render(delay + 6, 7).getpixel((0, 0))
assert widths[0] > widths[1] * 2 and widths[2] > 10, widths

# 288 partículas pequenas, com 192 de vapor e 96 gotículas.
particles = render(delay + 6, 8)
values = [particles.getpixel((int((i + .5) / 288 * w), 0)) for i in range(288)]
assert sum(p[1] > 0 for p in values) >= 280
assert sum(p[2] > 128 for p in values) == 192
assert max(p[0] / 255 * 2 for p in values) < .65
spray_early = render(delay + 6.5, 9).getpixel((0,0))
spray_late = render(delay + 7.2, 9).getpixel((0,0))
assert spray_late[0] < spray_early[0], (spray_early, spray_late)
assert spray_late[1] > spray_early[1], (spray_early, spray_late)
assert render(delay + 10, 8).getchannel('G').getbbox() is None

# Quatro sessões: corpo independente avança, respira e afunda, sem cauda.
contact = Image.new('RGB', (1600, 1120))
signatures = []
for encounter, seed in enumerate((192837, 918273, 432198, 712345)):
    set_seed(seed)
    metadata = render(0, 2).getpixel((0, 0))
    delay = metadata[0] / 255 * 32
    signatures.append(metadata[:3])
    for index, (phase, label) in enumerate(((3, 'emergindo'), (6, 'respirando'), (12, 'avancando'), (25, 'agua-fechando'))):
        frame = render(delay + phase).convert('RGB')
        frame.save(args.output_dir / f'mesh-{encounter}-{label}.png')
        thumb = frame.resize((400, 280))
        ImageDraw.Draw(thumb).text((8, 8), f'seed {seed}: {label}', fill='white')
        contact.paste(thumb, (index * 400, encounter * 280))
assert len(set(signatures)) == 4
contact.save(args.output_dir / 'swimming-contact.png')

set_seed(192837)
metadata = render(0, 2).getpixel((0, 0))
delay = metadata[0] / 255 * 32
if not args.skip_animation:
    frames = [render(delay + step * 0.25).convert('RGB').resize((800, 560)) for step in range(121)]
    frames[0].save(args.output_dir / 'swimming.gif', save_all=True, append_images=frames[1:], duration=250, loop=0)
print('OK: anatomia, flexão, 288 partículas, contato com água, movimento, seed e prompt.')
if not args.skip_animation:
    print('Prévia de QA (não usada pelo terminal):', args.output_dir / 'swimming.gif')
