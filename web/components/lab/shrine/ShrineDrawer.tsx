"use client";

import { motion, AnimatePresence, type Variants } from "framer-motion";
import { useState, useEffect, useRef } from "react";
import type { Master } from "./masters";

const drawerVariants: Variants = {
  closed: {
    x: "100%",
    transition: { duration: 0.48, ease: [0.22, 1, 0.36, 1] },
  },
  open: {
    x: "0%",
    transition: {
      duration: 0.64,
      ease: [0.16, 1, 0.3, 1],
      when: "beforeChildren",
      staggerChildren: 0.08,
      delayChildren: 0.18,
    },
  },
};

const contentVariants: Variants = {
  closed: { opacity: 0, y: 12 },
  open: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.22, 1, 0.36, 1] },
  },
};

type Props = {
  master: Master | null;
  onClose: () => void;
};

type Answer = {
  text: string;
  citations: Array<{ n: number; work: string; edition: string; translator: string; locator: string }>;
};

export default function ShrineDrawer({ master, onClose }: Props) {
  const open = master !== null;
  return (
    <AnimatePresence>
      {open && master && (
        <>
          {/* Rice-paper scrim */}
          <motion.div
            className="fixed inset-0 z-40"
            style={{
              backgroundColor: "rgba(251, 247, 238, 0.72)",
              backdropFilter: "blur(3px)",
              WebkitBackdropFilter: "blur(3px)",
            }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { duration: 0.4 } }}
            exit={{ opacity: 0, transition: { duration: 0.32 } }}
            onClick={onClose}
          />

          <motion.aside
            key={master.id}
            className="fixed right-0 top-0 z-50 h-full overflow-y-auto"
            style={{
              width: "min(620px, 94vw)",
              backgroundColor: "#F3ECDB",
              borderLeft: "1px solid #D6C8A5",
              boxShadow:
                "-18px 0 48px -16px rgba(42,34,24,0.28), -4px 0 0 0 #E8DEC4",
            }}
            variants={drawerVariants}
            initial="closed"
            animate="open"
            exit="closed"
          >
            {/* Washi paper fiber overlay */}
            <div
              className="pointer-events-none absolute inset-0"
              style={{
                backgroundImage: `
                  radial-gradient(circle at 20% 30%, rgba(120,90,60,0.025) 0, transparent 40%),
                  radial-gradient(circle at 80% 70%, rgba(255,250,235,0.4) 0, transparent 50%)
                `,
                mixBlendMode: "multiply",
              }}
              aria-hidden="true"
            />

            <motion.div
              variants={contentVariants}
              className="relative px-10 pt-12 pb-8 md:px-14"
            >
              <CloseButton onClick={onClose} />

              <div className="flex items-baseline gap-4">
                <h2
                  className="text-4xl md:text-5xl font-normal tracking-tight"
                  style={{
                    color: "#0A0705",
                    fontFamily: "'Cormorant Garamond', 'EB Garamond', Georgia, serif",
                  }}
                >
                  {master.primaryName}
                </h2>
                {master.scriptName && (
                  <span
                    className="text-2xl md:text-3xl"
                    style={{
                      color: "#4A4237",
                      fontFamily: "'Noto Serif JP', 'Noto Serif Tibetan', serif",
                    }}
                  >
                    {master.scriptName}
                  </span>
                )}
              </div>
              <p
                className="mt-1 text-xs uppercase tracking-[0.18em]"
                style={{ color: "#8A7050", fontFamily: "var(--font-display)" }}
              >
                {master.traditionLabel} · {master.country} · {master.lifespan}
              </p>
            </motion.div>

            <motion.div
              variants={contentVariants}
              className="relative px-10 md:px-14"
            >
              <p
                className="text-[1.1875rem] leading-[1.8]"
                style={{
                  color: "#2A2218",
                  fontFamily: "'Cormorant Garamond', 'EB Garamond', Georgia, serif",
                }}
              >
                {master.summary}
              </p>
            </motion.div>

            <motion.div
              variants={contentVariants}
              className="relative px-10 md:px-14 mt-8"
            >
              <SectionLabel>Passages</SectionLabel>
              <div className="mt-4 space-y-6">
                {master.passages.map((p, i) => (
                  <blockquote
                    key={i}
                    className="border-l-2 pl-5"
                    style={{ borderColor: "#B8001F" }}
                  >
                    <p
                      className="italic text-[1.125rem] leading-[1.75]"
                      style={{
                        color: "#0A0705",
                        fontFamily:
                          "'Cormorant Garamond', 'EB Garamond', Georgia, serif",
                      }}
                    >
                      &ldquo;{p.text}&rdquo;
                    </p>
                    <footer
                      className="mt-2 text-xs"
                      style={{
                        color: "#6A5A40",
                        fontFamily: "var(--font-display)",
                        letterSpacing: "0.04em",
                      }}
                    >
                      <span style={{ color: "#2A2218" }}>{p.work}</span> ·{" "}
                      {p.edition} · tr. {p.translator} · {p.locator}
                    </footer>
                  </blockquote>
                ))}
              </div>
            </motion.div>

            <motion.div
              variants={contentVariants}
              className="relative px-10 md:px-14 mt-12 pb-16"
            >
              <SectionLabel>Ask the Librarian</SectionLabel>
              <p
                className="mt-2 text-sm"
                style={{ color: "#6A5A40", fontFamily: "var(--font-display)" }}
              >
                Your question is answered only from this master&apos;s cited passages.
              </p>
              <LibrarianPanel master={master} />
            </motion.div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="h-px flex-1"
        style={{ backgroundColor: "#D6C8A5" }}
        aria-hidden="true"
      />
      <span
        className="text-[0.6875rem] uppercase tracking-[0.24em]"
        style={{ color: "#8A7050", fontFamily: "var(--font-display)" }}
      >
        {children}
      </span>
      <div
        className="h-px flex-1"
        style={{ backgroundColor: "#D6C8A5" }}
        aria-hidden="true"
      />
    </div>
  );
}

function CloseButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-label="Close shrine"
      className="absolute right-6 top-6 flex h-10 w-10 items-center justify-center rounded-full transition-colors"
      style={{
        backgroundColor: "transparent",
        color: "#4A4237",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = "rgba(184,0,31,0.08)";
        e.currentTarget.style.color = "#B8001F";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = "transparent";
        e.currentTarget.style.color = "#4A4237";
      }}
    >
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
        <path
          d="M3 3L15 15M15 3L3 15"
          stroke="currentColor"
          strokeWidth="1.25"
          strokeLinecap="round"
        />
      </svg>
    </button>
  );
}

