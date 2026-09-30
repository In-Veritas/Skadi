// Ghostty 1.3+: aurora discreta, partículas lentas e rastro azul/turquesa.
// Ajustes: AMBIENT_STRENGTH, STAR_STRENGTH e TRAIL_SECONDS abaixo.
// Usa a cor de fundo para proteger texto, seleções e painéis de aplicativos.
// alpha-blending = native na configuração mantém as cores em sRGB.
const float AMBIENT_STRENGTH = 0.075;
const float STAR_STRENGTH = 0.18;
const float TRAIL_SECONDS = 0.30;
const vec3 OCEAN_BLUE = vec3(0.20, 0.52, 1.00);
const vec3 TURQUOISE = vec3(0.15, 0.90, 0.80);

float randomCell(vec2 p) {
    vec3 q = fract(vec3(p.xyx) * 0.1031);
    q += dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}

vec2 segmentDistance(vec2 p, vec2 a, vec2 b) {
    vec2 ab = b - a;
    float along = clamp(dot(p - a, ab) / max(dot(ab, ab), 0.001), 0.0, 1.0);
    return vec2(length(p - a - ab * along), along);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    vec4 terminal = texture(iChannel0, uv);
    vec3 result = terminal.rgb;
    // Tolerância para a imagem escura de fundo com opacidade de 18%.
    float backgroundMask = 1.0 - smoothstep(
        0.040, 0.240, length(terminal.rgb - iBackgroundColor));

    // Duas faixas difusas movem-se devagar atrás do conteúdo.
    if (backgroundMask > 0.001) {
        float t = iTime * 0.12;
        float waveA = 0.32 + 0.13 * sin(uv.x * 4.0 + t)
                           + 0.045 * sin(uv.x * 9.0 - t * 0.7);
        float waveB = 0.68 + 0.15 * sin(uv.x * 3.3 - t * 0.65);
        float ribbonA = exp(-pow((uv.y - waveA) / 0.17, 2.0));
        float ribbonB = exp(-pow((uv.y - waveB) / 0.23, 2.0));
        vec3 atmosphere = OCEAN_BLUE * ribbonA * 0.65 + TURQUOISE * ribbonB * 0.38;

        // Uma partícula por célula; sem texturas extras ou histórico de frames.
        vec2 grid = fragCoord / 115.0;
        vec2 cell = floor(grid);
        float seed = randomCell(cell);
        vec2 center = vec2(randomCell(cell + 7.4), randomCell(cell + 23.1));
        center = 0.22 + center * 0.56;
        center += 0.10 * vec2(sin(t + seed * 40.0), cos(t * 0.8 + seed * 30.0));
        float d = length((fract(grid) - center) * 115.0);
        float twinkle = 0.45 + 0.55 * pow(0.5 + 0.5 * sin(iTime * 0.8 + seed * 50.0), 2.0);
        float star = (exp(-d * d / 2.0) + 0.10 * exp(-d * d / 35.0))
                   * twinkle * step(0.48, seed);
        result += backgroundMask * (atmosphere * AMBIENT_STRENGTH
                  + mix(TURQUOISE, OCEAN_BLUE, seed) * star * STAR_STRENGTH);
    }

    // Respeita cursores ocultos e evita rastros ao voltar de outra janela.
    float age = max(iTime - iTimeCursorChange, 0.0);
    if (iFocus > 0 && iCursorVisible > 0 && age < TRAIL_SECONDS
        && iTimeCursorChange >= iTimeFocus) {
        vec2 current = iCurrentCursor.xy + iCurrentCursor.zw * vec2(0.5, -0.5);
        vec2 previous = iPreviousCursor.xy + iPreviousCursor.zw * vec2(0.5, -0.5);
        vec2 movement = current - previous;
        float travel = length(movement);
        float height = max(iCurrentCursor.w, 12.0);

        // Saltos entre linhas não riscam a tela inteira.
        if (travel > 0.5 && travel < 180.0 && abs(movement.y) < height * 0.6) {
            float progress = clamp(age / TRAIL_SECONDS, 0.0, 1.0);
            float fade = pow(1.0 - progress, 2.0);
            vec2 direction = movement / travel;
            vec2 tail = previous - direction * height * 0.65;
            tail = mix(tail, current, 1.0 - pow(1.0 - progress, 3.0));
            vec2 scale = vec2(1.0, 0.42);
            vec2 trail = segmentDistance(
                fragCoord * scale, tail * scale, current * scale);
            float distanceToTrail = trail.x;
            float core = exp(-distanceToTrail * distanceToTrail / 8.0);
            float glow = exp(-distanceToTrail * distanceToTrail / 75.0);
            vec3 trailColor = mix(OCEAN_BLUE, TURQUOISE, trail.y);
            result += trailColor * (0.42 * core + 0.14 * glow)
                    * fade * backgroundMask;
        }
    }

    fragColor = vec4(clamp(result, 0.0, 1.0), terminal.a);
}
