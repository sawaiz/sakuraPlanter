// Step-by-step 3D instructions for an original LEGO set, laid out like its printed manual.
// Needs window.SET (geometry + models, from instructions/pack.py) and window.SETCFG (sections, theme, PDF link).
import * as THREE from 'three';
import { OrbitControls } from '../../vendor/OrbitControls.js';
import { makePart, modelRoot, edgeMaterial, condMaterial, partMaterial, partGeometry, Outliner, studio } from './scene.js';

const SET = window.SET, CFG = window.SETCFG, Q = new URLSearchParams(location.search);
const $ = s => document.querySelector(s);
const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } } };
const KEY = 'sakura-sets/' + CFG.set;
const AXLE_L = { '4519': 3, '32062': 2, '3705': 4, '32073': 5, '3706': 6, '44294': 7, '3707': 8 };

// ---------------------------------------------------------------- pages (manual order)
const pages = [];
for (const sec of CFG.sections) {
  const model = SET.models[sec.model];
  pages.push({ kind: 'intro', sec, model: sec.model, step: model.steps.length - 1 });
  model.steps.forEach((s, i) => {
    if (s.callout) addSub(s.callout.model, s.callout.mult, sec, i + 1);
    pages.push({ kind: 'main', sec, model: sec.model, step: i, num: i + 1, s });
  });
}
if (CFG.final) pages.push({ kind: 'final', sec: { title: CFG.final.title }, model: CFG.final.model, step: SET.models[CFG.final.model].steps.length - 1 });
function addSub(name, mult, sec, parentNum, outerMult = 1) {
  const m = SET.models[name];
  m.steps.forEach((ss, j) => {
    if (ss.callout) addSub(ss.callout.model, ss.callout.mult, sec, parentNum, mult * outerMult);
    pages.push({ kind: 'sub', sec, model: name, step: j, num: j + 1, of: m.steps.length, mult, total: mult * outerMult, parentNum, s: ss });
  });
}
// pieces placed by the end of each page (for "pieces left")
let placed = 0; const cnt = s => (s.count === false ? 0 : (s.mult || 1));
const totalPieces = CFG.sections.reduce((a, s) => a + SET.models[s.model].parts.length * cnt(s), 0);
for (const p of pages) {
  if (p.kind === 'main') { const st = SET.models[p.model].steps[p.step]; if (!st.callout) placed += st.new.length * cnt(p.sec); }
  else if (p.kind === 'sub') placed += SET.models[p.model].steps[p.step].new.length * p.total * cnt(p.sec);
  p.placed = placed;
}

// ---------------------------------------------------------------- renderer
const stage = $('#stage');
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: !!Q.get('shot') });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setClearColor(0x000000, 0);
stage.appendChild(renderer.domElement);
const scene = new THREE.Scene();
const HDR = '../../assets/studio_small_03_1k.hdr';
const lights = studio(renderer, scene, HDR, { shadows: true, exposure: 0.92, env: 0.75 }), key = lights.key;
const camera = new THREE.PerspectiveCamera(22, 1, 1, 2e5);
const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.dampingFactor = 0.1;
const style = { edge: CFG.theme === 'bouquet' ? 0x1d1f21 : 0x141c24, edgeOpacity: 0.85 };
const mats = { edge: edgeMaterial(style), cond: condMaterial(style) };
const outliner = new Outliner(renderer, getComputedStyle(document.documentElement).getPropertyValue('--hl').trim() || '#ffe500', 3);

// one root per model, parts built lazily and toggled by step
const roots = {};
function rootFor(name) {
  if (roots[name]) return roots[name];
  const m = SET.models[name], root = modelRoot(), objs = m.parts.map(row => { const o = makePart(SET, row, style, mats); o.userData.base = o.matrix.clone(); o.visible = false; root.add(o); return o; });
  const stepOf = new Array(m.parts.length).fill(0); m.steps.forEach((s, i) => s.new.forEach(k => { stepOf[k] = i; }));
  scene.add(root); root.visible = false; return (roots[name] = { root, objs, stepOf, m });
}