function LibrarianPanel({ master }: { master: Master }) {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Reset when master changes
  useEffect(() => {
    setQuery("");
    setAnswer(null);
    setLoading(false);
  }, [master.id]);

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setAnswer(null);

    // --- MOCK RESPONSE ---
    // In production this POSTs to /api/librarian with { master_id, query },
    // which embeds the query via onnxruntime-node (BGE-m3), runs a pgvector
    // similarity search scoped by master_id, and asks Claude to synthesize
    // a cited answer from the retrieved passages.
    await new Promise((r) => setTimeout(r, 700 + Math.random() * 400));

    const n = Math.min(master.passages.length, 2);
    const lines = master.passages.slice(0, n).map((p, i) => {
      const mark = i === 0 ? "[1]" : "[2]";
      return `${master.primaryName} meets your question directly. "${p.text}" ${mark}`;
    });
    const synth =
      lines.join(" ") +
      ` The passages do not resolve every nuance of the question, but they point toward the response ${master.primaryName} would have given: awareness precedes conclusion.`;

    setAnswer({
      text: synth,
      citations: master.passages.slice(0, n).map((p, i) => ({
        n: i + 1,
        work: p.work,
        edition: p.edition,
        translator: p.translator,
        locator: p.locator,
      })),
    });
    setLoading(false);
  }

  return (
    <div className="mt-4">
      <form onSubmit={handleAsk} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={`What would ${master.primaryName} say about…`}
          className="flex-1 rounded-lg border px-4 py-3 text-base outline-none transition-colors"
          style={{
            backgroundColor: "#FBF7EE",
            borderColor: "#D6C8A5",
            color: "#0A0705",
            fontFamily: "'Cormorant Garamond', Georgia, serif",
          }}
          onFocus={(e) => (e.currentTarget.style.borderColor = "#B8001F")}
          onBlur={(e) => (e.currentTarget.style.borderColor = "#D6C8A5")}
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="rounded-lg px-5 py-3 text-sm font-medium tracking-wide transition-all disabled:opacity-40"
          style={{
            backgroundColor: "#B8001F",
            color: "#FFFFFF",
            fontFamily: "var(--font-display)",
            letterSpacing: "0.08em",
          }}
        >
          {loading ? "…" : "ASK"}
        </button>
      </form>

      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-6 text-sm italic"
            style={{ color: "#8A7050", fontFamily: "'Cormorant Garamond', serif" }}
          >
            Consulting the archive…
          </motion.div>
        )}
        {answer && !loading && (
          <motion.div
            key={answer.text}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="mt-6"
          >
            <p
              className="text-[1.0625rem] leading-[1.8]"
              style={{
                color: "#2A2218",
                fontFamily: "'Cormorant Garamond', Georgia, serif",
              }}
            >
              {renderWithCitations(answer.text)}
            </p>
            <div
              className="mt-5 rounded-md border p-4"
              style={{
                backgroundColor: "#FBF7EE",
                borderColor: "#E8DEC4",
              }}
            >
              <div
                className="mb-2 text-[0.6875rem] uppercase tracking-[0.2em]"
                style={{ color: "#8A7050", fontFamily: "var(--font-display)" }}
              >
                Sources
              </div>
              <ol className="space-y-1.5 text-xs" style={{ color: "#4A4237" }}>
                {answer.citations.map((c) => (
                  <li key={c.n}>
                    <span style={{ color: "#B8001F", fontWeight: 600 }}>
                      [{c.n}]
                    </span>{" "}
                    <span style={{ color: "#0A0705" }}>{c.work}</span> ·{" "}
                    {c.edition} · tr. {c.translator} · {c.locator}
                  </li>
                ))}
              </ol>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function renderWithCitations(text: string): React.ReactNode {
  // Replace [1], [2] etc with styled superscript marks
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    if (/^\[\d+\]$/.test(part)) {
      return (
        <sup
          key={i}
          style={{ color: "#B8001F", fontWeight: 600, marginLeft: "1px" }}
        >
          {part}
        </sup>
      );
    }
    return <span key={i}>{part}</span>;
  });
}
