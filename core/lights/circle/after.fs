#version 300 es

precision mediump float;

uniform vec3 unif[20];

out vec4 fragColor;

void main() {
	vec2 iResolution = unif[16].rg;
	float iTime = unif[18].r;
	float bass = unif[19].r;

    vec2 uvmtp = (gl_FragCoord.xy - 0.5 * iResolution.xy) / iResolution.y;

    vec2 shake = vec2(sin(iTime*9.0), cos(iTime*5.0)) * 0.002;
    uvmtp += shake;

	// Lighten the screen when there is a lot of bass
    float bright_alpha = bass * 0.05;

    // Vignette
    float dark_alpha = -(1. - smoothstep(0.0, 1.0, 1.5 - length(uvmtp)));
	
	float alpha = bright_alpha + dark_alpha;
	fragColor = vec4(vec3(sign(alpha)), abs(alpha));
}
