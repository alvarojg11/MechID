
import streamlit as st
import pandas as pd
from collections import defaultdict

st.set_page_config(page_title="Resistance Mechanism Predictor", page_icon="🧪", layout="centered")

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("microbiology_cultures_cohort.csv")
        return df
    except Exception:
        try:
            df = pd.read_csv("/mnt/data/microbiology_cultures_cohort.csv")
            return df
        except Exception:
            return pd.DataFrame(columns=["organism", "antibiotic", "susceptibility"])

df = load_data()

st.title("🧪 Resistance Mechanism Predictor")
st.caption("Select an organism and record susceptibilities for the tested antibiotics. The app applies intrinsic/cascade rules and suggests likely resistance mechanisms.")

# Rules supplied by the user
USER_RULES = {
    "ACINETOBACTER": {
        "intrinsic_resistance": ["Aztreonam", "Cefazolin", "Minocycline", "Tetracycline"],
        "cascade": [
            {"target": "Doripenem", "rule": "same_as", "ref": "Meropenem"},
            {"target": "Ceftriaxone", "rule": "same_as", "ref": "Cefotaxime"},
            {"target": "Cefotaxime", "rule": "same_as", "ref": "Ceftriaxone"},
            {"target": "Ertapenem", "rule": "sus_if_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},  # treat as any_sus over 2 refs
            {"target": "Imipenem", "rule": "sus_if_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},
            {"target": "Meropenem", "rule": "sus_if_any_sus", "refs": ["Imipenem", "Ceftriaxone", "Cefotaxime"]},
        ],
    },
    "CITROBACTER": {
        "intrinsic_resistance": ["Ampicillin", "Cefazolin", "Cefotetan", "Cefoxitin"],
        "cascade": [
            {"target": "Cefepime", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},
            {"target": "Ceftazidime", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},
        ],
    },
    "Enterobacter": {
        "intrinsic_resistance": ["Ampicillin", "Cefazolin"],
        "cascade": [
            {"target": "Cefepime", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},
            {"target": "Ceftazidime", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},
            {"target": "Ceftriaxone", "rule": "same_as", "ref": "Cefotaxime"},
            {"target": "Cefotaxime", "rule": "same_as", "ref": "Ceftriaxone"},
            {"target": "Doxycycline", "rule": "sus_if_sus_else_res", "ref": "Tetracycline"},
            {"target": "Doripenem", "rule": "same_as", "ref": "Meropenem"},
            {"target": "Ertapenem", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},
            {"target": "Imipenem", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime"]},
            {"target": "Meropenem", "rule": "sus_if_any_sus", "refs": ["Imipenem", "Ceftriaxone", "Cefotaxime"]},
        ],
    },
    "ESCHERICHIA COLI": {
        "intrinsic_resistance": [],
        "cascade": [
            {"target": "Cefepime", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime", "Cefazolin"]},
            {"target": "Ceftazidime", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone", "Cefotaxime", "Cefazolin"]},
            {"target": "Ceftriaxone", "rule": "same_as", "ref": "Cefotaxime"},
            {"target": "Cefotetan", "rule": "sus_if_sus", "ref": "Cefazolin"},
            {"target": "Cefoxitin", "rule": "sus_if_sus", "ref": "Cefazolin"},
            {"target": "Cefpodoxime", "rule": "same_as_else_sus_if_sus", "primary": "Ceftriaxone", "fallback": "Cefazolin"},
            {"target": "Cefuroxime", "rule": "sus_if_sus", "ref": "Cefazolin"},
            {"target": "Doxycycline", "rule": "sus_if_sus_else_res", "ref": "Tetracycline"},
        ],
    },
    "KLEBSIELLA": {
        "intrinsic_resistance": ["Ampicillin"],
        "cascade": [],
    },
    "Proteus species": {
        "intrinsic_resistance": ["Tetracycline", "Tigecycline", "Colistin"],
        "cascade": [],
    },
    "Pseudomonas aeruginosa": {
        "intrinsic_resistance": ["Ampicillin", "Ceftriaxone", "Cefazolin", "Ertapenem", "Tetracycline", "Tigecycline"],
        "cascade": [],
    },
    "Serratia": {
        "intrinsic_resistance": ["Ampicillin", "Cefazolin", "Tetracycline"],
        "cascade": [],
    },
}

ENTEROBACTERALES = {"ESCHERICHIA COLI", "KLEBSIELLA", "Enterobacter", "CITROBACTER", "Serratia", "Proteus species"}
CARBAPENEMS = {"Imipenem", "Meropenem", "Ertapenem", "Doripenem"}
THIRD_GENS = {"Ceftriaxone", "Cefotaxime", "Ceftazidime", "Cefpodoxime"}

def normalize_org_name(name: str) -> str:
    if pd.isna(name):
        return name
    n = name.strip()
    if n.upper().startswith("ACINETOBACTER"):
        return "ACINETOBACTER"
    if n.upper().startswith("CITROBACTER"):
        return "CITROBACTER"
    if n.upper().startswith("ESCHERICHIA"):
        return "ESCHERICHIA COLI"
    if n.upper().startswith("KLEBSIELLA"):
        return "KLEBSIELLA"
    if n.upper().startswith("ENTEROBACTER"):
        return "Enterobacter"
    if n.upper().startswith("SERRATIA"):
        return "Serratia"
    if n.upper().startswith("PSEUDOMONAS"):
        return "Pseudomonas aeruginosa"
    if n.upper().startswith("PROTEUS"):
        return "Proteus species"
    return n

def apply_cascade_rules(org_rules, inputs):
    inferred = {}
    def get_status(ab):
        return inputs.get(ab, inferred.get(ab))
    for rule in org_rules.get("cascade", []):
        tgt = rule["target"]
        if get_status(tgt) is not None:
            continue
        kind = rule["rule"]
        if kind == "same_as":
            ref = rule["ref"]
            ref_val = get_status(ref)
            if ref_val is not None:
                inferred[tgt] = ref_val
        elif kind == "sus_if_sus":
            # supports 'ref' or 'refs'
            refs = rule.get("refs") or [rule.get("ref")]
            if any(get_status(r) == "Susceptible" for r in refs if r):
                inferred[tgt] = "Susceptible"
        elif kind == "sus_if_any_sus":
            refs = rule["refs"]
            if any(get_status(r) == "Susceptible" for r in refs):
                inferred[tgt] = "Susceptible"
        elif kind == "sus_if_sus_else_res":
            ref = rule["ref"]
            ref_val = get_status(ref)
            if ref_val == "Susceptible":
                inferred[tgt] = "Susceptible"
            elif ref_val is not None:
                inferred[tgt] = "Resistant"
        elif kind == "same_as_else_sus_if_sus":
            primary = rule["primary"]
            fallback = rule["fallback"]
            p_val = get_status(primary)
            if p_val is not None:
                inferred[tgt] = p_val
            else:
                f_val = get_status(fallback)
                if f_val == "Susceptible":
                    inferred[tgt] = "Susceptible"
    return inferred

def infer_mechanisms(organism, final_results):
    org_key = normalize_org_name(organism)
    mechs = []

    if org_key in ENTEROBACTERALES:
        carp_R = any(final_results.get(c) == "Resistant" for c in CARBAPENEMS if c in final_results)
        third_R = any(final_results.get(c) == "Resistant" for c in THIRD_GENS if c in final_results)
        cefoxitin_R = final_results.get("Cefoxitin") == "Resistant"
        cefotetan_R = final_results.get("Cefotetan") == "Resistant"

        if carp_R:
            mechs.append("Carbapenemase or carbapenem resistance (confirm with molecular/phenotypic testing).")
        if third_R and not carp_R and org_key not in {"CITROBACTER", "Enterobacter", "Serratia"}:
            mechs.append("ESBL (3rd-generation cephalosporin resistance pattern).")
        if org_key in {"CITROBACTER", "Enterobacter", "Serratia"} and (third_R or cefoxitin_R or cefotetan_R):
            mechs.append("AmpC (inducible/chromosomal β-lactamase).")

    if org_key == "Pseudomonas aeruginosa":
        if any(final_results.get(c) == "Resistant" for c in CARBAPENEMS if c in final_results):
            mechs.append("Carbapenem resistance (OprD loss ± AmpC upregulation or carbapenemase).")

    if org_key == "ACINETOBACTER":
        if any(final_results.get(c) == "Resistant" for c in CARBAPENEMS if c in final_results):
            mechs.append("Carbapenem resistance (OXA-type carbapenemase likely).")

    return mechs

# Build organism list from data + rules
org_from_data = sorted({normalize_org_name(o) for o in df["organism"].dropna().unique()}) if "organism" in df.columns else []
org_from_rules = sorted(USER_RULES.keys())
organisms = sorted(set(org_from_data) | set(org_from_rules))

organism = st.selectbox("Select organism", organisms)

org_key = normalize_org_name(organism)
org_rules = USER_RULES.get(org_key, {"intrinsic_resistance": [], "cascade": []})

# Antibiotics options from data and rules for the organism
ab_from_data = []
if not df.empty and "organism" in df.columns and "antibiotic" in df.columns:
    ab_from_data = sorted(df[df["organism"].apply(lambda x: normalize_org_name(x) == org_key)]["antibiotic"].dropna().unique())
ab_from_rules = sorted({r["target"] for r in org_rules.get("cascade", [])})
ab_options = sorted(set(ab_from_data) | set(ab_from_rules))

# Exclude intrinsic from input
intrinsic = org_rules.get("intrinsic_resistance", [])
ab_input_list = [ab for ab in ab_options if ab not in intrinsic]

st.subheader("Enter susceptibility results")
st.caption("Provide results only for antibiotics actually tested. Leave others blank.")

user_results = {}
choices = ["", "Susceptible", "Intermediate", "Resistant"]
for i, ab in enumerate(ab_input_list):
    user_choice = st.selectbox(f"{ab}", choices, index=0, key=f"ab_{org_key}_{i}")
    user_results[ab] = user_choice if user_choice != "" else None

# Intrinsic resistance shown separately
if intrinsic:
    st.info("**Intrinsic resistance (by rule):** " + ", ".join(intrinsic))

# Apply cascade rules
inferred = apply_cascade_rules(org_rules, user_results)

# Merge final results (user > inferred), then set intrinsic R
final_results = defaultdict(lambda: None)
for k, v in {**inferred, **user_results}.items():
    final_results[k] = v
for ab in intrinsic:
    final_results[ab] = "Resistant"

# Display consolidated table
st.subheader("Consolidated results")
rows = []
for ab in sorted(set(final_results.keys())):
    if final_results[ab] is None:
        continue
    source = "User-entered"
    if ab in intrinsic:
        source = "Intrinsic rule"
    elif ab in inferred and (ab not in user_results or user_results[ab] is None):
        source = "Cascade rule"
    rows.append({"Antibiotic": ab, "Result": final_results[ab], "Source": source})

if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
else:
    st.write("No results yet. Enter at least one susceptibility above.")

# Mechanism inference
st.subheader("Likely resistance mechanism(s)")
mechanisms = infer_mechanisms(org_key, final_results)

if mechanisms:
    for m in mechanisms:
        st.error(f"• {m}")
else:
    st.success("No major resistance mechanism identified based on current inputs.")

st.caption("Heuristic output; confirm with phenotypic/molecular tests per your lab policy.")
