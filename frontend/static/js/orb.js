/** Orb canvas renderer — states, pulsing, orbit dots, particles. */

// Public factory — normalizes state names and returns an OrbRenderer instance
function createOrbRenderer(canvas, initialState) {
  const stateMap = { IDLE: 'idle', LISTENING: 'listening', THINKING: 'thinking', SPEAKING: 'speaking', ERROR: 'error' };
  const renderer = new OrbRenderer(canvas);
  if (initialState) renderer.setState(stateMap[initialState] || initialState);
  return renderer;
}

const ORB_STATES = {
    idle:      { color: "#D9CFC4", pulseSpeed: 3000,  glowColor: "rgba(217,207,196,0.3)" },
    listening: { color: "#E8A96B", pulseSpeed: 1000,  glowColor: "rgba(232,169,107,0.5)" },
    thinking:  { color: "#4A2C17", pulseSpeed: 2000,  glowColor: "rgba(74,44,23,0.6)" },
    speaking:  { color: "#F0D9A0", pulseSpeed: 800,   glowColor: "rgba(240,217,160,0.5)" },
    error:     { color: "#7A4A3A", pulseSpeed: 4000,  glowColor: "rgba(122,74,58,0.4)" },
};

class OrbRenderer {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.state = 'idle';
        this.time = 0;
        this.orbitAngle = 0;
        this._running = true;
        this.orbitDots = [
            { radius: 55, angle: 0,   speed: 0.8,  size: 3,   opacity: 0.5 },
            { radius: 65, angle: 180, speed: -1.2, size: 2,   opacity: 0.35 },
            { radius: 50, angle: 90,  speed: 1.5,  size: 2.5, opacity: 0.4 },
        ];
        this.burstParticles = [];
        this.speechRings = [];
        this._loop = this._loop.bind(this);
        requestAnimationFrame(this._loop);
    }

    setState(newState) {
        if (!newState) return;
        const map = { IDLE: 'idle', LISTENING: 'listening', THINKING: 'thinking', SPEAKING: 'speaking', ERROR: 'error' };
        const resolved = map[newState] || newState;
        if (resolved === this.state) return;
        const prev = this.state;
        this.state = resolved;
        if (prev === 'listening') this._triggerWakeBurst();
        if (resolved === 'speaking') this._startSpeechRings();
        else this.speechRings = [];
    }

    start() { if (!this._running) { this._running = true; requestAnimationFrame(this._loop); } }
    stop()  { this._running = false; }

    _triggerWakeBurst() {
        for (let i = 0; i < 10; i++) {
            const angle = (Math.PI * 2 / 10) * i + Math.random() * 0.3;
            this.burstParticles.push({
                x: 0, y: 0,
                vx: Math.cos(angle) * (2 + Math.random() * 2),
                vy: Math.sin(angle) * (2 + Math.random() * 2),
                life: 1.0,
                decay: 0.016 + Math.random() * 0.01,
                size: 2 + Math.random() * 2,
            });
        }
    }

    _startSpeechRings() {
        const addRing = () => {
            if (this.state !== "speaking") return;
            this.speechRings.push({ radius: 30, opacity: 0.6 });
            setTimeout(addRing, 1200);
        };
        addRing();
    }

    _pulseFactor(elapsed, speed) {
        return 0.5 + 0.5 * Math.sin(elapsed / speed * Math.PI * 2);
    }

    _loop() {
        this.time += 16;
        this.orbitAngle += 0.02;
        this._updateBurst();
        this._updateRings();
        this.draw();
        requestAnimationFrame(this._loop);
    }

    _updateBurst() {
        this.burstParticles = this.burstParticles.filter(p => {
            p.x += p.vx; p.y += p.vy;
            p.life -= p.decay;
            return p.life > 0;
        });
    }

    _updateRings() {
        this.speechRings = this.speechRings.map(r => {
            r.radius += 0.8;
            r.opacity -= 0.012;
            return r;
        }).filter(r => r.opacity > 0);
    }

    draw() {
        const { canvas, ctx, state } = this;
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        const baseRadius = 38;
        const cfg = ORB_STATES[state] || ORB_STATES.idle;
        const pulse = this._pulseFactor(this.time % cfg.pulseSpeed, cfg.pulseSpeed);

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Glow halo
        const glowGrad = ctx.createRadialGradient(cx, cy, baseRadius * 0.5, cx, cy, baseRadius * 2.5);
        glowGrad.addColorStop(0, cfg.glowColor);
        glowGrad.addColorStop(1, "transparent");
        ctx.fillStyle = glowGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius * 2.5, 0, Math.PI * 2);
        ctx.fill();

        // Orb body with radial gradient + pulse
        const orbGrad = ctx.createRadialGradient(cx - 8, cy - 8, 4, cx, cy, baseRadius);
        orbGrad.addColorStop(0, this._lighten(cfg.color, 20));
        orbGrad.addColorStop(1, cfg.color);
        ctx.globalAlpha = 0.7 + 0.3 * pulse;
        ctx.fillStyle = orbGrad;
        ctx.beginPath();
        ctx.arc(cx, cy, baseRadius + pulse * 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;

        // Speech rings
        this.speechRings.forEach(r => {
            ctx.strokeStyle = cfg.color;
            ctx.lineWidth = 1.5;
            ctx.globalAlpha = r.opacity;
            ctx.beginPath();
            ctx.arc(cx, cy, r.radius, 0, Math.PI * 2);
            ctx.stroke();
        });
        ctx.globalAlpha = 1;

        // Burst particles
        this.burstParticles.forEach(p => {
            ctx.fillStyle = cfg.color;
            ctx.globalAlpha = p.life;
            ctx.beginPath();
            ctx.arc(cx + p.x, cy + p.y, p.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1;

        // Orbit dots
        this.orbitDots.forEach(dot => {
            const angleRad = (this.orbitAngle * dot.speed * Math.PI) / 180 + (dot.angle * Math.PI) / 180;
            const dx = cx + Math.cos(angleRad) * dot.radius;
            const dy = cy + Math.sin(angleRad) * dot.radius;
            ctx.fillStyle = cfg.color;
            ctx.globalAlpha = dot.opacity + 0.2 * pulse;
            ctx.beginPath();
            ctx.arc(dx, dy, dot.size, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.globalAlpha = 1;
    }

    _lighten(hex, amount) {
        const num = parseInt(hex.slice(1), 16);
        const r = Math.min(255, (num >> 16) + amount);
        const g = Math.min(255, ((num >> 8) & 0xff) + amount);
        const b = Math.min(255, (num & 0xff) + amount);
        return `rgb(${r},${g},${b})`;
    }
}