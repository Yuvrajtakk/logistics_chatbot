"use client";

import { lazy, Suspense, useEffect, useRef } from "react";

const Spline = lazy(() => import("@splinetool/react-spline"));

interface SplineSceneProps {
  scene: string;
  className?: string;
  fullViewportTracking?: boolean;
}

export function SplineScene({ scene, className, fullViewportTracking = false }: SplineSceneProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!fullViewportTracking) return;
    const forwardPointer = (event: PointerEvent) => {
      const canvas = containerRef.current?.querySelector("canvas");
      if (!canvas) return;
      const coordinates = { bubbles: true, clientX: event.clientX, clientY: event.clientY };
      canvas.dispatchEvent(new PointerEvent("pointermove", coordinates));
      canvas.dispatchEvent(new MouseEvent("mousemove", coordinates));
    };
    window.addEventListener("pointermove", forwardPointer, { passive: true });
    return () => window.removeEventListener("pointermove", forwardPointer);
  }, [fullViewportTracking]);

  return (
    <div ref={containerRef} className={className}>
      <Suspense fallback={<div className="flex h-full w-full items-center justify-center" aria-label="Loading interactive robot"><span className="h-10 w-10 animate-pulse rounded-full border border-accent/40 bg-accent/10 shadow-[0_0_30px_rgba(38,214,197,0.22)]" /></div>}>
        <Spline scene={scene} className="h-full w-full" />
      </Suspense>
    </div>
  );
}
