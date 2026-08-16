/**
 * 3D Holographic AI Doctor Neural Core Visualizer (Three.js + Web Audio API)
 * Renders an interactive 3D abstract orb that dynamically reacts to patient and doctor voice.
 */

let scene, camera, renderer, coreMesh, wireMesh, particleSystem, pointLight1, pointLight2;
let audioContext, analyser, dataArray, microphoneSource, audioSourceNode;
let isVisualizerInitialized = false;
let animationFrameId = null;
let currentVisualizerState = 'idle'; // 'idle', 'listening', 'speaking', 'thinking'
let baseVertices = [];

function init3DDoctorVisualizer() {
    const canvas = document.getElementById('canvas-3d-doctor');
    if (!canvas || typeof THREE === 'undefined') {
        console.warn('Three.js or 3D canvas not available.');
        return;
    }

    if (isVisualizerInitialized) return;

    const width = canvas.parentElement.clientWidth || 800;
    const height = canvas.parentElement.clientHeight || 360;

    // 1. Scene & Camera
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 7.5;

    // 2. WebGL Renderer
    renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: true,
        alpha: true
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // 3. Central Morphing Core Mesh (Icosahedron)
    const coreGeo = new THREE.IcosahedronGeometry(1.8, 3);
    const coreMat = new THREE.MeshPhongMaterial({
        color: 0x0d9488,
        emissive: 0x042f2e,
        shininess: 90,
        wireframe: false,
        transparent: true,
        opacity: 0.85,
        flatShading: true
    });
    coreMesh = new THREE.Mesh(coreGeo, coreMat);
    scene.add(coreMesh);

    // Save base vertices for morphing
    const pos = coreGeo.attributes.position;
    baseVertices = [];
    for (let i = 0; i < pos.count; i++) {
        baseVertices.push(new THREE.Vector3(pos.getX(i), pos.getY(i), pos.getZ(i)));
    }

    // 4. Outer Holographic Wireframe Cage
    const wireGeo = new THREE.IcosahedronGeometry(2.1, 2);
    const wireMat = new THREE.MeshBasicMaterial({
        color: 0x2dd4bf,
        wireframe: true,
        transparent: true,
        opacity: 0.4
    });
    wireMesh = new THREE.Mesh(wireGeo, wireMat);
    scene.add(wireMesh);

    // 5. Orbiting Luminous Particles (2,000 particles)
    const particleCount = 1800;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(Math.random() * 2 - 1);
        const radius = 2.4 + Math.random() * 1.8;

        particlePositions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
        particlePositions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
        particlePositions[i * 3 + 2] = radius * Math.cos(phi);

        // Mix teal, cyan, and gold colors
        const isTeal = Math.random() > 0.3;
        particleColors[i * 3] = isTeal ? 0.05 : 0.95;     // R
        particleColors[i * 3 + 1] = isTeal ? 0.75 : 0.75; // G
        particleColors[i * 3 + 2] = isTeal ? 0.65 : 0.2;  // B
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    const particleMat = new THREE.PointsMaterial({
        size: 0.05,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });
    particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // 6. Dynamic Point Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    pointLight1 = new THREE.PointLight(0x0d9488, 3, 20);
    pointLight1.position.set(4, 3, 4);
    scene.add(pointLight1);

    pointLight2 = new THREE.PointLight(0x06b6d4, 3, 20);
    pointLight2.position.set(-4, -3, 4);
    scene.add(pointLight2);

    isVisualizerInitialized = true;
    window.addEventListener('resize', onVisualizerResize);

    setupWebAudioAnalyser();
    animateVisualizer(0);
}

function onVisualizerResize() {
    const canvas = document.getElementById('canvas-3d-doctor');
    if (!canvas || !renderer || !camera) return;

    const width = canvas.parentElement.clientWidth || 800;
    const height = canvas.parentElement.clientHeight || 360;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

// ==========================================
// Web Audio API Frequency Extraction
// ==========================================

function setupWebAudioAnalyser() {
    if (audioContext) return;
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        audioContext = new AudioCtx();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 128;
        analyser.smoothingTimeConstant = 0.8;
        dataArray = new Uint8Array(analyser.frequencyBinCount);
    } catch (e) {
        console.warn('Web Audio API not supported:', e);
    }
}

async function connectMicrophoneToVisualizer() {
    if (!audioContext || !analyser) setupWebAudioAnalyser();
    if (!audioContext) return;

    if (audioContext.state === 'suspended') {
        await audioContext.resume();
    }

    if (microphoneSource) return;

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        microphoneSource = audioContext.createMediaStreamSource(stream);
        microphoneSource.connect(analyser);
    } catch (e) {
        console.warn('Could not connect microphone stream to 3D visualizer:', e);
    }
}

