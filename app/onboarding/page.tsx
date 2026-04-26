"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";

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

const TARGET_SCHOOLS = [
  "UC Davis",
  "UC Berkeley",
  "UCLA",
  "UC San Diego",
  "UC Santa Barbara",
  "UC Irvine",
  "UC Santa Cruz",
  "UC Riverside",
  "UC Merced",
  "Cal Poly SLO",
  "San Jose State",
  "Other",
];

const TRANSFER_YEARS = ["2025", "2026", "2027", "2028"];

export default function OnboardingPage() {
  const [step,         setStep]         = useState(1);
  const [major,        setMajor]        = useState("");
  const [targetSchool, setTargetSchool] = useState("");
  const [transferYear, setTransferYear] = useState("2026");
  const [unitsPerTerm, setUnitsPerTerm] = useState(15);
  const [error,        setError]        = useState("");
  const [loading,      setLoading]      = useState(false);

  const router   = useRouter();
  const supabase = createClient();

  async function handleComplete() {
    setError("");
    setLoading(true);

    try {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("Not logged in.");

      // Upsert profile
      const { error: profileError } = await supabase
        .from("profiles")
        .upsert({
          user_id:               user.id,
          intended_major:        major,
          unit_load_preference:  unitsPerTerm,
          transfer_year:         parseInt(transferYear),
        });

      if (profileError) throw profileError;

      // Add target school
      const { data: schoolData } = await supabase
        .from("schools")
        .select("id")
        .ilike("name", `%${targetSchool.split(" ").slice(-2).join(" ")}%`)
        .limit(1);

      if (schoolData && schoolData.length > 0) {
        await supabase.from("target_schools").upsert({
          user_id:   user.id,
          school_id: schoolData[0].id,
          priority:  1,
        });
      }

      router.push("/");
      router.refresh();
    } catch (err: any) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  const FONT = { fontFamily: "Georgia, serif" };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{ backgroundColor: "#f5f0e8", ...FONT }}
    >
      {/* Progress */}
      <div className="w-full max-w-sm mb-8">
        <div className="flex gap-2">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className="h-0.5 flex-1 transition-all duration-300"
              style={{ backgroundColor: s <= step ? "#0a0a0a" : "#d6cfc3" }}
            />
          ))}
        </div>
        <p className="text-xs mt-2" style={{ letterSpacing: "0.15em", color: "#0a0a0a", opacity: 0.4 }}>
          STEP {step} OF 3
        </p>
      </div>

      <div className="w-full max-w-sm p-8" style={{ backgroundColor: "#ede8df", border: "1px solid #d6cfc3" }}>

        {/* Step 1 — Major */}
        {step === 1 && (
          <div>
            <h2 className="text-sm font-bold mb-1" style={{ letterSpacing: "0.2em" }}>INTENDED MAJOR</h2>
            <p className="text-xs mb-6" style={{ color: "#0a0a0a", opacity: 0.5, letterSpacing: "0.03em" }}>
              What do you plan to study?
            </p>
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {MAJORS.map((m) => (
                <button
                  key={m}
                  onClick={() => setMajor(m)}
                  className="w-full text-left px-4 py-2.5 text-sm transition-all duration-150"
                  style={{
                    border: "1px solid",
                    borderColor: major === m ? "#0a0a0a" : "#c8c0b4",
                    backgroundColor: major === m ? "#0a0a0a" : "transparent",
                    color: major === m ? "#f5f0e8" : "#0a0a0a",
                    letterSpacing: "0.02em",
                    ...FONT,
                  }}
                >
                  {m}
                </button>
              ))}
            </div>
            <button
              onClick={() => major && setStep(2)}
              disabled={!major}
              className="w-full mt-6 py-3 text-xs disabled:opacity-30 transition-all"
              style={{ backgroundColor: "#0a0a0a", color: "#f5f0e8", letterSpacing: "0.2em", ...FONT }}
            >
              CONTINUE
            </button>
          </div>
        )}

        {/* Step 2 — Target school */}
        {step === 2 && (
          <div>
            <h2 className="text-sm font-bold mb-1" style={{ letterSpacing: "0.2em" }}>TARGET SCHOOL</h2>
            <p className="text-xs mb-6" style={{ color: "#0a0a0a", opacity: 0.5, letterSpacing: "0.03em" }}>
              Where do you want to transfer?
            </p>
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {TARGET_SCHOOLS.map((s) => (
                <button
                  key={s}
                  onClick={() => setTargetSchool(s)}
                  className="w-full text-left px-4 py-2.5 text-sm transition-all duration-150"
                  style={{
                    border: "1px solid",
                    borderColor: targetSchool === s ? "#0a0a0a" : "#c8c0b4",
                    backgroundColor: targetSchool === s ? "#0a0a0a" : "transparent",
                    color: targetSchool === s ? "#f5f0e8" : "#0a0a0a",
                    letterSpacing: "0.02em",
                    ...FONT,
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
            <div className="flex gap-2 mt-6">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-3 text-xs border transition-all"
                style={{ borderColor: "#c8c0b4", color: "#0a0a0a", letterSpacing: "0.15em", ...FONT }}
              >
                BACK
              </button>
              <button
                onClick={() => targetSchool && setStep(3)}
                disabled={!targetSchool}
                className="flex-1 py-3 text-xs disabled:opacity-30 transition-all"
                style={{ backgroundColor: "#0a0a0a", color: "#f5f0e8", letterSpacing: "0.15em", ...FONT }}
              >
                CONTINUE
              </button>
            </div>
          </div>
        )}

        {/* Step 3 — Timeline */}
        {step === 3 && (
          <div>
            <h2 className="text-sm font-bold mb-1" style={{ letterSpacing: "0.2em" }}>PLANNING DETAILS</h2>
            <p className="text-xs mb-6" style={{ color: "#0a0a0a", opacity: 0.5, letterSpacing: "0.03em" }}>
              When do you plan to transfer?
            </p>

            <div className="space-y-5">
              <div>
                <label className="block text-xs mb-2" style={{ letterSpacing: "0.12em", opacity: 0.6 }}>
                  TRANSFER YEAR
                </label>
                <div className="flex gap-2">
                  {TRANSFER_YEARS.map((y) => (
                    <button
                      key={y}
                      onClick={() => setTransferYear(y)}
                      className="flex-1 py-2 text-xs transition-all"
                      style={{
                        border: "1px solid",
                        borderColor: transferYear === y ? "#0a0a0a" : "#c8c0b4",
                        backgroundColor: transferYear === y ? "#0a0a0a" : "transparent",
                        color: transferYear === y ? "#f5f0e8" : "#0a0a0a",
                        letterSpacing: "0.05em",
                        ...FONT,
                      }}
                    >
                      {y}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs mb-2" style={{ letterSpacing: "0.12em", opacity: 0.6 }}>
                  UNITS PER TERM: {unitsPerTerm}
                </label>
                <input
                  type="range"
                  min={9}
                  max={19}
                  value={unitsPerTerm}
                  onChange={(e) => setUnitsPerTerm(parseInt(e.target.value))}
                  className="w-full accent-black"
                />
                <div className="flex justify-between text-xs mt-1" style={{ opacity: 0.4, letterSpacing: "0.05em" }}>
                  <span>9 (light)</span>
                  <span>19 (heavy)</span>
                </div>
              </div>
            </div>

            {error && (
              <p className="text-xs mt-4 text-center" style={{ color: "#8b3a3a", letterSpacing: "0.02em" }}>
                {error}
              </p>
            )}

            <div className="flex gap-2 mt-6">
              <button
                onClick={() => setStep(2)}
                className="flex-1 py-3 text-xs border transition-all"
                style={{ borderColor: "#c8c0b4", color: "#0a0a0a", letterSpacing: "0.15em", ...FONT }}
              >
                BACK
              </button>
              <button
                onClick={handleComplete}
                disabled={loading}
                className="flex-1 py-3 text-xs disabled:opacity-30 transition-all"
                style={{ backgroundColor: "#0a0a0a", color: "#f5f0e8", letterSpacing: "0.15em", ...FONT }}
              >
                {loading ? "..." : "START"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      {(major || targetSchool) && (
        <div className="mt-4 text-xs text-center" style={{ letterSpacing: "0.08em", color: "#0a0a0a", opacity: 0.4 }}>
          {[major, targetSchool, transferYear].filter(Boolean).join(" · ")}
        </div>
      )}
    </div>
  );
}
