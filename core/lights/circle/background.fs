#version 300 es

precision mediump float;

uniform vec3 unif[20];

out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

// Draw the background
vec3 background(vec2 uv, float total_bass, float iTime) {
    const float saturation = 0.6, value = 0.7;
    
    // Cycle faster when there is a lot of bass
    float scaled = total_bass * 0.05;
    
    // Gradient of cycling hsv colors
    vec3 color = mix(hsv2rgb(vec3((iTime*0.25 + scaled) * 0.02, saturation, value)), hsv2rgb(vec3((iTime*0.15 - scaled) * 0.1, saturation, value)), uv.y + 0.1);
    return color;
}


void main() {
	vec2 iResolution = unif[16].rg;
	float iTime = unif[18].r;
	float alarm_factor = unif[18].b;
	float extra = unif[19].g;

	vec2 uv = gl_FragCoord.xy / iResolution.xy;

	// Shake the background
    vec2 shake = vec2(sin(iTime*9.0), cos(iTime*5.0)) * 0.002;
    uv    += shake;

	// Draw the background
	uv.y = 1. - uv.y;
	vec3 color = background(uv, extra, iTime);

	// change into a red background during the alarm
	color *= 1. - step(0.001, alarm_factor);
	color += vec3(alarm_factor, 0, 0);

	fragColor = vec4(color, 1);
}
