import React, { useEffect, useRef } from 'react';

export const Oscilloscope: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let xPos = 0;
    const speed = 2.5;

    const resize = () => {
      if (canvas.parentElement) {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight || 38;
      }
    };

    window.addEventListener('resize', resize);
    resize();

    // Synthetic continuous ECG wave function
    const getEcgY = (t: number) => {
      const cycle = t % 1.0;
      if (cycle < 0.1) return 0;
      if (cycle < 0.18) return -6 * Math.sin(((cycle - 0.1) / 0.08) * Math.PI); // P wave
      if (cycle < 0.25) return 0;
      if (cycle < 0.28) return 4 * Math.sin(((cycle - 0.25) / 0.03) * Math.PI);  // Q dip
      if (cycle < 0.33) return -26 * Math.sin(((cycle - 0.28) / 0.05) * Math.PI); // R peak
      if (cycle < 0.38) return 6 * Math.sin(((cycle - 0.33) / 0.05) * Math.PI);  // S dip
      if (cycle < 0.5) return 0;
      if (cycle < 0.65) return -8 * Math.sin(((cycle - 0.5) / 0.15) * Math.PI);  // T wave
      return 0;
    };

    let lastY = canvas.height / 2;
    let time = 0;

    const animate = () => {
      const midY = canvas.height / 2;

      // Subtle phosphor trail fade
      ctx.fillStyle = 'rgba(7, 10, 16, 0.08)';
      ctx.fillRect(xPos, 0, 18, canvas.height);

      time += 0.015;
      const targetY = midY + getEcgY(time);

      ctx.beginPath();
      ctx.moveTo(xPos, lastY);
      ctx.lineTo(xPos + speed, targetY);
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 1.6;
      ctx.shadowBlur = 8;
      ctx.shadowColor = '#00f0ff';
      ctx.stroke();

      lastY = targetY;
      xPos += speed;

      if (xPos >= canvas.width) {
        xPos = 0;
        ctx.clearRect(0, 0, 20, canvas.height);
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="oscilloscope-wrapper">
      <canvas ref={canvasRef} height={38} />
    </div>
  );
};
