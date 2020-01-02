#version 300 es

precision mediump float;

uniform vec3 unif[20];

// uv in [-1, 1]^2
in vec2 uv;
in float age;

out vec4 fragColor;

// Circle, using cartesian coordinates
float smooth_circle(vec2 p, float r, float smoothness) {
    float dist = length(p) - r;
    float s = smoothness / 2.0;
    return 1.0 - smoothstep(r - s, r + s, dist);
}

void main() {
	float PARTICLE_SPAWN_Z = unif[17].b;

	float brightness = smooth_circle(uv - 0.5, 0.1, 0.5);
	// decrease the brightness due to additive blending
	brightness *= 0.75;
	
	float age_factor = 1. - age;
	age_factor *= age_factor;
	fragColor = vec4(vec3(brightness * age_factor), 1);
	//fragColor = vec4(vec3(1. - age), 1);
}
