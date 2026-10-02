/* Dependency-free regressions of actual app functions, with browser I/O stubs. */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'docs', 'app.js'), 'utf8');
const declarations = [...source.matchAll(/^(?:async )?function (\w+)\(/gm)];

function loadFunctions(names, stubs) {
  const context = vm.createContext(stubs);
  for (const name of names) {
    const index = declarations.findIndex(match => match[1] === name);
    assert.notEqual(index, -1, `Missing app function: ${name}`);
    const start = declarations[index].index;
    const end = declarations[index + 1]?.index ?? source.length;
    vm.runInContext(source.slice(start, end), context, {filename: `docs/app.js:${name}`});
  }
  return context;
}

function elementsDocument() {
  const elements = new Map();
  return {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, {value: '', textContent: '', dataset: {}});
      return elements.get(id);
    },
  };
}

async function checkFrameExports() {
  const document = elementsDocument();
  const state = {result: {history: [{year: 0}, {year: 2}, {year: 4}]}, frame: null, playback: 7};
  const exports = [], cleared = [];
  let rendered = '', pendingImage = false;
  document.createElement = name => name === 'canvas' ? {
    getContext() { return {fillRect() {}, drawImage(image) { this.image = image; }}; },
    toBlob(callback) { queueMicrotask(() => callback({})); },
  } : {
    click() { exports.push({name: this.download, xml: rendered}); },
  };
  const context = loadFunctions(['exportTimelinePng', 'exportBatchPng'], {
    worldState: state, document,
    renderWorldTimeline() { rendered = `<svg frame="${state.frame}"></svg>`; },
    clearInterval(id) { cleared.push(id); },
    XMLSerializer: class { serializeToString() { return rendered; } },
    Image: class {
      set src(value) {
        assert.equal(pendingImage, false, 'Frame conversion must finish before starting the next');
        pendingImage = true;
        queueMicrotask(() => { pendingImage = false; this.onload(); });
      }
    },
    URL: {createObjectURL() { return 'blob:frame'; }, revokeObjectURL() {}},
  });
  await context.exportBatchPng();
  assert.deepEqual(exports, [0, 1, 2].map(frame => ({
    name: `population_simu_frame_${frame}.png`, xml: `<svg frame="${frame}"></svg>`,
  })));
  assert.equal(state.frame, null, 'Restore the previous frame after export');
  assert.equal(state.exportingFrames, false);
  assert.equal(document.getElementById('timeline-batch-png').disabled, false);
  assert.deepEqual(cleared, [7]);

  state.frame = 1;
  const pending = context.exportTimelinePng();
  state.frame = 99;
  await pending;
  assert.equal(exports.at(-1).name, 'population_simu_frame_1.png', 'PNG filename must retain the captured frame');

  context.exportTimelinePng = async () => { throw new Error('conversion failed'); };
  await assert.rejects(context.exportBatchPng(), /conversion failed/);
  assert.equal(state.frame, 99);
  assert.equal(state.exportingFrames, false);
  assert.equal(document.getElementById('timeline-batch-png').disabled, false);
}

function checkCompletedWorldParameters() {
  const document = elementsDocument(), callbacks = [], runs = [], downloads = [];
  const controls = {years: 4, seed: 17, housingPressure: 0.2};
  const state = {result: {}, frame: 1, playback: null, uncertainty: {old: true}};
  const context = loadFunctions(['runWorldExperiment', 'runWorldUncertainty', 'exportReplay'], {
    worldState: state, document,
    worldParams() { return controls; },
    scheduleUi(callback) { callbacks.push(callback); },
    simulateWorld(params) {
      runs.push({...params});
      return {history: [{year: 0, families: 100}, {year: params.years, families: 110}]};
    },
    renderWorld() { assert.equal(state.uncertainty, null, 'New run must clear old bands before render'); },
    renderWorldTimeline() {}, clearInterval() {},
    downloadText(name, text) { downloads.push({name, text}); },
  });
  context.runWorldExperiment();
  controls.years = 60; controls.seed = 99; controls.housingPressure = 0.95;
  callbacks.shift()();
  assert.deepEqual(runs[0], {years: 4, seed: 17, housingPressure: 0.2});
  assert.equal(state.parameters.seed, 17);
  assert.equal(state.uncertainty, null);
  context.worldParams = () => { throw new Error('Completed results must not read edited controls'); };
  context.runWorldUncertainty();
  assert.equal(runs.length, 21);
  assert.ok(runs.slice(1).every(params => params.years === 4 && params.housingPressure === 0.2));
  assert.deepEqual(runs.slice(1).map(params => params.seed), Array.from({length: 20}, (_, i) => 18 + i));
  context.exportReplay();
  assert.equal(downloads[0].name, 'population_simu_replay_17.html');
  assert.ok(downloads[0].text.includes('"parameters":{"years":4,"seed":17,"housingPressure":0.2}'));
}

async function checkPythonCsvSnapshot() {
  const document = elementsDocument(), requests = [], downloads = [];
  document.getElementById('engine-scenario').value = 'completed.json';
  document.body = {appendChild() {}};
  document.createElement = () => ({click() { downloads.push(this.download); }, remove() {}});
  const controls = {years: 4, seed: 17};
  const state = {data: null, parameters: null, selectedCountry: null};
  const payload = {
    scenario: 'completed.json', history: [{country: 'TEST'}],
    snapshot: {year: 2004, population: 3, households: 1, clans: 1, countries: {}},
  };
  const context = loadFunctions(['runLocalEngine', 'downloadPythonCsv'], {
    pythonState: state, document, worldParams() { return controls; },
    localApiUrl(endpoint) { return `http://localhost/${endpoint}`; },
    async fetch(url) {
      requests.push(url);
      return {ok: true, async json() { return payload; }, async blob() { return {}; }};
    },
    renderPythonResults() {},
    URL: {createObjectURL() { return 'blob:csv'; }, revokeObjectURL() {}},
  });
  const pending = context.runLocalEngine();
  controls.years = 60; controls.seed = 99;
  document.getElementById('engine-scenario').value = 'unrun.json';
  await pending;
  context.worldParams = () => { throw new Error('CSV must use the completed run'); };
  await context.downloadPythonCsv();
  assert.deepEqual(requests, [
    'http://localhost/api/run?scenario=completed.json&years=4&seed=17',
    'http://localhost/api/run.csv?scenario=completed.json&years=4&seed=17',
  ]);
  assert.deepEqual(downloads, ['completed_annual.csv']);
  assert.equal(state.parameters.scenario, 'completed.json');
  assert.equal(state.parameters.seed, 17);
}

async function main() {
  await checkFrameExports();
  checkCompletedWorldParameters();
  await checkPythonCsvSnapshot();
  console.log('browser_regressions_ok groups=3 (frames, completed-world parameters/bands, Python CSV)');
}

main().catch(error => { console.error(error); process.exitCode = 1; });