function resize() {
  const r = stage.getBoundingClientRect(); renderer.setSize(r.width, r.height, false);
  camera.aspect = r.width / Math.max(1, r.height);
  const shift = document.body.classList.contains('sub') || innerWidth <= 760 ? 0 : Math.min(110, r.width * 0.07);   // keep clear of the parts column
  camera.setViewOffset(r.width, r.height, -shift, 0, r.width, r.height); camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(stage);

// ---------------------------------------------------------------- part icons for the parts box
const iconCache = new Map();
const iconR = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true }); iconR.setSize(140, 112); iconR.setClearColor(0, 0);
const iconScene = new THREE.Scene(); const iconLights = studio(iconR, iconScene, HDR);
const iconCam = new THREE.PerspectiveCamera(22, 140 / 112, 1, 1e5);
function icon(pid, code) {
  const k = pid + '|' + code; if (iconCache.has(k)) return iconCache.get(k);
  const row = [pid, code, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0];
  const g = makePart(SET, row, style, mats); const r = modelRoot(); r.add(g); iconScene.add(r); r.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(r), c = box.getCenter(new THREE.Vector3()), s = Math.max(box.getSize(new THREE.Vector3()).length(), 8);
  const d = s / (2 * Math.tan(THREE.MathUtils.degToRad(11))) * 1.02, az = -0.7, el = 0.5;
  iconCam.position.set(c.x + d * Math.cos(el) * Math.sin(az), c.y + d * Math.sin(el), c.z + d * Math.cos(el) * Math.cos(az)); iconCam.lookAt(c);
  iconR.render(iconScene, iconCam); const url = iconR.domElement.toDataURL(); iconScene.remove(r);
  iconCache.set(k, url); return url;
}

// ---------------------------------------------------------------- the spin popover (click a part in the box)
const spinBox = $('#spin'), spinR = new THREE.WebGLRenderer({ antialias: true, alpha: true }); spinR.setPixelRatio(Math.min(devicePixelRatio, 2)); spinR.setSize(180, 160); spinR.setClearColor(0, 0);
spinBox.prepend(spinR.domElement);
const spinScene = new THREE.Scene(); studio(spinR, spinScene, HDR);
const spinCam = new THREE.PerspectiveCamera(22, 180 / 160, 1, 1e5); let spinObj = null, spinUntil = 0, flash = null;
function showSpin(pid, code, btn) {
  if (spinObj) spinScene.remove(spinObj);
  const r = modelRoot(); r.add(makePart(SET, [pid, code, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0], style, mats)); r.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(r), c = box.getCenter(new THREE.Vector3()), piv = new THREE.Group(); r.position.sub(c); r.matrix.premultiply(new THREE.Matrix4().makeTranslation(-c.x, -c.y, -c.z));
  piv.add(r); spinScene.add(piv); spinObj = piv; const s = Math.max(box.getSize(new THREE.Vector3()).length(), 8);
  spinCam.position.set(0, s * 0.9, s * 2.3); spinCam.lookAt(0, 0, 0);
  const b = btn.getBoundingClientRect(); spinBox.style.left = (b.right + 8) + 'px'; spinBox.style.top = Math.max(60, b.top - 40) + 'px';
  $('#spin p').textContent = ((SET.names || {})[pid] || pid) + ' · ' + ((SET.colours[code] || [])[2] || '').replace(/_/g, ' ');
  spinBox.classList.add('on'); spinUntil = performance.now() + 4000;
  flash = { pid, code, until: performance.now() + 2600 };
}

