#version 300 es

precision mediump float;

uniform sampler2D logo;
uniform vec3 unif[20];

out vec4 fragColor;

// Radius of the circle
#define CIRCLE_RADIUS 0.12

// The size of the white line of the circle
#define CIRCLE_BORDER_SIZE 0.002

#define TWO_PI 6.28318530718

vec2 rotate(vec2 uv, float angle) {
    float s = sin(angle);
    float c = cos(angle);
    vec2 new = uv * mat2(c, s, -s, c);
    return new;
}

// Circle, using polar coordinates
#define circle_polar(len, r) smooth_circle_polar(len, r, 0.004)
float smooth_circle_polar(float len, float r, float smoothness) {
    float dist = len - r;
    float s = smoothness / 2.0;
    return 1.0 - smoothstep(r - s, r + s, dist);
}

vec2 uv_to_polar(vec2 uv, vec2 p) {
    vec2 translated_uv = uv - p;
    
    // Get polar coordinates
    vec2 polar = vec2(atan(translated_uv.x, translated_uv.y), length(translated_uv));
    
    // Scale to a range of 0 to 1
    polar.s /= TWO_PI;
    polar.s += 0.5;
    
    return polar;
}

vec2 polar_to_uv(vec2 polar, vec2 p) {
	float s = polar.s;
	float t = polar.t;
    // Scale to a range of -pi to pi
    s -= 0.5;
    s *= TWO_PI;
    
	vec2 uv = vec2(t * sin(s), t * cos(s));
	uv = uv + p;
    return uv;
}

void main() {
	vec2 iResolution = unif[16].rg;
	float FFT_HIST = unif[17].r;
	float iTime = unif[18].r;
	float bass = unif[19].r;
	float extra = unif[19].g;

    vec2 uvmtp = (gl_FragCoord.xy - 0.5 * iResolution.xy) / iResolution.y;

	// Shake the bubble
    vec2 shake = vec2(sin(iTime*9.0), cos(iTime*5.0)) * 0.002;
    uvmtp += shake;

	// Rotate the circle a bit
    uvmtp = rotate(uvmtp, sin(iTime * 1.5 + extra) * 0.005);
    
    // Shake the circle a bit
    vec2 circle_shake = vec2(cos(iTime*9.0 + extra*0.3), sin(iTime*9.0 + extra*0.3))*0.003;
    uvmtp += circle_shake;

    // Get polar coordinates for circle, shaking it a bit as well
	vec2 polar = uv_to_polar(uvmtp, vec2(0.0, 0.0));

	float r = bass * 0.05;
	float full_radius = CIRCLE_RADIUS + r - CIRCLE_BORDER_SIZE;

	float alpha = circle_polar(polar.t, full_radius);

	vec2 logo_uv = polar_to_uv(polar, vec2(0.5, 0.5));
	// scale the logo and translate it into the middle of the screen
	logo_uv.y = 1. - logo_uv.y;
	float scale = 0.35 / full_radius;
	logo_uv *= scale;
	logo_uv = logo_uv - 0.5*(scale-1.);

	// use the cartesian coordinates as fake normals for a spherical look
	vec3 normal = vec3(logo_uv - 0.5, 1);
	// increase curvature of the faked sphere
	normal.xy *= 0.5;
	normal = normalize(normal);
	vec3 light = normalize(vec3(1, -1, 1));
	vec3 reflected = normalize(2.0 * dot(normal, light) * normal - light);
	// center the logo_uv to get faked button like normals
	float intensity = 0.75;
	float shinyness = 8.;
	vec3 specular = vec3(1) * intensity * pow(max(0.0, dot(vec3(0, 0, 1), reflected)), shinyness);
	vec4 color = vec4(specular, alpha);
	
	vec2 texture_uv = logo_uv;
	texture_uv.y -= 0.5 / 256.;
	texture_uv.y = texture_uv.y / (256. + FFT_HIST) * 256.;
	vec4 tex_color = texture(logo, texture_uv).rgba;

	// only add the texture where uv in [0,1]² to prevent artifacts from mipmapping.
	float in_texture = 1.;
	in_texture = in_texture * step(0., logo_uv.x);
	in_texture = in_texture * (1. - step(1., logo_uv.x));
	in_texture = in_texture * step(0., logo_uv.y);
	in_texture = in_texture * (1. - step(1., logo_uv.y));
	float small_circle = circle_polar(polar.t, full_radius * 0.9);
	in_texture = min(in_texture, small_circle);
	color += tex_color * in_texture;

	fragColor = color;
}
