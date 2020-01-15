#version 300 es

precision mediump float;

attribute vec3 vertex;
attribute vec3 normal;
attribute vec2 texcoord;

uniform vec3 unif[20];

out vec2 texcoordout;

void main(void) {
  float iScale = unif[16].b;
  texcoordout = texcoord;
  texcoordout.y = 1.0 - texcoordout.y;
  gl_Position = vec4(vertex,1.0);
  gl_Position.xy = (gl_Position.xy + (1. - 1./iScale)) * iScale;
}
