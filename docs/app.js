// Sakura Planter: step-by-step 3D assembly. three.js r170, no build step.
import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { RGBELoader } from './vendor/RGBELoader.js';

const params = new URLSearchParams(location.search);
const SHOT = params.get('shot');                         // README image mode: ?shot=s5&w=1600&h=1000
const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches || !!SHOT;
const GUIDE = window.GUIDE.steps;
const FLOOR_Y = -83.8;                                   // underside of the feet, three.js Y-up millimetres
const $ = id => document.getElementById(id);

// ---------------------------------------------------------------- renderer, camera, controls
const canvas = $('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: !!SHOT });
renderer.setPixelRatio(SHOT ? 1 : Math.min(devicePixelRatio, 2));
renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = 0.88;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
scene.background = new THREE.Color('#BFAE90');
const camera = new THREE.PerspectiveCamera(30, 1, 5, 9000);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.minDistance = 160; controls.maxDistance = 2600;
controls.maxPolarAngle = Math.PI * 0.86;
function resize() {
  const w = SHOT && params.get('w') ? +params.get('w') : innerWidth, h = SHOT && params.get('h') ? +params.get('h') : innerHeight;
  renderer.setSize(w, h, !SHOT); if (SHOT) { canvas.style.width = w + 'px'; canvas.style.height = h + 'px'; }
  camera.aspect = w / h;
  // keep the model centred in the part of the screen the panel doesn't cover
  const panel = document.getElementById('panel'), ui = !document.body.classList.contains('shot') && panel;
  if (ui && w > 760) camera.setViewOffset(w, h, -Math.min(230, (panel.getBoundingClientRect().right + 10) / 2), 0, w, h);
  else if (ui) camera.setViewOffset(w, h, 0, Math.max(0, h - panel.getBoundingClientRect().top) / 2, w, h);
  else camera.clearViewOffset();
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize); resize();

// ---------------------------------------------------------------- light: studio HDR + one shadow-casting key
const pmrem = new THREE.PMREMGenerator(renderer);
const envReady = new Promise(res => new RGBELoader().load('assets/studio_small_03_1k.hdr', tex => {
  scene.environment = pmrem.fromEquirectangular(tex).texture; tex.dispose(); scene.environmentIntensity = 0.55; res();
}, undefined, () => res()));
const rig = new THREE.Group(); scene.add(rig);             // follows the camera's azimuth, like a photo studio
const key = new THREE.DirectionalLight(0xfff1e2, 1.5);
key.position.set(-520, 900, 640); key.castShadow = true;
key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.8;
Object.assign(key.shadow.camera, { left: -520, right: 520, top: 620, bottom: -420, near: 200, far: 2600 });
rig.add(key); rig.add(key.target); key.target.position.set(0, 80, 0);
const fill = new THREE.DirectionalLight(0xe8f0ff, 0.35); fill.position.set(700, 300, 300); rig.add(fill);

// ---------------------------------------------------------------- procedural linen sweep
function linenTextures(size = 1024, pitch = 8) {
  const n = size / pitch, rnd = mulberry(7);
  const noise = () => { const k = 32, a = Array.from({ length: k }, () => rnd()); return t => { const x = (t * k) % k, i = Math.floor(x), f = x - i, s = f * f * (3 - 2 * f); return a[i] * (1 - s) + a[(i + 1) % k] * s; }; };
  const warp = Array.from({ length: n }, () => ({ w: noise(), slub: noise(), tint: 0.93 + rnd() * 0.12 }));
  const weft = Array.from({ length: n }, () => ({ w: noise(), slub: noise(), tint: 0.93 + rnd() * 0.12 }));
  const H = new Float32Array(size * size), C = new Uint8ClampedArray(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const i = Math.floor(x / pitch), j = Math.floor(y / pitch), u = (x % pitch + 0.5) / pitch - 0.5, v = (y % pitch + 0.5) / pitch - 0.5;
    const A = warp[i], B = weft[j];
    const sa = Math.max(0, A.slub(y / size) - 0.72) * 2.2, sb = Math.max(0, B.slub(x / size) - 0.72) * 2.2;
    const hwA = 0.3 + 0.12 * A.w(y / size) + 0.18 * sa, hwB = 0.3 + 0.12 * B.w(x / size) + 0.18 * sb;
    const inA = Math.abs(u) < hwA, inB = Math.abs(v) < hwB, warpTop = (i + j) % 2 === 0;
    let h = 0, tint = 0.8;
    const profA = inA ? Math.cos(Math.PI * u / (2 * hwA)) : 0, profB = inB ? Math.cos(Math.PI * v / (2 * hwB)) : 0;
    if (inA && (warpTop || !inB)) { h = profA * (0.75 + 0.25 * Math.cos(Math.PI * v)); tint = A.tint * (1 + 0.06 * sa); }
    else if (inB) { h = profB * (0.75 + 0.25 * Math.cos(Math.PI * u)); tint = B.tint * (1 + 0.06 * sb); }
    H[y * size + x] = h;
    const shade = (0.8 + 0.2 * h) * tint, o = (y * size + x) * 4;
    C[o] = 184 * shade; C[o + 1] = 174 * shade; C[o + 2] = 158 * shade; C[o + 3] = 255;
  }
  const N = new Uint8ClampedArray(size * size * 4);
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const hx = H[y * size + (x + 1) % size] - H[y * size + (x - 1 + size) % size], hy = H[((y + 1) % size) * size + x] - H[((y - 1 + size) % size) * size + x];
    const nx = -hx * 1.6, ny = -hy * 1.6, l = Math.hypot(nx, ny, 1), o = (y * size + x) * 4;
    N[o] = (nx / l * 0.5 + 0.5) * 255; N[o + 1] = (ny / l * 0.5 + 0.5) * 255; N[o + 2] = (1 / l * 0.5 + 0.5) * 255; N[o + 3] = 255;
  }
  const mk = (data, srgb) => { const t = new THREE.DataTexture(data, size, size); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.generateMipmaps = true;
    t.minFilter = THREE.LinearMipmapLinearFilter; t.magFilter = THREE.LinearFilter; t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.needsUpdate = true; return t; };
  return { map: mk(C, true), normalMap: mk(N, false) };
}
function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function sweepGeometry(tile = 210) {
  // floor toward the camera (+z), a curved cove, then a wall behind (-z); UVs follow the cloth so the weave stays even
  const prof = [], R = 650;
  for (let z = 1900; z > -450; z -= 50) prof.push([z, 0]);
  for (let k = 0; k <= 24; k++) { const a = k / 24 * Math.PI / 2; prof.push([-450 - Math.sin(a) * R, R - Math.cos(a) * R]); }
  for (let y = R + 100; y <= 3000; y += 100) prof.push([-450 - R, y]);
  const xs = [-3000, -1500, 0, 1500, 3000], pos = [], uv = [], idx = [];
  let s = 0; const S = [0];
  for (let k = 1; k < prof.length; k++) { s += Math.hypot(prof[k][0] - prof[k - 1][0], prof[k][1] - prof[k - 1][1]); S.push(s); }
  prof.forEach(([z, y], k) => xs.forEach(x => { pos.push(x, y, z); uv.push(x / tile, -S[k] / tile); }));
  const W = xs.length;
  for (let k = 0; k < prof.length - 1; k++) for (let c = 0; c < W - 1; c++) {
    const a = k * W + c, b = a + 1, d = a + W, e = d + 1; idx.push(a, d, b, b, d, e);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals(); return g;
}
const linen = linenTextures();
const sweep = new THREE.Mesh(sweepGeometry(), new THREE.MeshStandardMaterial({ ...linen, roughness: 0.92, metalness: 0, normalScale: new THREE.Vector2(0.7, 0.7), side: THREE.DoubleSide }));
sweep.position.y = FLOOR_Y; sweep.receiveShadow = true; rig.add(sweep);

// ---------------------------------------------------------------- materials
const FADE_TO = new THREE.Color('#D9CFBE');
const matCache = {};
function materialSet(hex, kind) {
  const key = hex + kind; if (matCache[key]) return matCache[key];
  const color = new THREE.Color(hex);
  let full;
  if (kind === 'clear') full = new THREE.MeshPhysicalMaterial({ color, roughness: 0.32, transmission: 0.9, thickness: 2.5, ior: 1.5, transparent: true });
  else if (kind === 'tpu') full = new THREE.MeshPhysicalMaterial({ color: new THREE.Color('#121212'), roughness: 0.85, envMapIntensity: 0.35 });
  else if (kind === 'pla') full = new THREE.MeshPhysicalMaterial({ color: new THREE.Color('#E2D5BC'), roughness: 0.58, clearcoat: 0.06 });   // bone PLA, a shade deeper than its swatch so it reads off-white on screen
  else if (kind === 'paint') full = new THREE.MeshStandardMaterial({ color, roughness: 0.6 });
  else full = new THREE.MeshPhysicalMaterial({ color, roughness: 0.3, clearcoat: 0.35, clearcoatRoughness: 0.25 });   // LEGO ABS
  full.side = THREE.DoubleSide;
  const faded = new THREE.MeshStandardMaterial({ color: color.clone().lerp(FADE_TO, 0.62), roughness: 0.85, side: THREE.DoubleSide });
  const ghost = new THREE.MeshStandardMaterial({ color, roughness: 0.6, transparent: true, opacity: 0.18, depthWrite: false, side: THREE.DoubleSide });
  return (matCache[key] = { full, faded, ghost });
}

// ---------------------------------------------------------------- model
function b64(s) { const bin = atob(s), a = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return a; }
function geom(g) {
  if (!g) return null;
  const q = new Int16Array(b64(g.b).buffer), pos = new Float32Array(q.length);
  for (let i = 0; i < q.length; i++) pos[i] = q[i] / 32767 * g.s;
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.computeVertexNormals(); return geo;
}
const items = [];      // {obj, kind, step, inst?, base?, dir}
const MAIN = GUIDE.map((g, i) => [g.id, i]).filter(([id]) => /^s\d+$/.test(id));
const stepIndexOfLego = k => GUIDE.findIndex(g => g.id === 's' + k);
const PRINTED_STEP = { Planter: 's1', Paint: 's1', Foot: 's1', 'Soil core': 's2', 'Soil mat': 's2', Trunk: 's3', 'Joint sleeve': 's3', Branch: 's4' };
const KIND_MAT = { Planter: 'pla', 'Soil core': 'pla', Trunk: 'pla', Branch: 'pla', 'Soil mat': 'tpu', Foot: 'clear', 'Joint sleeve': 'clear', Paint: 'paint' };

function buildModel() {
  const D = window.SAKURA, ST = window.STEPS.steps;
  const m4 = new THREE.Matrix4(), geoCache = {};
  const partGeo = pid => geoCache[pid] || (geoCache[pid] = { inh: geom(D.geoms[pid].inh), fixed: D.geoms[pid].fixed.map(f => ({ c: f.c, geo: geom(f.g) })) });
  const buckets = {};
  D.inst.forEach((r, i) => { const k = r[0] + '|' + r[1] + '|' + ST[i]; (buckets[k] = buckets[k] || []).push(r); });
  Object.entries(buckets).forEach(([k, list]) => {
    const step = stepIndexOfLego(+k.split('|')[2]);
    const pg = partGeo(list[0][0]);
    list.sort((a, b) => a[13] - b[13]);                  // bottom pieces arrive first
    const base = list.map(r => { const e = r.slice(3); return new THREE.Matrix4().set(e[0], e[1], e[2], e[9], e[3], e[4], e[5], e[10], e[6], e[7], e[8], e[11], 0, 0, 0, 1); });
    const add = (geo, hex) => {
      if (!geo) return; const ms = materialSet(hex, 'lego');
      const im = new THREE.InstancedMesh(geo, ms.full, list.length); im.castShadow = im.receiveShadow = true;
      base.forEach((m, i) => im.setMatrixAt(i, m)); scene.add(im);
      items.push({ obj: im, kind: 'LEGO', step, ms, base, dir: new THREE.Vector3(0, 1, 0), dist: 70 });
    };
    add(pg.inh, list[0][1]); pg.fixed.forEach(f => add(f.geo, f.c));
  });
  D.pla.forEach(p => {
    const kind = p.name.startsWith('Paint') ? 'Paint' : p.name.replace(/ \d+$/, '');
    const g = geom(p); g.computeBoundingBox(); const ctr = g.boundingBox.getCenter(new THREE.Vector3());
    const ms = materialSet(p.c, KIND_MAT[kind] || 'pla');
    const mesh = new THREE.Mesh(g, ms.full); mesh.castShadow = kind !== 'Paint' && !p.clear; mesh.receiveShadow = true; scene.add(mesh);
    let dir = new THREE.Vector3(0, 1, 0), dist = 160;
    if (kind === 'Foot') { dir.set(0, -1, 0); dist = 45; }
    if (kind === 'Soil core') dist = 140;
    if (kind === 'Soil mat') dist = 190;
    if (kind === 'Trunk') dist = 260;
    if (kind === 'Joint sleeve' || kind === 'Branch') {
      const h = new THREE.Vector3(ctr.x, 0, ctr.z).normalize(); dir.set(h.x * 0.75, 0.65, h.z * 0.75).normalize(); dist = kind === 'Branch' ? 90 : 35;
    }
    if (kind === 'Paint') dist = 0;
    items.push({ obj: mesh, kind, name: p.name, step: GUIDE.findIndex(s => s.id === PRINTED_STEP[kind]), ms, dir, dist, ctr });
  });
}

// ---------------------------------------------------------------- step state
let current = 0, fadeEarlier = true, anim = null;
const has = (list, kind) => (list || []).includes(kind);
function applyStep(idx, animate) {
  const S = GUIDE[idx];
  flipped = !!S.flip;
  const mainPos = idx;                                  // step order in GUIDE is the build order
  const newOnes = [];
  items.forEach(it => {
    let visible, mode = 'full', isNew = false;
    if (S.only) { visible = it.kind !== 'LEGO' && S.only.includes(it.kind); isNew = has(S.new, it.kind); }
    else {
      visible = it.step >= 0 && it.step <= mainPos;
      isNew = it.step === mainPos && (it.kind === 'LEGO' || has(S.new, it.kind));
      if (!isNew && fadeEarlier && it.kind !== 'Paint') mode = 'faded';
      if (it.step < mainPos && it.kind === 'Paint') mode = fadeEarlier ? 'faded' : 'full';
      if (has(S.ghost, it.kind)) mode = 'ghost';
    }
    it.obj.visible = visible;
    it.obj.material = it.ms[mode];
    it.obj.castShadow = visible && mode !== 'ghost' && it.kind !== 'Paint' && it.kind !== 'Foot' && it.kind !== 'Joint sleeve';
    resetPose(it);
    if (visible && isNew && it.dist > 0) newOnes.push(it);
  });
  if (animate && !REDUCED && newOnes.length) startAnim(newOnes);
  moveCamera(S.cam, animate && !REDUCED);
  renderPanel(idx);
}
// "flip" steps show the planter upside down on its rim (as you hold it to fit the feet)
const FLIP_DY = FLOOR_Y - (-12.0);                       // rim (y = +12) lands on the floor
let flipped = false;
function setPose(it, off) {
  if (flipped) { it.obj.rotation.set(Math.PI, 0, 0); it.obj.position.set(off.x, -off.y + FLIP_DY, -off.z); }
  else { it.obj.rotation.set(0, 0, 0); it.obj.position.copy(off); }
}
const ZERO = new THREE.Vector3();
function resetPose(it) {
  if (it.base) { it.base.forEach((m, i) => it.obj.setMatrixAt(i, m)); it.obj.instanceMatrix.needsUpdate = true; }
  else setPose(it, ZERO);
}
const ease = t => 1 - Math.pow(1 - t, 3);
function startAnim(list) {
  const t0 = performance.now(); let order = 0;
  const jobs = list.map(it => ({ it, start: (order++) * 90 }));
  anim = { t0, jobs, dur: 900 };
}
const tmpM = new THREE.Matrix4(), tmpV = new THREE.Vector3();
function stepAnim(now) {
  if (!anim) return;
  let running = false;
  for (const { it, start } of anim.jobs) {
    if (it.base) {
      const n = it.base.length;
      for (let i = 0; i < n; i++) {
        const t = Math.min(1, Math.max(0, (now - anim.t0 - start - i * Math.min(40, 1400 / n)) / anim.dur));
        if (t < 1) running = true;
        tmpV.copy(it.dir).multiplyScalar(it.dist * (1 - ease(t)));
        tmpM.copy(it.base[i]); tmpM.elements[12] += tmpV.x; tmpM.elements[13] += tmpV.y; tmpM.elements[14] += tmpV.z;
        it.obj.setMatrixAt(i, tmpM);
      }
      it.obj.instanceMatrix.needsUpdate = true;
    } else {
      const t = Math.min(1, Math.max(0, (now - anim.t0 - start) / (anim.dur * 1.3)));
      if (t < 1) running = true;
      setPose(it, tmpV.copy(it.dir).multiplyScalar(it.dist * (1 - ease(t))));
    }
  }
  if (!running) anim = null;
}

// ---------------------------------------------------------------- camera moves
let camTween = null;
function camPose(c) {
  const az = THREE.MathUtils.degToRad(c.az), el = THREE.MathUtils.degToRad(c.el);
  const target = new THREE.Vector3(c.tx || 0, c.ty, c.tz || 0);
  return { target, pos: target.clone().add(new THREE.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az)).multiplyScalar(c.dist * camScale())) };
}
function camScale() { return camera.aspect < 1 ? 1.25 / Math.max(camera.aspect, 0.5) : 1; }
function moveCamera(c, animate) {
  const p = camPose(c);
  if (!animate) { camera.position.copy(p.pos); controls.target.copy(p.target); camTween = null; return; }
  camTween = { t0: performance.now(), from: { pos: camera.position.clone(), target: controls.target.clone() }, to: p };
}
function stepCam(now) {
  if (!camTween) return;
  const t = Math.min(1, (now - camTween.t0) / 1100), e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  camera.position.lerpVectors(camTween.from.pos, camTween.to.pos, e); controls.target.lerpVectors(camTween.from.target, camTween.to.target, e);
  if (t >= 1) camTween = null;
}