// ---------------------------------------------------------------- UI
const sel = $('#section');
CFG.sections.forEach((s, i) => { const o = document.createElement('option'); o.value = i; o.textContent = (s.bag ? `Bag ${s.bag} · ` : '') + s.title + (s.mult > 1 ? ` (${s.mult}x)` : ''); sel.appendChild(o); });
if (CFG.final) { const o = document.createElement('option'); o.value = 'final'; o.textContent = CFG.final.title; sel.appendChild(o); }
sel.addEventListener('change', () => { const v = sel.value; go(v === 'final' ? pages.length - 1 : pages.findIndex(p => p.sec === CFG.sections[+v])); });
$('#prev').onclick = () => go(cur - 1); $('#next').onclick = () => go(cur + 1);
for (const el of [document.querySelector('.left'), document.querySelector('.bottom')]) {
  let x0 = null; el.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
  el.addEventListener('touchend', e => { if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 50) go(cur + (dx < 0 ? 1 : -1)); }, { passive: true });
}
addEventListener('keydown', e => { if (e.target.closest('select,input')) return; if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); go(cur + 1); } if (e.key === 'ArrowLeft') go(cur - 1); });
const hl = $('#hl'); hl.checked = store.get(KEY + '/hl') !== '0'; hl.onchange = () => { store.set(KEY + '/hl', hl.checked ? '1' : '0'); };

// 1:1 calibration: CSS px per mm, set by matching a bank card (85.6 mm)
let pxmm = +(store.get('sakura-sets/pxmm') || 0) || 96 / 25.4;
const calib = $('#calib'), card = $('#card'), cs = $('#cardsize');
$('#oneone button').onclick = () => { cs.value = pxmm * 85.6; card.style.width = cs.value + 'px'; calib.classList.add('on'); };
cs.oninput = () => { card.style.width = cs.value + 'px'; };
$('#calibdone').onclick = () => { pxmm = +cs.value / 85.6; store.set('sakura-sets/pxmm', String(pxmm)); calib.classList.remove('on'); draw11(); };
function draw11(len) {
  if (len) draw11.len = len; const L = draw11.len || 3, w = L * 8 * pxmm, h = 4.8 * pxmm;
  $('#oneone svg').setAttribute('width', w + 22); $('#oneone svg').setAttribute('height', Math.max(h, 18) + 4);
  $('#oneone svg').innerHTML = `<rect x="1" y="2" width="${w}" height="${h}" rx="${h * 0.25}" fill="#C9CCCF" stroke="#1B2733" stroke-width="1.2"/>
    <line x1="2" y1="${2 + h / 2}" x2="${w}" y2="${2 + h / 2}" stroke="#1B2733" stroke-width="0.8"/>
    <circle cx="${w + 11}" cy="${2 + h / 2}" r="8" fill="#fff" stroke="#1B2733" stroke-width="1.2"/><text x="${w + 11}" y="${2 + h / 2 + 4}" font-size="11" text-anchor="middle" fill="#1B2733">${L}</text>`;
}

