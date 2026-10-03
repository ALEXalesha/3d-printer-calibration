// Loads the whole core into Node (the same files the page loads with <script>).
'use strict';
const path = require('path');

const CORE = path.join(__dirname, '..', '..', 'web', 'js', 'core');
for (const f of ['data', 'num', 'templates', 'profiles', 'gcode_sim', 'params', 'generator', 'check', 'importer', 'preview']) {
  require(path.join(CORE, f + '.js'));
}
module.exports = globalThis.C3D;