// ---------------------------------------------------------------- panel and rail
const PRINTED_INFO = {
  Planter: ['Planter', '#EDE4D3'], Paint: ['Acrylic paint (motif)', '#F2A7C3'], Foot: ['Feet ×6, clear TPU', '#DCE6E8'],
  'Joint sleeve': ['Joint sleeves ×5, clear TPU', '#DCE6E8'], 'Soil core': ['Soil core, bone PLA', '#EDE4D3'],
  'Soil mat': ['Soil mat, black TPU', '#202020'], Trunk: ['Trunk, bone PLA', '#EDE4D3'], Branch: ['Branches 1–5, bone PLA', '#EDE4D3']
};
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function renderPanel(idx) {
  const S = GUIDE[idx];
  const nMain = MAIN.length, mi = MAIN.findIndex(([id]) => id === S.id);
  $('where').textContent = mi >= 0 ? `Step ${mi + 1} of ${nMain}` : `${S.label}: before you start`;
  $('title').textContent = S.title;
  $('body').innerHTML = S.body.map(p => `<p>${esc(p)}</p>`).join('');
  $('tips').innerHTML = S.tips && S.tips.length ? `<div class="tips"><h3>Notes</h3><ul>${S.tips.map(t => `<li>${esc(t)}</li>`).join('')}</ul></div>` : '';
  const pr = (S.new || []).filter(n => PRINTED_INFO[n]);
  $('printed').innerHTML = pr.length ? `<div class="printed"><h3>Printed parts</h3><div class="chips">${pr.map(n => `<span class="chip"><i style="background:${PRINTED_INFO[n][1]}"></i>${esc(PRINTED_INFO[n][0])}</span>`).join('')}</div></div>` : '';
  const L = S.lego ? (window.STEPS.lists[String(S.lego)] || []) : [];
  const tot = L.reduce((a, p) => a + p.n, 0);
  $('parts').innerHTML = L.length ? `<div class="parts"><h3>LEGO pieces</h3><ul>${L.map(p => `<li><b>${p.n}×</b><i style="background:${p.hex}"></i><span>${esc(p.colour)} ${esc(p.name)}</span><small>${esc(p.part)}</small></li>`).join('')}</ul><div class="total">${tot} pieces in this step</div></div>` : '';
  $('prev').disabled = idx === 0; $('next').disabled = idx === GUIDE.length - 1;
  $('next').textContent = idx === GUIDE.length - 2 ? 'Last step' : 'Next step';
  document.querySelectorAll('#nodes li').forEach((li, i) => { li.classList.toggle('done', i < idx); li.classList.toggle('current', i === idx); li.querySelector('button').setAttribute('aria-current', i === idx ? 'step' : 'false'); });
  $('panel').scrollTop = 0;
  if (!SHOT) history.replaceState(null, '', '#' + S.id);
}
function buildRail() {
  const n = GUIDE.length, ys = [], pts = [];
  for (let i = 0; i < n; i++) { const y = 30 + 9 * Math.sin(i * 1.3 + 0.4) + 4 * Math.sin(i * 2.9); ys.push(y); pts.push([i / (n - 1) * 1000, y]); }
  let d = `M ${pts[0][0]} ${pts[0][1] + 4}`;
  for (let i = 1; i < n; i++) { const [x0, y0] = pts[i - 1], [x1, y1] = pts[i]; d += ` C ${x0 + 40} ${y0 - 6}, ${x1 - 40} ${y1 + 6}, ${x1} ${y1}`; }
  $('twigpath').setAttribute('d', d);
  const petal = '<g class="petals">' + [0, 72, 144, 216, 288].map(a => `<ellipse cx="15" cy="7.5" rx="5.2" ry="7" transform="rotate(${a} 15 15)"/>`).join('') + '</g><circle class="heart" cx="15" cy="15" r="2.6"/>';
  const yScale = innerWidth <= 760 ? 44 / 60 : 44 / 60, y0 = innerWidth <= 760 ? 12 : 18;
  $('nodes').innerHTML = GUIDE.map((s, i) => `<li style="--y:${y0 + ys[i] * yScale}px"><button type="button" aria-label="${esc(s.label)}: ${esc(s.title)}"><svg viewBox="0 0 30 30">${petal}</svg></button><span>${esc(s.label.replace('Step ', ''))}</span></li>`).join('');
  document.querySelectorAll('#nodes button').forEach((b, i) => b.addEventListener('click', () => go(i)));
}
function go(i) { i = Math.max(0, Math.min(GUIDE.length - 1, i)); if (i === current) return; current = i; applyStep(i, true); }