// ---------------------------------------------------------------- insertion arrows (manual style)
const ALONG_X = new Set(['4519', '32062', '50450', '32054', '3705', '3706', '3707', '30374', '63965', '89678']);
const ALONG_Z = new Set(['26287', '6538b', '32034', '32039', '24122']);
const ARROW_COL = CFG.theme === 'bouquet' ? '#D7262E' : '#35A853';
const arrowMat = new THREE.MeshBasicMaterial({ color: ARROW_COL, transparent: true, opacity: 0.95, depthTest: false, toneMapped: false });
const arrowOutline = new THREE.MeshBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9, depthTest: false, toneMapped: false, side: THREE.BackSide });
const shaftGeo = new THREE.CylinderGeometry(1, 1, 1, 12), headGeo = new THREE.ConeGeometry(2.6, 6, 16);
let arrows = [];
function clearArrows() { arrows.forEach(a => a.parent && a.parent.remove(a)); arrows = []; }
function partCentre(o) {
  const bb = SET.geoms[o.userData.pid].bb, c = new THREE.Vector3((bb[0][0] + bb[1][0]) / 2, (bb[0][1] + bb[1][1]) / 2, (bb[0][2] + bb[1][2]) / 2);
  return { c: c.applyMatrix4(o.userData.base), half: new THREE.Vector3((bb[1][0] - bb[0][0]) / 2, (bb[1][1] - bb[0][1]) / 2, (bb[1][2] - bb[0][2]) / 2) };
}
// the way a piece goes in, in the model's own (LDraw) frame: studded pieces come down from their own 'up',
// axles and connectors slide along their length, away from what is already built
function insertDir(o, centre) {
  const e = o.userData.base.elements, pid = o.userData.pid;
  const ax = ALONG_X.has(pid) ? new THREE.Vector3(e[0], e[1], e[2]) : ALONG_Z.has(pid) ? new THREE.Vector3(e[8], e[9], e[10]) : new THREE.Vector3(-e[4], -e[5], -e[6]);
  ax.normalize();
  if (ALONG_X.has(pid) || ALONG_Z.has(pid)) { const pc = partCentre(o).c; if (centre && pc.clone().sub(centre).dot(ax) < 0) ax.negate(); else if (!centre && ax.y > 0) ax.negate(); }
  return ax;
}
function makeArrow(from, to, r) {
  const g = new THREE.Group(), d = to.clone().sub(from), L = d.length(); d.normalize();
  const head = Math.min(L * 0.45, r * 7), shaft = new THREE.Mesh(shaftGeo, arrowMat), cone = new THREE.Mesh(headGeo, arrowMat);
  shaft.scale.set(r, L - head, r); shaft.position.y = (L - head) / 2;
  cone.scale.set(r, head / 6, r); cone.position.y = L - head / 2;
  const o1 = new THREE.Mesh(shaftGeo, arrowOutline); o1.scale.set(r * 1.6, L - head, r * 1.6); o1.position.copy(shaft.position);
  const o2 = new THREE.Mesh(headGeo, arrowOutline); o2.scale.set(r * 1.35, head / 6 * 1.2, r * 1.35); o2.position.copy(cone.position);
  g.add(o1, o2, shaft, cone); g.renderOrder = 10; g.children.forEach(c => { c.renderOrder = c.material === arrowOutline ? 9 : 10; });
  g.position.copy(from); g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d);
  return g;
}

