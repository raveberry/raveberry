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

#define HISTORY_USED 5.0

#define PI 3.14159265359
#define TWO_PI 6.28318530718

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

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
float get_draw_radius(float fft_x, float r, int fft_y, float base) {
	float FFT_HIST = unif[17].r;
	float hist = float(fft_y * 2) / FFT_HIST;

	hist += 0.5 / FFT_HIST;
	hist = hist / (256. + FFT_HIST) * FFT_HIST + 256. / (256. + FFT_HIST);
    float fft = texture(spectrum, vec2(fft_x, hist)).r;

	// how much of the spectrum is white. the rest is colorful border
	float white = 0.5;
	float max_height = (1.0 - white) * float(fft_y) / HISTORY_USED + white;

	// how much the current color (=history value) is under or over the current (white) spectrum
	float behind = base - fft;
	behind = min(behind, 0.);
	float ahead = fft - base;
	ahead = max(ahead, 0.);
	
	// if the current color is bigger than white use its actual value to have it fall down after a peak
	float drawn = CIRCLE_RADIUS + r + fft * 0.07 * max_height * 1.1;
	// if the current color is smaller than white shove it in front of white so it can still be seen
	float shoved = CIRCLE_RADIUS + r + base * 0.07 * max_height * (1. + 0.1 * behind);
	// mix the two values to hide the transition
	float radius = mix(shoved, drawn, ahead * 0.75);
    
    return radius;
}

void main() {
	vec2 iResolution = unif[16].rg;
	float iTime = unif[18].r;
	float time_delta = unif[18].g;
	float FFT_HIST = unif[17].r;
	float bass = unif[19].r;
	float extra = unif[19].g;

    vec2 uvmtp = (gl_FragCoord.xy - 0.5 * iResolution.xy) / iResolution.y;

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

	const float saturation = 1.0, value = 0.8;
    float scaled = extra * 0.05;
	// lower background: hsv2rgb(vec3((iTime*0.15 - scaled) * 0.1, saturation, value));
    // upper background: hsv2rgb(vec3((iTime*0.25 + scaled) * 0.02, saturation, value));
    vec3 recent_color = hsv2rgb(vec3((iTime*0.15 - scaled) * 0.1 + 0.33, saturation, value));
    vec3 past_color = hsv2rgb(vec3((iTime*0.15 - scaled) * 0.1, saturation, value));

	fft_x += 1. / 256.;
	fft_x *= (199. - 2.*2. - 2.) / 256.;
	float now = 0.5 / FFT_HIST;
	now = now / (256. + FFT_HIST) * FFT_HIST + 256. / (256. + FFT_HIST);
    float base = texture(spectrum, vec2(fft_x, now)).r;

	// with more than 5 colors performance drops significantly on target resolution
	/*color = mix(color, mix(past_color, recent_color, 0.00), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 8, base), 0.00625) * 0.60);
	color = mix(color, mix(past_color, recent_color, 0.14), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 7, base), 0.00600) * 0.65);
	color = mix(color, mix(past_color, recent_color, 0.29), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 6, base), 0.00575) * 0.70);
	color = mix(color, mix(past_color, recent_color, 0.00), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 5, base), 0.00550) * 0.75);*/
	color = mix(color, mix(past_color, recent_color, 0.25), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 4, base), 0.00525) * 0.80);
	color = mix(color, mix(past_color, recent_color, 0.50), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 3, base), 0.00500) * 0.85);
	color = mix(color, mix(past_color, recent_color, 0.75), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 2, base), 0.00475) * 0.90);
	color = mix(color, mix(past_color, recent_color, 1.00), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 1, base), 0.00450) * 0.95);
	color = mix(color,                       vec3(1, 1, 1), smooth_circle_polar(polar.t, get_draw_radius(fft_x, r, 0, base), 0.00400) * 1.00);

	// if there is still black in the color, it should be transparent
	float alpha = color.x + color.y + color.y;
	alpha = sqrt(alpha);
	fragColor = vec4(color, alpha);
}
