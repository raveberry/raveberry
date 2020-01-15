#version 300 es

#define NUM_PARTICLES 200
// How much impact the bass has on the particles
#define BASS_IMPACT_ON_PARTICLES 1.0

precision mediump float;

in vec3 vertex;
in vec2 texcoord;
in vec4 particle;

uniform vec3 unif[20];
//uniform vec4 particles[NUM_PARTICLES];
uniform mat4 modelviewmatrix[2];

out vec2 uv;
out float age;

void main(void) {
	uv = texcoord;
	float PARTICLE_SPAWN_Z = unif[17].b;

	float time_elapsed = unif[18].r;
	float bass_fraction = unif[19].b;
	float iTime = time_elapsed;
    vec2 shake = vec2(sin(iTime*9.0), cos(iTime*5.0)) * 0.002;

	float x = particle[0];
	float y = particle[1];
	float speed = particle[2];
	float start_z = particle[3];
	float avg_speed = bass_fraction * (speed + BASS_IMPACT_ON_PARTICLES) + (1. - bass_fraction) * speed;
	float z = start_z - (time_elapsed * (avg_speed));
	z = mod(mod(z, PARTICLE_SPAWN_Z + PARTICLE_SPAWN_Z), PARTICLE_SPAWN_Z);
	vec3 position = vec3(x, y, z);

	age = position.z / PARTICLE_SPAWN_Z;
	gl_Position = modelviewmatrix[1] * vec4(position + vertex, 1.0);
	gl_Position.z = 0.;
	gl_Position.xy += shake;

}