// ---------------------------------------------------------------- show a page
let cur = -1, anim = null, camTween = null, active = null, fresh = [];
function go(i, instant) {
  i = Math.max(0, Math.min(pages.length - 1, i)); if (i === cur) return; const back = i < cur; cur = i; const p = pages[i];
  store.set(KEY + '/page', String(i));
  const R = rootFor(p.model);
  if (active && active !== R) active.root.visible = false; R.root.visible = true; active = R;
  const showAll = p.kind === 'intro' || p.kind === 'final';
  fresh = [];
  R.objs.forEach((o, k) => { o.userData.idx = k; const st = R.stepOf[k]; o.visible = st <= p.step; o.matrix.copy(o.userData.base); if (!showAll && st === p.step) fresh.push(o); });
  // insertion directions and arrows for the new pieces
  clearArrows();
  const old = R.objs.filter((o, k) => o.visible && !fresh.includes(o)), centre = old.length ? old.reduce((a, o) => a.add(partCentre(o).c), new THREE.Vector3()).multiplyScalar(1 / old.length) : null;
  const vb = new THREE.Box3(); R.objs.forEach(o => { if (o.visible) { const pc = partCentre(o); vb.expandByPoint(pc.c.clone().add(pc.half)); vb.expandByPoint(pc.c.clone().sub(pc.half)); } });
  const vsize = Math.max(vb.isEmpty() ? 100 : vb.getSize(new THREE.Vector3()).length(), 140);
  const AL = Math.max(16, Math.min(90, vsize * 0.22)), AR = Math.max(0.45, Math.min(2.0, vsize * 0.0042));
  const st = p.s || {}; const showArrows = !showAll && !(p.kind === 'main' && st.callout) && fresh.length && fresh.length <= 6;
  const groups = (p.kind === 'main' && st.groups) ? st.groups.map(g => g.map(k => R.objs[k])) : null;
  // directions worked out by instructions/check.py: the way each piece (or fitted sub-build) can slide in without
  // passing through the model; steps without them fall back to the heuristics below
  const insDir = new Map();
  if (!showAll && st.ins) st.ins.forEach(u => { if (u.k !== 'blocked' && u.k !== 'first') u.p.forEach(k => insDir.set(k, new THREE.Vector3(u.d[0], u.d[1], u.d[2]).normalize())); });
  if (groups) {
    // sub-builds fitted in this step move in as whole groups, away from what is already built
    groups.forEach(g => {
      const gc = g.reduce((a, o) => a.add(partCentre(o).c), new THREE.Vector3()).multiplyScalar(1 / g.length);
      let d = insDir.get(g[0].userData.idx);
      if (d) d = d.clone(); else { d = centre ? gc.clone().sub(centre) : new THREE.Vector3(0, -1, 0); d.y = Math.min(d.y, 0) * 0.3 + d.y * 0.7; if (d.lengthSq() < 1e-6) d.set(0, -1, 0); d.normalize(); }
      g.forEach(o => { o.userData.dir = d; o.userData.slide = AL * 1.3; });
      if (groups.length <= 6) {
        const bb = new THREE.Box3(); g.forEach(o => { const pc = partCentre(o); bb.expandByPoint(pc.c.clone().add(pc.half)); bb.expandByPoint(pc.c.clone().sub(pc.half)); });
        const half = bb.getSize(new THREE.Vector3()).multiplyScalar(0.5), ext = Math.abs(half.x * d.x) + Math.abs(half.y * d.y) + Math.abs(half.z * d.z);
        const end = gc.clone().addScaledVector(d, ext + AR * 3), a = makeArrow(end.clone().addScaledVector(d, AL), end, AR); R.root.add(a); arrows.push(a);
      }
    });
  } else {
    const cand = [];
    fresh.forEach(o => {
      const d = insDir.has(o.userData.idx) ? insDir.get(o.userData.idx).clone() : insertDir(o, centre); o.userData.dir = d; o.userData.slide = AL;
      const { c, half } = partCentre(o), ext = Math.abs(half.x * d.x) + Math.abs(half.y * d.y) + Math.abs(half.z * d.z);
      cand.push({ d, end: c.clone().addScaledVector(d, ext + AR * 3), c });
    });
    // one arrow per line of insertion: pieces stacked on the same line share the outermost arrow
    if (showArrows) cand.forEach((a, i) => {
      const hidden = cand.some((b, j) => j !== i && a.d.dot(b.d) > 0.95 && b.end.clone().sub(a.end).dot(a.d) > 0.5
        && b.end.clone().sub(a.end).projectOnPlane(a.d).length() < Math.max(6, AR * 6));
      if (!hidden) { const ar = makeArrow(a.end.clone().addScaledVector(a.d, AL), a.end, AR); R.root.add(ar); arrows.push(ar); }
    });
  }
  // page furniture
  document.body.classList.toggle('sub', p.kind === 'sub');
  $('#mult').textContent = (p.kind === 'sub' ? p.mult : p.sec.mult) + 'x';
  $('#mult').classList.toggle('on', (p.kind === 'sub' && p.mult > 1 && p.num === p.of));
  const meta = (p.s && p.s.meta) || {};
  if (p.kind === 'intro') { $('#stepno').innerHTML = `<small>${p.sec.bag ? 'Bag ' + p.sec.bag : ''}</small>`; }
  else if (p.kind === 'final') { $('#stepno').innerHTML = '<small>Finished</small>'; }
  else if (p.kind === 'sub') { $('#stepno').innerHTML = `${p.parentNum}<small>Sub-build, part ${p.num} of ${p.of}${p.total > 1 ? ' · make ' + p.total : ''}</small>`; }
  else { $('#stepno').innerHTML = `${p.num}<small>${p.s.callout ? 'Fit the sub-build' + (p.s.callout.mult > 1 ? 's' : '') : ''}</small>`; }
  $('#rotate').classList.toggle('on', !!meta.rotate && p.kind === 'main');
  // parts box: pieces new in this step (times the sub-build count)
  const counts = new Map();
  if (p.kind === 'main' || p.kind === 'sub') {
    const st = SET.models[p.model].steps[p.step];
    if (!st.callout || p.kind === 'sub') st.new.forEach(k => { const row = SET.models[p.model].parts[k]; const kk = row[0] + '|' + row[1]; counts.set(kk, (counts.get(kk) || 0) + 1); });
  }
  const mul = p.kind === 'sub' ? p.total : 1, box = $('#parts'); box.innerHTML = '';
  let axle = 0;
  [...counts].forEach(([k, n]) => {
    const [pid, code] = k.split('|'); const b = document.createElement('button'); b.type = 'button';
    b.innerHTML = `<img alt="" src="${icon(pid, +code)}"><span>${n * mul}x</span>`;
    b.title = ((SET.names || {})[pid] || pid) + ' — click to see it turn and where it goes'; b.onclick = () => showSpin(pid, +code, b); box.appendChild(b);
    if (AXLE_L[pid]) axle = Math.max(axle, AXLE_L[pid]);
  });
  $('#oneone').classList.toggle('on', !!axle); if (axle) draw11(axle);
  // right column
  $('#title').textContent = p.sec.title;
  const pdf = meta.pdf || (p.kind === 'intro' ? p.sec.pdf : null) || (p.kind === 'sub' ? findPdf(i) : null);
  $('#pdflink').innerHTML = pdf ? `Official instructions, <a href="${CFG.pdf}#page=${pdf}" target="_blank" rel="noopener">page ${pdf}</a>` : '';
  $('#note').textContent = meta.note || (p.kind === 'intro' ? (p.sec.note || (p.sec.mult > 1 ? `Build ${p.sec.mult} of these.` : 'Build one of these.')) : '');
  // progress
  const frac = i / (pages.length - 1); $('#bar').style.width = (frac * 100) + '%'; $('#dot').style.left = (frac * 100) + '%';
  $('#count').textContent = `${i + 1} / ${pages.length}`; $('#left').textContent = `${Math.max(0, totalPieces - p.placed)} pieces to go`;
  $('#prev').disabled = i === 0; $('#next').disabled = i === pages.length - 1;
  sel.value = p.kind === 'final' ? 'final' : String(CFG.sections.indexOf(p.sec));
  requestAnimationFrame(() => {
    resize(); frame(R, p, meta, instant || back);
    if (!instant && !back && fresh.length && !showAll) anim = { t0: performance.now(), objs: fresh };
  });
}
function findPdf(i) { for (let j = i; j < pages.length; j++) if (pages[j].kind === 'main') return pages[j].s.meta?.pdf; return null; }

