"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type TranslateResult = {
  generic_answer: string;
  empathetic_personalized_answer: string;
  safety_flag: "none" | "crisis";
};

const QUICK_CHIPS = [
  {
    label: "Interview gap",
    message:
      "How do I explain the 4-year gap in my resume during a job interview? I served overseas and the interviewer keeps asking what I did during that time.",
  },
  {
    label: "Awkward question",
    message:
      "Someone at a networking event asked me 'Did you kill anyone?' I froze and didn't know how to respond. What could I say?",
  },
  {
    label: "Dinner party",
    message:
      "At a dinner party, someone said 'Thank you for your service' and wants to know more about my deployment. I don't want to get into details. How do I redirect?",
  },
] as const;

export default function TranslatePage() {
  const [token, setToken] = useState("");
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<TranslateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("komrade_token");
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  const authHeaders = () => {
    if (!token.trim()) {
      throw new Error("JWT token is required. Save one in the Auth Token section.");
    }
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  };

  const onSubmit = async () => {
    const trimmed = message.trim();
    if (!trimmed) {
      setError("Please enter a message.");
      return;
    }
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const response = await fetch(`${API_BASE_URL}/ai/translate`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ message: trimmed, context: {} }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Failed to translate");
      }
      const data: TranslateResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  const onChipClick = (chipMessage: string) => {
    setMessage(chipMessage);
    setError(null);
    setResult(null);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 px-6 py-8">
      <div>
        <h1 className="text-3xl font-semibold">VetBridge Translation Layer</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Translate military experiences into civilian-friendly and empathetic
          responses. Compare generic vs personalized answers.
        </p>
        <div className="mt-3 flex gap-4 text-sm">
          <a className="text-primary underline" href="/">
            Home
          </a>
          <a className="text-primary underline" href="/ladder">
            Social Exposure Ladder
          </a>
        </div>
      </div>

      <section className="rounded-lg border bg-card p-5">
        <h2 className="mb-3 text-lg font-semibold">Auth Token</h2>
        <input
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          placeholder="Paste JWT token from /auth/login"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <Button
          variant="outline"
          className="mt-3"
          onClick={() => {
            window.localStorage.setItem("komrade_token", token.trim());
          }}
        >
          Save Token
        </Button>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h2 className="mb-2 text-lg font-semibold">Your Message</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          Describe your military experience or the situation you need help
          translating for civilians.
        </p>
        <div className="mb-3 flex flex-wrap gap-2">
          {QUICK_CHIPS.map((chip) => (
            <button
              key={chip.label}
              type="button"
              onClick={() => onChipClick(chip.message)}
              className="rounded-full border border-input bg-background px-4 py-1.5 text-sm transition-colors hover:bg-muted"
            >
              {chip.label}
            </button>
          ))}
        </div>
        <textarea
          className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[120px]"
          placeholder="e.g. How do I explain my deployment to a hiring manager?"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={4}
        />
        <Button
          className="mt-3"
          onClick={onSubmit}
          disabled={loading || !message.trim()}
        >
          {loading ? "Translating…" : "Translate"}
        </Button>
      </section>

      {error ? (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {result ? (
        <section className="grid gap-4 md:grid-cols-2">
          <article className="rounded-lg border bg-card p-5">
            <h3 className="mb-3 text-base font-semibold text-muted-foreground">
              Generic Answer
            </h3>
            <p className="text-sm leading-relaxed">{result.generic_answer}</p>
          </article>
          <article className="rounded-lg border bg-card p-5">
            <h3 className="mb-3 text-base font-semibold text-muted-foreground">
              Personalized, Empathetic Answer
            </h3>
            <p className="text-sm leading-relaxed">
              {result.empathetic_personalized_answer}
            </p>
          </article>
        </section>
      ) : null}
    </main>
  );
}
