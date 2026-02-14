"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type LadderWeek = {
  week: number;
  title: string;
  difficulty: "low" | "med" | "high";
  rationale: string;
  suggested_time: string;
};

type LadderResult = {
  weeks: LadderWeek[];
};

type LadderChallenge = {
  id: string;
  week: number;
  title: string;
  difficulty: string;
  rationale: string;
  suggested_time: string | null;
  status: string;
  completed: boolean;
};

type LadderPlanOut = {
  plan_id: string;
  created_at: string;
  challenges: LadderChallenge[];
};

export default function LadderPage() {
  const [token, setToken] = useState("");
  const [anxietyLevel, setAnxietyLevel] = useState(5);
  const [preferredTime, setPreferredTime] = useState("Evenings");
  const [crowdTolerance, setCrowdTolerance] = useState("low");
  const [interests, setInterests] = useState("Fitness, coffee, volunteering");
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");

  const [generated, setGenerated] = useState<LadderResult | null>(null);
  const [savedPlan, setSavedPlan] = useState<LadderPlanOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("Idle");

  useEffect(() => {
    const savedToken = window.localStorage.getItem("komrade_token");
    if (savedToken) {
      setToken(savedToken);
    }
  }, []);

  const xp = useMemo(() => {
    if (!savedPlan) return 0;
    return savedPlan.challenges.filter((c) => c.completed).length * 100;
  }, [savedPlan]);

  const streak = useMemo(() => {
    if (!savedPlan) return 0;
    const sorted = [...savedPlan.challenges].sort((a, b) => a.week - b.week);
    let current = 0;
    for (const challenge of sorted) {
      if (challenge.completed) {
        current += 1;
      } else {
        break;
      }
    }
    return current;
  }, [savedPlan]);

  const authHeaders = () => {
    if (!token.trim()) {
      throw new Error("JWT token is required.");
    }
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  };

  const onGenerate = async () => {
    setError(null);
    setLoading(true);
    setStatus("Generating ladder...");
    try {
      const intake = {
        anxiety_level: anxietyLevel,
        preferred_time: preferredTime,
        crowd_tolerance: crowdTolerance,
        interests: interests.split(",").map((item) => item.trim()).filter(Boolean),
        lat: lat ? Number(lat) : null,
        lng: lng ? Number(lng) : null,
      };

      const response = await fetch(`${API_BASE_URL}/ai/ladder`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ intake }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Failed to generate ladder");
      }
      const data: LadderResult = await response.json();
      setGenerated(data);
      setStatus("Generated. Review and save.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("Failed");
    } finally {
      setLoading(false);
    }
  };

  const onSave = async () => {
    if (!generated) {
      setError("Generate ladder first.");
      return;
    }
    setError(null);
    setLoading(true);
    setStatus("Saving plan...");
    try {
      const response = await fetch(`${API_BASE_URL}/ladder/plans`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ weeks: generated.weeks }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Failed to save plan");
      }
      const data: LadderPlanOut = await response.json();
      setSavedPlan(data);
      setStatus("Plan saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("Failed");
    } finally {
      setLoading(false);
    }
  };

  const loadLatest = async () => {
    setError(null);
    setLoading(true);
    setStatus("Loading latest plan...");
    try {
      const response = await fetch(`${API_BASE_URL}/ladder/plans/latest`, {
        headers: authHeaders(),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail ?? "No plan available");
      }
      const data: LadderPlanOut = await response.json();
      setSavedPlan(data);
      setStatus("Latest plan loaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("Failed");
    } finally {
      setLoading(false);
    }
  };

  const completeChallenge = async (challengeId: string) => {
    setError(null);
    setLoading(true);
    setStatus("Saving completion...");
    try {
      const response = await fetch(
        `${API_BASE_URL}/ladder/challenges/${challengeId}/complete`,
        {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({
            lat: lat ? Number(lat) : null,
            lng: lng ? Number(lng) : null,
          }),
        },
      );
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail ?? "Failed to complete challenge");
      }
      const data: LadderPlanOut = await response.json();
      setSavedPlan(data);
      setStatus("Challenge completed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("Failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col gap-6 px-6 py-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold">KOMRADE Social Exposure Ladder</h1>
          <p className="text-sm text-muted-foreground">
            Generate an 8-week plan, save it, and mark challenge completion.
          </p>
        </div>
        <div className="rounded-lg border bg-card px-4 py-3 text-sm">
          <p>XP: <span className="font-semibold">{xp}</span></p>
          <p>Streak: <span className="font-semibold">{streak} weeks</span></p>
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
        <div className="mt-3 flex gap-2">
          <Button
            variant="outline"
            onClick={() => {
              window.localStorage.setItem("komrade_token", token.trim());
              setStatus("Token saved locally.");
            }}
          >
            Save Token
          </Button>
          <Button variant="outline" onClick={loadLatest} disabled={loading}>
            Load Latest Plan
          </Button>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h2 className="mb-4 text-lg font-semibold">Intake Form</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="text-sm">
            Anxiety Level (1-10)
            <input
              type="number"
              min={1}
              max={10}
              value={anxietyLevel}
              onChange={(e) => setAnxietyLevel(Number(e.target.value))}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Preferred Time
            <input
              value={preferredTime}
              onChange={(e) => setPreferredTime(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Crowd Tolerance
            <select
              value={crowdTolerance}
              onChange={(e) => setCrowdTolerance(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            >
              <option value="low">Low</option>
              <option value="med">Medium</option>
              <option value="high">High</option>
            </select>
          </label>
          <label className="text-sm">
            Interests (comma-separated)
            <input
              value={interests}
              onChange={(e) => setInterests(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Latitude
            <input
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </label>
          <label className="text-sm">
            Longitude
            <input
              value={lng}
              onChange={(e) => setLng(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button onClick={onGenerate} disabled={loading}>
            Generate Ladder
          </Button>
          <Button onClick={onSave} variant="outline" disabled={loading || !generated}>
            Save Plan
          </Button>
        </div>
      </section>

      <section className="rounded-lg border bg-card p-5">
        <h2 className="mb-3 text-lg font-semibold">Ladder View</h2>
        <p className="mb-4 text-sm text-muted-foreground">Status: {status}</p>
        {error ? (
          <p className="mb-4 rounded-md border border-red-300 bg-red-50 p-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        <div className="grid gap-3 md:grid-cols-2">
          {(savedPlan?.challenges ??
            generated?.weeks.map((week) => ({
              id: `${week.week}`,
              week: week.week,
              title: week.title,
              difficulty: week.difficulty,
              rationale: week.rationale,
              suggested_time: week.suggested_time,
              status: "generated",
              completed: false,
            })) ??
            []
          ).map((challenge) => (
            <article key={challenge.id} className="rounded-lg border bg-background p-4">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-base font-semibold">Week {challenge.week}</h3>
                <span className="text-xs uppercase text-muted-foreground">
                  {challenge.difficulty}
                </span>
              </div>
              <p className="font-medium">{challenge.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                {challenge.rationale}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Suggested time: {challenge.suggested_time ?? "Flexible"}
              </p>
              <div className="mt-3 flex items-center gap-2">
                <span className="text-xs text-muted-foreground">
                  {challenge.completed ? "Completed" : challenge.status}
                </span>
                {savedPlan && !challenge.completed ? (
                  <Button
                    size="sm"
                    onClick={() => completeChallenge(challenge.id)}
                    disabled={loading}
                  >
                    Complete
                  </Button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