// camera: fit what is on screen, from the step's view (or the section's)
function frame(R, p, meta, instant) {
  R.root.updateMatrixWorld(true);
  const box = new THREE.Box3(); R.objs.forEach(o => { if (o.visible) box.expandByObject(o); }); arrows.forEach(a => box.expandByObject(a));
  if (box.isEmpty()) return;
  const c = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3());
  const v = Object.assign({ az: -30, el: 20, zoom: 1 }, p.sec.view || {}, (p.kind === 'sub' ? SET.models[p.model].steps.at(-1).meta?.view : null) || {}, meta.view || {});
  const az = THREE.MathUtils.degToRad(v.az), el = THREE.MathUtils.degToRad(v.el);
  const dir = new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));
  const fov = THREE.MathUtils.degToRad(camera.fov), rad = Math.max(size.length() / 2, v.min ?? 70);
  const fitH = rad / Math.sin(fov / 2), fitW = rad / Math.sin(Math.atan(Math.tan(fov / 2) * camera.aspect));
  const d = Math.max(fitH, fitW) * 1.08 / v.zoom;
  const to = { pos: c.clone().addScaledVector(dir, d), target: c.clone() };
  // key light from the camera's upper left, its shadow box sized to the model
  const kd = new THREE.Vector3(Math.cos(0.75) * Math.sin(az - 0.7), Math.sin(0.75), Math.cos(0.75) * Math.cos(az - 0.7));
  key.position.copy(c).addScaledVector(kd, rad * 4); key.target.position.copy(c);
  const sc = key.shadow.camera; sc.left = sc.bottom = -rad * 1.15; sc.right = sc.top = rad * 1.15; sc.near = rad * 1.5; sc.far = rad * 7; sc.updateProjectionMatrix();
  camera.near = d / 50; camera.far = d * 50; camera.updateProjectionMatrix();
  controls.minDistance = d * 0.15; controls.maxDistance = d * 4;
  if (instant) { camera.position.copy(to.pos); controls.target.copy(to.target); camTween = null; }
  else camTween = { t0: performance.now(), from: { pos: camera.position.clone(), target: controls.target.clone() }, to };
}

