const defaults = {
  resources: 100, generations: 4, trials: 1200, childcare: 45,
  grandparents: 55, dynamic: 40, need: 25, education: 55,
  welfare: 20, housing: 65, seed: 2026
};

const colors = {1: '#245d45', 2: '#c98c3a', 3: '#b44f38'};
const state = {results: null, selectedPlan: 2};
const ids = Object.keys(defaults);

function numberFormat(value) { return new Intl.NumberFormat('zh-CN').format(value); }
function percent(value, digits = 1) { return `${(value * 100).toFixed(digits)}%`; }
function clamp(value, low = 0, high = 1) { return Math.max(low, Math.min(high, value)); }
function sigmoid(value) { return 1 / (1 + Math.exp(-value)); }

function hashSeed(seed, plan) {
  let value = (Number(seed) || 1) ^ (plan * 0x9e3779b9);
  value = Math.imul(value ^ (value >>> 16), 0x21f0aaad);
  value = Math.imul(value ^ (value >>> 15), 0x735a2d97);
  return (value ^ (value >>> 15)) >>> 0;
}

function mulberry32(seed) {
  return function random() {
    let t = seed += 0x6d2b79f5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function normal(random) {
  const u = Math.max(1e-9, random());
  const v = Math.max(1e-9, random());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function readParams() {
  const raw = Object.fromEntries(ids.map(id => [id, Number(document.getElementById(id).value)]));
  return {
    ...raw,
    childcare: raw.childcare / 100,
    grandparents: raw.grandparents / 100,
    dynamic: raw.dynamic / 100,
    need: raw.need / 100,
    education: raw.education / 100,
    welfare: raw.welfare / 100,
    housing: raw.housing / 100
  };
}

function allocationProfile(count, parent, params, random) {
  const observed = Array.from({length: count}, () => clamp(0.52 * random() + 0.48 * random()));
  const mean = observed.reduce((sum, value) => sum + value, 0) / count;
  const weights = observed.map(signal => {
    const performance = Math.exp(1.8 * params.dynamic * (signal - mean));
    const need = 1 + params.need * Math.max(0, mean - signal);
    return performance * need;
  });
  const totalWeight = weights.reduce((sum, value) => sum + value, 0);
  const careCoverage = 1 - (1 - params.childcare) * (1 - params.grandparents * 0.72);
  const workRecovery = 0.78 + 0.28 * careCoverage;
  const familyPool = parent.resources * workRecovery + 15 * params.welfare;
  return observed.map((signal, index) => ({
    signal,
    potential: clamp(0.5 + 0.19 * normal(random)),
    share: weights[index] / totalWeight,
    investment: familyPool * weights[index] / totalWeight / (count ** 0.20),
    careCoverage
  }));
}

function makeChildren(count, parent, params, random) {
  return allocationProfile(count, parent, params, random).map(profile => {
    const publicInput = 0.22 * params.education + 0.12 * params.childcare;
    const grandparentInput = 0.08 * params.grandparents;
    const investmentReturn = 0.38 * sigmoid((profile.investment - 31) / 15);
    const status = clamp(
      0.08 + 0.22 * parent.status + investmentReturn + publicInput + grandparentInput
      + 0.20 * profile.potential + 0.08 * normal(random)
    );
    const resources = Math.max(
      2,
      parent.resources * (0.30 + 0.78 * status) / (count ** (0.54 - 0.18 * params.education))
      + 12 * params.welfare - 8 * params.housing
    );
    return {status, resources, observed: profile.signal, investment: profile.investment};
  });
}

function reproductionProbability(adult, params) {
  const material = sigmoid((adult.resources - (46 + 35 * params.housing - 20 * params.welfare)) / 11);
  const status = sigmoid(9 * (adult.status - (0.47 - 0.14 * params.education)));
  const support = 0.78 + 0.16 * params.childcare + 0.10 * params.grandparents;
  return clamp(0.06 + 0.84 * material * status * support + 0.18 * params.welfare, 0.02, 0.98);
}

function realizedChildCount(plan, adult, params, random) {
  const support = 0.42 * params.childcare + 0.26 * params.grandparents + 0.24 * params.welfare;
  const pressure = 0.36 * params.housing + 0.18 * Math.max(0, 0.5 - adult.status);
  const target = clamp(plan + support - pressure, 0.2, 4.2);
  const low = Math.floor(target);
  return Math.max(0, Math.min(4, low + (random() < target - low ? 1 : 0)));
}

function simulatePlan(plan, params) {
  const random = mulberry32(hashSeed(params.seed, plan));
  const generation = Array.from({length: params.generations}, (_, index) => ({
    generation: index + 1, survival: 0, mobility: 0, descendants: 0
  }));
  let finalSurvival = 0, totalFinal = 0, anyMobility = 0, firstAllocation = null;
  for (let trial = 0; trial < params.trials; trial += 1) {
    const founder = {resources: params.resources, status: 0.56};
    let adults = makeChildren(plan, founder, params, random);
    if (trial === 0) firstAllocation = allocationProfile(plan, founder, params, mulberry32(hashSeed(params.seed + 71, plan)));
    let everUp = adults.some(child => child.status >= 0.72);
    generation[0].survival += adults.length > 0;
    generation[0].mobility += everUp;
    generation[0].descendants += adults.length;
    for (let index = 1; index < params.generations; index += 1) {
      const next = [];
      for (const adult of adults) {
        if (random() > reproductionProbability(adult, params)) continue;
        const count = realizedChildCount(plan, adult, params, random);
        next.push(...makeChildren(count, adult, params, random));
        if (next.length >= 180) break;
      }
      adults = next.slice(0, 180);
      everUp ||= adults.some(child => child.status >= 0.72);
      generation[index].survival += adults.length > 0;
      generation[index].mobility += everUp;
      generation[index].descendants += adults.length;
      if (!adults.length) {
        for (let rest = index + 1; rest < params.generations; rest += 1) {
          generation[rest].mobility += everUp;
        }
        break;
      }
    }
    finalSurvival += adults.length > 0;
    totalFinal += adults.length;
    anyMobility += everUp;
  }
  generation.forEach(row => {
    row.survival /= params.trials;
    row.mobility /= params.trials;
    row.descendants /= params.trials;
  });
  const hhi = firstAllocation.reduce((sum, child) => sum + child.share ** 2, 0);
  const normalizedConcentration = plan === 1 ? 0 : (hhi - 1 / plan) / (1 - 1 / plan);
  return {
    plan, generation, firstAllocation,
    finalSurvival: finalSurvival / params.trials,
    upwardMobility: anyMobility / params.trials,
    finalDescendants: totalFinal / params.trials,
    concentration: clamp(normalizedConcentration)
  };
}

function runExperiment() {
  const button = document.getElementById('run-button');
  button.disabled = true;
  button.textContent = '计算中…';
  requestAnimationFrame(() => {
    const params = readParams();
    state.results = [1, 2, 3].map(plan => simulatePlan(plan, params));
    document.getElementById('experiment-summary').textContent = `${params.generations} 代 · ${numberFormat(params.trials)} 次 · 种子 ${params.seed}`;
    renderAll();
    button.disabled = false;
    button.textContent = '重新运行实验';
  });
}

function metricMeta(metric) {
  return {
    survival: {key: 'survival', title: '各代家族存续率', desc: '曲线显示在每一代仍至少有一名后代的试验比例。', format: value => percent(value), max: 1},
    mobility: {key: 'mobility', title: '至少一人向上跃迁', desc: '曲线显示截至该代至少出现一名高状态后代的试验比例。', format: value => percent(value), max: 1},
    descendants: {key: 'descendants', title: '各代平均在世后代', desc: '曲线显示每次试验在该代仍在模拟中的平均后代人数。', format: value => value.toFixed(1), max: null}
  }[metric];
}

function renderChart() {
  const svg = document.getElementById('line-chart');
  const metric = metricMeta(document.getElementById('metric').value);
  const visible = new Set([...document.querySelectorAll('input[name="series"]:checked')].map(input => Number(input.value)));
  const width = Math.max(540, svg.clientWidth || 760), height = width < 660 ? 300 : 360;
  const margin = {top: 24, right: 30, bottom: 40, left: 56};
  const plotWidth = width - margin.left - margin.right, plotHeight = height - margin.top - margin.bottom;
  const allValues = state.results.flatMap(result => result.generation.map(row => row[metric.key]));
  const maxValue = metric.max || Math.max(1, ...allValues) * 1.08;
  const x = generation => margin.left + (generation - 1) * plotWidth / Math.max(1, readParams().generations - 1);
  const y = value => margin.top + plotHeight - value / maxValue * plotHeight;
  let content = '';
  for (let tick = 0; tick <= 4; tick += 1) {
    const value = maxValue * tick / 4;
    const yy = y(value);
    content += `<line class="chart-grid" x1="${margin.left}" y1="${yy}" x2="${width - margin.right}" y2="${yy}"></line>`;
    content += `<text class="chart-axis" x="${margin.left - 10}" y="${yy + 4}" text-anchor="end">${metric.format(value)}</text>`;
  }
  for (let generation = 1; generation <= readParams().generations; generation += 1) {
    content += `<text class="chart-axis" x="${x(generation)}" y="${height - 12}" text-anchor="middle">第 ${generation} 代</text>`;
  }
  state.results.forEach(result => {
    if (!visible.has(result.plan)) return;
    const points = result.generation.map(row => `${x(row.generation)},${y(row[metric.key])}`).join(' ');
    content += `<polyline class="chart-line" stroke="${colors[result.plan]}" points="${points}"></polyline>`;
    result.generation.forEach(row => {
      content += `<circle class="chart-point" fill="${colors[result.plan]}" cx="${x(row.generation)}" cy="${y(row[metric.key])}" r="5"><title>${result.plan} 孩 · 第 ${row.generation} 代：${metric.format(row[metric.key])}</title></circle>`;
    });
  });
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = content;
  document.getElementById('chart-title').textContent = metric.title;
  document.getElementById('chart-desc').textContent = metric.desc;
}

function renderCards() {
  const ranked = [...state.results].sort((a, b) => b.finalSurvival - a.finalSurvival);
  document.getElementById('result-cards').innerHTML = state.results.map(result => {
    const rank = ranked.findIndex(item => item.plan === result.plan) + 1;
    return `<article class="result-card ${state.selectedPlan === result.plan ? 'active' : ''}" data-select-plan="${result.plan}" tabindex="0">
      <header><span>${['', '一', '二', '三'][result.plan]}孩家庭</span><span class="rank">存续第 ${rank}</span></header>
      <strong>${percent(result.finalSurvival)}</strong>
      <p>最终代存续 · 向上跃迁 ${percent(result.upwardMobility)} · 后代 ${result.finalDescendants.toFixed(1)} 人</p>
    </article>`;
  }).join('');
  document.querySelectorAll('[data-select-plan]').forEach(card => {
    const select = () => { state.selectedPlan = Number(card.dataset.selectPlan); renderCards(); renderAllocation(); };
    card.addEventListener('click', select);
    card.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') select(); });
  });
}

function renderAllocation() {
  const result = state.results.find(item => item.plan === state.selectedPlan);
  const params = readParams();
  document.querySelectorAll('[data-plan]').forEach(button => button.classList.toggle('active', Number(button.dataset.plan) === state.selectedPlan));
  document.getElementById('allocation-visual').innerHTML = result.firstAllocation.map((child, index) => {
    const share = child.share;
    return `<div class="child-column">
      <div class="child-bar-wrap"><div class="child-bar" style="height:${Math.max(12, share * 190)}px"></div></div>
      <strong>${percent(share, 0)}</strong><span>孩子 ${index + 1} · 观察信号 ${child.signal.toFixed(2)}</span>
    </div>`;
  }).join('');
  const mode = params.dynamic > params.need + 0.15 ? '偏向追投当前表现较强者' : params.need > params.dynamic + 0.15 ? '偏向补偿当前弱势者' : '接近均衡分配';
  document.getElementById('allocation-note').textContent = `${['', '一', '二', '三'][result.plan]}孩方案当前${mode}；标准化投资集中度为 ${percent(result.concentration)}。拖动两个投资策略旋钮后重新运行，可观察分配变化。`;
}

function renderAll() { renderChart(); renderCards(); renderAllocation(); }

function updateOutputs() {
  const suffix = {generations: ' 代'};
  const percentIds = new Set(['childcare', 'grandparents', 'dynamic', 'need', 'education', 'welfare', 'housing']);
  ids.forEach(id => {
    const output = document.getElementById(`${id}-value`);
    if (!output) return;
    const value = Number(document.getElementById(id).value);
    output.textContent = percentIds.has(id) ? `${value}%` : id === 'trials' ? numberFormat(value) : `${value}${suffix[id] || ''}`;
  });
}

ids.forEach(id => document.getElementById(id).addEventListener('input', updateOutputs));
document.getElementById('run-button').addEventListener('click', runExperiment);
document.getElementById('reset-button').addEventListener('click', () => {
  Object.entries(defaults).forEach(([id, value]) => { document.getElementById(id).value = value; });
  updateOutputs(); runExperiment();
});
document.getElementById('metric').addEventListener('change', renderChart);
document.querySelectorAll('input[name="series"]').forEach(input => input.addEventListener('change', renderChart));
document.querySelectorAll('[data-plan]').forEach(button => button.addEventListener('click', () => {
  state.selectedPlan = Number(button.dataset.plan); renderCards(); renderAllocation();
}));
window.addEventListener('resize', () => { if (state.results) renderChart(); });

updateOutputs();
runExperiment();

const worldDefaults = {
  'world-families': 900,
  'world-years': 60,
  'migration-open': 65,
  'opportunity-gap': 55,
  'world-housing': 60,
  'education-equality': 45,
  'world-welfare': 25,
  'world-childcare': 40,
  'economic-volatility': 30,
  'world-tax': 18,
  'world-capacity': 100,
  'technology-growth': 12,
  'world-seed': 2026
};

const regionTemplates = [
  {id: 'NA', name: '北美', x: .18, y: .34, share: .10, development: .88, wage: 1.35, housing: 1.22, education: .80, fertility: .72, school: .82, medical: .84, transport: .78, safety: .70},
  {id: 'LA', name: '拉丁美洲', x: .28, y: .69, share: .11, development: .58, wage: .72, housing: .66, education: .60, fertility: .94, school: .58, medical: .52, transport: .55, safety: .48},
  {id: 'EU', name: '欧洲', x: .48, y: .27, share: .12, development: .86, wage: 1.17, housing: 1.02, education: .84, fertility: .64, school: .88, medical: .90, transport: .86, safety: .82},
  {id: 'AF', name: '非洲', x: .50, y: .66, share: .22, development: .30, wage: .40, housing: .32, education: .35, fertility: 1.46, school: .32, medical: .28, transport: .30, safety: .36},
  {id: 'SA', name: '南亚', x: .69, y: .57, share: .22, development: .42, wage: .55, housing: .46, education: .45, fertility: 1.23, school: .42, medical: .38, transport: .40, safety: .44},
  {id: 'EA', name: '东亚', x: .81, y: .37, share: .23, development: .72, wage: 1.03, housing: 1.12, education: .77, fertility: .73, school: .76, medical: .72, transport: .74, safety: .68}
];

const worldState = {result: null, selectedRegion: 'EA'};
const pythonState = {data: null, selectedCountry: null};

function weightedChoice(random, items, weightKey) {
  const total = items.reduce((sum, item) => sum + item[weightKey], 0);
  let draw = random() * total;
  for (const item of items) {
    draw -= item[weightKey];
    if (draw <= 0) return item;
  }
  return items[items.length - 1];
}

function median(values) {
  if (!values.length) return 0;
  const ordered = [...values].sort((a, b) => a - b);
  const middle = Math.floor(ordered.length / 2);
  return ordered.length % 2 ? ordered[middle] : (ordered[middle - 1] + ordered[middle]) / 2;
}

function worldParams() {
  const raw = Object.fromEntries(Object.keys(worldDefaults).map(id => [id, Number(document.getElementById(id).value)]));
  return {
    initialFamilies: raw['world-families'], years: raw['world-years'], seed: raw['world-seed'],
    migrationOpen: raw['migration-open'] / 100, opportunityGap: raw['opportunity-gap'] / 100,
    housingPressure: raw['world-housing'] / 100, educationEquality: raw['education-equality'] / 100,
    welfare: raw['world-welfare'] / 100, childcare: raw['world-childcare'] / 100,
    volatility: raw['economic-volatility'] / 100, taxRate: raw['world-tax'] / 100,
    capacityScale: raw['world-capacity'] / 100, technologyGrowth: raw['technology-growth'] / 100
  };
}

function regionConditions(template, params, year) {
  const convergence = params.educationEquality * .34;
  const development = clamp(template.development + year * .0014 * (1 - template.development) + params.educationEquality * .05);
  const education = clamp(template.education * (1 - convergence) + .68 * convergence);
  const wageSpread = .66 + params.opportunityGap * (template.wage - .66);
  const cycle = params.volatility * .10 * Math.sin((year + regionTemplates.indexOf(template) * 3.1) / 6.5);
  const school = clamp(template.school * (1 - convergence) + .68 * convergence);
  const childcare = clamp(params.childcare * .68 + .22 * template.development + .10 * params.welfare);
  const medical = clamp(template.medical * .72 + .20 * template.development + .08 * params.welfare);
  const transport = clamp(template.transport * .70 + .24 * template.development);
  const safety = clamp(template.safety * .72 + .18 * template.development + .10 * params.welfare);
  const service = (school + childcare + medical + transport + safety) / 5;
  return {
    development, education: school, school, childcare, medical, transport, safety, service,
    wage: Math.max(.25, wageSpread * (1 + cycle)),
    housing: template.housing * (.55 + .75 * params.housingPressure),
    capacity: Math.max(50, params.initialFamilies * template.share * 3.8 * params.capacityScale * (.55 + .45 * service) / Math.max(.7, template.housing))
  };
}

function initialChildren(random, region) {
  const target = Math.max(0, region.fertility * (1.35 - .58 * region.development));
  const count = Math.min(4, Math.floor(target) + (random() < target % 1 ? 1 : 0));
  return Array.from({length: count}, () => Math.floor(random() * 17));
}

function createInitialWorld(params, random) {
  const families = [];
  for (let id = 1; id <= params.initialFamilies; id += 1) {
    const region = weightedChoice(random, regionTemplates, 'share');
    const resources = Math.max(3, Math.exp(Math.log(42 * (.65 + region.wage)) + normal(random) * .58));
    const human = clamp(.16 + .56 * region.education + .20 * random());
    families.push({
      id, clan: id, region: region.id, generation: 0, adultAge: 22 + Math.floor(random() * 20),
      resources, human, status: clamp(.18 + .36 * human + .18 * Math.log1p(resources) / 5),
      children: initialChildren(random, region), alive: true
    });
  }
  return families;
}

function familyUtility(family, template, params, year, random) {
  const conditions = regionConditions(template, params, year);
  const childNeed = Math.min(1, family.children.length / 2);
  const poverty = clamp(1 - family.resources / 100);
  return (
    1.05 * conditions.wage * (.55 + family.human)
    + .72 * conditions.education * childNeed
    + .32 * params.welfare * poverty
    - .70 * conditions.housing * (1.08 - .45 * clamp(family.resources / 120))
    + .08 * normal(random)
  );
}

function summarizeWorldYear(families, year, migrations, params) {
  const living = families.filter(family => family.alive);
  const technology = 1 + params.technologyGrowth * year;
  const automation = clamp(.08 + .30 * (technology - 1));
  const taxRevenue = living.reduce((sum, family) => sum + family.resources, 0) * params.taxRate;
  const childCount = living.reduce((sum, family) => sum + family.children.length, 0);
  const retirees = living.filter(family => family.adultAge >= 65).length;
  const publicSpending = childCount * (.55 + .65 * params.educationEquality) + living.length * (.22 + .18 * params.welfare) + retirees * .70;
  const capacityPressure = regionTemplates.reduce((sum, template) => {
    const conditions = regionConditions(template, params, year);
    const count = living.filter(family => family.region === template.id).length;
    return sum + count / Math.max(1, conditions.capacity);
  }, 0) / regionTemplates.length;
  return {
    year,
    families: living.length,
    migrations,
    resources: median(living.map(family => family.resources)),
    children: living.reduce((sum, family) => sum + family.children.length, 0) / Math.max(1, living.length),
    mobility: living.filter(family => family.status >= .72).length / Math.max(1, living.length),
    taxRevenue, publicSpending, fiscalBalance: taxRevenue - publicSpending,
    capacityPressure, technology, automation,
    laborShortage: clamp(.65 * (1 - living.filter(family => family.adultAge >= 22 && family.adultAge < 65).length / Math.max(1, living.length)) + .35 * automation)
  };
}

function simulateWorld(params) {
  const random = mulberry32(hashSeed(params.seed, 17));
  const families = createInitialWorld(params, random);
  const history = [summarizeWorldYear(families, 0, 0, params)];
  const flows = {};
  let nextFamilyId = families.length + 1;
  let totalBranches = 0;
  let totalMigrations = 0;

  for (let year = 1; year <= params.years; year += 1) {
    let migrations = 0;
    const newBranches = [];
    const snapshot = families.filter(family => family.alive);
    for (const family of snapshot) {
      const originTemplate = regionTemplates.find(region => region.id === family.region);
      const origin = regionConditions(originTemplate, params, year);
      family.adultAge += 1;
      family.children = family.children.map(age => age + 1);
      const childCount = family.children.length;
      const careRelief = .68 + .34 * params.childcare + .18 * params.welfare;
      const income = 9.2 * origin.wage * (.58 + family.human) * careRelief;
      const expenses = 2.8 + childCount * (1.7 + 1.5 * origin.development) + 2.0 * origin.housing;
      family.resources = Math.max(.5, family.resources * .985 + income - expenses);
      family.human = clamp(family.human + .004 * origin.education * (1 - family.human));

      if (family.adultAge <= 44 && childCount < 4) {
        const richRebound = Math.max(0, Math.log2(Math.max(1, family.resources / 100))) * .12;
        const desired = Math.max(
          .2,
          originTemplate.fertility * (1.30 - .72 * origin.development)
          + .52 * params.childcare + .20 * params.welfare + richRebound
          - .34 * origin.housing
        );
        const birthProbability = Math.max(0, desired - childCount) * .075;
        if (random() < birthProbability) family.children.push(0);
      }

      const matured = family.children.filter(age => age >= 22);
      family.children = family.children.filter(age => age < 22);
      matured.forEach(() => {
        if (families.length + newBranches.length >= 5200) return;
        const transfer = family.resources * .18 / Math.max(1, matured.length);
        family.resources = Math.max(.5, family.resources - transfer);
        const branchHuman = clamp(.52 * family.human + .32 * origin.education + .12 * random());
        newBranches.push({
          id: nextFamilyId++, clan: family.clan, region: family.region, generation: family.generation + 1,
          adultAge: 23 + Math.floor(random() * 6), resources: Math.max(2, transfer), human: branchHuman,
          status: clamp(.20 + .40 * branchHuman + .12 * Math.log1p(transfer) / 4), children: [], alive: true
        });
        totalBranches += 1;
      });

      const migrationProbability = .052 * params.migrationOpen * (1 + .60 * params.opportunityGap);
      if (random() < migrationProbability) {
        const originScore = familyUtility(family, originTemplate, params, year, random) + .16;
        let best = originTemplate;
        let bestScore = originScore;
        for (const candidate of regionTemplates) {
          if (candidate.id === family.region) continue;
          const score = familyUtility(family, candidate, params, year, random);
          if (score > bestScore) { best = candidate; bestScore = score; }
        }
        if (best.id !== family.region) {
          const key = `${family.region}>${best.id}`;
          flows[key] = (flows[key] || 0) + 1;
          family.region = best.id;
          family.resources = Math.max(.5, family.resources - 3.5 * (1 - params.welfare));
          migrations += 1;
          totalMigrations += 1;
        }
      }

      family.status = clamp(
        .10 + .42 * family.human + .24 * sigmoid((family.resources - 48) / 25)
        + .12 * origin.education + .07 * normal(random)
      );
      if (family.adultAge > 80) {
        const mortality = Math.min(.42, .018 * (family.adultAge - 79) * (1.08 - .32 * params.welfare));
        if (random() < mortality) family.alive = false;
      }
    }
    families.push(...newBranches);
    if (year % 2 === 0 || year === params.years) history.push(summarizeWorldYear(families, year, migrations, params));
  }

  const living = families.filter(family => family.alive);
  const regions = regionTemplates.map(template => {
    const members = living.filter(family => family.region === template.id);
    const inflow = Object.entries(flows).filter(([key]) => key.endsWith(`>${template.id}`)).reduce((sum, [, value]) => sum + value, 0);
    const outflow = Object.entries(flows).filter(([key]) => key.startsWith(`${template.id}>`)).reduce((sum, [, value]) => sum + value, 0);
    const conditions = regionConditions(template, params, params.years);
    return {
      ...template, ...conditions, families: members.length,
      resources: median(members.map(family => family.resources)),
      children: members.reduce((sum, family) => sum + family.children.length, 0) / Math.max(1, members.length),
      highStatus: members.filter(family => family.status >= .72).length / Math.max(1, members.length),
      inflow, outflow, netFlow: inflow - outflow,
      ...regionConditions(template, params, params.years),
      capacityPressure: members.length / Math.max(1, regionConditions(template, params, params.years).capacity)
    };
  });
  return {families: living, regions, flows, history, totalBranches, totalMigrations};
}

function updateWorldOutputs() {
  const percentIds = new Set(['migration-open', 'opportunity-gap', 'world-housing', 'education-equality', 'world-welfare', 'world-childcare', 'economic-volatility']);
  Object.keys(worldDefaults).forEach(id => {
    const output = document.getElementById(`${id}-value`);
    if (!output) return;
    const value = Number(document.getElementById(id).value);
    output.textContent = percentIds.has(id) ? `${value}%` : id === 'world-years' ? `${value} 年` : numberFormat(value);
  });
}

function worldMetricValue(region, metric) {
  if (metric === 'development') return region.development;
  if (metric === 'children') return region.children;
  return region.resources;
}

function mixColor(amount) {
  const low = [220, 232, 223], high = [36, 93, 69];
  const value = clamp(amount);
  return `rgb(${low.map((channel, index) => Math.round(channel + (high[index] - channel) * value)).join(',')})`;
}

function renderWorldStats() {
  const result = worldState.result;
  const final = result.history[result.history.length - 1];
  const initial = result.history[0];
  const gap = Math.max(...result.regions.map(region => region.resources)) - Math.min(...result.regions.map(region => region.resources));
  document.getElementById('world-stats').innerHTML = [
    ['在世家庭', numberFormat(final.families)],
    ['新家庭分支', numberFormat(result.totalBranches)],
    ['跨区域迁徙', numberFormat(result.totalMigrations)],
    ['区域资源差距', gap.toFixed(1)]
  ].map(([label, value]) => `<div class="world-stat"><span>${label}</span><strong>${value}</strong></div>`).join('');
  document.getElementById('world-summary').textContent = `${worldParams().years} 年 · ${numberFormat(initial.families)} 个初始家庭`;
  document.getElementById('system-feedback').innerHTML = [
    ['税收收入', final.taxRevenue.toFixed(1)],
    ['公共支出', final.publicSpending.toFixed(1)],
    ['财政结余', final.fiscalBalance.toFixed(1)],
    ['平均承载压力', percent(final.capacityPressure)],
    ['技术指数', final.technology.toFixed(2)],
    ['自动化占比', percent(final.automation)],
    ['劳动短缺压力', percent(final.laborShortage)]
  ].map(([label, value]) => `<div class="region-fact"><span>${label}</span><strong>${value}</strong></div>`).join('');
}

function renderWorldNetwork() {
  const svg = document.getElementById('world-network');
  const width = Math.max(320, svg.clientWidth || 820), height = width < 700 ? 350 : 450;
  const metric = document.getElementById('world-map-metric').value;
  const values = worldState.result.regions.map(region => worldMetricValue(region, metric));
  const low = Math.min(...values), high = Math.max(...values);
  const maxFamilies = Math.max(...worldState.result.regions.map(region => region.families), 1);
  const flowEntries = Object.entries(worldState.result.flows).sort((a, b) => b[1] - a[1]).slice(0, 12);
  const maxFlow = Math.max(...flowEntries.map(([, value]) => value), 1);
  let content = `<defs><marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#427c91"></path></marker></defs>`;
  flowEntries.forEach(([key, value]) => {
    const [fromId, toId] = key.split('>');
    const from = worldState.result.regions.find(region => region.id === fromId);
    const to = worldState.result.regions.find(region => region.id === toId);
    const x1 = from.x * width, y1 = from.y * height, x2 = to.x * width, y2 = to.y * height;
    const curve = (x1 + x2) / 2 + (y2 - y1) * .18;
    const curveY = (y1 + y2) / 2 - (x2 - x1) * .08;
    content += `<path class="flow-line" d="M${x1},${y1} Q${curve},${curveY} ${x2},${y2}" stroke-width="${1.2 + 6 * value / maxFlow}" marker-end="url(#flow-arrow)"><title>${from.name} → ${to.name}：${value} 个家庭</title></path>`;
  });
  worldState.result.regions.forEach(region => {
    const normalized = high === low ? .5 : (worldMetricValue(region, metric) - low) / (high - low);
    const radius = (width < 600 ? 13 : 20)
      + (width < 600 ? 18 : 30) * Math.sqrt(region.families / maxFamilies);
    const x = region.x * width, y = region.y * height;
    const valueLabel = metric === 'development' ? percent(region.development, 0) : metric === 'children' ? `${region.children.toFixed(2)} 孩` : `${region.resources.toFixed(0)} 资源`;
    content += `<g data-world-region="${region.id}" role="button" aria-label="查看${region.name}" tabindex="0">
      <circle class="region-node ${worldState.selectedRegion === region.id ? 'selected' : ''}" cx="${x}" cy="${y}" r="${radius}" fill="${mixColor(normalized)}"><title>${region.name}：${region.families} 个家庭，${valueLabel}</title></circle>
      <text class="region-label" x="${x}" y="${y + 3}" text-anchor="middle">${region.name}</text>
      <text class="region-value" x="${x}" y="${y + 18}" text-anchor="middle">${numberFormat(region.families)} 户</text>
    </g>`;
  });
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = content;
  svg.querySelectorAll('[data-world-region]').forEach(node => {
    const select = () => { worldState.selectedRegion = node.dataset.worldRegion; renderWorldNetwork(); renderRegionDetail(); };
    node.addEventListener('click', select);
    node.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') select(); });
  });
}

function timelineMeta(metric) {
  return {
    families: ['家庭总数变化', '包含原家庭与成年子女建立的新家庭分支。', value => numberFormat(Math.round(value))],
    migrations: ['年度迁徙家庭', '显示每个记录年份发生跨区域迁徙的家庭数。', value => numberFormat(Math.round(value))],
    resources: ['家庭资源中位数', '显示所有在世家庭资源中位数。', value => value.toFixed(0)],
    children: ['户均未成年子女', '显示每个在世家庭平均未成年子女数。', value => value.toFixed(2)],
    mobility: ['高状态家庭占比', '显示状态指标达到 0.72 的家庭比例。', value => percent(value, 0)],
    taxRevenue: ['税收收入', '家庭资源形成的简化地区税收。', value => value.toFixed(0)],
    fiscalBalance: ['财政结余', '税收减去教育、医疗和养老支出的简化余额。', value => value.toFixed(0)],
    capacityPressure: ['承载力压力', '人口与地区公共服务、住房和就业容量的比值。', value => percent(value, 0)],
    technology: ['技术指数', '技术进步提高生产率，同时伴随自动化替代。', value => value.toFixed(2)]
  }[metric];
}

function renderWorldTimeline() {
  const svg = document.getElementById('world-timeline');
  const metric = document.getElementById('world-timeline-metric').value;
  const meta = timelineMeta(metric), data = worldState.result.history;
  const width = Math.max(320, svg.clientWidth || 800), height = width < 660 ? 280 : 320;
  const margin = {top: 20, right: width < 500 ? 14 : 28, bottom: 38, left: width < 500 ? 54 : 66};
  const plotWidth = width - margin.left - margin.right, plotHeight = height - margin.top - margin.bottom;
  const minValue = Math.min(...data.map(row => row[metric]));
  const maxValue = Math.max(...data.map(row => row[metric]));
  const padding = Math.max(.01, (maxValue - minValue) * .12);
  const yLow = Math.max(0, minValue - padding), yHigh = maxValue + padding;
  const x = year => margin.left + year / Math.max(1, worldParams().years) * plotWidth;
  const y = value => margin.top + plotHeight - (value - yLow) / Math.max(.001, yHigh - yLow) * plotHeight;
  let content = '';
  for (let tick = 0; tick <= 4; tick += 1) {
    const value = yLow + (yHigh - yLow) * tick / 4, yy = y(value);
    content += `<line class="chart-grid" x1="${margin.left}" y1="${yy}" x2="${width - margin.right}" y2="${yy}"></line><text class="chart-axis" x="${margin.left - 10}" y="${yy + 4}" text-anchor="end">${meta[2](value)}</text>`;
  }
  const points = data.map(row => `${x(row.year)},${y(row[metric])}`).join(' ');
  content += `<polyline class="chart-line" stroke="#245d45" points="${points}"></polyline>`;
  data.filter((_, index) => index % Math.max(1, Math.floor(data.length / 12)) === 0 || index === data.length - 1).forEach(row => {
    content += `<circle class="chart-point" fill="#245d45" cx="${x(row.year)}" cy="${y(row[metric])}" r="4"><title>第 ${row.year} 年：${meta[2](row[metric])}</title></circle>`;
  });
  [0, .25, .5, .75, 1].forEach(fraction => {
    const year = Math.round(worldParams().years * fraction);
    content += `<text class="chart-axis" x="${x(year)}" y="${height - 11}" text-anchor="middle">${year} 年</text>`;
  });
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.innerHTML = content;
  document.getElementById('world-timeline-title').textContent = meta[0];
  document.getElementById('world-timeline-desc').textContent = meta[1];
}

function renderRegionDetail() {
  const regions = worldState.result.regions;
  document.getElementById('region-buttons').innerHTML = regions.map(region => `<button type="button" data-region-button="${region.id}" class="${worldState.selectedRegion === region.id ? 'active' : ''}">${region.name}</button>`).join('');
  document.querySelectorAll('[data-region-button]').forEach(button => button.addEventListener('click', () => {
    worldState.selectedRegion = button.dataset.regionButton; renderWorldNetwork(); renderRegionDetail();
  }));
  const region = regions.find(item => item.id === worldState.selectedRegion) || regions[0];
  const facts = [
    ['在世家庭', `${numberFormat(region.families)} 户`],
    ['资源中位数', region.resources.toFixed(1)],
    ['户均未成年子女', region.children.toFixed(2)],
    ['高状态家庭', percent(region.highStatus)],
    ['累计迁入', `${numberFormat(region.inflow)} 户`],
    ['累计迁出', `${numberFormat(region.outflow)} 户`],
    ['净迁徙', `${region.netFlow >= 0 ? '+' : ''}${numberFormat(region.netFlow)} 户`],
    ['学校供给', percent(region.school)],
    ['托育供给', percent(region.childcare)],
    ['医疗供给', percent(region.medical)],
    ['交通可达性', percent(region.transport)],
    ['安全水平', percent(region.safety)],
    ['承载力压力', percent(region.capacityPressure)],
    ['公共服务综合指数', percent(region.service)]
  ];
  document.getElementById('region-detail-title').textContent = `${region.name}为何吸引或流失家庭？`;
  document.getElementById('region-detail-content').innerHTML = facts.map(([label, value]) => `<div class="region-fact"><span>${label}</span><strong>${value}</strong></div>`).join('');
}

function renderWorld() {
  renderWorldStats(); renderWorldNetwork(); renderWorldTimeline(); renderRegionDetail();
}

function localApiUrl(path) {
  return new URL(path.replace(/^\//, ''), document.baseURI).toString();
}

async function checkLocalEngine() {
  const status = document.getElementById('engine-status');
  const button = document.getElementById('engine-run');
  try {
    const response = await fetch(localApiUrl('api/health'), {headers: {'Accept': 'application/json'}});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (payload.ok && payload.engine === 'python') {
      status.textContent = '本地 Python 引擎已连接：可以运行完整家庭、职业、婚姻、健康和政策模型。';
      button.disabled = false;
      return true;
    }
  } catch (error) {
    // GitHub Pages 是静态部署，没有 API 时保留浏览器模型，不阻断页面。
  }
  status.textContent = '当前页面使用浏览器轻量模型；若要运行完整 Python 引擎，请在项目根目录启动 population-simu-app。';
  button.disabled = false;
  return false;
}

async function runLocalEngine() {
  const button = document.getElementById('engine-run');
  const status = document.getElementById('engine-status');
  const output = document.getElementById('engine-output');
  const scenario = document.getElementById('engine-scenario').value;
  button.disabled = true; button.textContent = '运行完整引擎中…';
  output.hidden = false; output.textContent = '正在运行 Python 年度家庭模型…';
  try {
    const years = worldParams().years;
    const seed = worldParams().seed;
    const url = `${localApiUrl('api/run')}?scenario=${encodeURIComponent(scenario)}&years=${years}&seed=${seed}`;
    const response = await fetch(url, {headers: {'Accept': 'application/json'}});
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.error || `HTTP ${response.status}`);
    const snapshot = payload.snapshot;
    pythonState.data = payload;
    document.getElementById('engine-download').disabled = false;
    const countries = [...new Set(payload.history.map(row => row.country))];
    pythonState.selectedCountry = pythonState.selectedCountry && countries.includes(pythonState.selectedCountry)
      ? pythonState.selectedCountry : countries[0];
    renderPythonResults();
    document.getElementById('python-results').hidden = false;
    output.textContent = JSON.stringify({
      情景: payload.scenario,
      年份: snapshot.year,
      在世人口: snapshot.population,
      家庭数: snapshot.households,
      姓氏家族数: snapshot.clans,
      国家: Object.fromEntries(Object.entries(snapshot.countries).map(([id, row]) => [id, {
        家庭: row.households, 人口: row.population, 地区: row.regions.length
      }]))
    }, null, 2);
    status.textContent = '完整 Python 情景已完成；上方网页图形仍展示浏览器即时模型，详细年度结果保存在本地 API 响应中。';
  } catch (error) {
    output.textContent = `无法运行本地 Python 引擎：${error.message}`;
    status.textContent = '请确认已在项目根目录启动 population-simu-app；静态网页模式仍可继续使用。';
  } finally {
    button.disabled = false; button.textContent = '运行 Python 情景';
  }
}

async function downloadPythonCsv() {
  if (!pythonState.data) return;
  const scenario = document.getElementById('engine-scenario').value;
  const years = worldParams().years, seed = worldParams().seed;
  const url = `${localApiUrl('api/run.csv')}?scenario=${encodeURIComponent(scenario)}&years=${years}&seed=${seed}`;
  const response = await fetch(url, {headers: {'Accept': 'text/csv'}});
  if (!response.ok) throw new Error(`CSV HTTP ${response.status}`);
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = objectUrl; link.download = `${scenario.replace(/\.json$/, '')}_annual.csv`;
  document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(objectUrl);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]));
}

function pythonMetricMeta(metric) {
  return {
    population: ['人口', value => numberFormat(Math.round(value))],
    households: ['家庭/分支存量', value => numberFormat(Math.round(value))],
    median_household_resources: ['家庭资源中位数', value => Number(value).toFixed(1)],
    high_status_share: ['高状态家庭占比', value => percent(value)],
    births: ['出生数', value => numberFormat(Math.round(value))],
    migrants: ['跨国迁移数', value => numberFormat(Math.round(value))]
  }[metric];
}

function renderPythonTimeline() {
  if (!pythonState.data) return;
  const svg = document.getElementById('python-timeline');
  const country = document.getElementById('python-country').value;
  const metric = document.getElementById('python-metric').value;
  const rows = pythonState.data.history.filter(row => row.country === country);
  const meta = pythonMetricMeta(metric);
  const width = Math.max(320, svg.clientWidth || 800), height = width < 620 ? 270 : 320;
  const margin = {top: 18, right: width < 500 ? 14 : 26, bottom: 38, left: width < 500 ? 58 : 76};
  const plotWidth = width - margin.left - margin.right, plotHeight = height - margin.top - margin.bottom;
  const values = rows.map(row => Number(row[metric]) || 0);
  const low = Math.min(...values), high = Math.max(...values);
  const padding = Math.max(.01, (high - low) * .12), yLow = Math.max(0, low - padding), yHigh = high + padding;
  const years = rows.map(row => row.year);
  const x = year => margin.left + (year - years[0]) / Math.max(1, years[years.length - 1] - years[0]) * plotWidth;
  const y = value => margin.top + plotHeight - (value - yLow) / Math.max(.001, yHigh - yLow) * plotHeight;
  let content = '';
  for (let tick = 0; tick <= 4; tick += 1) {
    const value = yLow + (yHigh - yLow) * tick / 4, yy = y(value);
    content += `<line class="chart-grid" x1="${margin.left}" y1="${yy}" x2="${width - margin.right}" y2="${yy}"></line><text class="chart-axis" x="${margin.left - 10}" y="${yy + 4}" text-anchor="end">${meta[1](value)}</text>`;
  }
  const points = rows.map(row => `${x(row.year)},${y(Number(row[metric]) || 0)}`).join(' ');
  content += `<polyline class="chart-line python-chart-line" points="${points}"></polyline>`;
  rows.filter((_, index) => index % Math.max(1, Math.floor(rows.length / 12)) === 0 || index === rows.length - 1).forEach(row => {
    content += `<circle class="chart-point python-chart-point" cx="${x(row.year)}" cy="${y(Number(row[metric]) || 0)}" r="4"><title>${row.year} 年：${meta[1](Number(row[metric]) || 0)}</title></circle>`;
  });
  [0, .25, .5, .75, 1].forEach(fraction => {
    const year = Math.round(years[0] + (years[years.length - 1] - years[0]) * fraction);
    content += `<text class="chart-axis" x="${x(year)}" y="${height - 11}" text-anchor="middle">${year}</text>`;
  });
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`); svg.innerHTML = content;
  document.getElementById('python-timeline-title').textContent = `${country} · ${meta[0]}`;
  document.getElementById('python-timeline-desc').textContent = '完整 Python 家庭引擎的年度结果；曲线不是网页轻量模型的估算。';
}

function renderPythonComparisons() {
  const data = pythonState.data;
  const byCountry = new Map();
  data.history.forEach(row => byCountry.set(row.country, row));
  document.getElementById('python-country-comparison').innerHTML = `<table><thead><tr><th>国家</th><th>政策阶段</th><th>人口</th><th>家庭/分支</th><th>高状态</th></tr></thead><tbody>${[...byCountry.values()].map(row => {
    const policies = [...new Set(data.history.filter(item => item.country === row.country).map(item => item.policy).filter(Boolean))].join(' → ');
    return `<tr><td><strong>${escapeHtml(row.country)}</strong></td><td>${escapeHtml(policies || '无专项政策')}</td><td>${numberFormat(row.population)}</td><td>${numberFormat(row.households)}</td><td>${percent(row.high_status_share)}</td></tr>`;
  }).join('')}</tbody></table>`;
  const latest = data.region_history[data.region_history.length - 1];
  document.getElementById('python-region-comparison').innerHTML = `<table><thead><tr><th>国家/地区</th><th>城乡</th><th>人口</th><th>家庭</th><th>资源中位数</th></tr></thead><tbody>${latest.regions.map(row => `<tr><td>${escapeHtml(row.country)} · ${escapeHtml(row.region_name)}</td><td>${row.urban ? '城市' : '乡村'}</td><td>${numberFormat(row.population)}</td><td>${numberFormat(row.households)}</td><td>${Number(row.median_resources).toFixed(1)}</td></tr>`).join('')}</tbody></table>`;
}

function renderPythonResults() {
  const countries = [...new Set(pythonState.data.history.map(row => row.country))];
  const select = document.getElementById('python-country');
  select.innerHTML = countries.map(country => `<option value="${escapeHtml(country)}">${escapeHtml(country)}</option>`).join('');
  select.value = pythonState.selectedCountry;
  renderPythonTimeline(); renderPythonComparisons();
}

function runWorldExperiment() {
  const button = document.getElementById('world-run');
  button.disabled = true; button.textContent = '模拟家庭迁徙中…';
  requestAnimationFrame(() => {
    worldState.result = simulateWorld(worldParams());
    renderWorld();
    button.disabled = false; button.textContent = '运行世界沙盘';
  });
}

Object.keys(worldDefaults).forEach(id => document.getElementById(id).addEventListener('input', updateWorldOutputs));
document.getElementById('world-run').addEventListener('click', runWorldExperiment);
document.getElementById('engine-run').addEventListener('click', runLocalEngine);
document.getElementById('engine-download').addEventListener('click', async () => {
  const button = document.getElementById('engine-download');
  button.disabled = true;
  try { await downloadPythonCsv(); } catch (error) { document.getElementById('engine-status').textContent = `CSV 下载失败：${error.message}`; }
  button.disabled = false;
});
document.getElementById('world-reset').addEventListener('click', () => {
  Object.entries(worldDefaults).forEach(([id, value]) => { document.getElementById(id).value = value; });
  updateWorldOutputs(); runWorldExperiment();
});
document.getElementById('world-map-metric').addEventListener('change', renderWorldNetwork);
document.getElementById('world-timeline-metric').addEventListener('change', renderWorldTimeline);
document.getElementById('python-country').addEventListener('change', event => {
  pythonState.selectedCountry = event.target.value; renderPythonTimeline();
});
document.getElementById('python-metric').addEventListener('change', renderPythonTimeline);
document.querySelectorAll('[data-view-button]').forEach(button => button.addEventListener('click', () => {
  const view = button.dataset.viewButton;
  document.querySelectorAll('[data-view-button]').forEach(item => item.classList.toggle('active', item === button));
  document.querySelectorAll('[data-view-panel]').forEach(panel => { panel.hidden = panel.dataset.viewPanel !== view; });
  if (view === 'world' && worldState.result) { renderWorldNetwork(); renderWorldTimeline(); }
  if (view === 'family' && state.results) renderChart();
}));
window.addEventListener('resize', () => {
  if (worldState.result && !document.getElementById('world-view').hidden) { renderWorldNetwork(); renderWorldTimeline(); }
  if (pythonState.data && !document.getElementById('python-results').hidden) renderPythonTimeline();
});

updateWorldOutputs();
runWorldExperiment();
checkLocalEngine();
