"use client";

import { motion } from "framer-motion";

export function AILoader() {
  return (
    <div className="inline-flex items-center gap-3 rounded-2xl border border-border bg-background/85 px-4 py-3 text-sm text-muted-foreground shadow-[0_14px_32px_rgba(0,0,0,0.16)]">
      <span className="flex items-end gap-1" aria-hidden="true">
        {[0, 1, 2].map((index) => (
          <motion.span
            key={index}
            className="h-2 w-1 rounded-full bg-accent"
            animate={{ height: [7, 18, 7], opacity: [0.45, 1, 0.45] }}
            transition={{ duration: 0.75, repeat: Infinity, delay: index * 0.12 }}
          />
        ))}
      </span>
      <span>Agent is reasoning through the data…</span>
    </div>
  );
}
