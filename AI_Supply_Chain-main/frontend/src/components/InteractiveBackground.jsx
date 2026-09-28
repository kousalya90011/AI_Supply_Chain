import { useEffect, useRef } from "react";

/**
 * InteractiveBackground
 * 
 * An ultra-lightweight, performant canvas-based interactive background
 * inspired by aerospace & supply chain control tower telemetry displays.
 * 
 * Features:
 * - 0 React re-renders during mouse movement (uses ref + requestAnimationFrame)
 * - pointer-events: none (will never block clicks or scrolling)
 * - Subtle radial illumination follows pointer
 * - Faint grid + slowly drifting telemetry node particles with delicate connections
 * - Automatically pauses / simplifies on prefers-reduced-motion or mobile
 */
function InteractiveBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const isMobile = window.innerWidth <= 768;

    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Mouse coordinates (stored in memory, not React state)
    const mouse = {
      x: width / 2,
      y: height / 2,
      targetX: width / 2,
      targetY: height / 2,
      active: false,
    };

    // Telemetry particle pool
    const particleCount = prefersReducedMotion ? 0 : isMobile ? 18 : 36;
    const particles = [];

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: Math.random() * 1.5 + 1,
        alpha: Math.random() * 0.25 + 0.1,
      });
    }

    const handleMouseMove = (e) => {
      mouse.targetX = e.clientX;
      mouse.targetY = e.clientY;
      mouse.active = true;
    };

    const handleMouseLeave = () => {
      mouse.active = false;
    };

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    window.addEventListener("mouseleave", handleMouseLeave, { passive: true });
    window.addEventListener("resize", handleResize, { passive: true });

    const render = () => {
      // Smooth lerp mouse coordinates
      mouse.x += (mouse.targetX - mouse.x) * 0.08;
      mouse.y += (mouse.targetY - mouse.y) * 0.08;

      ctx.clearRect(0, 0, width, height);

      // 1. Subtle interactive radial illumination (subtle dark gold)
      if (mouse.active) {
        const spotlight = ctx.createRadialGradient(
          mouse.x,
          mouse.y,
          0,
          mouse.x,
          mouse.y,
          isMobile ? 260 : 420
        );
        spotlight.addColorStop(0, "rgba(212, 175, 55, 0.04)");
        spotlight.addColorStop(0.5, "rgba(212, 175, 55, 0.012)");
        spotlight.addColorStop(1, "rgba(8, 8, 8, 0)");

        ctx.fillStyle = spotlight;
        ctx.fillRect(0, 0, width, height);
      }

      // 2. Telemetry network particles and connecting filaments (restrained gold/charcoal)
      if (!prefersReducedMotion && particleCount > 0) {
        for (let i = 0; i < particles.length; i++) {
          const p = particles[i];

          p.x += p.vx;
          p.y += p.vy;

          if (p.x < 0) p.x = width;
          else if (p.x > width) p.x = 0;
          if (p.y < 0) p.y = height;
          else if (p.y > height) p.y = 0;

          // Parallax nudge toward mouse cursor
          if (mouse.active) {
            const dx = mouse.x - p.x;
            const dy = mouse.y - p.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 180) {
              const force = (180 - dist) / 180;
              p.x -= (dx / dist) * force * 0.4;
              p.y -= (dy / dist) * force * 0.4;
            }
          }

          // Draw node particle
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(212, 175, 55, ${p.alpha * 0.35})`;
          ctx.fill();

          // Connect nearby nodes
          for (let j = i + 1; j < particles.length; j++) {
            const p2 = particles[j];
            const dx = p.x - p2.x;
            const dy = p.y - p2.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < 110) {
              ctx.beginPath();
              ctx.moveTo(p.x, p.y);
              ctx.lineTo(p2.x, p2.y);
              const lineAlpha = (1 - dist / 110) * 0.04;
              ctx.strokeStyle = `rgba(212, 175, 55, ${lineAlpha})`;
              ctx.lineWidth = 0.75;
              ctx.stroke();
            }
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseleave", handleMouseLeave);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <div
      className="interactive-background-layer"
      aria-hidden="true"
      style={{
        position: "fixed",
        inset: 0,
        pointerEvents: "none",
        zIndex: 0,
        overflow: "hidden",
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          display: "block",
          width: "100%",
          height: "100%",
          pointerEvents: "none",
        }}
      />
      <div className="control-tower-grid-overlay" />
    </div>
  );
}

export default InteractiveBackground;
