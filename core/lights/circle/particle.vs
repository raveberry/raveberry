#version 300 es

#define NUM_PARTICLES 200

precision mediump float;

in vec3 vertex;
in vec2 texcoord;

uniform vec3 unif[20];
uniform vec4 positions[NUM_PARTICLES];

out vec2 uv;
out float age;

void main(void) {
	uv = texcoord;
	float PARTICLE_SPAWN_Z = unif[17].b;

	float iScale = unif[16].b;
	float time_elapsed = unif[18].r;
	float iTime = time_elapsed;
    vec2 shake = vec2(sin(iTime*9.0), cos(iTime*5.0)) * 0.002;

	// the modelmatrix in camera coords, calculated with the static default camera. Only the rightmost column changes for different particles
	mat4 cam_mtrx = mat4(1.3579952, 0., 0., 0.,
			0., 2.4142137, 0., 0.,
			0., 0., 1.002002, 1.,
			0., 0., 1., 0.1);
	vec4 projected = positions[gl_InstanceID] * cam_mtrx;

	mat4 m1 = mat4(1.3579952, 0., 0., 0.,
			0., 2.4142137, 0., 0.,
			0., 0., 1.002002, 1.,
			projected);

	age = positions[gl_InstanceID].z / PARTICLE_SPAWN_Z;
	gl_Position = m1 * vec4(vertex, 1.0);
	gl_Position.z = 0.;
	gl_Position.xy += shake;
	gl_Position.xy /= iScale;
}
