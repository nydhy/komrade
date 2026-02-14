"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";

type HealthResponse = {
  status: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<string>("unknown");
  const [loading, setLoading] = useState(false);

  const statusLabel = useMemo(() => {
    if (loading) return "Checking...";
    if (health === "ok") return "Backend is healthy";
    if (health === "error") return "Backend is unreachable";
    return "Not checked yet";
  }, [health, loading]);

  const checkHealth = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error("Health endpoint failed");
      }
      const data: HealthResponse = await response.json();
      setHealth(data.status);
    } catch {
      setHealth("error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void checkHealth();
  }, []);

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col items-start justify-center gap-6 px-6">
      <h1 className="text-3xl font-semibold">KOMRADE - Phase 1</h1>
      <p className="text-muted-foreground">
        Frontend to backend connectivity check on localhost.
      </p>
      <div className="rounded-lg border bg-card p-5">
        <p className="mb-3 text-sm text-muted-foreground">API status:</p>
        <p className="mb-4 text-lg font-medium">{statusLabel}</p>
        <Button onClick={checkHealth} disabled={loading}>
          Retry /health
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">
        Calling: <code>{API_BASE_URL}/health</code>
      </p>
      <div className="flex gap-4 text-sm">
        <a className="text-primary underline" href="/ladder">
          Go to Social Exposure Ladder
        </a>
        <a className="text-primary underline" href="/translate">
          Go to Translation Layer
        </a>
      </div>
    </main>
  );
}
