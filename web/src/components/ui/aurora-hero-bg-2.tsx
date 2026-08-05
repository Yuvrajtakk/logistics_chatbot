"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

type Action = { label: string; onClick: () => void };

type OceanHeroProps = {
  title: string;
  description: string;
  primaryAction: Action;
  secondaryAction?: Action;
};

export function OceanHero({ title, description, primaryAction, secondaryAction }: OceanHeroProps) {
  return (
    <section className="relative flex min-h-screen items-center overflow-hidden px-6 py-24 md:px-12 lg:px-[8vw]">
      <div aria-hidden="true" className="absolute inset-0 bg-[radial-gradient(circle_at_72%_34%,rgba(38,214,197,0.18),transparent_18%),radial-gradient(circle_at_18%_75%,rgba(52,107,255,0.16),transparent_24%)]" />
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, ease: "easeOut" }}
        className="relative z-10 max-w-2xl lg:max-w-[44%]"
      >
        <p className="mb-6 text-sm font-semibold uppercase tracking-[0.2em] text-accent">Olist intelligence agent</p>
        <h1 className="text-balance text-5xl font-extrabold tracking-[-0.045em] text-foreground sm:text-6xl lg:text-7xl">{title}</h1>
        <p className="mt-7 max-w-xl text-lg leading-relaxed text-muted-foreground">{description}</p>
        <div className="mt-10 flex flex-wrap items-center gap-4">
          <button onClick={primaryAction.onClick} className="group inline-flex items-center gap-2 rounded-xl bg-accent px-5 py-3 text-sm font-bold text-accent-foreground transition-transform hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-canvas">
            {primaryAction.label}<ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </button>
          {secondaryAction && <button onClick={secondaryAction.onClick} className="rounded-xl px-4 py-3 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">{secondaryAction.label}</button>}
        </div>
        <p className="mt-8 text-sm text-muted-foreground">Read-only analysis · Validated SQL · Bounded repair</p>
      </motion.div>
    </section>
  );
}
