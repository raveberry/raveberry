import multi from '@rollup/plugin-multi-entry';
import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import inject from '@rollup/plugin-inject';

export default {
	input: './js/**/*.js',
	external: [
		'CSRF_TOKEN',
		'urls',
		'VOTING_SYSTEM',
		'ADMIN',
		'CONTROLS_ENABLED',
		'ADDITIONAL_KEYWORDS',
		'FORBIDDEN_KEYWORDS'
	],
	output: {
		file: './bundle.js',
		format: 'iife',
	},
	plugins: [multi(), nodeResolve(), commonjs(), inject({
		// define jQuery as a global because jquerykeyframes relies on it
		// but we cannot enforce that jquery is loaded beforehand
		jQuery: 'jquery',
	})],

};
