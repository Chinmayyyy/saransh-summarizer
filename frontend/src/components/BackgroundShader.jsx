import { useEffect, useState } from 'react';

export default function BackgroundShader() {
  const [position, setPosition] = useState({ x: -100, y: -100 });

  useEffect(() => {
    let animationFrameId;
    
    // Smooth trailing effect (Linear Interpolation)
    let currentX = window.innerWidth / 2;
    let currentY = window.innerHeight / 2;
    let targetX = currentX;
    let targetY = currentY;

    const updatePosition = (e) => {
      targetX = e.clientX;
      targetY = e.clientY;
    };

    const animate = () => {
      // Lerp logic for buttery smooth trailing
      currentX += (targetX - currentX) * 0.08;
      currentY += (targetY - currentY) * 0.08;
      setPosition({ x: currentX, y: currentY });
      
      animationFrameId = requestAnimationFrame(animate);
    };

    window.addEventListener('mousemove', updatePosition);
    animate();

    return () => {
      window.removeEventListener('mousemove', updatePosition);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden bg-slate-50/50">
      {/* Base static ambient glows */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-violet-200/40 blur-[120px] animate-pulse-slow" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] rounded-full bg-cyan-200/40 blur-[120px] animate-pulse-slow" style={{ animationDelay: '2s' }} />
      
      {/* Interactive cursor glow */}
      <div
        className="absolute inset-0 transition-opacity duration-300"
        style={{
          background: `radial-gradient(800px circle at ${position.x}px ${position.y}px, rgba(139, 92, 246, 0.12), transparent 50%)`
        }}
      />
    </div>
  );
}
