import { useEffect, useRef } from 'react';

interface AstraOrbitalCanvasProps {
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH' | 'UNKNOWN';
  isListening?: boolean;
  audioLevel?: number; // 0 to 1
}

interface OrbitingCube {
  orbitRadiusX: number;
  orbitRadiusY: number;
  tiltAngle: number;
  currentAngle: number;
  speed: number;
  size: number;
  color: string;
  glowColor: string;
  rotationX: number;
  rotationY: number;
  rotationZ: number;
  rotSpeedX: number;
  rotSpeedY: number;
  trail: Array<{ x: number; y: number; alpha: number }>;
}

export default function AstraOrbitalCanvas({
  riskLevel = 'LOW',
  isListening = false,
  audioLevel = 0,
}: AstraOrbitalCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.targetX = (e.clientX - width / 2) * 0.08;
      mouseRef.current.targetY = (e.clientY - height / 2) * 0.08;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Color palettes based on risk state
    const palettes = {
      LOW: {
        coreGlow: 'rgba(192, 132, 252, 0.4)', // Candlelight purple
        ambientGlow: 'rgba(52, 211, 153, 0.15)', // Emerald mint
        cubeColors: ['#a855f7', '#34d399', '#c084fc', '#10b981', '#7c3aed'],
        ringStroke: 'rgba(192, 132, 252, 0.12)',
        flameCore: '#f3e8ff',
      },
      MEDIUM: {
        coreGlow: 'rgba(251, 191, 36, 0.4)', // Amber candlelight
        ambientGlow: 'rgba(168, 85, 247, 0.18)',
        cubeColors: ['#f59e0b', '#fbbf24', '#c084fc', '#d97706'],
        ringStroke: 'rgba(251, 191, 36, 0.16)',
        flameCore: '#fef3c7',
      },
      HIGH: {
        coreGlow: 'rgba(239, 68, 68, 0.55)', // Alert Red Candlelight
        ambientGlow: 'rgba(244, 63, 94, 0.25)',
        cubeColors: ['#ef4444', '#f87171', '#dc2626', '#fb7185'],
        ringStroke: 'rgba(239, 68, 68, 0.22)',
        flameCore: '#fee2e2',
      },
      UNKNOWN: {
        coreGlow: 'rgba(147, 128, 185, 0.25)',
        ambientGlow: 'rgba(74, 222, 128, 0.08)',
        cubeColors: ['#9380b9', '#34d399', '#7e6ba3'],
        ringStroke: 'rgba(147, 128, 185, 0.1)',
        flameCore: '#f1e8ff',
      },
    };

    // Instantiate 7 3D Orbiting Blocks (Astra style)
    const cubes: OrbitingCube[] = [
      {
        orbitRadiusX: 180,
        orbitRadiusY: 65,
        tiltAngle: -0.35,
        currentAngle: 0,
        speed: 0.014,
        size: 18,
        color: '#c084fc',
        glowColor: 'rgba(192, 132, 252, 0.7)',
        rotationX: 0.2,
        rotationY: 0.3,
        rotationZ: 0,
        rotSpeedX: 0.02,
        rotSpeedY: 0.03,
        trail: [],
      },
      {
        orbitRadiusX: 240,
        orbitRadiusY: 85,
        tiltAngle: 0.25,
        currentAngle: Math.PI * 0.7,
        speed: -0.011,
        size: 22,
        color: '#34d399',
        glowColor: 'rgba(52, 211, 153, 0.75)',
        rotationX: 0.4,
        rotationY: 0.1,
        rotationZ: 0.2,
        rotSpeedX: -0.025,
        rotSpeedY: 0.015,
        trail: [],
      },
      {
        orbitRadiusX: 300,
        orbitRadiusY: 105,
        tiltAngle: -0.15,
        currentAngle: Math.PI * 1.3,
        speed: 0.009,
        size: 15,
        color: '#a855f7',
        glowColor: 'rgba(168, 85, 247, 0.6)',
        rotationX: 0.1,
        rotationY: 0.5,
        rotationZ: 0.1,
        rotSpeedX: 0.018,
        rotSpeedY: -0.022,
        trail: [],
      },
      {
        orbitRadiusX: 130,
        orbitRadiusY: 50,
        tiltAngle: 0.55,
        currentAngle: Math.PI * 0.4,
        speed: 0.022,
        size: 12,
        color: '#6ee7b7',
        glowColor: 'rgba(110, 231, 183, 0.65)',
        rotationX: 0.3,
        rotationY: 0.2,
        rotationZ: 0.4,
        rotSpeedX: 0.03,
        rotSpeedY: 0.03,
        trail: [],
      },
      {
        orbitRadiusX: 360,
        orbitRadiusY: 125,
        tiltAngle: -0.45,
        currentAngle: Math.PI * 1.8,
        speed: -0.0075,
        size: 24,
        color: '#c084fc',
        glowColor: 'rgba(192, 132, 252, 0.5)',
        rotationX: 0.5,
        rotationY: 0.2,
        rotationZ: 0,
        rotSpeedX: -0.012,
        rotSpeedY: 0.02,
        trail: [],
      },
    ];

    // Background stardust particles
    const stars: Array<{ x: number; y: number; r: number; alpha: number; pulseSpeed: number }> = [];
    for (let i = 0; i < 90; i++) {
      stars.push({
        x: Math.random() * width,
        y: Math.random() * height,
        r: Math.random() * 1.8 + 0.3,
        alpha: Math.random() * 0.6 + 0.1,
        pulseSpeed: Math.random() * 0.03 + 0.01,
      });
    }

    let time = 0;

    // Helper: Draw projected 3D Wireframe / Glass Cube
    const draw3DCube = (
      centerX: number,
      centerY: number,
      size: number,
      rotX: number,
      rotY: number,
      color: string,
      glow: string
    ) => {
      const half = size / 2;
      // 8 Vertices of cube
      const vertices = [
        [-half, -half, -half],
        [half, -half, -half],
        [half, half, -half],
        [-half, half, -half],
        [-half, -half, half],
        [half, -half, half],
        [half, half, half],
        [-half, half, half],
      ];

      // Rotate around X and Y
      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);

      const projected = vertices.map(([vx, vy, vz]) => {
        // Rot Y
        const x1 = vx * cosY - vz * sinY;
        const z1 = vx * sinY + vz * cosY;
        // Rot X
        const y2 = vy * cosX - z1 * sinX;
        const z2 = vy * sinX + z1 * cosX;

        // Perspective projection
        const fov = 350;
        const scale = fov / (fov + z2 + 100);
        return {
          x: centerX + x1 * scale,
          y: centerY + y2 * scale,
          z: z2,
        };
      });

      // 6 faces
      const faces = [
        [0, 1, 2, 3], // back
        [4, 5, 6, 7], // front
        [0, 1, 5, 4], // top
        [2, 3, 7, 6], // bottom
        [0, 3, 7, 4], // left
        [1, 2, 6, 5], // right
      ];

      ctx.save();
      ctx.shadowColor = glow;
      ctx.shadowBlur = 16;

      // Draw faces with subtle translucent glass fill
      faces.forEach((face) => {
        ctx.beginPath();
        ctx.moveTo(projected[face[0]].x, projected[face[0]].y);
        for (let i = 1; i < face.length; i++) {
          ctx.lineTo(projected[face[i]].x, projected[face[i]].y);
        }
        ctx.closePath();
        ctx.fillStyle = color + '22';
        ctx.fill();
        ctx.strokeStyle = color + 'dd';
        ctx.lineWidth = 1.4;
        ctx.stroke();
      });

      // Glowing corner dots
      projected.forEach((p) => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
      });

      ctx.restore();
    };

    const render = () => {
      time += 0.016;

      // Smooth mouse follow
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      const cx = width / 2 + mouseRef.current.x;
      const cy = height * 0.42 + mouseRef.current.y;

      // Deep Obsidian background clear
      ctx.clearRect(0, 0, width, height);

      const pal = palettes[riskLevel] || palettes.LOW;
      const listeningBoost = isListening ? 1.4 : 1.0;
      const soundBoost = 1.0 + (audioLevel || 0) * 0.8;

      // 1. Draw Stardust
      stars.forEach((star) => {
        const pulse = Math.sin(time * star.pulseSpeed * 10) * 0.3 + 0.7;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(220, 205, 255, ${star.alpha * pulse})`;
        ctx.fill();
      });

      // 2. Central Candlelight Core + Obsidian Glow
      const candleFlicker = Math.sin(time * 6) * 0.08 + Math.cos(time * 11) * 0.04 + 1;
      const coreRadius = (80 + Math.sin(time * 2) * 12) * listeningBoost * soundBoost * candleFlicker;

      // Wide ambient purple obsidian radial glow
      const ambientGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreRadius * 4.2);
      ambientGrad.addColorStop(0, pal.coreGlow);
      ambientGrad.addColorStop(0.35, pal.ambientGlow);
      ambientGrad.addColorStop(0.75, 'rgba(13, 6, 25, 0.4)');
      ambientGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = ambientGrad;
      ctx.fillRect(0, 0, width, height);

      // Inner candlelight flame core
      const flameGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreRadius * 0.85);
      flameGrad.addColorStop(0, pal.flameCore);
      flameGrad.addColorStop(0.4, pal.coreGlow);
      flameGrad.addColorStop(1, 'transparent');
      ctx.save();
      ctx.shadowColor = pal.flameCore;
      ctx.shadowBlur = 35;
      ctx.beginPath();
      ctx.arc(cx, cy, coreRadius * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = flameGrad;
      ctx.fill();
      ctx.restore();

      // 3. Draw Elliptical Orbit Rings
      cubes.forEach((cube) => {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(cube.tiltAngle);
        ctx.beginPath();
        ctx.ellipse(0, 0, cube.orbitRadiusX, cube.orbitRadiusY, 0, 0, Math.PI * 2);
        ctx.strokeStyle = pal.ringStroke;
        ctx.lineWidth = 1;
        ctx.setLineDash([4, 6]);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.restore();
      });

      // 4. Update & Draw Orbiting 3D Cubes (Astra style)
      // Sort cubes by Z (pseudo depth) so foreground renders over background
      const cubesToDraw = cubes.map((cube) => {
        // Accelerate when listening or sound detected
        const currentSpeed = cube.speed * listeningBoost * (1 + audioLevel * 1.5);
        cube.currentAngle += currentSpeed;
        cube.rotationX += cube.rotSpeedX;
        cube.rotationY += cube.rotSpeedY;

        // Position on tilted ellipse
        const cosAngle = Math.cos(cube.currentAngle);
        const sinAngle = Math.sin(cube.currentAngle);

        const rawX = cosAngle * cube.orbitRadiusX;
        const rawY = sinAngle * cube.orbitRadiusY;

        // Apply tilt rotation matrix
        const cosTilt = Math.cos(cube.tiltAngle);
        const sinTilt = Math.sin(cube.tiltAngle);

        const rotatedX = rawX * cosTilt - rawY * sinTilt;
        const rotatedY = rawX * sinTilt + rawY * cosTilt;

        const posX = cx + rotatedX;
        const posY = cy + rotatedY;
        const depthZ = sinAngle; // -1 back, +1 front

        // Add to trail
        cube.trail.unshift({ x: posX, y: posY, alpha: 0.6 });
        if (cube.trail.length > 14) cube.trail.pop();

        return { cube, posX, posY, depthZ };
      });

      // Sort back-to-front
      cubesToDraw.sort((a, b) => a.depthZ - b.depthZ);

      cubesToDraw.forEach(({ cube, posX, posY, depthZ }) => {
        // Draw trailing particles
        for (let i = 1; i < cube.trail.length; i++) {
          const pt = cube.trail[i];
          const fadeAlpha = ((cube.trail.length - i) / cube.trail.length) * 0.35;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, (cube.size * 0.2 * (cube.trail.length - i)) / cube.trail.length, 0, Math.PI * 2);
          ctx.fillStyle = cube.glowColor.replace('0.7', String(fadeAlpha));
          ctx.fill();
        }

        // Draw connection beam to core
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(posX, posY);
        ctx.strokeStyle = cube.glowColor.replace(/[\d.]+\)$/, '0.12)');
        ctx.lineWidth = 0.8;
        ctx.stroke();

        // Dynamic size scaling with 3D depth
        const scaleFactor = 0.75 + (depthZ + 1) * 0.3;
        const activeSize = cube.size * scaleFactor * (isListening ? 1.15 : 1.0);

        draw3DCube(
          posX,
          posY,
          activeSize,
          cube.rotationX,
          cube.rotationY,
          cube.color,
          cube.glowColor
        );
      });

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [riskLevel, isListening, audioLevel]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none select-none"
      style={{ zIndex: 0 }}
    />
  );
}
