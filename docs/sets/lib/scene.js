// Shared renderer for the set instruction pages: LDraw geometry with outline edges and silhouette (conditional)
// lines, drawn flat and clean like a printed manual, plus a screen-space outline for newly added parts.
import * as THREE from 'three';

function b64(s) { const bin = atob(s), a = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return a; }
function unpack(q) { if (!q) return null; const i16 = new Int16Array(b64(q.b).buffer), f = new Float32Array(i16.length); for (let i = 0; i < i16.length; i++) f[i] = i16[i] / 32767 * q.s; return f; }

// ---------------------------------------------------------------- geometry cache
const geoCache = new Map();
export function partGeometry(SET, pid) {
  if (geoCache.has(pid)) return geoCache.get(pid);
  const g = SET.geoms[pid], out = { tri: null, fixed: [], edge: null, cond: null, bb: g.bb };
  const tri = f => { if (!f) return null; const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(f, 3)); geo.computeVertexNormals(); return geo; };
  out.tri = tri(unpack(g.tri));
  out.fixed = g.fixed.map(x => ({ c: x.c, geo: tri(unpack(x.tri)) }));
  const e = unpack(g.edge); if (e) { const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.BufferAttribute(e, 3)); out.edge = geo; }
  const c = unpack(g.cond);
  if (c) {
    const n = c.length / 12, pos = new Float32Array(n * 6), c0 = new Float32Array(n * 6), c1 = new Float32Array(n * 6), dir = new Float32Array(n * 6);
    for (let i = 0; i < n; i++) {
      const o = i * 12;
      for (let k = 0; k < 2; k++) {
        const v = i * 6 + k * 3;
        for (let j = 0; j < 3; j++) {
          pos[v + j] = c[o + k * 3 + j]; c0[v + j] = c[o + 6 + j]; c1[v + j] = c[o + 9 + j]; dir[v + j] = c[o + 3 + j] - c[o + j];
        }
      }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('control0', new THREE.BufferAttribute(c0, 3));
    geo.setAttribute('control1', new THREE.BufferAttribute(c1, 3)); geo.setAttribute('direction', new THREE.BufferAttribute(dir, 3));
    out.cond = geo;
  }
  geoCache.set(pid, out); return out;
}

// ---------------------------------------------------------------- materials
const matCache = new Map();
// ABS plastic: a glossy clear coat over a slightly satin base, so the studio environment shows as soft highlights.
const METAL = { 297: { metalness: 0.75, roughness: 0.32 }, 334: { metalness: 0.8, roughness: 0.25 }, 383: { metalness: 0.85, roughness: 0.2 } };
export function partMaterial(SET, code, style) {
  const k = code + '|' + (style.shading || 'abs');
  if (matCache.has(k)) return matCache.get(k);
  const col = (SET.colours[code] || ['#888888'])[0], met = METAL[code];
  const m = new THREE.MeshPhysicalMaterial({
    color: col, roughness: met ? met.roughness : 0.34, metalness: met ? met.metalness : 0,
    clearcoat: met ? 0.2 : 0.65, clearcoatRoughness: 0.12, specularIntensity: 0.6, envMapIntensity: 1.0,
    polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1, side: THREE.DoubleSide });
  matCache.set(k, m); return m;
}

// Soft studio lighting: an HDR environment for reflections plus a key light that casts soft shadows.
export function studio(renderer, scene, hdrUrl, opts = {}) {
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = opts.exposure ?? 1.0;
  const hemi = new THREE.HemisphereLight(0xffffff, 0x9aa4ae, opts.hemi ?? 0.55); scene.add(hemi);
  const key = new THREE.DirectionalLight(0xfff6ec, opts.key ?? 1.9); key.position.set(-1.2, 2.2, 1.6);
  if (opts.shadows) {
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.bias = -0.0004; key.shadow.normalBias = 0.6; key.shadow.radius = 4;
  }
  scene.add(key); scene.add(key.target);
  const rim = new THREE.DirectionalLight(0xe8f0ff, opts.rim ?? 0.6); rim.position.set(1.4, 0.6, -1.6); scene.add(rim);
  const ready = import('../../vendor/RGBELoader.js').then(({ RGBELoader }) => new Promise(res => {
    new RGBELoader().load(hdrUrl, tex => {
      const pm = new THREE.PMREMGenerator(renderer); scene.environment = pm.fromEquirectangular(tex).texture;
      scene.environmentIntensity = opts.env ?? 0.9; tex.dispose(); pm.dispose(); res();
    }, undefined, () => res());
  }));
  return { key, rim, hemi, ready };
}

export function edgeMaterial(style) {
  return new THREE.LineBasicMaterial({ color: style.edge ?? 0x1b1b1b, transparent: true, opacity: style.edgeOpacity ?? 0.9 });
}
export function condMaterial(style) {
  return new THREE.ShaderMaterial({
    uniforms: { color: { value: new THREE.Color(style.edge ?? 0x1b1b1b) }, opacity: { value: style.edgeOpacity ?? 0.9 } },
    transparent: true,
    vertexShader: `attribute vec3 control0; attribute vec3 control1; attribute vec3 direction; varying float discardFlag;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0); gl_Position = projectionMatrix * mv;
        vec4 c0 = projectionMatrix * modelViewMatrix * vec4(control0, 1.0); vec4 c1 = projectionMatrix * modelViewMatrix * vec4(control1, 1.0);
        vec4 p0 = projectionMatrix * modelViewMatrix * vec4(position, 1.0); vec4 p1 = projectionMatrix * modelViewMatrix * vec4(position + direction, 1.0);
        c0.xy /= c0.w; c1.xy /= c1.w; p0.xy /= p0.w; p1.xy /= p1.w;
        vec2 dir = p1.xy - p0.xy; vec2 norm = vec2(-dir.y, dir.x);
        float d0 = dot(normalize(norm), normalize(c0.xy - p1.xy)); float d1 = dot(normalize(norm), normalize(c1.xy - p1.xy));
        discardFlag = float(sign(d0) != sign(d1));
      }`,
    fragmentShader: `uniform vec3 color; uniform float opacity; varying float discardFlag;
      void main() { if (discardFlag > 0.5) discard; gl_FragColor = vec4(color, opacity); }`,
  });
}

