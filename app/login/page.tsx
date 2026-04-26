"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [mode,     setMode]     = useState<"login" | "signup">("login");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);

  const router   = useRouter();
  const supabase = createClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
        });
        if (error) throw error;
        setError("Check your email to confirm your account, then log in.");
        setMode("login");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        router.push("/");
        router.refresh();
      }
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ backgroundColor: "#f5f0e8", fontFamily: "Georgia, serif" }}
    >
      {/* Header */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold mb-2" style={{ letterSpacing: "0.15em", color: "#0a0a0a" }}>
          TRANSFERAI
        </h1>
        <p className="text-xs" style={{ letterSpacing: "0.25em", color: "#0a0a0a", opacity: 0.45 }}>
          TRANSFER PLANNING ASSISTANT
        </p>
      </div>

      {/* Card */}
      <div
        className="w-full max-w-sm p-8"
        style={{ backgroundColor: "#ede8df", border: "1px solid #d6cfc3" }}
      >
        <h2
          className="text-sm font-bold mb-6 text-center"
          style={{ letterSpacing: "0.2em", color: "#0a0a0a" }}
        >
          {mode === "login" ? "SIGN IN" : "CREATE ACCOUNT"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              className="block text-xs mb-1"
              style={{ letterSpacing: "0.1em", color: "#0a0a0a", opacity: 0.6 }}
            >
              EMAIL
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-3 py-2 text-sm outline-none"
              style={{
                border: "1px solid #c8c0b4",
                backgroundColor: "#f5f0e8",
                color: "#0a0a0a",
                fontFamily: "Georgia, serif",
                letterSpacing: "0.02em",
              }}
            />
          </div>

          <div>
            <label
              className="block text-xs mb-1"
              style={{ letterSpacing: "0.1em", color: "#0a0a0a", opacity: 0.6 }}
            >
              PASSWORD
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-3 py-2 text-sm outline-none"
              style={{
                border: "1px solid #c8c0b4",
                backgroundColor: "#f5f0e8",
                color: "#0a0a0a",
                fontFamily: "Georgia, serif",
                letterSpacing: "0.02em",
              }}
            />
          </div>

          {error && (
            <p
              className="text-xs text-center"
              style={{
                color: error.includes("Check your email") ? "#5a6e4a" : "#8b3a3a",
                letterSpacing: "0.02em",
              }}
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 text-xs transition-all duration-200 disabled:opacity-40"
            style={{
              backgroundColor: "#0a0a0a",
              color: "#f5f0e8",
              letterSpacing: "0.2em",
              fontFamily: "Georgia, serif",
            }}
          >
            {loading ? "..." : mode === "login" ? "SIGN IN" : "CREATE ACCOUNT"}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}
            className="text-xs"
            style={{ color: "#0a0a0a", opacity: 0.5, letterSpacing: "0.08em" }}
          >
            {mode === "login"
              ? "Don't have an account? Sign up"
              : "Already have an account? Sign in"}
          </button>
        </div>
      </div>

      <p
        className="mt-8 text-xs text-center"
        style={{ letterSpacing: "0.15em", color: "#0a0a0a", opacity: 0.3 }}
      >
        DE ANZA COLLEGE · 2025–2026
      </p>
    </div>
  );
}
