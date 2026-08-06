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
