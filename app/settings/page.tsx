"use client";

import { useState, useEffect } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { displaySchoolName } from "@/lib/schools";

const MAJORS = [
  "Computer Science",
  "Computer Science & Engineering",
  "Electrical Engineering",
  "Mechanical Engineering",
  "Biology",
  "Chemistry",
  "Mathematics",
  "Physics",
  "Psychology",
  "Economics",
  "Business Administration",
  "Political Science",
  "Sociology",
  "English",
  "History",
  "Other",
];

const TARGET_SCHOOLS: { label: string; dbName: string }[] = [
  { label: "UC Davis",         dbName: "UC Davis" },
  { label: "UC Berkeley",      dbName: "University of California, Berkeley" },
  { label: "UCLA",             dbName: "University of California, Los Angeles" },
  { label: "UC San Diego",     dbName: "University of California, San Diego" },
  { label: "UC Santa Barbara", dbName: "University of California, Santa Barbara" },
  { label: "UC Irvine",        dbName: "University of California, Irvine" },
  { label: "UC Santa Cruz",    dbName: "University of California, Santa Cruz" },
  { label: "UC Riverside",     dbName: "University of California, Riverside" },
  { label: "UC Merced",        dbName: "University of California, Merced" },
  { label: "Cal Poly SLO",     dbName: "California Polytechnic State University, San Luis Obispo" },
  { label: "San Jose State",   dbName: "San Jose State University" },
  { label: "Other",            dbName: "" },
];

const TRANSFER_YEARS = ["2025", "2026", "2027", "2028"];