// ---------------------------------------------------------------- loop
const ease = t => 1 - Math.pow(1 - t, 3);
const tmp = new THREE.Matrix4(), up = new THREE.Vector3();
function loop(now) {
  if (camTween) {
    const t = Math.min(1, (now - camTween.t0) / 550), e = ease(t);
    camera.position.lerpVectors(camTween.from.pos, camTween.to.pos, e); controls.target.lerpVectors(camTween.from.target, camTween.to.target, e);
    if (t >= 1) camTween = null;
  }
  controls.update();
  { const d = camera.position.distanceTo(controls.target), o = Math.max(0.12, Math.min(0.85, 1.5 - d / 2200)); mats.edge.opacity = o; mats.cond.uniforms.opacity.value = o; }
  if (anim) {
    const t = Math.min(1, (now - anim.t0 - 150) / 450), e = ease(Math.max(0, t));
    // new pieces slide in along their arrows (directions are in the model's own LDraw frame)
    anim.objs.forEach(o => { const d = o.userData.dir, k = (1 - e) * (o.userData.slide || 60); o.matrix.copy(tmp.makeTranslation(d.x * k, d.y * k, d.z * k)).multiply(o.userData.base); });
    if (t >= 1) { anim.objs.forEach(o => o.matrix.copy(o.userData.base)); anim = null; }
  }
  renderer.render(scene, camera);
  let hlObjs = hl.checked ? fresh : [];
  if (flash && now < flash.until && active) {
    const on = Math.floor((flash.until - now) / 260) % 2 === 0;
    const match = active.objs.filter(o => o.visible && o.userData.pid === flash.pid && o.userData.code === flash.code);
    hlObjs = on ? (match.filter(o => fresh.includes(o)).length ? match.filter(o => fresh.includes(o)) : match) : [];
  }
  if (hlObjs.length) outliner.render(scene, camera, hlObjs);
  if (spinObj && spinBox.classList.contains('on')) { spinObj.rotation.y = now / 700; spinObj.rotation.x = Math.sin(now / 1300) * 0.35; spinR.render(spinScene, spinCam); if (now > spinUntil) spinBox.classList.remove('on'); }
  requestAnimationFrame(loop);
}
addEventListener('pointerdown', e => { if (!e.target.closest('#spin,.parts')) spinBox.classList.remove('on'); });

$('#loading').remove();
iconLights.ready.then(() => { iconCache.clear(); const c = cur; cur = -1; go(c, true); });
const start = Q.has('page') ? +Q.get('page') : +(store.get(KEY + '/page') || 0);
go(isNaN(start) ? 0 : start, true);
requestAnimationFrame(loop);
window.pages = pages; window.goPage = i => go(i, true); window.ready = true;
