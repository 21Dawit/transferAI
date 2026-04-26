// Maps full DB school names to short display labels
export const SCHOOL_DISPLAY_NAMES: Record<string, string> = {
  "UC Davis":                                                      "UC Davis",
  "University of California, Berkeley":                            "UC Berkeley",
  "University of California, Los Angeles":                         "UCLA",
  "University of California, San Diego":                           "UC San Diego",
  "University of California, Santa Barbara":                       "UC Santa Barbara",
  "University of California, Irvine":                              "UC Irvine",
  "University of California, Santa Cruz":                          "UC Santa Cruz",
  "University of California, Riverside":                           "UC Riverside",
  "University of California, Merced":                              "UC Merced",
  "California Polytechnic State University, San Luis Obispo":      "Cal Poly SLO",
  "San Jose State University":                                     "San Jose State",
};

export function displaySchoolName(dbName: string): string {
  return SCHOOL_DISPLAY_NAMES[dbName] || dbName;
}
