/**
 * CityGate — Interactive Three.js municipal permit visualization
 * Reactive to agent pipeline stages with orbit, hover, and scan effects.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const STAGE_THEME = {
    idle:       { color: 0x334155, emissive: 0x111827, scan: 0x64748b, speed: 0.15 },
    intake:     { color: 0xFBBF24, emissive: 0x92400e, scan: 0xFBBF24, speed: 0.4 },
    vault:      { color: 0xA78BFA, emissive: 0x5b21b6, scan: 0xA78BFA, speed: 0.35 },
    parse:      { color: 0xFBBF24, emissive: 0xb45309, scan: 0xFF6B00, speed: 0.5 },
    city_code:  { color: 0x3B82F6, emissive: 0x1e3a8a, scan: 0x3B82F6, speed: 0.45 },
    compliance: { color: 0x3B82F6, emissive: 0x1d4ed8, scan: 0x60a5fa, speed: 0.4 },
    form_fill:  { color: 0x3B82F6, emissive: 0x2563eb, scan: 0x93c5fd, speed: 0.35 },
    hitl:       { color: 0xFF6B00, emissive: 0xc2410c, scan: 0xFF6B00, speed: 0.25 },
    complete:   { color: 0x22C55E, emissive: 0x15803d, scan: 0x4ade80, speed: 0.2 },
    error:      { color: 0xEF4444, emissive: 0x991b1b, scan: 0xf87171, speed: 0.3 },
};

const BUILDING_META = [
    { id: 'intake',     label: 'Intake',     x: -3.2, z: -1.5, h: 1.2, w: 1.4, d: 1.4 },
    { id: 'vault',      label: 'PII Vault',  x: -1.6, z: -2.8, h: 0.9, w: 1.1, d: 1.1 },
    { id: 'parse',      label: 'Doc Parse',  x: 1.6,  z: -2.8, h: 1.0, w: 1.2, d: 1.2 },
    { id: 'city_code',  label: 'City Code',  x: 3.2,  z: -1.5, h: 1.3, w: 1.3, d: 1.3 },
    { id: 'compliance', label: 'Compliance', x: 3.0,  z: 1.8,  h: 1.5, w: 1.5, d: 1.5 },
    { id: 'form_fill',  label: 'Form Fill',  x: 0,    z: 3.2,  h: 1.1, w: 1.6, d: 1.2 },
    { id: 'hitl',       label: 'HITL Gate',  x: -3.0, z: 1.8,  h: 1.4, w: 1.4, d: 1.4 },
];

export class PermitScene3D {
    constructor(containerId = 'cad-container') {
        this.container = document.getElementById(containerId);
        this.canvas = document.getElementById('three-canvas');
        this.tooltip = document.getElementById('three-tooltip');
        this.coordsChip = document.getElementById('active-coordinates');
        this.emptyPlaceholder = document.getElementById('empty-viewport-text');

        this.stage = 'idle';
        this.active = false;
        this.clock = new THREE.Clock();
        this.raycaster = new THREE.Raycaster();
        this.pointer = new THREE.Vector2();
        this.hovered = null;
        this.buildings = new Map();
        this.particles = null;
        this.scanPlane = null;
        this.scanY = 0;
        this.scanDir = 1;
        this.dataLines = null;
        this.hubRing = null;
        this.complianceScore = 0;

        if (!this.container || !this.canvas) return;
        this._init();
        this._bindEvents();
        this._animate();
    }

    _init() {
        const w = this.container.clientWidth || 600;
        const h = this.container.clientHeight || 400;

        this.scene = new THREE.Scene();
        this.scene.fog = new THREE.FogExp2(0x0a0f14, 0.045);

        this.camera = new THREE.PerspectiveCamera(48, w / h, 0.1, 100);
        this.camera.position.set(6, 5.5, 7);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
        });
        this.renderer.setSize(w, h);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setClearColor(0x0f1419, 1);

        this.controls = new OrbitControls(this.camera, this.canvas);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.06;
        this.controls.maxPolarAngle = Math.PI / 2.1;
        this.controls.minDistance = 4;
        this.controls.maxDistance = 16;
        this.controls.autoRotate = true;
        this.controls.autoRotateSpeed = 0.6;

        // Lights
        this.scene.add(new THREE.AmbientLight(0x404860, 0.6));
        const key = new THREE.DirectionalLight(0xff6b00, 0.8);
        key.position.set(5, 8, 4);
        this.scene.add(key);
        const fill = new THREE.PointLight(0x3b82f6, 0.5, 20);
        fill.position.set(-4, 3, -3);
        this.scene.add(fill);

        // Grid
        const grid = new THREE.GridHelper(14, 28, 0x1e293b, 0x162029);
        grid.position.y = -0.01;
        this.scene.add(grid);
        this.grid = grid;
        if (Array.isArray(grid.material)) {
            grid.material.forEach(m => { m.transparent = true; });
        }

        // Central permit hub
        const hubGeo = new THREE.CylinderGeometry(1.1, 1.3, 2.2, 6);
        const hubMat = new THREE.MeshStandardMaterial({
            color: 0x1a2332,
            emissive: 0x0f172a,
            metalness: 0.7,
            roughness: 0.35,
            wireframe: false,
        });
        this.hub = new THREE.Mesh(hubGeo, hubMat);
        this.hub.position.y = 1.1;
        this.hub.userData = { id: 'hub', label: 'Permit Hub', interactive: true };
        this.scene.add(this.hub);

        const hubEdges = new THREE.EdgesGeometry(hubGeo);
        this.hubWire = new THREE.LineSegments(
            hubEdges,
            new THREE.LineBasicMaterial({ color: 0xff6b00, transparent: true, opacity: 0.5 })
        );
        this.hubWire.position.copy(this.hub.position);
        this.scene.add(this.hubWire);

        // Hub ring
        const ringGeo = new THREE.TorusGeometry(1.6, 0.03, 8, 48);
        this.hubRing = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({
            color: 0xff6b00, transparent: true, opacity: 0.35,
        }));
        this.hubRing.rotation.x = Math.PI / 2;
        this.hubRing.position.y = 0.05;
        this.scene.add(this.hubRing);

        // Agent buildings
        BUILDING_META.forEach((b) => {
            const geo = new THREE.BoxGeometry(b.w, b.h, b.d);
            const mat = new THREE.MeshStandardMaterial({
                color: 0x1a2332,
                emissive: 0x0a0f14,
                metalness: 0.5,
                roughness: 0.5,
                transparent: true,
                opacity: 0.85,
            });
            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.set(b.x, b.h / 2, b.z);
            mesh.userData = { id: b.id, label: b.label, interactive: true, baseH: b.h };

            const edges = new THREE.EdgesGeometry(geo);
            const wire = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({
                color: 0x334155, transparent: true, opacity: 0.6,
            }));
            wire.position.copy(mesh.position);
            mesh.userData.wire = wire;

            this.scene.add(mesh);
            this.scene.add(wire);
            this.buildings.set(b.id, mesh);
        });

        // Data flow lines hub → buildings
        this._rebuildDataLines(0x334155);

        // Scan plane
        const scanGeo = new THREE.PlaneGeometry(12, 12);
        const scanMat = new THREE.MeshBasicMaterial({
            color: 0xff6b00,
            transparent: true,
            opacity: 0.08,
            side: THREE.DoubleSide,
            depthWrite: false,
        });
        this.scanPlane = new THREE.Mesh(scanGeo, scanMat);
        this.scanPlane.rotation.x = -Math.PI / 2;
        this.scanPlane.visible = false;
        this.scene.add(this.scanPlane);

        // Particles
        this._createParticles(0xff6b00);

        // Ground glow disc
        const discGeo = new THREE.CircleGeometry(3, 32);
        const discMat = new THREE.MeshBasicMaterial({
            color: 0xff6b00, transparent: true, opacity: 0.06,
        });
        this.groundGlow = new THREE.Mesh(discGeo, discMat);
        this.groundGlow.rotation.x = -Math.PI / 2;
        this.groundGlow.position.y = 0.02;
        this.scene.add(this.groundGlow);
    }

    _createParticles(color) {
        if (this.particles) {
            this.scene.remove(this.particles);
            this.particles.geometry.dispose();
            this.particles.material.dispose();
        }
        const count = 120;
        const positions = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 10;
            positions[i * 3 + 1] = Math.random() * 4;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 10;
        }
        const geo = new THREE.BufferGeometry();
        geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const mat = new THREE.PointsMaterial({
            color, size: 0.06, transparent: true, opacity: 0.7,
            blending: THREE.AdditiveBlending, depthWrite: false,
        });
        this.particles = new THREE.Points(geo, mat);
        this.particles.visible = false;
        this.scene.add(this.particles);
    }

    _rebuildDataLines(color) {
        if (this.dataLines) {
            this.scene.remove(this.dataLines);
            this.dataLines.geometry.dispose();
            this.dataLines.material.dispose();
        }
        const pts = [];
        BUILDING_META.forEach((b) => {
            pts.push(new THREE.Vector3(0, 1.5, 0));
            pts.push(new THREE.Vector3(b.x, b.h, b.z));
        });
        const geo = new THREE.BufferGeometry().setFromPoints(pts);
        this.dataLines = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({
            color, transparent: true, opacity: 0.25,
        }));
        this.scene.add(this.dataLines);
    }

    _bindEvents() {
        this._onResize = () => this.resize();
        window.addEventListener('resize', this._onResize);

        this.canvas.addEventListener('pointermove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            this.pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
            this.pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
        });

        this.canvas.addEventListener('pointerdown', () => {
            this.controls.autoRotate = false;
        });

        this.canvas.addEventListener('click', () => this._onClick());
    }

    _getInteractiveMeshes() {
        return [this.hub, ...this.buildings.values()];
    }

    _onClick() {
        this.raycaster.setFromCamera(this.pointer, this.camera);
        const hits = this.raycaster.intersectObjects(this._getInteractiveMeshes());
        if (hits.length > 0) {
            const { id, label } = hits[0].object.userData;
            if (this.coordsChip) {
                this.coordsChip.textContent = `${label.toUpperCase()} · STAGE: ${id.toUpperCase()}`;
            }
            this.setStage(id === 'hub' ? this.stage : id, true);
        }
    }

    resize() {
        if (!this.container || !this.renderer) return;
        const w = this.container.clientWidth;
        const h = this.container.clientHeight;
        if (w === 0 || h === 0) return;
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(w, h);
    }

    activate(formType = 'business_license', city = 'San Antonio') {
        this.active = true;
        this.container?.classList.add('has-content');
        if (this.emptyPlaceholder) this.emptyPlaceholder.style.display = 'none';
        if (this.coordsChip) {
            this.coordsChip.style.display = 'block';
            this.coordsChip.textContent = `${city.toUpperCase()} · ${formType.replace('_', ' ').toUpperCase()}`;
        }
        this.canvas.style.opacity = '1';
        this.setStage('intake');
    }

    deactivate() {
        this.active = false;
        this.setStage('idle');
        if (this.emptyPlaceholder) this.emptyPlaceholder.style.display = 'flex';
        if (this.coordsChip) this.coordsChip.style.display = 'none';
        this.container?.classList.remove('has-content');
    }

    setStage(stageId, fromClick = false) {
        this.stage = stageId;
        const theme = STAGE_THEME[stageId] || STAGE_THEME.idle;
        const isProcessing = !['idle', 'complete', 'error'].includes(stageId);

        this.controls.autoRotate = !fromClick && (stageId === 'idle' || isProcessing);

        // Theme colors
        const c = new THREE.Color(theme.color);
        this.hub.material.emissive.setHex(theme.emissive);
        this.hubWire.material.color.copy(c);
        this.hubRing.material.color.copy(c);
        this.groundGlow.material.color.copy(c);
        if (Array.isArray(this.grid.material)) {
            this.grid.material.forEach(m => { m.opacity = isProcessing ? 0.9 : 0.5; });
        }

        if (this.dataLines) {
            this.dataLines.material.color.setHex(theme.color);
            this.dataLines.material.opacity = isProcessing ? 0.5 : 0.2;
        }

        // Highlight active building
        this.buildings.forEach((mesh, id) => {
            const isActive = id === stageId;
            const wire = mesh.userData.wire;
            if (isActive) {
                mesh.material.emissive.setHex(theme.emissive);
                mesh.material.opacity = 1;
                mesh.scale.y = 1.15;
                mesh.position.y = (mesh.userData.baseH / 2) * 1.15;
                wire.material.color.setHex(theme.color);
                wire.material.opacity = 1;
            } else {
                mesh.material.emissive.setHex(0x0a0f14);
                mesh.material.opacity = 0.7;
                mesh.scale.y = 1;
                mesh.position.y = mesh.userData.baseH / 2;
                wire.material.color.setHex(0x334155);
                wire.material.opacity = 0.4;
            }
            if (wire) wire.position.copy(mesh.position);
        });

        // Scan + particles
        this.scanPlane.visible = isProcessing;
        this.scanPlane.material.color.setHex(theme.scan);
        this.particles.visible = isProcessing || stageId === 'complete';
        if (this.particles) this.particles.material.color.setHex(theme.color);

        if (stageId === 'hitl') {
            this.hubRing.material.opacity = 0.8;
        } else if (stageId === 'complete') {
            this._burstComplete();
        }
    }

    setComplianceScore(score) {
        this.complianceScore = score;
        const scale = 0.8 + (score / 100) * 0.6;
        this.hub.scale.set(scale, scale, scale);
        this.hubWire.scale.copy(this.hub.scale);
    }

    _burstComplete() {
        this._createParticles(0x22c55e);
        this.particles.visible = true;
    }

    _animate() {
        requestAnimationFrame(() => this._animate());
        if (!this.renderer) return;

        const t = this.clock.getElapsedTime();
        const theme = STAGE_THEME[this.stage] || STAGE_THEME.idle;

        this.controls.update();

        // Hub pulse
        if (this.hub) {
            this.hub.rotation.y = t * 0.15;
            this.hubWire.rotation.y = this.hub.rotation.y;
        }
        if (this.hubRing) {
            this.hubRing.rotation.z = t * (this.stage === 'hitl' ? 1.2 : 0.3);
            this.hubRing.material.opacity = this.stage === 'hitl'
                ? 0.5 + Math.sin(t * 4) * 0.3
                : 0.35;
        }

        // Scan plane sweep
        if (this.scanPlane?.visible) {
            this.scanY += theme.speed * 0.03 * this.scanDir;
            if (this.scanY > 3.5 || this.scanY < 0) this.scanDir *= -1;
            this.scanPlane.position.y = this.scanY;
            this.scanPlane.material.opacity = 0.06 + Math.sin(t * 3) * 0.04;
        }

        // Particles drift
        if (this.particles?.visible) {
            this.particles.rotation.y = t * 0.08;
            const pos = this.particles.geometry.attributes.position;
            for (let i = 0; i < pos.count; i++) {
                pos.array[i * 3 + 1] += Math.sin(t + i) * 0.002;
            }
            pos.needsUpdate = true;
        }

        // Raycast hover
        this.raycaster.setFromCamera(this.pointer, this.camera);
        const hits = this.raycaster.intersectObjects(this._getInteractiveMeshes());
        const hit = hits[0]?.object;

        if (hit !== this.hovered) {
            if (this.hovered && this.hovered !== hit) {
                this.hovered.scale.set(
                    this.hovered.userData.id === 'hub' ? 1 : 1,
                    this.hovered.userData.id === 'hub' ? 1 : (this.hovered.userData.id === this.stage ? 1.15 : 1),
                    this.hovered.userData.id === 'hub' ? 1 : 1
                );
            }
            this.hovered = hit || null;
            this.canvas.style.cursor = hit ? 'pointer' : 'grab';

            if (this.tooltip) {
                if (hit) {
                    this.tooltip.textContent = hit.userData.label;
                    this.tooltip.style.opacity = '1';
                } else {
                    this.tooltip.style.opacity = '0';
                }
            }
        }

        if (hit) {
            hit.material.emissive = hit.material.emissive || new THREE.Color();
            const pulse = 0.5 + Math.sin(t * 5) * 0.2;
            hit.material.emissive.setHex(theme.emissive).multiplyScalar(pulse);
        }

        this.renderer.render(this.scene, this.camera);
    }

    dispose() {
        window.removeEventListener('resize', this._onResize);
        this.renderer?.dispose();
    }
}

export default PermitScene3D;
