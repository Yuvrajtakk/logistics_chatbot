"use client";

import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";

type DropdownMenuProps = {
  options: { label: string; onClick: () => void; Icon?: React.ReactNode }[];
  children: React.ReactNode;
};

const DropdownMenu = ({ options, children }: DropdownMenuProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && setIsOpen(false);
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setIsOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("mousedown", closeOnOutsideClick);
    };
  }, []);

  return (
    <div ref={menuRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        onClick={() => setIsOpen((open) => !open)}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        className="rounded-xl border border-border bg-background/75 px-3.5 text-foreground shadow-[0_10px_28px_rgba(0,0,0,0.18)] backdrop-blur-md hover:bg-muted"
      >
        {children}
        <motion.span className="ml-2" animate={{ rotate: isOpen ? 180 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </motion.span>
      </Button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -6, scale: 0.98, filter: "blur(6px)" }}
            animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -6, scale: 0.98, filter: "blur(6px)" }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="absolute z-50 mt-2 flex w-56 flex-col gap-1 rounded-xl border border-border bg-background/95 p-1.5 shadow-[0_18px_48px_rgba(0,0,0,0.28)] backdrop-blur-xl"
          >
            {options.length ? options.map((option) => (
              <button
                key={option.label}
                role="menuitem"
                type="button"
                onClick={() => { option.onClick(); setIsOpen(false); }}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                {option.Icon}
                {option.label}
              </button>
            )) : <div className="px-3 py-2 text-xs text-muted-foreground">No providers available</div>}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export { DropdownMenu };
