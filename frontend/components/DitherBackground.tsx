'use client';

import React, { useEffect, useRef } from 'react';

export default function DitherBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let t = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    resize();
    window.addEventListener('resize', resize);

    // Standard 4x4 Bayer Dithering Matrix
    const bayer4x4 = [
      [ 0,  8,  2, 10],
      [12,  4, 14,  6],
      [ 3, 11,  1,  9],
      [15,  7, 13,  5]
    ];

    const render = () => {
      t += 0.012;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const width = canvas.width;
      const height = canvas.height;

      // Single best refined dither animation: subtle organic stippled waves
      ctx.fillStyle = 'rgba(24, 24, 27, 0.038)';
      const step = 18;

      for (let x = 0; x < width; x += step) {
        for (let y = 0; y < height; y += step) {
          const wave = Math.sin(x * 0.004 + t) * Math.cos(y * 0.004 + t * 0.8);
          const intensity = (wave + 1) / 2;
          const bx = Math.floor(x / 4) % 4;
          const by = Math.floor(y / 4) % 4;
          const bayerThreshold = bayer4x4[bx][by] / 16;

          if (intensity > bayerThreshold * 0.75) {
            ctx.beginPath();
            ctx.arc(x, y, 1.15, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none z-0 opacity-70"
    />
  );
}