function connectAudioElementToVisualizer(audioElement) {
    if (!audioContext || !analyser || !audioElement) return;

    if (audioContext.state === 'suspended') {
        audioContext.resume();
    }

    try {
        if (!audioSourceNode) {
            audioSourceNode = audioContext.createMediaElementSource(audioElement);
            audioSourceNode.connect(analyser);
            analyser.connect(audioContext.destination);
        }
    } catch (e) {
        // Already connected or CORS issue
    }
}

function getAudioEnergy() {
    if (!analyser || !dataArray) return 0;
    analyser.getByteFrequencyData(dataArray);

    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
    }
    return sum / (dataArray.length * 255); // 0.0 to 1.0
}

// ==========================================
// 3D Render Loop with Frequency Reaction
// ==========================================

function animateVisualizer(time) {
    animationFrameId = requestAnimationFrame(animateVisualizer);
    if (!renderer || !scene || !camera) return;

    const t = time * 0.001;
    const energy = getAudioEnergy();

    // 1. Rotation dynamics
    const rotSpeed = 0.006 + (energy * 0.04);
    if (coreMesh) {
        coreMesh.rotation.x += rotSpeed * 0.7;
        coreMesh.rotation.y += rotSpeed;
    }
    if (wireMesh) {
        wireMesh.rotation.x -= rotSpeed * 0.5;
        wireMesh.rotation.y -= rotSpeed * 0.8;
    }
    if (particleSystem) {
        particleSystem.rotation.y += rotSpeed * 0.4;
        particleSystem.rotation.z += rotSpeed * 0.2;
    }

    // 2. Vertex Displacement / Morphing
    if (coreMesh && baseVertices.length > 0) {
        const posAttr = coreMesh.geometry.attributes.position;
        const pulseFactor = 1 + (energy * 0.6) + Math.sin(t * 3) * 0.04;

        for (let i = 0; i < baseVertices.length; i++) {
            const base = baseVertices[i];
            const noise = Math.sin(base.x * 2 + t * 4) * Math.cos(base.y * 2 + t * 4) * (0.15 + energy * 0.7);
            const scale = pulseFactor + noise;
            posAttr.setXYZ(i, base.x * scale, base.y * scale, base.z * scale);
        }
        posAttr.needsUpdate = true;
    }

    // 3. Dynamic Shading and Light Colors based on State
    if (coreMesh && pointLight1 && pointLight2) {
        if (currentVisualizerState === 'listening') {
            // Patient Speaking -> Vibrant Coral/Ruby Red
            coreMesh.material.color.lerp(new THREE.Color(0xef4444), 0.1);
            coreMesh.material.emissive.lerp(new THREE.Color(0x7f1d1d), 0.1);
            pointLight1.color.lerp(new THREE.Color(0xf43f5e), 0.1);
            pointLight2.color.lerp(new THREE.Color(0xfb7185), 0.1);
        } else if (currentVisualizerState === 'speaking') {
            // Dr. Dhanvantari Speaking (VibeVoice) -> Glowing Cyan/Teal with Golden Sparkles
            coreMesh.material.color.lerp(new THREE.Color(0x0d9488), 0.1);
            coreMesh.material.emissive.lerp(new THREE.Color(0x042f2e), 0.1);
            pointLight1.color.lerp(new THREE.Color(0x2dd4bf), 0.1);
            pointLight2.color.lerp(new THREE.Color(0x06b6d4), 0.1);
        } else if (currentVisualizerState === 'thinking') {
            // Analyzing -> Golden Amber
            coreMesh.material.color.lerp(new THREE.Color(0xf59e0b), 0.1);
            coreMesh.material.emissive.lerp(new THREE.Color(0x78350f), 0.1);
            pointLight1.color.lerp(new THREE.Color(0xfbbf24), 0.1);
        } else {
            // Idle Serene Teal
            coreMesh.material.color.lerp(new THREE.Color(0x0d9488), 0.05);
            coreMesh.material.emissive.lerp(new THREE.Color(0x042f2e), 0.05);
            pointLight1.color.lerp(new THREE.Color(0x0d9488), 0.05);
            pointLight2.color.lerp(new THREE.Color(0x06b6d4), 0.05);
        }
    }

    // 4. Orbit point lights around the scene
    if (pointLight1 && pointLight2) {
        pointLight1.position.x = Math.sin(t * 1.5) * 4.5;
        pointLight1.position.y = Math.cos(t * 1.2) * 3.5;
        pointLight1.position.z = Math.sin(t * 1.8) * 4.5;

        pointLight2.position.x = Math.cos(t * 1.4) * 4.5;
        pointLight2.position.y = Math.sin(t * 1.6) * 3.5;
        pointLight2.position.z = Math.cos(t * 1.3) * 4.5;
    }

    renderer.render(scene, camera);
}

function set3DVisualizerState(state) {
    currentVisualizerState = state;
}
