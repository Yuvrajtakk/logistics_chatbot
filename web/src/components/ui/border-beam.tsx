"use client";

import { motion } from "framer-motion";
import type { ReactNode } from "react";

type BorderBeamProps = { children: ReactNode; className?: string };

export function BorderBeam({ children, className = "" }: BorderBeamProps) {
  return (
    <div className={`relative rounded-[22px] p-px ${className}`}>
      <motion.div
        aria-hidden="true"
        className="absolute inset-0 rounded-[22px] bg-[linear-gradient(110deg,#1f3a50_0%,#26d6c5_50%,#346bff_100%)]"
        animate={{ opacity: [0.5, 0.9, 0.5] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="relative z-10 rounded-[21px] bg-[#0d1b2b]">{children}</div>
    </div>
  );
}
