#version 300 es

precision mediump float;

in vec3 vertex;

uniform mat4 modelviewmatrix[3]; // [0] model movement in real coords, [1] in camera coords, [2] camera at light

void main(void) {
	float z = modelviewmatrix[0][3][2];
	gl_Position = vec4(vertex.xy, z, 1.0);
}
