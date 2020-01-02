#version 300 es

precision mediump float;

uniform sampler2D tex0;
uniform vec3 unif[20];
// see docstring Shape

in vec2 texcoordout;

out vec4 fragColor;

void main(void) {
	fragColor = vec4(texture2D(tex0, texcoordout).rgb, 1);
	//fragColor = vec4(vec3(0), 1);
}