// ---------------------------------------------------------------- loop
function frame(now) {
  stepAnim(now); stepCam(now); controls.update();
  rig.rotation.y = Math.atan2(camera.position.x - controls.target.x, camera.position.z - controls.target.z);
  renderer.render(scene, camera);
  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------- start
(async function start() {
  if (SHOT) { if (params.get('ui') !== '1') document.body.classList.add('shot'); $('loading').style.display = 'none'; }
  try { await window.dataReady; } catch (e) { $('loading').classList.add('error'); $('loading').querySelector('p').textContent = 'The model data could not be loaded (' + e.message + '). Serve the docs/ folder over http.'; return; }
  buildModel(); buildRail(); resize();
  const fromHash = GUIDE.findIndex(s => '#' + s.id === location.hash);
  current = SHOT ? Math.max(0, GUIDE.findIndex(s => s.id === SHOT)) : (fromHash >= 0 ? fromHash : 0);
  if (SHOT && params.get('fade') === '0') fadeEarlier = false;
  $('fade').checked = fadeEarlier;
  applyStep(current, false);
  if (SHOT && params.get('cam')) { const [az, el, dist, ty, tx, tz] = params.get('cam').split(',').map(Number); moveCamera({ az, el, dist, ty, tx, tz }, false); }
  await envReady;
  $('loading').classList.add('done');
  $('prev').onclick = () => go(current - 1); $('next').onclick = () => go(current + 1);
  $('replay').onclick = () => applyStep(current, true);
  $('fade').onchange = e => { fadeEarlier = e.target.checked; applyStep(current, false); };
  addEventListener('keydown', e => { if (e.target.tagName === 'INPUT') return; if (e.key === 'ArrowRight') go(current + 1); if (e.key === 'ArrowLeft') go(current - 1); });
  canvas.addEventListener('dblclick', () => moveCamera(GUIDE[current].cam, !REDUCED));
  if (SHOT) {                                            // render on demand only: software GL is slow
    controls.update(); rig.rotation.y = Math.atan2(camera.position.x - controls.target.x, camera.position.z - controls.target.z);
    const t0 = performance.now(); renderer.render(scene, camera); renderer.render(scene, camera);
    window.shotMs = performance.now() - t0; window.shotReady = true;
  } else requestAnimationFrame(frame);
})();