// ---------------------------------------------------------------- one placed part
const FLIP = new THREE.Matrix4().makeRotationX(Math.PI);           // LDraw (-Y up) -> three (+Y up)
export function partMatrix(row) {
  const e = row.slice(2); const m = new THREE.Matrix4();
  m.set(e[0], e[1], e[2], e[9], e[3], e[4], e[5], e[10], e[6], e[7], e[8], e[11], 0, 0, 0, 1);
  return m;
}
export function makePart(SET, row, style, mats) {
  const [pid, code] = row; const g = partGeometry(SET, pid); const grp = new THREE.Group();
  if (g.tri) grp.add(new THREE.Mesh(g.tri, partMaterial(SET, code, style)));
  for (const f of g.fixed) if (f.geo) grp.add(new THREE.Mesh(f.geo, partMaterial(SET, f.c, style)));
  if (style.edges !== false) {
    if (g.edge) grp.add(new THREE.LineSegments(g.edge, mats.edge));
    if (g.cond) grp.add(new THREE.LineSegments(g.cond, mats.cond));
  }
  grp.matrixAutoUpdate = false; grp.matrix.copy(partMatrix(row)); grp.userData = { pid, code };
  grp.traverse(o => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return grp;
}

// ---------------------------------------------------------------- a whole model up to a step
export function modelRoot() { const r = new THREE.Group(); r.matrixAutoUpdate = false; r.matrix.copy(FLIP); return r; }

// steps -> for each step index, which part indices exist (cumulative) and which are new
export function stepParts(model, upto) {
  const have = [], fresh = [];
  model.steps.forEach((s, i) => { if (i <= upto) { have.push(...s.new); if (i === upto) fresh.push(...s.new); } });
  return { have, fresh };
}

// ---------------------------------------------------------------- outline of new parts (screen space)
export class Outliner {
  constructor(renderer, color = '#ffe500', width = 3) {
    this.r = renderer; this.color = new THREE.Color(color); this.width = width;
    this.mask = new THREE.WebGLRenderTarget(4, 4, { samples: 0 });
    this.maskMat = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide });
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
      uniforms: { mask: { value: null }, texel: { value: new THREE.Vector2() }, color: { value: this.color }, w: { value: width } },
      transparent: true, depthTest: false, depthWrite: false,
      vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
      fragmentShader: `uniform sampler2D mask; uniform vec2 texel; uniform vec3 color; uniform float w; varying vec2 vUv;
        void main(){
          float c = texture2D(mask, vUv).r; float m = 0.0;
          for (int i = 0; i < 16; i++) { float a = float(i) * 0.3927; for (int j = 1; j <= 3; j++) {
            vec2 o = vec2(cos(a), sin(a)) * texel * w * float(j) / 3.0; m = max(m, texture2D(mask, vUv + o).r); } }
          float edge = clamp(m - c, 0.0, 1.0);
          if (edge < 0.01) discard;
          gl_FragColor = vec4(color, edge);
        }`,
    }));
    this.qscene = new THREE.Scene(); this.qscene.add(this.quad); this.qcam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  }
  render(scene, camera, objects) {
    const r = this.r, size = r.getDrawingBufferSize(new THREE.Vector2());
    if (this.mask.width !== size.x || this.mask.height !== size.y) this.mask.setSize(size.x, size.y);
    this.quad.material.uniforms.texel.value.set(1 / size.x, 1 / size.y);
    this.quad.material.uniforms.w.value = this.width * r.getPixelRatio();
    // mask: only the new parts, white, with everything else as depth-only occluders hidden
    const vis = new Map(); scene.traverse(o => { vis.set(o, o.visible); });
    const keep = new Set(); objects.forEach(g => g.traverse(o => keep.add(o)));
    scene.traverse(o => { if ((o.isMesh || o.isLine || o.isLineSegments) && !keep.has(o)) o.visible = false; if (o.isLine || o.isLineSegments) o.visible = false; });
    const bg = scene.background, ov = scene.overrideMaterial; scene.background = null; scene.overrideMaterial = this.maskMat;
    const cc = r.getClearColor(new THREE.Color()), ca = r.getClearAlpha();
    r.setRenderTarget(this.mask); r.setClearColor(0x000000, 1); r.clear(); r.render(scene, camera); r.setRenderTarget(null); r.setClearColor(cc, ca);
    scene.overrideMaterial = ov; scene.background = bg; vis.forEach((v, o) => { o.visible = v; });
    this.quad.material.uniforms.mask.value = this.mask.texture;
    const ac = r.autoClear; r.autoClear = false; r.render(this.qscene, this.qcam); r.autoClear = ac;
  }
}
