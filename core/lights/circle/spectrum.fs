#version 300 es

precision mediump float;
// spectrum contains the spectrum history
// first row (y==0): current spectrum
// second row: spectrum one frame ago
// third row: spectrum two frames ago
// ...
uniform sampler2D spectrum;

uniform vec3 unif[20];

out vec4 fragColor;

// Radius of the circle
#define CIRCLE_RADIUS 0.12

// The size of the white line of the circle
#define CIRCLE_BORDER_SIZE 0.002

// Colors
#define SPECTRUM_COLOR_1 vec4(1.0, 1.0, 1.0, 1.0)
#define SPECTRUM_COLOR_2 vec4(1.0, 1.0, 0.0, 0.95)
#define SPECTRUM_COLOR_3 vec4(1.0, 0.5, 0.0, 0.9)
#define SPECTRUM_COLOR_4 vec4(1.0, 0.0, 0.0, 0.85)
#define SPECTRUM_COLOR_5 vec4(1.0, 0.2, 0.3, 0.8)
#define SPECTRUM_COLOR_6 vec4(1.0, 0.0, 1.0, 0.75)
#define SPECTRUM_COLOR_7 vec4(0.0, 0.0, 1.0, 0.7)
#define SPECTRUM_COLOR_8 vec4(0.0, 0.8, 1.0, 0.65)
#define SPECTRUM_COLOR_9 vec4(0.0, 1.0, 0.0, 0.6)

#define PI 3.14159265359
#define TWO_PI 6.28318530718

// Convert uv coordinates to polar coordinates
vec2 uv_to_polar(vec2 uv, vec2 p) {
    vec2 translated_uv = uv - p;
    
    // Get polar coordinates
    vec2 polar = vec2(atan(translated_uv.x, translated_uv.y), length(translated_uv));
    
    // Scale to a range of 0 to 1
    polar.s /= TWO_PI;
    polar.s += 0.5;
    
    return polar;
}

// Circle, using polar coordinates
#define circle_polar(len, r) smooth_circle_polar(len, r, 0.004)
float smooth_circle_polar(float len, float r, float smoothness) {
    float dist = len - r;
    float s = smoothness / 2.0;
    return 1.0 - smoothstep(r - s, r + s, dist);
}

// Scale to values higher than another value
float cut_lower(float v, float low) {
    return clamp((v - low) * 1.0 / (1.0 - low), 0.0, 1.0);
}

// Rotate a coordinate
vec2 rotate(vec2 uv, float angle) {
    float s = sin(angle);
    float c = cos(angle);
    vec2 new = uv * mat2(c, s, -s, c);
    return new;
}

// Calculate radius
float get_draw_radius(float x, float r, int fft_y) {
	float hist = float(fft_y) / float(unif[17].r);
    // Get FFT value
    float fft = texture2D(spectrum, vec2(x, hist)).r;
    
    // Calculate radius
    float radius = CIRCLE_RADIUS + r + fft * 0.07;
    
    // Clamp to the circle radius
    radius = clamp(radius, CIRCLE_RADIUS + r, 1.0);
    
    return radius;
}

void main() {
	vec2 iResolution = unif[16].rg;
	float iScale = unif[16].b;
	float iTime = unif[18].r;
	float time_delta = unif[18].g;
	float bass = unif[19].r;
	float extra = unif[19].g;

    vec2 uvmtp = (gl_FragCoord.xy - 0.5 * iResolution.xy) / iResolution.y;
	uvmtp *= iScale;

	// Shake the bubble
    vec2 shake = vec2(sin(iTime*9.0), cos(iTime*5.0)) * 0.002;
    uvmtp += shake;

	vec3 color = vec3(0, 0, 0);

	// Rotate the circle a bit
    uvmtp = rotate(uvmtp, sin(iTime * 1.5 + extra) * 0.005);
    
    // Shake the circle a bit
    vec2 circle_shake = vec2(cos(iTime*9.0 + extra*0.3), sin(iTime*9.0 + extra*0.3))*0.003;
    uvmtp += circle_shake;

    // Get polar coordinates for circle, shaking it a bit as well
	vec2 polar = uv_to_polar(uvmtp, vec2(0.0, 0.0));

    float fft_x = polar.s;
    // Mirror
    fft_x *= 2.0;
    if (fft_x > 1.0) {
        fft_x = 2.0 - fft_x;
    }
    
    // Invert (low frequencies on top)
    fft_x = 1.0 - fft_x;

	// How much the circle should grow
	float r = bass * 0.05;

    // Draw spectrum
    color = mix(color, SPECTRUM_COLOR_9.rgb, smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 4), 0.006) * SPECTRUM_COLOR_8.a);
    color = mix(color, SPECTRUM_COLOR_7.rgb, smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 3), 0.0055) * SPECTRUM_COLOR_6.a);
    color = mix(color, SPECTRUM_COLOR_5.rgb, smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 2), 0.005) * SPECTRUM_COLOR_4.a);
    color = mix(color, SPECTRUM_COLOR_3.rgb, smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 1), 0.0045) * SPECTRUM_COLOR_2.a);
    color = mix(color, SPECTRUM_COLOR_1.rgb, smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 0), 0.004) * SPECTRUM_COLOR_1.a);
	
	// if there is still black in the color, it should be transparent
	float alpha = color.x + color.y + color.y;
	alpha = sqrt(alpha);
	fragColor = vec4(color, alpha);

	// looks different, but also nice :D
	/*if (alpha == 1.) {
		alpha = 0.;
	}
	fragColor = vec4(alpha, 0, 0, 1);*/
}
