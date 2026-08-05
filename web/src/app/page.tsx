"use client";

import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Cpu, Database, Lock, Send, Sparkles } from "lucide-react";

import { AILoader } from "@/components/ui/ai-loader";
import { OceanHero } from "@/components/ui/aurora-hero-bg-2";
import { BorderBeam } from "@/components/ui/border-beam";
import { DropdownMenu } from "@/components/ui/dropdown-menu";
import { SplineScene } from "@/components/ui/splite";

type ProviderState = { groq: boolean; ollama: boolean; gemini: boolean };
type Message = { id: string; role: "user" | "assistant"; content: string; route?: string; sql?: string };

const SUGGESTED_QUESTIONS = [
  "Which product categories have the highest late-delivery rate?",
  "Which Brazilian states have the longest average delivery time?",
  "Does delivery time correlate with review score?",
  "Which payment type is most common, and does it vary by region?",
  "What do customers complain about most when deliveries are late?",
  "What are customers saying about receiving damaged or wrong items?",
  "Who are the top sellers by revenue, and how do their reviews look?",
];

export default function Home() {
  const [providers, setProviders] = useState<ProviderState>({ groq: true, ollama: true, gemini: false });
  const [selectedProvider, setSelectedProvider] = useState<"groq" | "ollama">("groq");
  const [isChatMode, setIsChatMode] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/providers")
      .then((res) => res.json())
      .then((data) => setProviders({ groq: data.groq ?? true, ollama: data.ollama ?? true, gemini: data.gemini ?? false }))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (isChatMode) window.setTimeout(() => inputRef.current?.focus(), 550);
  }, [isChatMode]);

  const enterChat = () => setIsChatMode(true);
  const handleChipClick = (question: string) => {
    setInputValue(question);
    inputRef.current?.focus();
  };

  const handleSend = async () => {
    const question = inputValue.trim();
    if (!question || isLoading) return;

    setMessages((current) => [...current, { id: Date.now().toString(), role: "user", content: question }]);
    setInputValue("");
    setIsLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, provider: selectedProvider, session_id: "demo-session" }),
      });
      const data = await response.json();
      setMessages((current) => [...current, { id: `${Date.now()}-answer`, role: "assistant", content: data.answer, route: data.route, sql: data.sql }]);
    } catch {
      setMessages((current) => [...current, { id: `${Date.now()}-error`, role: "assistant", content: "Sorry, there was an error connecting to the API." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-screen overflow-hidden bg-canvas font-sans">
      <motion.aside
        animate={isChatMode ? { left: "0vw", top: "0vh", width: "36vw", height: "100vh" } : { left: "51vw", top: "10vh", width: "42vw", height: "76vh" }}
        transition={{ type: "spring", stiffness: 110, damping: 20, mass: 0.9 }}
        className="fixed z-20 hidden overflow-hidden lg:block"
        aria-label="Interactive robot assistant"
      >
        <div className="pointer-events-none absolute inset-0 z-10 bg-[radial-gradient(circle_at_50%_45%,transparent_38%,rgba(7,17,31,0.48)_74%,rgba(7,17,31,0.95)_100%)]" />
        <SplineScene scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode" className="h-full w-full" fullViewportTracking />
        <motion.p animate={{ opacity: isChatMode ? 1 : 0.72 }} className="pointer-events-none absolute bottom-8 left-1/2 z-20 -translate-x-1/2 whitespace-nowrap text-xs font-semibold text-muted-foreground">
          I&apos;m following your cursor
        </motion.p>
      </motion.aside>

      <AnimatePresence mode="wait">
        {!isChatMode ? (
          <motion.div key="landing" exit={{ opacity: 0, y: -18, filter: "blur(8px)" }} transition={{ duration: 0.32 }}>
            <OceanHero
              title="Ask the operations questions hiding in your data."
              description="A safeguarded intelligence agent for delivery performance, payment behavior, and the customer signals behind every Olist order."
              primaryAction={{ label: "Chat with the agent", onClick: enterChat }}
            />
          </motion.div>
        ) : (
          <motion.main key="chat" initial={{ opacity: 0, x: 52 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.45, ease: "easeOut" }} className="relative h-full bg-canvas lg:ml-[36vw]">
            <header className="absolute inset-x-0 top-0 z-20 flex h-16 items-center justify-between border-b border-border bg-canvas/95 px-5 backdrop-blur-xl md:px-7">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground"><Sparkles className="h-4 w-4 text-accent" /> Analysis workspace</div>
              <DropdownMenu
                options={[
                  ...(providers.groq ? [{ label: "Groq", onClick: () => setSelectedProvider("groq"), Icon: selectedProvider === "groq" ? <CheckCircle2 className="h-4 w-4 text-accent" /> : undefined }] : []),
                  ...(providers.ollama ? [{ label: "Ollama · Local", onClick: () => setSelectedProvider("ollama"), Icon: selectedProvider === "ollama" ? <CheckCircle2 className="h-4 w-4 text-accent" /> : undefined }] : []),
                ]}
              >
                <span>{selectedProvider === "groq" ? "Groq" : "Ollama · Local"}</span>
              </DropdownMenu>
            </header>

            <div className="h-full overflow-y-auto px-5 pb-44 pt-24 md:px-8">
              <div className="mx-auto max-w-3xl space-y-5">
                {messages.length === 0 && (
                  <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} className="flex min-h-[calc(100vh-15rem)] flex-col justify-center">
                    <div className="mb-6 inline-flex w-fit rounded-2xl border border-border bg-background/70 p-3 text-accent shadow-[0_14px_32px_rgba(0,0,0,0.14)]"><Database className="h-6 w-6" /></div>
                    <h2 className="max-w-xl text-3xl font-bold tracking-[-0.03em] text-foreground">What would you like to understand?</h2>
                    <p className="mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">Ask about orders, delivery delays, payments, sellers, or customer feedback. Every data question passes through the validation pipeline first.</p>
                    <div className="mt-8 flex max-w-2xl flex-wrap gap-2">
                      {SUGGESTED_QUESTIONS.map((question) => <button key={question} onClick={() => handleChipClick(question)} className="rounded-full border border-border bg-background/60 px-4 py-2 text-left text-sm text-muted-foreground transition-colors hover:border-accent hover:bg-accent/10 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent">{question}</button>)}
                    </div>
                  </motion.div>
                )}

                {messages.map((message) => (
                  <motion.article key={message.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2, ease: "easeOut" }} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[88%] rounded-2xl px-5 py-4 ${message.role === "user" ? "bg-accent text-accent-foreground" : "border border-border bg-background text-foreground shadow-[0_14px_32px_rgba(0,0,0,0.12)]"}`}>
                      <p className="whitespace-pre-wrap break-words text-sm leading-7">{message.content}</p>
                      {message.role === "assistant" && (message.route || message.sql) && <div className="mt-4 flex flex-col gap-2 border-t border-border/60 pt-3 text-xs text-muted-foreground">{message.route && <span className="flex items-center gap-1.5"><Cpu className="h-3.5 w-3.5" /> Routed to <strong className="uppercase tracking-wider text-foreground">{message.route}</strong></span>}{message.sql && <code className="overflow-x-auto rounded-lg bg-muted px-3 py-2 text-[11px] text-foreground">{message.sql}</code>}</div>}
                    </div>
                  </motion.article>
                ))}

                {isLoading && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}><AILoader /></motion.div>}
              </div>
            </div>

            <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-canvas via-canvas to-transparent px-5 pb-5 pt-12 md:px-8 md:pb-7">
              <div className="mx-auto max-w-3xl">
                <BorderBeam>
                  <div className="p-2">
                    <textarea ref={inputRef} value={inputValue} onChange={(event) => setInputValue(event.target.value)} onKeyDown={handleKeyDown} placeholder="Ask anything about the Olist dataset…" rows={2} className="min-h-[76px] w-full resize-none bg-transparent px-3 pt-2 text-sm text-foreground outline-none placeholder:text-muted-foreground" />
                    <div className="flex items-center gap-2 px-1 pb-1">
                      <span className="rounded-full bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-muted-foreground ring-1 ring-white/[0.05]">Agent</span>
                      <span className="rounded-full bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-muted-foreground ring-1 ring-white/[0.05]">Auto</span>
                      <button onClick={handleSend} disabled={!inputValue.trim() || isLoading} aria-label="Send question" className="ml-auto inline-flex h-9 w-9 items-center justify-center rounded-full bg-accent text-accent-foreground transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground"><Send className="h-4 w-4" /></button>
                    </div>
                  </div>
                </BorderBeam>
                <p className="mt-3 text-center text-xs text-muted-foreground">Read-only queries are validated against allowed schemas and values before execution.</p>
              </div>
            </div>
          </motion.main>
        )}
      </AnimatePresence>

      <div className="pointer-events-none fixed bottom-5 left-5 z-30 hidden items-center gap-2 text-xs font-semibold text-muted-foreground lg:flex"><Lock className="h-3.5 w-3.5 text-accent" /> Read-only & validated</div>
    </div>
  );
}
