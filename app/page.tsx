"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { displaySchoolName } from "@/lib/schools";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Profile {
  intended_major:       string | null;
  transfer_year:        number | null;
  unit_load_preference: number | null;
}

export default function Home() {
  const [messages,     setMessages]     = useState<Message[]>([]);
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [profile,      setProfile]      = useState<Profile | null>(null);
  const [school,       setSchool]       = useState<string>("UC Davis");
  const [profileReady, setProfileReady] = useState(false);
  const bottomRef                       = useRef<HTMLDivElement>(null);
  const router                          = useRouter();
  const supabase                        = createClient();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    async function loadProfile() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { setProfileReady(true); return; }

      const { data: p } = await supabase
        .from("profiles")
        .select("intended_major, transfer_year, unit_load_preference")
        .eq("user_id", user.id)
        .single();

      if (p) setProfile(p);

      const { data: t } = await supabase
        .from("target_schools")
        .select("schools(name)")
        .eq("user_id", user.id)
        .limit(1)
        .single();

      if (t?.schools) {
        const dbName = (t.schools as any).name;
        setSchool(displaySchoolName(dbName));
      }

      setProfileReady(true);
    }
    loadProfile();
  }, []);

  const suggestedQuestions = profileReady ? [
    `What courses do I need for my major?`,
    `Make me a transfer plan`,
    `Does EWRT 1A transfer to ${school}?`,
    `What courses articulate to ${school}?`,
  ] : [];

  async function handleSignOut() {
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  async function sendMessage(text: string) {
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const res = await fetch("/api/chat", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          message: text,
          history: messages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader  = res.body!.getReader();
      const decoder = new TextDecoder();
      let   done    = false;

      while (!done) {
        const { value, done: streamDone } = await reader.read();
        done = streamDone;
        if (value) {
          const chunk = decoder.decode(value);
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role:    "assistant",
              content: updated[updated.length - 1].content + chunk,
            };
            return updated;
          });
        }
      }
    } catch (err: any) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: `Error: ${err.message}` };
        return updated;
      });
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function cleanContent(content: string): string {
    return content.replace(/\[Checking [^\]]+\.\.\.\]\n?/g, "").trim();
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden"
      style={{ backgroundColor: "#f5f0e8", color: "#0a0a0a", fontFamily: "'Georgia', 'Times New Roman', serif" }}>

      <header className="flex-none px-8 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid #d6cfc3" }}>
        <span className="text-lg font-bold" style={{ letterSpacing: "0.25em", color: "#0a0a0a" }}>TRANSFERAI</span>
        <div className="flex items-center gap-4">
          {profile?.intended_major && (
            <div className="flex items-center gap-3 text-xs" style={{ color: "#0a0a0a", opacity: 0.5, letterSpacing: "0.08em" }}>
              <span>{profile.intended_major}</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span>{school}</span>
              <span style={{ opacity: 0.4 }}>·</span>
              <span>{profile.transfer_year}</span>
            </div>
          )}
          <button onClick={() => router.push("/settings")} className="text-xs transition-all"
            style={{ color: "#0a0a0a", opacity: 0.35, letterSpacing: "0.12em" }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.7")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.35")}>
            SETTINGS
          </button>
          <button onClick={handleSignOut} className="text-xs transition-all"
            style={{ color: "#0a0a0a", opacity: 0.35, letterSpacing: "0.12em" }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.7")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "0.35")}>
            SIGN OUT
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-10">
            <div className="text-center space-y-3">
              <h1 className="text-4xl font-bold" style={{ letterSpacing: "0.1em", color: "#0a0a0a" }}>TransferAI</h1>
              <p className="text-xs" style={{ letterSpacing: "0.3em", color: "#0a0a0a", opacity: 0.45 }}>
                POWERED BY OFFICIAL ASSIST.ORG ARTICULATION DATA
              </p>
              <div className="w-16 h-px mx-auto mt-2" style={{ backgroundColor: "#0a0a0a", opacity: 0.15 }} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-2xl">
              {suggestedQuestions.map((q) => (
                <button key={q} onClick={() => sendMessage(q)} className="text-left px-5 py-4 transition-all duration-200"
                  style={{ border: "1px solid #c8c0b4", color: "#0a0a0a", backgroundColor: "transparent", letterSpacing: "0.03em", lineHeight: "1.6", fontSize: "0.75rem" }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#ede8df")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-4 max-w-3xl mx-auto w-full ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}>
            <div className="flex-none text-xs mt-1 w-8 text-right"
              style={{ letterSpacing: "0.15em", fontFamily: "Georgia, serif", color: "#0a0a0a", opacity: msg.role === "user" ? 0.4 : 0.6 }}>
              {msg.role === "user" ? "YOU" : "TAI"}
            </div>
            <div className="text-sm max-w-[85%]"
              style={{ letterSpacing: "0.02em", lineHeight: "1.8", fontFamily: "Georgia, serif", padding: "12px 20px",
                backgroundColor: msg.role === "user" ? "#0a0a0a" : "#ede8df",
                color: msg.role === "user" ? "#f5f0e8" : "#0a0a0a",
                border: msg.role === "assistant" ? "1px solid #d6cfc3" : "none" }}>
              {msg.content ? (
                msg.role === "user" ? (
                  <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>
                ) : (
                  <ReactMarkdown components={{
                    h1: ({ children }) => <h1 style={{ fontSize: "1.2rem", fontWeight: "bold", marginBottom: "0.5rem", letterSpacing: "0.05em" }}>{children}</h1>,
                    h2: ({ children }) => <h2 style={{ fontSize: "1rem", fontWeight: "bold", marginTop: "1rem", marginBottom: "0.4rem", letterSpacing: "0.04em" }}>{children}</h2>,
                    h3: ({ children }) => <h3 style={{ fontSize: "0.9rem", fontWeight: "bold", marginTop: "0.8rem", marginBottom: "0.3rem" }}>{children}</h3>,
                    p:  ({ children }) => <p style={{ marginBottom: "0.6rem" }}>{children}</p>,
                    ul: ({ children }) => <ul style={{ paddingLeft: "1.2rem", marginBottom: "0.6rem" }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ paddingLeft: "1.2rem", marginBottom: "0.6rem" }}>{children}</ol>,
                    li: ({ children }) => <li style={{ marginBottom: "0.25rem" }}>{children}</li>,
                    strong: ({ children }) => <strong style={{ fontWeight: "bold" }}>{children}</strong>,
                    code: ({ children }) => <code style={{ backgroundColor: "#d6cfc3", padding: "1px 4px", fontSize: "0.8rem" }}>{children}</code>,
                    hr: () => <hr style={{ border: "none", borderTop: "1px solid #d6cfc3", margin: "0.8rem 0" }} />,
                  }}>
                    {cleanContent(msg.content)}
                  </ReactMarkdown>
                )
              ) : (
                <span style={{ color: "#0a0a0a", opacity: 0.3 }}>
                  <span className="animate-bounce inline-block" style={{ animationDelay: "0ms" }}>·</span>
                  <span className="animate-bounce inline-block" style={{ animationDelay: "150ms" }}>·</span>
                  <span className="animate-bounce inline-block" style={{ animationDelay: "300ms" }}>·</span>
                </span>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex-none px-6 py-5" style={{ borderTop: "1px solid #d6cfc3", backgroundColor: "#f5f0e8" }}>
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="Ask about transfer requirements, course articulation, or planning..."
            rows={1} disabled={loading}
            className="flex-1 resize-none outline-none transition-all duration-200 disabled:opacity-40"
            style={{ border: "1px solid #c8c0b4", padding: "10px 16px", fontSize: "0.875rem", fontFamily: "Georgia, serif", letterSpacing: "0.02em", lineHeight: "1.6", color: "#0a0a0a", backgroundColor: "#f5f0e8", minHeight: "44px", maxHeight: "128px" }} />
          <button onClick={() => sendMessage(input)} disabled={loading || !input.trim()}
            className="flex-none px-6 h-11 text-xs transition-all duration-200 disabled:opacity-25 disabled:cursor-not-allowed"
            style={{ backgroundColor: "#0a0a0a", color: "#f5f0e8", letterSpacing: "0.15em", fontFamily: "Georgia, serif" }}>
            {loading ? <span className="w-4 h-4 border-2 rounded-full animate-spin inline-block" style={{ borderColor: "#f5f0e8", borderTopColor: "transparent" }} /> : "SEND"}
          </button>
        </div>
        <p className="text-center text-xs mt-3" style={{ letterSpacing: "0.2em", color: "#0a0a0a", opacity: 0.3 }}>
          DE ANZA COLLEGE · 2025–2026 CATALOG
        </p>
      </div>
    </div>
  );
}
