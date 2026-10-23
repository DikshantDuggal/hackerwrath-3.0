import { useEffect, useRef } from 'react';

interface AstraOrbitalCanvasProps {
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | 'UNKNOWN';
  isListening?: boolean;
  audioLevel?: number; // 0 to 1
}

interface Planet {
  orbitA: number; // semi-major axis
  orbitB: number; // semi-minor axis
  tilt: number; // inclination angle
  angle: number; // current orbital position
  speed: number;
  radius: number;
  color: string;
  glowColor: string;
  hasRings?: boolean;
  ringRadius?: number;
  ringTilt?: number;
  hasMoon?: boolean;
  moonAngle?: number;
  moonDist?: number;
  trail: Array<{ x: number; y: number; alpha: number }>;
}

interface Star {
  x: number;
  y: number;
  size: number;
  baseAlpha: number;
  twinkleSpeed: number;
  twinklePhase: number;
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
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      initStars();
    };
    window.addEventListener('resize', handleResize);

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.targetX = (e.clientX - width / 2) * 0.04;
      mouseRef.current.targetY = (e.clientY - height / 2) * 0.04;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Color definitions based on Obsidian Cosmic design tokens
    const getThemeColors = () => {
      switch (riskLevel) {
        case 'CRITICAL':
          return {
            sunCore: '#FFE4E6',
            sunInner: '#F43F5E',
            sunOuter: 'rgba(244, 63, 94, 0.45)',
            sunGlow: 'rgba(225, 29, 72, 0.25)',
            orbitStroke: 'rgba(244, 63, 94, 0.16)',
            accent: '#F43F5E',
          };
        case 'HIGH':
          return {
            sunCore: '#FEE2E2',
            sunInner: '#EF4444',
            sunOuter: 'rgba(239, 68, 68, 0.4)',
            sunGlow: 'rgba(220, 38, 38, 0.2)',
            orbitStroke: 'rgba(239, 68, 68, 0.14)',
            accent: '#EF4444',
          };
        case 'MEDIUM':
          return {
            sunCore: '#FEF3C7',
            sunInner: '#F2C879',
            sunOuter: 'rgba(242, 200, 121, 0.35)',
            sunGlow: 'rgba(217, 119, 6, 0.18)',
            orbitStroke: 'rgba(242, 200, 121, 0.14)',
            accent: '#F2C879',
          };
        default:
          return {
            sunCore: '#FFFFFF',
            sunInner: '#00F0FF',
            sunOuter: 'rgba(0, 240, 255, 0.45)',
            sunGlow: 'rgba(0, 240, 255, 0.2)',
            orbitStroke: 'rgba(0, 240, 255, 0.15)',
            accent: '#00F0FF',
          };
      }
    };

    // Cosmic background starfield
    let stars: Star[] = [];
    const initStars = () => {
      stars = [];
      const starCount = Math.floor((width * height) / 12000);
      for (let i = 0; i < starCount; i++) {
        stars.push({
          x: Math.random() * width,
          y: Math.random() * height,
          size: Math.random() * 1.5 + 0.4,
          baseAlpha: Math.random() * 0.5 + 0.15,
          twinkleSpeed: Math.random() * 0.03 + 0.01,
          twinklePhase: Math.random() * Math.PI * 2,
        });
      }
    };
    initStars();

    // Solar System Planets
    const planets: Planet[] = [
      // 1. Inner Rocky World (Fast orbit)
      {
        orbitA: 130,
        orbitB: 50,
        tilt: -0.15,
        angle: 0.8,
        speed: 0.014,
        radius: 3.5,
        color: '#A2A9BA',
        glowColor: 'rgba(162, 169, 186, 0.4)',
        trail: [],
      },
      // 2. Electric Cyan Terrestrial World with Moon
      {
        orbitA: 210,
        orbitB: 80,
        tilt: 0.1,
        angle: 2.4,
        speed: 0.009,
        radius: 6,
        color: '#00F0FF',
        glowColor: 'rgba(0, 240, 255, 0.7)',
        hasMoon: true,
        moonAngle: 0,
        moonDist: 14,
        trail: [],
      },
      // 3. Ringed Violet Gas Giant (Saturn-like)
      {
        orbitA: 320,
        orbitB: 120,
        tilt: -0.22,
        angle: 4.1,
        speed: 0.0055,
        radius: 9,
        color: '#8B7CFF',
        glowColor: 'rgba(139, 124, 255, 0.55)',
        hasRings: true,
        ringRadius: 18,
        ringTilt: -0.3,
        trail: [],
      },
      // 4. Emerald Ice Giant
      {
        orbitA: 430,
        orbitB: 165,
        tilt: 0.18,
        angle: 1.2,
        speed: 0.0038,
        radius: 7,
        color: '#63D6A5',
        glowColor: 'rgba(99, 214, 165, 0.45)',
        trail: [],
      },
      // 5. Outer Golden Dwarf Planet
      {
        orbitA: 550,
        orbitB: 215,
        tilt: -0.08,
        angle: 5.5,
        speed: 0.0022,
        radius: 4,
        color: '#F2C879',
        glowColor: 'rgba(242, 200, 121, 0.4)',
        trail: [],
      },
    ];

    let time = 0;

    const render = () => {
      time += 0.016;

      // Smooth mouse parallax
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      const themeColors = getThemeColors();

      // Deep Obsidian base background
      ctx.fillStyle = '#0B0D12';
      ctx.fillRect(0, 0, width, height);

      // Radial background depth gradient
      const bgRadial = ctx.createRadialGradient(
        width / 2 + mouseRef.current.x * 0.5,
        height / 2 + mouseRef.current.y * 0.5,
        20,
        width / 2,
        height / 2,
        Math.max(width, height) * 0.8
      );
      bgRadial.addColorStop(0, '#141824');
      bgRadial.addColorStop(0.5, '#0E1119');
      bgRadial.addColorStop(1, '#0B0D12');
      ctx.fillStyle = bgRadial;
      ctx.fillRect(0, 0, width, height);

      // Render Stars
      stars.forEach((star) => {
        const twinkle = Math.sin(time * star.twinkleSpeed * 60 + star.twinklePhase);
        const alpha = Math.max(0.08, star.baseAlpha + twinkle * 0.25);
        ctx.fillStyle = `rgba(241, 243, 248, ${alpha})`;
        ctx.beginPath();
        const px = star.x + mouseRef.current.x * 0.15;
        const py = star.y + mouseRef.current.y * 0.15;
        ctx.arc(px, py, star.size, 0, Math.PI * 2);
        ctx.fill();
      });

      // Solar System Center
      const centerX = width / 2 + mouseRef.current.x;
      const centerY = height / 2 + mouseRef.current.y;

      // Audio reactivity pulse
      const audioPulse = isListening ? audioLevel * 18 : 0;
      const breath = Math.sin(time * 1.5) * 2;
      const baseSunRadius = 24 + breath + audioPulse;

      // 1. Draw Planetary Orbit Paths
      planets.forEach((p) => {
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(p.tilt);

        ctx.beginPath();
        ctx.ellipse(0, 0, p.orbitA, p.orbitB, 0, 0, Math.PI * 2);
        ctx.strokeStyle = themeColors.orbitStroke;
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 7]);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.restore();
      });

      // 2. Draw Central Star Glow & Corona
      const sunGlow = ctx.createRadialGradient(
        centerX,
        centerY,
        baseSunRadius * 0.2,
        centerX,
        centerY,
        baseSunRadius * 4.5
      );
      sunGlow.addColorStop(0, themeColors.sunCore);
      sunGlow.addColorStop(0.25, themeColors.sunInner);
      sunGlow.addColorStop(0.6, themeColors.sunOuter);
      sunGlow.addColorStop(1, 'rgba(11, 13, 18, 0)');

      ctx.fillStyle = sunGlow;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseSunRadius * 4.5, 0, Math.PI * 2);
      ctx.fill();

      // Core Star Sphere
      ctx.fillStyle = themeColors.sunCore;
      ctx.beginPath();
      ctx.arc(centerX, centerY, baseSunRadius * 0.7, 0, Math.PI * 2);
      ctx.shadowColor = themeColors.accent;
      ctx.shadowBlur = 25 + audioPulse * 1.5;
      ctx.fill();
      ctx.shadowBlur = 0;

      // 3. Update & Draw Planets
      planets.forEach((p) => {
        p.angle += p.speed;

        // Position on inclined ellipse
        const rawX = Math.cos(p.angle) * p.orbitA;
        const rawY = Math.sin(p.angle) * p.orbitB;

        // Apply tilt rotation
        const cosT = Math.cos(p.tilt);
        const sinT = Math.sin(p.tilt);
        const planetX = centerX + (rawX * cosT - rawY * sinT);
        const planetY = centerY + (rawX * sinT + rawY * cosT);

        // Record orbital trail
        p.trail.unshift({ x: planetX, y: planetY, alpha: 0.4 });
        if (p.trail.length > 20) p.trail.pop();

        // Draw Trail
        for (let i = 0; i < p.trail.length - 1; i++) {
          const pt = p.trail[i];
          const fade = (1 - i / p.trail.length) * 0.35;
          ctx.fillStyle = p.glowColor.replace(/[\d.]+\)$/, `${fade})`);
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, Math.max(1, p.radius * (1 - i / p.trail.length)), 0, Math.PI * 2);
          ctx.fill();
        }

        // Draw Planet Body
        const planetGrad = ctx.createRadialGradient(
          planetX - p.radius * 0.3,
          planetY - p.radius * 0.3,
          p.radius * 0.1,
          planetX,
          planetY,
          p.radius
        );
        planetGrad.addColorStop(0, '#FFFFFF');
        planetGrad.addColorStop(0.35, p.color);
        planetGrad.addColorStop(1, '#0B0D12');

        ctx.fillStyle = planetGrad;
        ctx.beginPath();
        ctx.arc(planetX, planetY, p.radius, 0, Math.PI * 2);
        ctx.shadowColor = p.color;
        ctx.shadowBlur = 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Optional Rings (e.g. Violet Gas Giant)
        if (p.hasRings && p.ringRadius) {
          ctx.save();
          ctx.translate(planetX, planetY);
          ctx.rotate(p.ringTilt || -0.2);

          ctx.beginPath();
          ctx.ellipse(0, 0, p.ringRadius, p.ringRadius * 0.32, 0, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(139, 124, 255, 0.45)';
          ctx.lineWidth = 2.5;
          ctx.stroke();

          ctx.beginPath();
          ctx.ellipse(0, 0, p.ringRadius * 1.25, p.ringRadius * 0.38, 0, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(114, 215, 232, 0.25)';
          ctx.lineWidth = 1;
          ctx.stroke();

          ctx.restore();
        }

        // Optional Moon (e.g. Terrestrial Cyan World)
        if (p.hasMoon && p.moonDist) {
          p.moonAngle = (p.moonAngle || 0) + 0.04;
          const moonX = planetX + Math.cos(p.moonAngle) * p.moonDist;
          const moonY = planetY + Math.sin(p.moonAngle) * (p.moonDist * 0.45);

          ctx.fillStyle = '#E2E8F0';
          ctx.beginPath();
          ctx.arc(moonX, moonY, 1.8, 0, Math.PI * 2);
          ctx.shadowColor = '#72D7E8';
          ctx.shadowBlur = 4;
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      });

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [riskLevel, isListening, audioLevel]);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none z-0"
      style={{
        background: '#0B0D12',
      }}
    />
  );
}