export default function SettingsPage() {
  const [major,        setMajor]        = useState("");
  const [targetSchool, setTargetSchool] = useState<{ label: string; dbName: string } | null>(null);
  const [transferYear, setTransferYear] = useState("2026");
  const [unitsPerTerm, setUnitsPerTerm] = useState(15);
  const [loading,      setLoading]      = useState(true);
  const [saving,       setSaving]       = useState(false);
  const [saved,        setSaved]        = useState(false);
  const [error,        setError]        = useState("");

  const router   = useRouter();
  const supabase = createClient();
  const FONT     = { fontFamily: "Georgia, serif" };

  useEffect(() => {
    async function loadProfile() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) { router.push("/login"); return; }

      const { data: p } = await supabase
        .from("profiles")
        .select("intended_major, transfer_year, unit_load_preference")
        .eq("user_id", user.id)
        .single();

      if (p) {
        setMajor(p.intended_major || "");
        setTransferYear(String(p.transfer_year || "2026"));
        setUnitsPerTerm(p.unit_load_preference || 15);
      }

      const { data: t } = await supabase
        .from("target_schools")
        .select("schools(name)")
        .eq("user_id", user.id)
        .limit(1)
        .single();

      if (t?.schools) {
        const dbName  = (t.schools as any).name;
        const display = displaySchoolName(dbName);
        const match   = TARGET_SCHOOLS.find((s) => s.dbName === dbName || s.label === display);
        if (match) setTargetSchool(match);
      }

      setLoading(false);
    }
    loadProfile();
  }, []);

  async function handleSave() {
    setError("");
    setSaving(true);
    setSaved(false);

    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("Not logged in.");

      await supabase.from("profiles").upsert({
        user_id:              user.id,
        intended_major:       major,
        unit_load_preference: unitsPerTerm,
        transfer_year:        parseInt(transferYear),
      });

      if (targetSchool?.dbName) {
        const { data: schoolData } = await supabase
          .from("schools")
          .select("id")
          .eq("name", targetSchool.dbName)
          .limit(1);

        if (schoolData && schoolData.length > 0) {
          await supabase.from("target_schools").upsert({
            user_id:   user.id,
            school_id: schoolData[0].id,
            priority:  1,
          });
        }
      }

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "#f5f0e8" }}>
        <p className="text-xs" style={{ letterSpacing: "0.2em", color: "#0a0a0a", opacity: 0.4, ...FONT }}>LOADING...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#f5f0e8", ...FONT }}>
      {/* Header */}
      <header className="px-8 py-4 flex items-center justify-between" style={{ borderBottom: "1px solid #d6cfc3" }}>
        <button onClick={() => router.push("/")} className="text-lg font-bold" style={{ letterSpacing: "0.25em", color: "#0a0a0a" }}>
          TRANSFERAI
        </button>
        <span className="text-xs" style={{ letterSpacing: "0.2em", color: "#0a0a0a", opacity: 0.5 }}>SETTINGS</span>
      </header>

      <div className="max-w-lg mx-auto px-6 py-10 space-y-8">

        {/* Major */}
        <div>
          <h2 className="text-xs font-bold mb-3" style={{ letterSpacing: "0.2em" }}>INTENDED MAJOR</h2>
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {MAJORS.map((m) => (
              <button key={m} onClick={() => setMajor(m)}
                className="w-full text-left px-4 py-2.5 text-sm transition-all"
                style={{ border: "1px solid", borderColor: major === m ? "#0a0a0a" : "#c8c0b4", backgroundColor: major === m ? "#0a0a0a" : "transparent", color: major === m ? "#f5f0e8" : "#0a0a0a", letterSpacing: "0.02em", ...FONT }}>
                {m}
              </button>
            ))}
          </div>
        </div>

        {/* Target school */}
        <div>
          <h2 className="text-xs font-bold mb-3" style={{ letterSpacing: "0.2em" }}>TARGET SCHOOL</h2>
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {TARGET_SCHOOLS.map((s) => (
              <button key={s.label} onClick={() => setTargetSchool(s)}
                className="w-full text-left px-4 py-2.5 text-sm transition-all"
                style={{ border: "1px solid", borderColor: targetSchool?.label === s.label ? "#0a0a0a" : "#c8c0b4", backgroundColor: targetSchool?.label === s.label ? "#0a0a0a" : "transparent", color: targetSchool?.label === s.label ? "#f5f0e8" : "#0a0a0a", letterSpacing: "0.02em", ...FONT }}>
                {s.label}
              </button>
            ))}
          </div>
        </div>

        {/* Transfer year */}
        <div>
          <h2 className="text-xs font-bold mb-3" style={{ letterSpacing: "0.2em" }}>TRANSFER YEAR</h2>
          <div className="flex gap-2">
            {TRANSFER_YEARS.map((y) => (
              <button key={y} onClick={() => setTransferYear(y)}
                className="flex-1 py-2 text-xs transition-all"
                style={{ border: "1px solid", borderColor: transferYear === y ? "#0a0a0a" : "#c8c0b4", backgroundColor: transferYear === y ? "#0a0a0a" : "transparent", color: transferYear === y ? "#f5f0e8" : "#0a0a0a", letterSpacing: "0.05em", ...FONT }}>
                {y}
              </button>
            ))}
          </div>
        </div>

        {/* Units per term */}
        <div>
          <h2 className="text-xs font-bold mb-3" style={{ letterSpacing: "0.2em" }}>UNITS PER TERM: {unitsPerTerm}</h2>
          <input type="range" min={9} max={19} value={unitsPerTerm}
            onChange={(e) => setUnitsPerTerm(parseInt(e.target.value))}
            className="w-full accent-black" />
          <div className="flex justify-between text-xs mt-1" style={{ opacity: 0.4, letterSpacing: "0.05em" }}>
            <span>9 (light)</span><span>19 (heavy)</span>
          </div>
        </div>

        {/* Save */}
        {error && <p className="text-xs" style={{ color: "#8b3a3a" }}>{error}</p>}

        <div className="flex gap-3">
          <button onClick={() => router.push("/")}
            className="flex-1 py-3 text-xs border transition-all"
            style={{ borderColor: "#c8c0b4", color: "#0a0a0a", letterSpacing: "0.15em", ...FONT }}>
            BACK
          </button>
          <button onClick={handleSave} disabled={saving}
            className="flex-1 py-3 text-xs transition-all disabled:opacity-40"
            style={{ backgroundColor: saved ? "#3a6e4a" : "#0a0a0a", color: "#f5f0e8", letterSpacing: "0.15em", ...FONT }}>
            {saving ? "SAVING..." : saved ? "SAVED ✓" : "SAVE CHANGES"}
          </button>
        </div>
      </div>
    </div>
  );
}
