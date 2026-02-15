import streamlit as st
import pandas as pd
from collections import defaultdict

# ======================
# Page setup
# ======================
st.set_page_config(
    page_title="MechID — Mechanism-Based Interpretation of Antibiograms",
    page_icon="🧫",
    layout="centered"
)
st.markdown("""
<h1 style='text-align:center; color:#1f6f4a; font-weight:800; margin-bottom:0.2rem;'>
MechID
</h1>
<h3 style='text-align:center; color:#2f8059; margin-top:0;'>
Mechanism-Based Interpretation of Antibiograms
</h3>
<p style='text-align:center; color:#3f5649; font-size:0.9rem;'>
From MIC cutoffs to likely resistance mechanisms and practical therapy notes.<br>
Heuristic output — always confirm with your microbiology lab, ID consult, and IDSA/CLSI guidance.
</p>
""", unsafe_allow_html=True)

st.markdown("""
<style>
    :root {
        --background: #e7f1ea;
        --foreground: #0f1a13;
        --card: #f7fbf8;
        --card2: #ffffff;
        --border: #cfe0d4;
        --muted: #3f5649;
        --primary: #1f6f4a;
    }

    .stApp {
        background: radial-gradient(1200px 800px at 20% 0%, #f1faf4 0%, var(--background) 55%);
        color: var(--foreground);
        font-family: Arial, Helvetica, sans-serif;
    }

    .stMarkdown, .stText, .stCaption, .stMetric, label, p, h1, h2, h3 {
        color: var(--foreground);
    }

    section[data-testid="stSidebar"] {
        background-color: var(--card);
        color: var(--foreground);
        border-right: 1px solid var(--border);
    }

    div[data-testid="stSelectbox"] > div,
    div[data-testid="stMultiSelect"] > div,
    div[data-testid="stTextInput"] > div > div,
    div[data-testid="stTextArea"] textarea {
        background: var(--card2);
        border: 1px solid var(--border);
        border-radius: 10px;
    }

    div[data-testid="stAlert"] {
        border: 1px solid var(--border);
        border-radius: 10px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border);
        border-radius: 10px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)


# ======================
# Fancy Divider and helpers
# ======================
def fancy_divider():
    st.markdown("""
    <hr style="
        border:0;
        height:2px;
        margin:1.5rem 0 1rem 0;
        background: linear-gradient(to right, #1f6f4a, #2f8059, #74b88f);
    ">
    """, unsafe_allow_html=True)

def badge(text, bg="#1f6f4a", fg="#ffffff"):
    html = f"""
    <span style="
        display:inline-block;
        padding:0.12rem 0.45rem;
        border-radius:999px;
        font-size:0.7rem;
        font-weight:600;
        letter-spacing:0.03em;
        background:{bg};
        color:{fg};
        margin-right:0.4rem;
        text-transform:uppercase;
    ">{text}</span>
    """
    return html


# ======================
# Reference mapping (auto-detected from mechanism text)
# ======================
MECH_REF_MAP = {
    "esbl": [
        "IDSA Guidance for ESBL-producing Enterobacterales (latest).",
        "Paterson DL, Bonomo RA. Extended-Spectrum β-Lactamases: a clinical update. Clin Microbiol Rev."
    ],
    "ampc": [
        "Harris PN et al. AmpC β-lactamases in Enterobacterales—clinical guidance.",
        "CLSI M100 (current edition): AmpC comments and reporting guidance."
    ],
    "cre": [
        "IDSA Guidance for CRE and carbapenemase testing (mCIM/eCIM, molecular).",
        "CLSI M100 (current edition): Carbapenemase detection and reporting."
    ],
    "porin_oprd": [
        "Livermore DM. Mechanisms of carbapenem resistance in Pseudomonas (OprD loss).",
        "Poole K. Pseudomonas aeruginosa: porins and intrinsic resistance."
    ],
    "pseudomonas_efflux": [
        "Poole K. Efflux-mediated resistance in Pseudomonas (MexAB-OprM, MexXY-OprM).",
        "CLSI M100 notes on anti-pseudomonal agent testing nuances."
    ],
    "aminoglycoside_mod": [
        "Ramirez MS, Tolmasky ME. Aminoglycoside modifying enzymes. Drug Resist Updates."
    ],
    "fq_qrdr": [
        "Hooper DC, Jacoby GA. Mechanisms of fluoroquinolone resistance (QRDR)."
    ],
    "tmpsmx_folate": [
        "Sköld O. Sulfonamide and trimethoprim resistance (dfrA, sul genes)."
    ],
    "staph_mrsa": [
        "IDSA MRSA guidelines (latest): mecA/mecC (PBP2a) and therapy.",
        "CLSI M100: Oxacillin/cefoxitin testing for Staphylococcus."
    ],
    "staph_dtest": [
        "CLSI M100: Inducible clindamycin resistance (D-test) for staphylococci."
    ],
    "vre": [
        "IDSA VRE guidance: VanA/VanB (D-Ala-D-Lac).",
        "CLSI M100: Enterococcus glycopeptide resistance reporting."
    ],
    "serr_sme": [
        "Queenan AM et al. SME carbapenemases in Serratia marcescens."
    ],
}

def _collect_mech_ref_keys(org: str, mechs: list, banners: list) -> list:
    """Map mechanism/banners text to reference keys and return a deduped list of refs."""
    keys = set()
    texts = " ".join((mechs or []) + (banners or [])).lower()

    if "esbl" in texts or "extended-spectrum" in texts:
        keys.add("esbl")
    if "ampc" in texts:
        keys.add("ampc")
    if "carbapenemase" in texts or "carbapenem-resistant" in texts or "cre" in texts:
        keys.add("cre")
    if org == "Pseudomonas aeruginosa" and ("oprd" in texts or "porin" in texts):
        keys.add("porin_oprd")
    if org == "Pseudomonas aeruginosa" and "efflux" in texts:
        keys.add("pseudomonas_efflux")
    if "aminoglycoside" in texts and ("enzyme" in texts or "modifying" in texts):
        keys.add("aminoglycoside_mod")
    if "fluoroquinolone" in texts or "qrdr" in texts or ("gyr" in texts and "par" in texts):
        keys.add("fq_qrdr")
    if "tmp-smx" in texts or "trimethoprim" in texts or "sulfamethoxazole" in texts or "dfr" in texts or "sul1" in texts or "sul2" in texts:
        keys.add("tmpsmx_folate")
    if "mrsa" in texts or "meca" in texts or "mecc" in texts or "pbp2a" in texts:
        keys.add("staph_mrsa")
    if "d-test" in texts or "d test" in texts or ("erythromycin" in texts and "clindamycin" in texts):
        keys.add("staph_dtest")
    if org.startswith("Enterococcus") and ("vancomycin" in texts and ("vana" in texts or "vanb" in texts or "vre" in texts)):
        keys.add("vre")
    if org == "Serratia marcescens" and ("sme" in texts or ("serratia" in texts and "carbapenemase" in texts)):
        keys.add("serr_sme")

    refs = []
    for k in keys:
        refs.extend(MECH_REF_MAP.get(k, []))
    out, seen = [], set()
    for r in refs:
        if r not in seen:
            out.append(r); seen.add(r)
    return out

# ======================
# Shared helpers
# ======================
def _collect_panel_inputs(panel, intrinsic_map, keyprefix):
    user = {}
    choices = ["", "Susceptible", "Intermediate", "Resistant"]
    for i, ab in enumerate(panel):
        if intrinsic_map.get(ab):
            _ = st.selectbox(
                f"{ab} (intrinsic)", choices, index=3,
                key=f"{keyprefix}_{i}", disabled=True,
                help="Intrinsic resistance by rule"
            )
            user[ab] = None
        else:
            val = st.selectbox(ab, choices, index=0, key=f"{keyprefix}_{i}")
            user[ab] = val if val else None
    final = defaultdict(lambda: None)
    for k, v in user.items():
        final[k] = v
    for ab, intrinsic in intrinsic_map.items():
        if intrinsic:
            final[ab] = "Resistant"
    return user, final

# ======================
# Gram-negative module (organism-specific)
# ======================

GNR_CANON = [
    "Achromobacter xylosoxidans",
    "Acinetobacter baumannii complex",
    "Citrobacter freundii complex",
    "Citrobacter koseri",
    "Enterobacter cloacae complex",
    "Escherichia coli",
    "Klebsiella aerogenes",
    "Klebsiella oxytoca",
    "Klebsiella pneumoniae",
    "Morganella morganii",
    "Proteus mirabilis",
    "Proteus vulgaris group",
    "Pseudomonas aeruginosa",
    "Salmonella enterica",
    "Serratia marcescens",
    "Stenotrophomonas maltophilia",
]

def normalize_org(name: str) -> str:
    if not isinstance(name, str):
        return name
    n = name.strip()
    ln = n.lower()
    if ln.startswith("achromobacter"):
        return "Achromobacter xylosoxidans"
    if ln.startswith("acinetobacter"):
        return "Acinetobacter baumannii complex"
    if ln.startswith("citrobacter freun") or "freundii" in ln:
        return "Citrobacter freundii complex"
    if ln.startswith("citrobacter kos"):
        return "Citrobacter koseri"
    if ln.startswith("enterobacter clo"):
        return "Enterobacter cloacae complex"
    if ln.startswith("escherichia") or ln.startswith("e. coli"):
        return "Escherichia coli"
    if ln.startswith("klebsiella aer"):
        return "Klebsiella aerogenes"
    if ln.startswith("klebsiella oxy"):
        return "Klebsiella oxytoca"
    if ln.startswith("klebsiella pneu"):
        return "Klebsiella pneumoniae"
    if ln.startswith("morganella"):
        return "Morganella morganii"
    if ln.startswith("proteus mira"):
        return "Proteus mirabilis"
    if ln.startswith("proteus vulg"):
        return "Proteus vulgaris group"
    if ln.startswith("ps.") or ln.startswith("pseudomonas"):
        return "Pseudomonas aeruginosa"
    if ln.startswith("salmonella"):
        return "Salmonella enterica"
    if ln.startswith("serratia"):
        return "Serratia marcescens"
    if ln.startswith("stenotrophomonas"):
        return "Stenotrophomonas maltophilia"
    return n

PANEL = {
    "Escherichia coli": [
        "Ampicillin","Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefazolin","Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Nitrofurantoin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Klebsiella pneumoniae": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefazolin","Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Nitrofurantoin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Klebsiella oxytoca": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefazolin","Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Nitrofurantoin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Klebsiella aerogenes": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Enterobacter cloacae complex": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Citrobacter freundii complex": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefoxitin","Cefotetan","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Citrobacter koseri": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefazolin","Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Nitrofurantoin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Serratia marcescens": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Salmonella enterica": [
        "Ceftriaxone","Ciprofloxacin","Trimethoprim/Sulfamethoxazole"
    ],
    "Proteus mirabilis": [
        "Ampicillin","Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefazolin","Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Proteus vulgaris group": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Morganella morganii": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Cefoxitin","Ceftriaxone","Ceftazidime","Cefepime","Aztreonam",
        "Imipenem","Meropenem","Ertapenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Acinetobacter baumannii complex": [
        "Ampicillin/Sulbactam","Piperacillin/Tazobactam",
        "Ceftriaxone","Cefepime","Aztreonam",
        "Imipenem","Meropenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Achromobacter xylosoxidans": [
        "Piperacillin/Tazobactam","Cefepime","Aztreonam",
        "Imipenem","Meropenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Pseudomonas aeruginosa": [
        "Piperacillin/Tazobactam","Cefepime","Ceftazidime","Aztreonam",
        "Imipenem","Meropenem",
        "Gentamicin","Tobramycin","Amikacin",
        "Ciprofloxacin","Levofloxacin",
    ],
    "Stenotrophomonas maltophilia": [
        "Trimethoprim/Sulfamethoxazole","Levofloxacin"
    ],
}

RULES = {
    "Escherichia coli": {
        "intrinsic_resistance": [],
        "cascade": [
            {"target": "Ceftriaxone", "rule": "same_as", "ref": "Cefotaxime"},
            {"target": "Cefepime", "rule": "sus_if_any_sus", "refs": ["Ceftriaxone","Cefotaxime","Cefazolin"]},
            {"target": "Cefuroxime", "rule": "sus_if_sus", "ref": "Cefazolin"},
            {"target": "Cefoxitin", "rule": "sus_if_sus", "ref": "Cefazolin"},
            {"target": "Cefotetan", "rule": "sus_if_sus", "ref": "Cefazolin"},
            {"target": "Cefpodoxime", "rule": "same_as_else_sus_if_sus", "primary":"Ceftriaxone", "fallback":"Cefazolin"},
            {"target": "Doxycycline", "rule": "sus_if_sus_else_res", "ref": "Tetracycline"},
        ],
    },
    "Klebsiella pneumoniae": {
        "intrinsic_resistance": ["Ampicillin"],
        "cascade": [],
    },
    "Klebsiella oxytoca": {
        "intrinsic_resistance": ["Ampicillin"],
        "cascade": [],
    },
    "Klebsiella aerogenes": {
        "intrinsic_resistance": ["Ampicillin","Cefazolin"],
        "cascade": [
            {"target":"Cefepime","rule":"sus_if_any_sus","refs":["Ceftriaxone"]},
        ],
    },
    "Enterobacter cloacae complex": {
        "intrinsic_resistance": ["Ampicillin","Cefazolin"],
        "cascade": [
            {"target":"Cefepime","rule":"sus_if_any_sus","refs":["Ceftriaxone"]},
        ],
    },
    "Citrobacter freundii complex": {
        "intrinsic_resistance": ["Ampicillin","Cefazolin","Cefoxitin","Cefotetan"],
        "cascade": [
            {"target":"Cefepime","rule":"sus_if_any_sus","refs":["Ceftriaxone","Cefotaxime"]},
            {"target":"Ceftazidime","rule":"sus_if_any_sus","refs":["Ceftriaxone","Cefotaxime"]},
        ],
    },
    "Citrobacter koseri": {
        "intrinsic_resistance": [],
        "cascade": [
            {"target":"Cefepime","rule":"sus_if_any_sus","refs":["Ceftriaxone","Cefotaxime","Cefazolin"]},
            {"target":"Ceftazidime","rule":"sus_if_any_sus","refs":["Ceftriaxone","Cefotaxime","Cefazolin"]},
        ],
    },
    "Serratia marcescens": {
        "intrinsic_resistance": ["Ampicillin","Cefazolin","Tetracycline"],
        "cascade": [],
    },
    "Proteus mirabilis": {
        "intrinsic_resistance": ["Nitrofurantoin"],
        "cascade": [],
    },
    "Proteus vulgaris group": {
        "intrinsic_resistance": ["Nitrofurantoin","Tetracycline","Tigecycline","Colistin"],
        "cascade": [],
    },
    "Morganella morganii": {
        "intrinsic_resistance": ["Nitrofurantoin"],
        "cascade": [],
    },
    "Acinetobacter baumannii complex": {
        "intrinsic_resistance": ["Aztreonam","Cefazolin","Minocycline","Tetracycline"],
        "cascade": [
            {"target":"Doripenem","rule":"same_as","ref":"Meropenem"},
            {"target":"Ceftriaxone","rule":"same_as","ref":"Cefotaxime"},
            {"target":"Cefotaxime","rule":"same_as","ref":"Ceftriaxone"},
            {"target":"Ertapenem","rule":"sus_if_any_sus","refs":["Ceftriaxone","Cefotaxime"]},
            {"target":"Imipenem","rule":"sus_if_any_sus","refs":["Ceftriaxone","Cefotaxime"]},
            {"target":"Meropenem","rule":"sus_if_any_sus","refs":["Imipenem","Ceftriaxone","Cefotaxime"]},
        ],
    },
    "Achromobacter xylosoxidans": {
        "intrinsic_resistance": [],
        "cascade": [],
    },
    "Pseudomonas aeruginosa": {
        "intrinsic_resistance": ["Ampicillin","Cefazolin","Ceftriaxone","Ertapenem","Tetracycline","Tigecycline"],
        "cascade": [],
    },
    "Salmonella enterica": {
        "intrinsic_resistance": [],
        "cascade": [],
    },
    "Stenotrophomonas maltophilia": {
        "intrinsic_resistance": [],
        "cascade": [],
    },
}

ENTEROBACTERALES = {
    "Escherichia coli","Klebsiella pneumoniae","Klebsiella oxytoca","Klebsiella aerogenes",
    "Enterobacter cloacae complex","Citrobacter freundii complex","Citrobacter koseri",
    "Serratia marcescens","Proteus mirabilis","Proteus vulgaris group","Morganella morganii","Salmonella enterica"
}
CARBAPENEMS = {"Imipenem","Meropenem","Ertapenem","Doripenem"}
THIRD_GENS = {"Ceftriaxone","Cefotaxime","Ceftazidime","Cefpodoxime"}

# ======================
# Cascade
# ======================
def apply_cascade(org_rules, inputs):
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
            val = get_status(ref)
            if val is not None:
                inferred[tgt] = val
        elif kind == "sus_if_sus":
            ref = rule["ref"]
            if get_status(ref) == "Susceptible":
                inferred[tgt] = "Susceptible"
        elif kind == "sus_if_any_sus":
            refs = rule["refs"]
            if any(get_status(r) == "Susceptible" for r in refs):
                inferred[tgt] = "Susceptible"
        elif kind == "sus_if_sus_else_res":
            ref = rule["ref"]
            val = get_status(ref)
            if val == "Susceptible":
                inferred[tgt] = "Susceptible"
            elif val is not None:
                inferred[tgt] = "Resistant"
        elif kind == "same_as_else_sus_if_sus":
            primary = rule["primary"]; fallback = rule["fallback"]
            pv = get_status(primary)
            if pv is not None:
                inferred[tgt] = pv
            else:
                fv = get_status(fallback)
                if fv == "Susceptible":
                    inferred[tgt] = "Susceptible"
    return inferred

# ======================
# References (rendered at bottom of the app)
# ======================
REFERENCES = [
    "IDSA Guidance for Gram-negative Bacteria (latest applicable version).",
    "CLSI M100 Performance Standards for Antimicrobial Susceptibility Testing.",
    "Harris PN et al. AmpC β-lactamases—clinical implications.",
    "Livermore DM. Mechanisms of resistance in Pseudomonas aeruginosa.",
    "EUCAST/IDSA guidance documents on ESBL/CRE.",
]

# ======================
# Small shared helpers
# ======================
CARBAPENEMS = {"Imipenem","Meropenem","Doripenem"}
THIRD_GENS  = {"Ceftriaxone","Cefotaxime","Ceftazidime","Cefpodoxime"}

def _get(R, ab): return R.get(ab)
def _any_R(R, names): return any(_get(R,n) == "Resistant" for n in names if n in R)
def _any_S(R, names): return any(_get(R,n) == "Susceptible" for n in names if n in R)

def _dedup_list(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            out.append(x); seen.add(x)
    return out

# ----------------------
# Reusable organism subsets
# ----------------------
ENTEROBACTERALES = {
    "Escherichia coli","Klebsiella pneumoniae","Klebsiella oxytoca","Klebsiella aerogenes",
    "Enterobacter cloacae complex","Citrobacter freundii complex","Citrobacter koseri",
    "Serratia marcescens","Proteus mirabilis","Proteus vulgaris group","Morganella morganii","Salmonella enterica"
}
CLIN_AMPC = {"Klebsiella aerogenes","Citrobacter freundii complex","Enterobacter cloacae complex"}

# ======================
# Per-organism MECHANISMS
# ======================

def mech_ecoli(R):
    mechs, banners, greens = [], [], []
    carp_R = _any_R(R, CARBAPENEMS)
    third_R = _any_R(R, THIRD_GENS)
    cefepime_R = _get(R, "Cefepime") == "Resistant"
    ctx_S = _get(R, "Ceftriaxone") == "Susceptible"
    cefazolin_R = _get(R, "Cefazolin") == "Resistant"
    caz = _get(R, "Ceftazidime")
    amp_R = (_get(R, "Ampicillin") == "Resistant")

    if carp_R:
        mechs.append("Carbapenem resistance (screen for carbapenemase; confirm by phenotypic/molecular tests).")
    elif third_R:
        mechs.append("ESBL pattern (3rd-generation cephalosporin resistance).")

    # Cefazolin R + CTX S with Amp R → TEM/SHV pattern (not ESBL)
    if not carp_R and cefazolin_R and ctx_S and amp_R and (caz not in {"Resistant", "Intermediate"}):
        banners.append("β-lactam pattern **Amp R + Cefazolin R + Ceftriaxone S** → **broad-spectrum β-lactamase (TEM-1/SHV)**, not ESBL.")

    # Uncommon: Cefepime R with CTX S
    if not carp_R and cefepime_R and ctx_S:
        mechs.append("Uncommon: **Cefepime R** with **Ceftriaxone S** — consider ESBL variant/porin–efflux/testing factors.")

    # Ertapenem R with IMP/MEM S
    if _get(R, "Ertapenem") == "Resistant" and (_get(R, "Imipenem") == "Susceptible" or _get(R, "Meropenem") == "Susceptible"):
        banners.append("**Ertapenem R** with **Imipenem/Meropenem S** → often ESBL or AmpC + porin loss.")

    # ---- Fluoroquinolones ----
    cip = _get(R, "Ciprofloxacin")
    lev = _get(R, "Levofloxacin")

    # Generic FQ resistance mechanism when either FQ is R
    if cip == "Resistant" or lev == "Resistant":
        mechs.append(
            "Fluoroquinolone resistance: typically **QRDR mutations** in **gyrA/parC** ± **efflux upregulation** "
            "(AcrAB–TolC / OqxAB) and sometimes **plasmid-mediated qnr / AAC(6')-Ib-cr**."
        )

    # Special discordance — Ciprofloxacin R / Levofloxacin S
    if cip == "Resistant" and lev == "Susceptible":
        mechs.append(
            "Fluoroquinolone discordance: **Ciprofloxacin R** with **Levofloxacin S** — suggests **low-level, non–target-mediated resistance** "
            "such as **PMQR** (e.g., **qnr** target protection or **AAC(6')-Ib-cr** acetylation) and/or **efflux upregulation (AcrAB–TolC / OqxAB)** "
            "± porin changes. These mechanisms can **step up to high-level FQ resistance during therapy**."
        )
        banners.append(
            "Caution using **levofloxacin** despite apparent susceptibility — PMQR/efflux phenotypes carry a **higher risk of on-therapy failure** "
            "via stepwise QRDR mutations."
        )

    # TMP-SMX resistance mechanism
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Resistant":
        mechs.append(
            "TMP-SMX resistance: **dfrA** (trimethoprim-resistant DHFR), **sul1/sul2** (sulfonamide-resistant DHPS), "
            "often on **class 1 integrons**; efflux and target mutation can contribute."
        )

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_ecoli(R):
    out = []

    # FQ R but BL S → use BL
    if _any_S(R, ["Piperacillin/Tazobactam", "Ceftriaxone", "Cefepime", "Aztreonam",
                  "Imipenem", "Meropenem", "Ertapenem"]) and \
       _any_R(R, ["Ciprofloxacin", "Levofloxacin", "Moxifloxacin"]):
        out.append("**Fluoroquinolone R but β-lactam S** → prefer a **β-lactam** that is susceptible.")

    # ESBL
    if _any_R(R, THIRD_GENS) and not _any_R(R, CARBAPENEMS):
        out.append("**ESBL pattern** → use a **carbapenem** for serious infections.")

    # Ertapenem R / others S
    if _get(R, "Ertapenem") == "Resistant" and (_get(R, "Imipenem") == "Susceptible" or _get(R, "Meropenem") == "Susceptible"):
        out.append("**Ertapenem R / IMI or MEM S** → consider **extended-infusion meropenem**.")

    # CRE signal
    if _get(R, "Meropenem") == "Resistant" and _get(R, "Ertapenem") == "Resistant":
        out.append("**CRE phenotype** → isolate should be tested for **carbapenemase**.\n")

    # TEM/SHV broad BL pattern
    if (_get(R, "Cefazolin") == "Resistant") and (_get(R, "Ceftriaxone") == "Susceptible") and \
       (_get(R, "Ampicillin") in {"Resistant", "Intermediate"}) and (_get(R, "Ceftazidime") not in {"Resistant", "Intermediate"}):
        out.append("**TEM-1/SHV pattern** → **Ceftriaxone is preferred** when susceptible; Piperacillin/Tazobactam often active; amoxicillin clavulanate may also be considered for non-severe *E. coli*.")

    # Special FQ discordance message (CIP R / LEV S)
    cip = _get(R, "Ciprofloxacin")
    lev = _get(R, "Levofloxacin")
    if cip == "Resistant" and lev == "Susceptible":
        out.append(
            "**Ciprofloxacin R / Levofloxacin S** → if an FQ is considered, **levofloxacin** may be used based on susceptibility, "
            "but **failure risk is higher** with **PMQR/efflux** phenotypes. Prefer a confirmed-active **β-lactam** (or other class) "
            "for **severe/invasive** infections; reserve levofloxacin for **low-risk sites** with close follow-up."
        )

    # Generic: avoid FQs when all tested FQs are R
    if _any_R(R, ["Ciprofloxacin", "Levofloxacin", "Moxifloxacin"]) and \
       not _any_S(R, ["Ciprofloxacin", "Levofloxacin", "Moxifloxacin"]):
        out.append(
            "**All tested fluoroquinolones are resistant** → avoid FQs; choose a non-FQ agent that is susceptible."
        )

    # TMP-SMX susceptible → oral step-down option
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Susceptible":
        out.append(
            "**TMP-SMX susceptible** → reasonable **oral step-down** option in selected scenarios "
            "(e.g., **uncomplicated cystitis/pyelonephritis** once clinically improved, source control achieved, and GI absorption assured). "
            "Avoid as sole therapy in **severe sepsis or uncontrolled bacteremia**."
        )

    return _dedup_list(out)

def mech_serratia(R):
    mechs, banners, greens = [], [], []

    # Core drugs
    imi  = _get(R, "Imipenem")
    mero = _get(R, "Meropenem")
    ept  = _get(R, "Ertapenem")
    ctx  = _get(R, "Ceftriaxone")
    fep  = _get(R, "Cefepime")
    caz  = _get(R, "Ceftazidime")
    cefox = _get(R, "Cefoxitin")

    carp_R  = _any_R(R, ["Imipenem","Meropenem","Ertapenem"])
    third_R = _any_R(R, THIRD_GENS)  # ceftriaxone/cefotaxime/ceftazidime/cefpodoxime
    ctx_S   = (ctx == "Susceptible")
    fep_S   = (fep == "Susceptible")
    caz_S   = (caz == "Susceptible")

    # ---- Serratia baseline teaching point ----
    mechs.append(
        "*Serratia marcescens* has an **inducible chromosomal AmpC β-lactamase**, "
        "so it is typically **resistant to ampicillin and 1st-generation cephalosporins**."
    )
    # If cefoxitin is tested, use it as an AmpC signal comment (not all labs report it)
    if cefox in {"Intermediate","Resistant"}:
        banners.append(
            "**Cefoxitin non-susceptible** supports an **AmpC** signal (common in *Serratia*). "
            "Interpret 3rd-gen cephalosporins carefully in serious infections."
        )

    # ---- ESBL pattern (not the main baseline issue for Serratia, but can happen) ----
    if third_R and not carp_R:
        mechs.append("3rd-generation cephalosporin resistance pattern — consider **ESBL** and/or **AmpC derepression**; confirm per lab policy.")

    # ---- Carbapenem resistance: include SME/chromosomal possibility + preserved cephalosporins ----
    if carp_R:
        mechs.append(
            "Carbapenem resistance in *Serratia*: evaluate for **carbapenemase**. "
            "This can be due to **chromosomal SME-type carbapenemase**, or acquired enzymes (e.g., **KPC**) depending on epidemiology."
        )

        # Key phenotype you asked for: carbapenem R but some cephalosporins still S
        if ctx_S or fep_S or caz_S:
            banners.append(
                "Carbapenem R with **some cephalosporins still susceptible** can occur in *Serratia* "
                "(e.g., **SME-type chromosomal carbapenemase** phenotypes). "
                "**Do not assume all cephalosporins are inactive** — treat according to **specific reported susceptibilities** and confirm mechanism."
            )

    # ---- “Ceftriaxone acceptable when susceptible” (low induction risk teaching point you used before) ----
    if (not carp_R) and ctx_S:
        greens.append(
            "If **ceftriaxone is susceptible**, it can be used for *S. marcescens* in many scenarios; "
            "*Serratia* is often considered **lower risk for clinically significant AmpC induction** than classic AmpC inducers "
            "(still use clinical judgment for severe/high-inoculum infections)."
        )

    # ---- Ertapenem R with IMI/MEM S pattern (less common in Serratia than Enterobacterales generally, but keep if you like) ----
    if ept == "Resistant" and (imi == "Susceptible" or mero == "Susceptible"):
        banners.append(
            "**Ertapenem R** with **Imipenem/Meropenem S** → can reflect **β-lactamase + permeability changes**; "
            "confirm and select therapy by **tested carbapenem MICs/site**."
        )

    # ---- Fluoroquinolones ----
    cip = _get(R, "Ciprofloxacin")
    lev = _get(R, "Levofloxacin")

    if cip == "Resistant" or lev == "Resistant":
        mechs.append(
            "Fluoroquinolone resistance: typically **QRDR mutations** (gyrA/parC) ± **efflux upregulation**; "
            "sometimes **plasmid-mediated qnr / AAC(6')-Ib-cr**."
        )

    if cip == "Resistant" and lev == "Susceptible":
        mechs.append(
            "FQ discordance (**Ciprofloxacin R / Levofloxacin S**) suggests **low-level non-target mechanisms** "
            "(e.g., **PMQR** such as **qnr** or **AAC(6')-Ib-cr**) and/or **efflux**. "
            "These can **step up during therapy** with additional QRDR mutations."
        )
        banners.append(
            "Use **levofloxacin** cautiously despite S — higher risk of **on-therapy failure** with PMQR/efflux phenotypes, "
            "especially for invasive disease."
        )

    # ---- TMP-SMX ----
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Resistant":
        mechs.append(
            "TMP-SMX resistance: **dfrA** (DHFR) and/or **sul1/sul2** (DHPS), often on **class 1 integrons**."
        )
    elif tmpsmx == "Susceptible":
        greens.append("TMP-SMX is **susceptible** — may be an oral option depending on site/severity.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_serratia(R):
    out = []

    # Pull key results
    imi  = _get(R, "Imipenem")
    mero = _get(R, "Meropenem")
    ept  = _get(R, "Ertapenem")
    ctx  = _get(R, "Ceftriaxone")
    fep  = _get(R, "Cefepime")
    caz  = _get(R, "Ceftazidime")

    cip = _get(R, "Ciprofloxacin")
    lev = _get(R, "Levofloxacin")
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")

    carp_R  = any(x == "Resistant" for x in [imi, mero, ept] if x is not None)
    any_ceph_S = any(x == "Susceptible" for x in [ctx, fep, caz] if x is not None)

    # Prefer β-lactam when FQ resistant and BL susceptible
    if _any_S(R, ["Ceftriaxone","Cefepime","Ceftazidime","Piperacillin/Tazobactam","Aztreonam","Imipenem","Meropenem","Ertapenem"]) and \
       _any_R(R, ["Ciprofloxacin","Levofloxacin","Moxifloxacin"]):
        out.append("**Fluoroquinolone R but β-lactam S** → prefer a **β-lactam** that is susceptible.")

    # ESBL / 3rd-gen resistance without carbapenem resistance
    if _any_R(R, THIRD_GENS) and not carp_R:
        out.append("3rd-gen cephalosporin resistance → for serious infections, choose a **reliably active agent** (often **cefepime** if susceptible/MIC appropriate or a **carbapenem** depending on local guidance).")

    # Carbapenem resistance but cephalosporins still susceptible (SME-like phenotype)
    if carp_R and any_ceph_S:
        choices = []
        if ctx == "Susceptible": choices.append("**ceftriaxone**")
        if fep == "Susceptible": choices.append("**cefepime**")
        if caz == "Susceptible": choices.append("**ceftazidime**")
        out.append(
            "**Carbapenem R with cephalosporin S** can occur in *Serratia* (e.g., **SME-type chromosomal carbapenemase** phenotypes). "
            f"Use a susceptible cephalosporin: {', '.join(choices)} (dose by site/MIC/severity) and confirm mechanism with lab/ID."
        )
    elif carp_R:
        out.append("**Carbapenem resistance present** → prioritize confirmed actives; request **carbapenemase workup** and involve **ID** for invasive disease.")

    # Ertapenem R / IMI or MEM S
    if ept == "Resistant" and (imi == "Susceptible" or mero == "Susceptible"):
        out.append("**Ertapenem R / IMI or MEM S** → select based on **tested MICs**; consider **optimized meropenem dosing** when appropriate.")

    # FQ discordance: CIP R / LEV S
    if cip == "Resistant" and lev == "Susceptible":
        out.append(
            "**Ciprofloxacin R / Levofloxacin S** → levofloxacin *may* be used for selected **low-risk** scenarios if no better oral options, "
            "but **failure risk is higher** (PMQR/efflux). Prefer a confirmed-active **β-lactam** for **severe/invasive** infections."
        )

    # TMP-SMX oral step-down
    if tmpsmx == "Susceptible":
        out.append(
            "**TMP-SMX susceptible** → possible **oral step-down** in selected cases once improving and source controlled "
            "(site/severity dependent; avoid as sole therapy for uncontrolled bacteremia/severe sepsis)."
        )

    return _dedup_list(out)

def mech_k_aerogenes(R):
    """
    Klebsiella aerogenes (formerly Enterobacter aerogenes)
    - Chromosomal AmpC: inducible/derepressible → avoid 3rd-gen cephalosporins/P-T for serious infections
    - Can acquire ESBL + porin loss → ertapenem-R with MEM/IMI-S
    - Can be CRE/carbapenemase (KPC/NDM/etc) but also non-carbapenemase mechanisms
    """
    mechs, banners, greens = [], [], []

    # Core markers
    carp_R   = _any_R(R, CARBAPENEMS)
    third_R  = _any_R(R, THIRD_GENS)

    fep      = _get(R, "Cefepime")
    ctx      = _get(R, "Ceftriaxone")
    caz      = _get(R, "Ceftazidime")
    cefox    = _get(R, "Cefoxitin")
    cefotet  = _get(R, "Cefotetan")

    ept      = _get(R, "Ertapenem")
    imi      = _get(R, "Imipenem")
    mero     = _get(R, "Meropenem")

    cip      = _get(R, "Ciprofloxacin")
    lev      = _get(R, "Levofloxacin")
    tmpsmx   = _get(R, "Trimethoprim/Sulfamethoxazole")

    # ----------------------------
    # AmpC baseline (organism-specific, always relevant)
    # ----------------------------
    # (Don’t label as "detected" unless you want; it's intrinsic biology.)
    mechs.append(
        "Intrinsic **chromosomal AmpC β-lactamase** (inducible/derepressible) — risk of on-therapy resistance with "
        "**3rd-gen cephalosporins** and sometimes **piperacillin–tazobactam** in serious infections."
    )

    # Phenotypic AmpC signals (supportive)
    if cefox in {"Intermediate", "Resistant"} or cefotet == "Resistant":
        banners.append("**Cefoxitin/Cefotetan non-susceptible** supports **AmpC** expression/derepression phenotype.")

    # ----------------------------
    # Carbapenems / CRE patterns
    # ----------------------------
    if carp_R:
        mechs.append(
            "Carbapenem resistance present — evaluate for **carbapenemase (KPC/NDM/VIM/IMP/OXA-48-like)** vs "
            "**AmpC/ESBL + porin loss**; confirm with phenotypic/molecular testing."
        )

    # “Ertapenem R / IMI or MEM S” often porin loss + AmpC/ESBL (non-carbapenemase CRE mechanism)
    if ept == "Resistant" and (imi == "Susceptible" or mero == "Susceptible"):
        banners.append(
            "**Ertapenem R** with **Imipenem/Meropenem S** → commonly **AmpC/ESBL + porin loss** (non-carbapenemase) phenotype."
        )

    # ----------------------------
    # ESBL overlay (possible, but AmpC organism complicates interpretation)
    # ----------------------------
    # If 3rd-gens are R (or CAZ R) and no carbapenem-R, call out ESBL possibility *in addition* to AmpC.
    if (third_R or caz == "Resistant") and not carp_R:
        mechs.append(
            "β-lactam pattern with **3rd-gen cephalosporin resistance** could reflect **AmpC derepression** and/or **acquired ESBL**; "
            "confirm per lab policy (ESBL testing may be less informative in AmpC organisms)."
        )

    # Helpful “cefepime status” interpretation
    if fep == "Susceptible":
        greens.append("Cefepime susceptible — often remains active despite AmpC; still consider site/severity and MIC if available.")
    elif fep in {"Intermediate", "Resistant"} and not carp_R:
        banners.append("Cefepime non-susceptible in an AmpC organism suggests high-level AmpC ± additional mechanisms (e.g., porin/efflux).")
    elif fep in {"Intermediate", "Resistant"} and carp_R:
        banners.append("Cefepime non-susceptible with carbapenem resistance raises concern for **carbapenemase** or **multi-mechanism resistance**.")

    # ----------------------------
    # Fluoroquinolones (including discordance)
    # ----------------------------
    if cip == "Resistant" or lev == "Resistant":
        mechs.append(
            "Fluoroquinolone resistance: typically **QRDR mutations** (gyrA/parC ± parE/gyrB) ± **efflux upregulation**, "
            "and sometimes **plasmid-mediated qnr / AAC(6')-Ib-cr**."
        )

    if cip == "Resistant" and lev == "Susceptible":
        mechs.append(
            "Fluoroquinolone discordance (**Ciprofloxacin R / Levofloxacin S**) suggests **low-level non–target-mediated resistance** "
            "(e.g., **PMQR** such as **qnr** or **AAC(6')-Ib-cr**) and/or **efflux**. These can **evolve to high-level resistance on therapy**."
        )
        banners.append(
            "Caution: **Levofloxacin** may test susceptible but has **higher risk of failure/on-therapy resistance** with PMQR/efflux phenotypes."
        )

    # ----------------------------
    # TMP-SMX
    # ----------------------------
    if tmpsmx == "Resistant":
        mechs.append(
            "TMP-SMX resistance: **dfrA** (trimethoprim-resistant DHFR) and/or **sul1/sul2** (sulfonamide-resistant DHPS), "
            "often carried on **class 1 integrons**."
        )

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)

def tx_k_aerogenes(R):
    out = []
    fep    = _get(R,"Cefepime")
    cip    = _get(R,"Ciprofloxacin")
    lev    = _get(R,"Levofloxacin")
    tmpsmx = _get(R,"Trimethoprim/Sulfamethoxazole")

    # ---- CRE signal ----
    if _get(R,"Meropenem") == "Resistant" and _get(R,"Ertapenem") == "Resistant":
        out.append("**CRE phenotype** → request **carbapenemase workup**; involve **ID**.")

    # ---- Baseline AmpC guidance (always present) ----
    if fep == "Susceptible":
        out.append("**AmpC inducer** → **Cefepime (MIC ≤4) preferred**; avoid 3rd-gens/P-T for serious infections.")
    elif fep in {"Intermediate","Resistant"}:
        out.append("AmpC with cefepime not S → **Carbapenem** preferred for serious infections.")

    # ---- Fluoroquinolones ----

    # If β-lactams are S but FQs are R → don’t chase the FQ
    if _any_S(R, ["Cefepime","Piperacillin/Tazobactam","Imipenem","Meropenem"]) and \
       _any_R(R, ["Ciprofloxacin","Levofloxacin"]):
        out.append("**Fluoroquinolone R but β-lactam S** → prefer a **β-lactam** that is susceptible (avoid FQs).")

    # Special discordance: CIP R / LEV S
    if cip == "Resistant" and lev == "Susceptible":
        out.append(
            "**Ciprofloxacin R / Levofloxacin S** → if an FQ is considered, **levofloxacin** may be used based on susceptibility, "
            "but **failure risk is higher** with **PMQR/efflux** phenotypes. Prefer a confirmed-active **β-lactam** "
            "for **severe/invasive** infections; reserve levofloxacin for **low-risk sites** with close follow-up."
        )

    # If all tested FQs are R → explicitly tell them to avoid FQs
    if _any_R(R, ["Ciprofloxacin","Levofloxacin"]) and \
       not _any_S(R, ["Ciprofloxacin","Levofloxacin"]):
        out.append("**All tested fluoroquinolones are resistant** → avoid FQs; use a non-FQ agent that is susceptible.")

    # ---- TMP-SMX: oral step-down ----
    if tmpsmx == "Susceptible":
        out.append(
            "**TMP-SMX susceptible** → reasonable **oral step-down** option for selected cases "
            "(e.g., **uncomplicated UTI** or low-risk bloodstream infections once clinically improved, source controlled, and GI absorption assured). "
            "Avoid as sole therapy in **severe sepsis or uncontrolled bacteremia**."
        )

    return _dedup_list(out)


def mech_ecloacae(R):  # Enterobacter cloacae complex
    return mech_k_aerogenes(R)

def tx_ecloacae(R):
    return tx_k_aerogenes(R)

def mech_cfreundii(R):
    # Same clinical AmpC playbook (plus cefotetan intrinsic often)
    return mech_k_aerogenes(R)

def tx_cfreundii(R):
    return tx_k_aerogenes(R)

def mech_pseudomonas(R):
    mechs, banners, greens = [], [], []

    # β-lactams / carbapenems
    piptazo = _get(R,"Piperacillin/Tazobactam")
    fep     = _get(R,"Cefepime")
    caz     = _get(R,"Ceftazidime")
    imi     = _get(R,"Imipenem")
    mero    = _get(R,"Meropenem")
    aztre   = _get(R,"Aztreonam")

    # Fluoroquinolones
    cipro   = _get(R,"Ciprofloxacin")
    levo    = _get(R,"Levofloxacin")

    # Aminoglycosides
    genta   = _get(R,"Gentamicin")
    tobra   = _get(R,"Tobramycin")
    amik    = _get(R,"Amikacin")

    carb_R = any(x == "Resistant" for x in [imi, mero] if x is not None)
    bl_R   = any(x == "Resistant" for x in [piptazo, fep, caz, aztre] if x is not None)
    bl_S   = any(x == "Susceptible" for x in [piptazo, fep, caz, aztre] if x is not None)

    fq_R   = any(x == "Resistant" for x in [cipro, levo] if x is not None)
    ag_R   = any(x == "Resistant" for x in [genta, tobra, amik] if x is not None)
    ag_S   = any(x == "Susceptible" for x in [genta, tobra, amik] if x is not None)

    # ----------------------------
    # Core β-lactam/carbapenem patterns
    # ----------------------------
    if carb_R:
        mechs.append("Carbapenem resistance: **carbapenemase (VIM/IMP/NDM/OXA)** vs **OprD loss ± AmpC/efflux**; confirm.")
    if bl_R and not carb_R:
        mechs.append("Broad β-lactam R without carbapenem R → **AmpC overproduction ± efflux**.")
    if carb_R and bl_S:
        mechs.append("Carbapenem R with other β-lactams S → **OprD porin loss** (non-carbapenemase) likely.")

    # Specific β-lactam banners
    if piptazo == "Resistant":
        banners.append("**Piperacillin/Tazobactam R** → consider **AmpC derepression** and/or **efflux**.")
    if fep == "Resistant":
        banners.append("**Cefepime R** → consider **MexXY-OprM efflux** and/or **AmpC**.")
    if caz == "Resistant":
        banners.append("**Ceftazidime R** → consider **AmpC**, **ESBLs (VEB/PER/GES/TEM/SHV)**, and/or **efflux**.")

    # ----------------------------
    # Fluoroquinolones (mechanisms)
    # ----------------------------
    if fq_R:
        mechs.append(
            "Fluoroquinolone resistance: usually **QRDR mutations** (gyrA/parC ± parE) and/or **efflux (Mex systems)**; "
            "plasmid-mediated mechanisms are less common than in Enterobacterales."
        )

    # Key discordance teaching point
    if (cipro == "Resistant") and (levo == "Susceptible"):
        banners.append(
            "**FQ discordance: Ciprofloxacin R / Levofloxacin S** → most consistent with **efflux/stepwise resistance**. "
            "Even if levo tests susceptible, there is a **high risk of on-therapy resistance and clinical failure**, especially in invasive infections."
        )

    # ----------------------------
    # Aminoglycosides (mechanisms)
    # ----------------------------
    if ag_R:
        # Common pattern: gent/tobra R, amik S
        if (genta == "Resistant" or tobra == "Resistant") and (amik == "Susceptible"):
            mechs.append(
                "Aminoglycoside resistance pattern (**Gent/Tobra R, Amik S**) → consistent with **aminoglycoside-modifying enzymes (AMEs)**; "
                "**amikacin** may retain activity."
            )
        else:
            mechs.append(
                "Aminoglycoside resistance: **AMEs** and/or **efflux**; less commonly **16S rRNA methylases** (broad high-level resistance)."
            )

    # If all AG are resistant, add a stronger banner
    if (genta in {"Resistant","Intermediate"} and tobra in {"Resistant","Intermediate"} and amik in {"Resistant","Intermediate"}):
        banners.append("**All aminoglycosides non-susceptible** → consistent with multiple AMEs/efflux or rarely **16S rRNA methylase**; avoid AG reliance.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_pseudomonas(R):
    out = []

    piptazo = _get(R,"Piperacillin/Tazobactam")
    fep     = _get(R,"Cefepime")
    caz     = _get(R,"Ceftazidime")
    imi     = _get(R,"Imipenem")
    mero    = _get(R,"Meropenem")
    aztre   = _get(R,"Aztreonam")

    cipro   = _get(R,"Ciprofloxacin")
    levo    = _get(R,"Levofloxacin")

    genta   = _get(R,"Gentamicin")
    tobra   = _get(R,"Tobramycin")
    amik    = _get(R,"Amikacin")

    carb_R = any(x == "Resistant" for x in [imi, mero] if x is not None)
    any_bl_S = any(x == "Susceptible" for x in [piptazo, fep, caz, aztre] if x is not None)

    fq_any_R = any(x == "Resistant" for x in [cipro, levo] if x is not None)
    fq_any_S = any(x == "Susceptible" for x in [cipro, levo] if x is not None)

    ag_any_S = any(x == "Susceptible" for x in [genta, tobra, amik] if x is not None)
    ag_any_R = any(x == "Resistant" for x in [genta, tobra, amik] if x is not None)

    # ----------------------------
    # If FQ R but β-lactam S → prefer β-lactam
    # ----------------------------
    if any_bl_S and fq_any_R:
        out.append("**Fluoroquinolone R but β-lactam S** → prefer a **susceptible anti-pseudomonal β-lactam** (avoid relying on FQs).")

    # ----------------------------
    # Special OprD pattern: carbapenem R but other β-lactams S
    # ----------------------------
    if carb_R and any_bl_S:
        choices = []
        if fep == "Susceptible":
            choices.append("**cefepime**")
        if piptazo == "Susceptible":
            choices.append("**piperacillin–tazobactam**")
        if caz == "Susceptible":
            choices.append("**ceftazidime**")
        if aztre == "Susceptible":
            choices.append("**aztreonam**")

        if choices:
            out.append(
                "**Carbapenem R with other β-lactams S** → pattern consistent with **OprD porin loss (non-carbapenemase)**. "
                f"Use a susceptible β-lactam: {', '.join(choices)} (site/MIC/severity dependent)."
            )
    else:
        # Carbapenem-R path only when no other β-lactam is susceptible
        if carb_R and not any_bl_S:
            out.append(
                "**Carbapenem R present** → prioritize confirmed actives; consider **ceftolozane–tazobactam** or "
                "**ceftazidime–avibactam** if tested susceptible; consider ID input for severe infections."
            )
        else:
            # No carbapenem R → phenotype-based suggestions
            if fep == "Susceptible" and piptazo == "Resistant":
                out.append("**Cefepime S / P-T R** → choose **cefepime** (phenotype compatible with **AmpC derepression**).")
            if fep == "Resistant" and piptazo == "Susceptible":
                out.append("**Cefepime R / P-T S** → choose **piperacillin–tazobactam** (compatible with **MexXY-OprM efflux**).")

    # ----------------------------
    # Ceftazidime refinement
    # ----------------------------
    if caz == "Resistant":
        if fep == "Susceptible":
            out.append("**CAZ R / FEP S** → prefer **cefepime** (AmpC-compatible pattern).")
        elif piptazo == "Susceptible":
            out.append("**CAZ R / P-T S** → prefer **piperacillin–tazobactam**; confirm susceptibility.")
        elif (fep == "Resistant") and (piptazo == "Resistant"):
            out.append("**CAZ, FEP, and P-T all R** → consider **ceftolozane–tazobactam** if tested susceptible; evaluate combinations for severe infections.")
        else:
            out.append("**Ceftazidime R** → choose among confirmed susceptible β-lactams; consider novel agents if none.")

    # ----------------------------
    # Fluoroquinolone discordance therapy note (Cipro R / Levo S)
    # ----------------------------
    if (cipro == "Resistant") and (levo == "Susceptible"):
        out.append(
            "**Cipro R / Levo S** → **levofloxacin may appear usable**, but discordance suggests **efflux/stepwise resistance** with **high failure risk**, "
            "especially for bacteremia, pneumonia, CNS, or deep-seated infection. If used at all, reserve for **limited/low-inoculum situations** and "
            "ensure close clinical monitoring."
        )

    # ----------------------------
    # Aminoglycosides therapy notes
    # ----------------------------
    if ag_any_S:
        # Prefer amikacin if it’s the only S agent
        if (amik == "Susceptible") and (genta in {None,"Resistant","Intermediate"}) and (tobra in {None,"Resistant","Intermediate"}):
            out.append("**Aminoglycosides**: **amikacin susceptible** while gent/tobra not S → **amikacin** may be the best AG option (often as adjunct depending on site).")
        else:
            out.append("**Aminoglycosides**: if one is susceptible, it can be considered (often **adjunctive** in severe infections depending on site/toxicity).")

    if ag_any_R and not ag_any_S:
        out.append("**Aminoglycosides non-susceptible** → avoid relying on AG therapy; consider alternative active classes/novel agents when available.")

    return _dedup_list(out)


def mech_achromobacter(R):
    # Start with the pseudomonas-style β-lactam/efflux heuristics
    mechs, banners, greens = mech_pseudomonas(R)

    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Resistant":
        mechs.append(
            "TMP-SMX resistance: usually **folate-pathway target changes** (e.g., **dfrA** for trimethoprim, **sul1/sul2** for sulfonamides) "
            "and/or **efflux**."
        )
    elif tmpsmx == "Susceptible":
        greens.append("TMP-SMX is **susceptible** — often a key active option for **Achromobacter** (site/severity dependent).")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_achromobacter(R):
    out = tx_pseudomonas(R)

    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Susceptible":
        out.append(
            "**TMP-SMX susceptible** → consider **TMP-SMX** as a primary option (including **oral step-down** when clinically appropriate: "
            "source controlled, stable patient, adequate absorption, and a non–high-inoculum site)."
        )
    elif tmpsmx == "Resistant":
        out.append(
            "**TMP-SMX resistant** → do **not** rely on TMP-SMX; select among other confirmed susceptible agents."
        )

    return _dedup_list(out)


def mech_acinetobacter(R):
    mechs, banners, greens = [], [], []

    # Helpful pulls
    imi  = _get(R, "Imipenem")
    mero = _get(R, "Meropenem")
    sulb = _get(R, "Ampicillin/Sulbactam")
    pipt = _get(R, "Piperacillin/Tazobactam")
    fep  = _get(R, "Cefepime")
    ctx  = _get(R, "Ceftriaxone")
    ctz  = _get(R, "Ceftazidime")

    cip  = _get(R, "Ciprofloxacin")
    lev  = _get(R, "Levofloxacin")

    genta = _get(R, "Gentamicin")
    tobra = _get(R, "Tobramycin")
    amik  = _get(R, "Amikacin")

    col  = _get(R, "Colistin")      # only if you include it in your panel
    polyB = _get(R, "Polymyxin B")  # optional

    carb_R = _any_R(R, ["Imipenem", "Meropenem"])
    bl_any_R = _any_R(R, ["Ampicillin/Sulbactam","Piperacillin/Tazobactam","Cefepime","Ceftriaxone","Ceftazidime"])
    bl_any_S = _any_S(R, ["Ampicillin/Sulbactam","Piperacillin/Tazobactam","Cefepime","Ceftriaxone","Ceftazidime"])

    # Clinical context reminder (from your excerpt)
    banners.append(
        "Acinetobacter frequently **colonizes** and forms **biofilm** on mucosa and devices; interpret cultures in clinical context (infection vs colonization)."
    )

    # ---- Carbapenems / carbapenemases
    if carb_R:
        mechs.append(
            "Carbapenem resistance: most often **OXA-type (class D) carbapenemase** in *A. baumannii*; "
            "**MBLs (IMP/VIM/NDM)** are less common but important to consider (confirm phenotypic/molecularly)."
        )

    # ---- Broad cephalosporin/penicillin resistance (AmpC/ESBL/efflux/porin)
    # Acinetobacter commonly has chromosomal AmpC and can overexpress it (e.g., via IS elements).
    # We keep this as a general mechanism line when there is broad BL resistance.
    if bl_any_R:
        mechs.append(
            "β-lactam resistance is often driven by **β-lactamases** (including **AmpC** and sometimes **ESBLs**) "
            "plus **efflux** and **outer-membrane/porin (OMP) permeability** changes."
        )

    # Efflux emphasis if multi-class phenotype (BL + FQ and/or AG resistance)
    fq_R = _any_R(R, ["Ciprofloxacin","Levofloxacin"])
    ag_R = _any_R(R, ["Gentamicin","Tobramycin","Amikacin"])
    if bl_any_R and (fq_R or ag_R):
        mechs.append(
            "Multidrug phenotype suggests contribution from **RND efflux pumps (e.g., AdeABC)** in addition to enzyme-mediated resistance."
        )

    # Porin/OMP emphasis if carbapenem-R but some other BL remain S (permeability + enzyme interplay)
    if carb_R and bl_any_S:
        banners.append(
            "Carbapenem R with some other β-lactams S can reflect **permeability/OMP (porin) changes** plus variable β-lactamase expression."
        )

    # ---- Sulbactam (intrinsic anti-Acinetobacter activity via PBPs)
    # If sulbactam-containing agent is resistant, call out plausible mechanism.
    if sulb == "Resistant":
        mechs.append(
            "Sulbactam resistance: sulbactam has intrinsic activity via **PBP binding**; resistance may involve **PBP alterations** "
            "plus **β-lactamase overexpression**."
        )
    elif sulb == "Susceptible":
        greens.append("Sulbactam-containing therapy tests **susceptible** — may be a key option (site/severity dependent).")

    # ---- Aminoglycosides
    if ag_R:
        mechs.append(
            "Aminoglycoside resistance: typically **aminoglycoside-modifying enzymes (AMEs)** (often on **integrons**) "
            "and sometimes **efflux**."
        )
        # Optional, gentle nuance
        if amik == "Susceptible" and (genta == "Resistant" or tobra == "Resistant"):
            banners.append("Aminoglycoside pattern: **amikacin may retain activity** despite gent/tobra resistance (agent-specific).")

    # ---- Fluoroquinolones
    if fq_R:
        mechs.append(
            "Fluoroquinolone resistance: **QRDR mutations** (DNA gyrase/topoisomerase IV) often combined with **AdeABC efflux**."
        )

    # ---- Polymyxins (if you test/report them)
    if (col == "Resistant") or (polyB == "Resistant"):
        mechs.append(
            "Polymyxin resistance: often due to **two-component regulatory mutations (e.g., PmrA/PmrB)** and/or "
            "**LPS alterations/loss**, reducing drug binding."
        )

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_acinetobacter(R):
    out = []

    imi  = _get(R, "Imipenem")
    mero = _get(R, "Meropenem")
    sulb = _get(R, "Ampicillin/Sulbactam")

    cip  = _get(R, "Ciprofloxacin")
    lev  = _get(R, "Levofloxacin")

    genta = _get(R, "Gentamicin")
    tobra = _get(R, "Tobramycin")
    amik  = _get(R, "Amikacin")

    col  = _get(R, "Colistin")
    polyB = _get(R, "Polymyxin B")

    carb_R = _any_R(R, ["Imipenem","Meropenem"])
    fq_R   = _any_R(R, ["Ciprofloxacin","Levofloxacin"])
    ag_R   = _any_R(R, ["Gentamicin","Tobramycin","Amikacin"])

    # Big picture clinical reminder
    out.append("Before treating: confirm this represents **infection vs colonization**, especially with respiratory cultures and device-associated isolates.")

    # Carbapenem resistance
    if carb_R:
        out.append(
            "**Carbapenem-resistant *A. baumannii*** → choose therapy based on **confirmed susceptibilities** and local guidance; "
            "consider consultation with **ID** and use institutionally available active agents/combination strategies when needed."
        )
    else:
        out.append(
            "**Carbapenem susceptible** → select among susceptible β-lactams per site/severity; avoid unnecessary broadening."
        )

    # Sulbactam note (intrinsic activity)
    if sulb == "Susceptible":
        out.append(
            "**Ampicillin/sulbactam susceptible** → sulbactam has intrinsic anti-Acinetobacter activity (PBP binding); "
            "may be a useful option depending on site/severity."
        )
    elif sulb == "Resistant":
        out.append("**Ampicillin/sulbactam resistant** → avoid relying on sulbactam as an active agent unless other testing supports it.")

    # FQ + AG stewardship guidance
    if fq_R:
        out.append("**Fluoroquinolone resistant** → avoid FQs unless a specific agent is tested susceptible and clinically appropriate.")
    if ag_R:
        if amik == "Susceptible" and (genta == "Resistant" or tobra == "Resistant"):
            out.append("Aminoglycosides: **amikacin susceptible** while gent/tobra resistant → amikacin may be the preferred AG (agent-specific).")
        else:
            out.append("Aminoglycoside resistance present → avoid AGs unless a specific agent tests susceptible and is appropriate for site.")

    # Polymyxins (if present)
    if (col == "Resistant") or (polyB == "Resistant"):
        out.append("**Polymyxin resistant** → do not use colistin/polymyxin B; prioritize other confirmed actives and involve ID.")
    elif (col == "Susceptible") or (polyB == "Susceptible"):
        out.append("Polymyxin susceptible (if reported) → consider only when needed and with careful toxicity monitoring per local protocols.")

    return _dedup_list(out)


def mech_steno(R):
    mechs, banners, greens = [], [], []

    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    lev    = _get(R, "Levofloxacin")
    moxi   = _get(R, "Moxifloxacin")   # optional in panel
    mina   = _get(R, "Minocycline")    # optional in panel
    gent   = _get(R, "Gentamicin")     # optional in panel
    tobra  = _get(R, "Tobramycin")     # optional in panel
    amik   = _get(R, "Amikacin")       # optional in panel

    # Baseline biology: inherent resistance is common (teaching point)
    banners.append(
        "*S. maltophilia* has **intrinsic resistance** to many antibiotics (notably many **β-lactams** and **aminoglycosides**) "
        "due to multiple mechanisms including **efflux pumps**, β-lactamases, and reduced outer-membrane permeability."
    )

    # TMP-SMX
    if tmpsmx == "Resistant":
        mechs.append(
            "TMP-SMX resistance: often via **sul1** (and related folate-pathway resistance determinants) carried on "
            "**class 1 integrons**; resistance has increased globally."
        )
    elif tmpsmx == "Susceptible":
        greens.append("TMP-SMX is **susceptible** — historically the mainstay with strong in-vitro activity against *S. maltophilia*.")

    # Fluoroquinolones
    if (lev == "Resistant") or (moxi == "Resistant"):
        mechs.append(
            "Fluoroquinolone resistance: commonly due to **efflux pump overexpression** (e.g., **SmeDEF** and other RND pumps; **MfsA**), "
            "sometimes via regulatory mutations (e.g., derepression of SmeDEF)."
        )
    # Susceptible FQ but still caution for emergence
    if (lev == "Susceptible") or (moxi == "Susceptible"):
        banners.append(
            "Even when a fluoroquinolone tests **susceptible**, **on-therapy resistance can emerge** during monotherapy; "
            "risk may be higher in deep-seated/systemic infections."
        )

    # Aminoglycosides (if your panel includes them; many labs don’t report because intrinsically resistant)
    if _any_R(R, ["Gentamicin","Tobramycin","Amikacin"]):
        mechs.append(
            "Aminoglycoside resistance: frequently **intrinsic** and can also involve **aminoglycoside-modifying enzymes** plus reduced permeability."
        )
    # If they appear susceptible, warn to interpret carefully
    if any(x == "Susceptible" for x in [gent, tobra, amik] if x is not None):
        banners.append(
            "If aminoglycosides are reported **susceptible**, interpret cautiously and follow lab/CLSI reporting practices (intrinsic resistance is common)."
        )

    # Minocycline note (optional)
    if mina == "Susceptible":
        greens.append("Minocycline is **susceptible** — can be an alternative option depending on site/severity.")
    elif mina == "Resistant":
        mechs.append("Tetracycline/minocycline resistance can be mediated by **efflux** and other determinants (often co-traveling with MDR phenotypes).")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_steno(R):
    out = []
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    lev    = _get(R, "Levofloxacin")
    moxi   = _get(R, "Moxifloxacin")   # optional
    mina   = _get(R, "Minocycline")    # optional
    # cefiderocol optional: add to panel if you want
    cfd    = _get(R, "Cefiderocol")    # optional

    # Core recommendations
    if tmpsmx == "Susceptible":
        out.append("**Preferred**: **TMP-SMX** when susceptible (often used as backbone).")
    elif lev == "Susceptible":
        out.append("**Alternative**: **Levofloxacin** when susceptible (avoid assuming class effect).")
    elif moxi == "Susceptible":
        out.append("**Alternative**: **Moxifloxacin** when susceptible (watch for rapid resistance on monotherapy).")
    elif mina == "Susceptible":
        out.append("**Alternative**: **Minocycline** when susceptible (site/severity dependent).")
    elif cfd == "Susceptible":
        out.append("**Option**: **Cefiderocol** when tested susceptible (use per local availability/guidance).")
    else:
        out.append("No preferred oral option identified from current inputs — choose among confirmed actives and involve **ID** for severe disease.")

    # When to think combination therapy (from your text)
    out.append(
        "Consider **combination therapy** (often TMP-SMX-based when susceptible) for higher-risk scenarios: "
        "**endovascular infection**, **CNS infection**, **bone/joint infection**, **severe neutropenia/immune defect**, "
        "or **multifocal lung disease** (align with local/ID team guidance)."
    )

    # Warn about FQ monotherapy resistance emergence
    if (lev == "Susceptible") or (moxi == "Susceptible"):
        out.append(
            "If using a **fluoroquinolone**, note that **resistance can develop during monotherapy**; consider combination approaches in severe/systemic infections."
        )

    return _dedup_list(out)


def mech_efaecalis(R):
    mechs, banners, greens = [], [], []

    pen = _get(R, "Penicillin")
    amp = _get(R, "Ampicillin")

    # β-lactams (E. faecalis)
    if pen == "Resistant":
        mechs.append(
            "Penicillin resistance in *E. faecalis*: most often due to **altered PBPs** (reduced β-lactam affinity); "
            "**β-lactamase production is rare** but can occur."
        )
    if amp == "Resistant":
        mechs.append(
            "Ampicillin resistance in *E. faecalis*: usually **PBP alterations** (reduced affinity); "
            "rarely **β-lactamase**. Consider confirming with local lab methods if unexpected."
        )

    # Glycopeptides / oxazolidinones / lipopeptides
    if _get(R, "Vancomycin") == "Resistant":
        mechs.append("Vancomycin resistance (**VanA/VanB**; **D-Ala–D-Lac** target modification).")
    if _get(R, "Linezolid") == "Resistant":
        mechs.append("Linezolid resistance: **23S rRNA** mutations and/or **optrA/poxtA**.")
    if _get(R, "Daptomycin") == "Resistant":
        mechs.append("Daptomycin resistance: membrane adaptation/regulatory mutations (**liaFSR/yvqGH**).")

    # HLAR (synergy loss)
    if _get(R, "High-level Gentamicin") == "Resistant" or _get(R, "High-level Streptomycin") == "Resistant":
        banners.append("**HLAR**: synergy with cell-wall agents is lost.")

    # Greens
    if amp == "Susceptible":
        greens.append("Preferred: **Ampicillin** for *E. faecalis* when susceptible.")
    if _get(R, "Nitrofurantoin") == "Susceptible":
        greens.append("Cystitis: **Nitrofurantoin** is appropriate when susceptible.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_efaecalis(R):
    out = []

    pen = _get(R, "Penicillin")
    amp = _get(R, "Ampicillin")
    vanc = _get(R, "Vancomycin")

    # First-line β-lactam therapy
    if amp == "Susceptible":
        out.append(
            "**Ampicillin** preferred when susceptible (site-dependent). "
            "For **endocarditis**, consider **Ampicillin + Ceftriaxone** for synergy when aminoglycoside synergy is not feasible/to reduce nephrotoxicity."
        )
    elif amp in {"Intermediate", "Resistant"}:
        # Practical guidance when ampicillin not usable
        if vanc == "Susceptible":
            out.append(
                "**Ampicillin not susceptible** → use **Vancomycin** when susceptible (adjust to site/severity); involve ID for invasive disease."
            )

    # If penicillin is resistant but ampicillin is susceptible, steer to ampicillin
    if pen == "Resistant" and amp == "Susceptible":
        out.append("**Penicillin R / Ampicillin S** → treat with **ampicillin** (preferred) rather than penicillin.")

    # VRE
    if vanc == "Resistant":
        out.append("**VRE**: **Linezolid** or **Daptomycin** (dose by site/severity).")

    # HLAR synergy note
    if _get(R, "High-level Gentamicin") == "Resistant" or _get(R, "High-level Streptomycin") == "Resistant":
        out.append("**HLAR present** → β-lactam/vancomycin + aminoglycoside synergy is lost; avoid relying on gent/strept synergy regimens.")

    # Cystitis option
    if _get(R, "Nitrofurantoin") == "Susceptible":
        out.append("For cystitis: **Nitrofurantoin** is appropriate.")

    return _dedup_list(out)


def mech_efaecium(R):
    mechs, banners, greens = [], [], []
    if _get(R,"Vancomycin") == "Resistant":
        mechs.append("Vancomycin resistance (VanA/VanB).")
    if _get(R,"Nitrofurantoin") == "Susceptible":
        greens.append("Cystitis: **Nitrofurantoin** is appropriate when susceptible.")
    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)

def tx_efaecium(R):
    out = []
    if _get(R,"Vancomycin") == "Resistant":
        out.append("**VRE (faecium)**: **Linezolid** or **Daptomycin** (dose by site/severity).")
    else:
        out.append("Many *E. faecium* are ampicillin-resistant; glycopeptide or oxazolidinone/lipopeptide often required per site/severity.")
    return _dedup_list(out)

def mech_spneumo(R):
    mechs, banners, greens = [], [], []

    pen = _get(R, "Penicillin")
    ctx = _get(R, "Ceftriaxone")
    lvo = _get(R, "Levofloxacin")
    vanc = _get(R, "Vancomycin")
    ery, cli = _get(R, "Erythromycin"), _get(R, "Clindamycin")

    # ----------------------------
    # β-lactams: Pneumococcus = PBP alterations (not β-lactamase)
    # ----------------------------
    # For S. pneumoniae, penicillin/cephalosporin non-susceptibility is classically via mosaic PBPs (pbp1a/pbp2x/pbp2b),
    # sometimes with increased MICs for both penicillin and 3rd-gen cephs.
    if pen in {"Intermediate", "Resistant"}:
        mechs.append(
            "β-lactam non-susceptibility via **altered PBPs** (mosaic **pbp2x/pbp2b/pbp1a**; not β-lactamase). "
            "Higher MICs can reduce activity of penicillin and some cephalosporins."
        )

    if ctx in {"Intermediate", "Resistant"}:
        mechs.append(
            "**Ceftriaxone non-susceptibility** usually reflects additional/greater **PBP (pbp2x ± pbp1a)** alterations. "
            "This is most clinically relevant for **meningitis**, where higher exposures are required."
        )
        banners.append(
            "If invasive disease (especially **meningitis**), interpret penicillin/ceftriaxone using **site-specific breakpoints** "
            "and ensure **high-dose** regimens where appropriate."
        )

    # Helpful teaching point: discordant penicillin vs ceftriaxone can happen because of breakpoint differences/site
    if (pen in {"Intermediate", "Resistant"}) and (ctx == "Susceptible"):
        banners.append(
            "Penicillin non-susceptible but ceftriaxone susceptible can occur (breakpoints/site). "
            "Ceftriaxone often remains effective for **non-meningitis** when reported susceptible."
        )

    # ----------------------------
    # Macrolide / lincosamide patterns
    # ----------------------------
    if ery == "Resistant" and cli == "Resistant":
        mechs.append("Macrolide/Lincosamide resistance: **erm(B)** (MLS_B, often high-level).")
    elif ery == "Resistant" and cli == "Susceptible":
        mechs.append("Macrolide resistance consistent with **mef(A/E)** efflux (clindamycin often remains susceptible).")
        banners.append(
            "Erythromycin R with clindamycin S → supports **mef(A/E)** efflux or inducible mechanisms; "
            "macrolides should be avoided; clindamycin may still be active if tested susceptible."
        )

    # ----------------------------
    # Fluoroquinolones
    # ----------------------------
    if lvo in {"Intermediate", "Resistant"}:
        mechs.append("Fluoroquinolone resistance: **QRDR mutations** (gyrA/parC) ± efflux; can emerge on therapy.")

    # ----------------------------
    # Green: preferred when fully susceptible
    # ----------------------------
    if pen == "Susceptible":
        greens.append(
            "**Penicillin** is preferred when susceptible (dose by site: meningitis vs non-meningitis). "
            "**Ceftriaxone** is an alternative when susceptible."
        )

    # Vancomycin (mechanism not usually inferred from susceptibility alone, but include if non-susceptibility ever appears)
    if vanc in {"Intermediate", "Resistant"}:
        mechs.append("Vancomycin non-susceptibility is rare; consider confirmatory testing and ID consultation.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_spneumo(R):
    out = []

    pen = _get(R, "Penicillin")
    ctx = _get(R, "Ceftriaxone")
    lvo = _get(R, "Levofloxacin")
    ery = _get(R, "Erythromycin")
    vanc = _get(R, "Vancomycin")

    # ----------------------------
    # Core β-lactam guidance (site matters)
    # ----------------------------
    if pen == "Susceptible":
        out.append("**Penicillin** (or **Ceftriaxone**) when susceptible; dose per site (meningitis vs non-meningitis).")

    # Penicillin non-susceptible but ceftriaxone susceptible (common for non-meningitis)
    if pen in {"Intermediate", "Resistant"} and ctx == "Susceptible":
        out.append(
            "**Penicillin non-susceptible / Ceftriaxone susceptible** → **ceftriaxone** (or **high-dose amoxicillin/penicillin** where appropriate) "
            "may still be effective for **non-meningitis** infections; ensure site-appropriate dosing."
        )

    # Ceftriaxone non-susceptible: escalation (esp meningitis)
    if ctx in {"Intermediate", "Resistant"}:
        out.append(
            "**Ceftriaxone non-susceptible** → avoid ceftriaxone monotherapy for invasive disease. "
            "For **suspected/confirmed meningitis**, use **vancomycin + a high-dose 3rd-gen cephalosporin** initially; "
            "if cephalosporin resistance is present, continue **vancomycin** and consider adding **rifampin** per institutional guidance."
        )

    # If both penicillin and ceftriaxone not susceptible, highlight meningitis-style approach
    if (pen in {"Intermediate", "Resistant"}) and (ctx in {"Intermediate", "Resistant"}):
        out.append(
            "**Penicillin and Ceftriaxone non-susceptible** → pattern consistent with significant PBP alteration. "
            "For severe/invasive disease (especially CNS), prioritize **vancomycin-based** therapy guided by MICs and ID input."
        )

    # Vancomycin role (mostly relevant in meningitis or severe disease; susceptibility usually reported S)
    if vanc == "Susceptible":
        # Don't always spam; only add if CTX non-susceptible (above) or user wants meningitis framing.
        pass
    elif vanc in {"Intermediate", "Resistant"}:
        out.append("Vancomycin non-susceptible is very uncommon → confirm MIC and involve **ID** urgently.")

    # ----------------------------
    # Macrolides & FQs
    # ----------------------------
    if ery == "Resistant":
        out.append("Avoid macrolides when **Erythromycin R** unless a specific macrolide is tested susceptible.")
    if lvo == "Resistant":
        out.append("Avoid fluoroquinolones unless the **specific agent** is susceptible.")

    return _dedup_list(out)


def mech_bhs(R):
    """
    β-hemolytic streptococci (GAS/GBS): penicillin remains reliably active;
    resistance issues are mainly macrolides/clindamycin (erm/mef) and D-test.
    """
    mechs, banners, greens = [], [], []

    pen = _get(R, "Penicillin")
    ery = _get(R, "Erythromycin")
    cli = _get(R, "Clindamycin")
    lvo = _get(R, "Levofloxacin")

    # Penicillin: true resistance is extraordinarily rare in GAS/GBS
    if pen in {"Intermediate", "Resistant"}:
        banners.append(
            "**Penicillin non-susceptible reported** in β-hemolytic streptococci is **very unusual** → "
            "confirm identification and MIC; consider repeat testing / lab review."
        )
    elif pen == "Susceptible":
        greens.append("**Penicillin** remains first-line when susceptible (GAS/GBS).")

    # Macrolide / clindamycin mechanisms
    if ery == "Resistant" and cli == "Resistant":
        mechs.append("Macrolide/Lincosamide resistance: likely **erm**-mediated **MLS_B** (constitutive).")
    elif ery == "Resistant" and cli == "Susceptible":
        mechs.append("Macrolide resistance consistent with **mef(A/E)** efflux or **inducible erm**.")
        banners.append("**Erythromycin R / Clindamycin S** → perform **D-test** to assess inducible MLS_B; avoid clindamycin if D-test positive.")
    elif ery == "Susceptible" and cli == "Resistant":
        banners.append(
            "Clindamycin R with erythromycin S is uncommon; consider repeat testing / lab confirmation "
            "(can reflect other resistance determinants)."
        )

    # Fluoroquinolones (not typical first-line; add mechanism if resistant)
    if lvo in {"Intermediate", "Resistant"}:
        mechs.append("Fluoroquinolone non-susceptibility: **QRDR mutations** (gyrA/parC) ± efflux.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_bhs(R):
    out = []

    pen = _get(R, "Penicillin")
    ery = _get(R, "Erythromycin")
    cli = _get(R, "Clindamycin")

    # First-line
    if pen == "Susceptible" or pen is None:
        out.append("**Penicillin** (or **amoxicillin**) is first-line for GAS/GBS when susceptible; **cefazolin/ceftriaxone** are alternatives when appropriate.")
    else:
        out.append("Penicillin non-susceptibility is rare → **confirm**; treat with a susceptible β-lactam while results are clarified.")

    # Toxin suppression / clindamycin caution
    if ery == "Resistant" and cli == "Susceptible":
        out.append("If considering clindamycin (e.g., toxin suppression in severe GAS), obtain **D-test**; only use clindamycin if D-test negative.")
    elif cli == "Resistant":
        out.append("If clindamycin is needed for GAS toxin suppression but is **not susceptible**, use alternatives per local guidance (often alongside β-lactam backbone).")

    # Avoid macrolides when R
    if ery == "Resistant":
        out.append("Avoid macrolides when **Erythromycin R** unless a specific macrolide is tested susceptible.")

    return _dedup_list(out)


def mech_vgs(R):
    """
    Viridans group streptococci: β-lactam non-susceptibility is via altered PBPs;
    ceftriaxone often remains active even when penicillin is intermediate.
    Endocarditis breakpoints/dosing matter (high inoculum).
    """
    mechs, banners, greens = [], [], []

    pen = _get(R, "Penicillin")
    ctx = _get(R, "Ceftriaxone")
    vanc = _get(R, "Vancomycin")
    ery = _get(R, "Erythromycin")
    cli = _get(R, "Clindamycin")
    lvo = _get(R, "Levofloxacin")

    # β-lactams
    if pen in {"Intermediate", "Resistant"}:
        mechs.append("β-lactam non-susceptibility via **altered PBPs** (reduced affinity).")
        banners.append(
            "For **endocarditis/invasive** VGS disease, ensure **site-specific breakpoints** and use **high-dose** regimens when indicated "
            "(higher inoculum can worsen outcomes with marginal β-lactam activity)."
        )

    if ctx in {"Intermediate", "Resistant"}:
        mechs.append("**Ceftriaxone non-susceptibility** reflects more extensive **PBP** changes; may limit standard ceftriaxone regimens.")
        banners.append("Ceftriaxone non-susceptibility → avoid ceftriaxone monotherapy for invasive disease; select alternative susceptible agent(s).")

    # Greens (preferred agents)
    if pen == "Susceptible":
        greens.append("**Penicillin G** is preferred when susceptible; tailor dosing to site/severity (e.g., endocarditis).")
    elif ctx == "Susceptible":
        greens.append("**Ceftriaxone** is appropriate when susceptible, especially for invasive disease/endocarditis (dose by regimen).")

    # Macrolide / lincosamide
    if ery == "Resistant" and cli == "Resistant":
        mechs.append("Macrolide/Lincosamide resistance: likely **erm**-mediated **MLS_B** (constitutive).")
    elif ery == "Resistant" and cli == "Susceptible":
        mechs.append("Macrolide resistance consistent with **mef(A/E)** efflux or inducible **erm**.")
        banners.append("**Erythromycin R / Clindamycin S** → consider **D-test** where applicable; avoid clindamycin if inducible MLS_B is present.")

    # Fluoroquinolones
    if lvo in {"Intermediate", "Resistant"}:
        mechs.append("Fluoroquinolone non-susceptibility: **QRDR mutations** (gyrA/parC) ± efflux.")

    # Vancomycin (usually reserved for allergy/non-susceptibility)
    if vanc in {"Intermediate", "Resistant"}:
        banners.append("Vancomycin non-susceptibility is uncommon in VGS; confirm MIC and involve ID for invasive disease.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_vgs(R):
    out = []

    pen = _get(R, "Penicillin")
    ctx = _get(R, "Ceftriaxone")
    vanc = _get(R, "Vancomycin")
    ery = _get(R, "Erythromycin")
    cli = _get(R, "Clindamycin")
    lvo = _get(R, "Levofloxacin")

    # β-lactam backbone selection
    if pen == "Susceptible":
        out.append("**Penicillin G** (or **ceftriaxone**) preferred when susceptible; tailor regimen to site (e.g., endocarditis dosing/duration).")
    elif ctx == "Susceptible":
        out.append("**Ceftriaxone** appropriate when susceptible, particularly for invasive disease/endocarditis (use regimen-appropriate dosing).")
    elif (pen in {"Intermediate", "Resistant"}) and (ctx in {"Intermediate", "Resistant"}):
        out.append(
            "**Penicillin and Ceftriaxone non-susceptible** → choose an alternative susceptible agent; "
            "**vancomycin** is commonly used when β-lactams cannot be used or are not reliably active (site/severity dependent)."
        )

    # Vancomycin as fallback (allergy or β-lactam non-susceptibility)
    if vanc == "Susceptible" and pen in {"Intermediate", "Resistant"} and (ctx not in {"Susceptible"}):
        out.append("β-lactam non-susceptibility (and/or allergy) → **Vancomycin** is reasonable (site/severity dependent).")

    # Macrolides/clinda are not typical for invasive VGS, but keep safety notes
    if ery == "Resistant":
        out.append("Avoid macrolides when **Erythromycin R** unless a specific macrolide is tested susceptible.")
    if ery == "Resistant" and cli == "Susceptible":
        out.append("If considering clindamycin, consider **D-test** where applicable; avoid clindamycin if inducible MLS_B is present.")

    # FQ caution
    if lvo == "Susceptible":
        out.append("If a fluoroquinolone is considered, use only if **the specific agent is susceptible**; avoid class assumptions.")
    elif lvo in {"Intermediate", "Resistant"}:
        out.append("Fluoroquinolone non-susceptible → avoid FQs; select a susceptible β-lactam or vancomycin per site/severity.")

    return _dedup_list(out)

# ======================
# Staphylococcus: mechanisms & therapy
# ======================

def mech_staph(org: str, R: dict):
    """
    Mechanism inference for Staphylococcus spp.
    org: "Staphylococcus aureus", "Coagulase-negative Staphylococcus", "Staphylococcus lugdunensis"
    R:   dict of {antibiotic: S/I/R}
    """
    mechs, banners, greens = [], [], []

    ox   = _get(R, "Nafcillin/Oxacillin")
    pen  = _get(R, "Penicillin")
    vanc = _get(R, "Vancomycin")
    ery  = _get(R, "Erythromycin")
    clin = _get(R, "Clindamycin")
    genta = _get(R, "Gentamicin")
    tmp  = _get(R, "Trimethoprim/Sulfamethoxazole")
    moxi = _get(R, "Moxifloxacin")
    tet  = _get(R, "Tetracycline/Doxycycline")
    lino = _get(R, "Linezolid")

    # ---- β-lactam (oxacillin) phenotype: MRSA/MSSA vs CoNS ----
    if ox == "Resistant":
        # MRSA or methicillin-resistant CoNS
        if org == "Staphylococcus aureus":
            mechs.append("**MRSA phenotype** (likely **mecA/mecC → PBP2a**; oxacillin/nafcillin resistant).")
        elif org == "Staphylococcus lugdunensis":
            mechs.append("**Methicillin-resistant S. lugdunensis** phenotype (mecA-mediated PBP2a).")
        elif org == "Coagulase-negative Staphylococcus":
            mechs.append("**Methicillin-resistant CoNS** (mecA-mediated PBP2a), common in device-associated infections.")
    elif ox == "Susceptible":
        if org in {"Staphylococcus aureus", "Staphylococcus lugdunensis"}:
            greens.append("**MSSA-like phenotype** → β-lactams (e.g., nafcillin/oxacillin or cefazolin) are preferred when susceptible.")
        elif org == "Coagulase-negative Staphylococcus":
            greens.append("CoNS with oxacillin susceptibility → consider as truly susceptible; β-lactams can be effective when clinically indicated.")

    # ---- Penicillin: add explicit mechanism for resistance ----
    # NOTE: If oxacillin is Resistant (MRSA/MR-CoNS), penicillin guidance is usually not clinically helpful,
    # so suppress the penicillinase-focused messaging in that scenario.
    if ox != "Resistant":
        if pen == "Susceptible":
            banners.append(
                "**Penicillin susceptible reported** → confirm absence of **penicillinase (β-lactamase; blaZ)** before using penicillin; "
                "many centers still favor anti-staphylococcal β-lactams (nafcillin/oxacillin/cefazolin) for invasive disease."
            )
        elif pen == "Resistant":
            mechs.append(
                "Penicillin resistance: most commonly **penicillinase (β-lactamase; blaZ)** hydrolyzing penicillin. "
                "Oxacillin/nafcillin may remain active if mecA/mecC is absent."
            )
            # If oxacillin is explicitly susceptible, call out the classic pattern
            if ox == "Susceptible":
                banners.append("Pattern **Penicillin R + Oxacillin S** → strongly supports **penicillinase (blaZ)** production.")

    # ---- Macrolide / lincosamide (D-test pattern) ----
    if ery == "Resistant" and clin == "Resistant":
        mechs.append("Macrolide/Lincosamide resistance: likely **erm-mediated MLS_B** (constitutive).")
    elif ery == "Resistant" and clin == "Susceptible":
        banners.append(
            "**Erythromycin R / Clindamycin S** → perform **D-test** for inducible MLS_B (erm). "
            "Avoid clindamycin if D-test positive; **mef(A/E)** efflux also possible."
        )

    # ---- Vancomycin: add VISA mechanism when Intermediate ----
    if vanc == "Intermediate":
        mechs.append(
            "**VISA phenotype** (vancomycin-intermediate): typically due to **cell-wall thickening / reduced autolysis** "
            "with trapping of vancomycin in the outer cell-wall layers (not VanA/VanB)."
        )
        banners.append(
            "Vancomycin **Intermediate** → treat as reduced efficacy: obtain **repeat MIC / confirmatory testing** per lab policy; "
            "consider alternative agents depending on site/severity."
        )
    elif vanc == "Resistant":
        mechs.append(
            "**Vancomycin resistance**: consider **VanA/VanB** (rare in *S. aureus*, more in some CoNS → VRSA/VR-CoNS) "
            "vs VISA/heteroresistance; confirm by MIC and reference testing."
        )

    # ---- Linezolid ----
    if lino == "Resistant":
        mechs.append("**Linezolid resistance**: 23S rRNA mutations and/or **cfr/optrA/poxtA** genes.")

    # ---- Aminoglycosides ----
    if genta == "Resistant":
        mechs.append("**Aminoglycoside resistance**: **aminoglycoside-modifying enzymes** (e.g., aac(6')-Ie-aph(2'')-Ia).")

    # ---- Fluoroquinolones ----
    if moxi == "Resistant":
        mechs.append("**Fluoroquinolone resistance**: **gyrA/parC** mutations ± efflux.")

    # ---- Tetracyclines ----
    if tet == "Resistant":
        mechs.append("**Tetracycline resistance**: **tetK** (efflux) and/or **tetM** (ribosomal protection).")

    # ---- TMP-SMX ----
    if tmp == "Resistant":
        mechs.append("**TMP-SMX resistance**: mutations or acquired **dfr** (DHFR) and/or **sul** (DHPS) genes.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_staph(org: str, R: dict):
    """
    Therapy guidance for Staphylococcus spp. (heuristic; align with local ID/CLSI guidance).
    """
    out = []

    ox   = _get(R, "Nafcillin/Oxacillin")
    pen  = _get(R, "Penicillin")
    vanc = _get(R, "Vancomycin")
    ery  = _get(R, "Erythromycin")
    clin = _get(R, "Clindamycin")
    tmp  = _get(R, "Trimethoprim/Sulfamethoxazole")
    moxi = _get(R, "Moxifloxacin")
    tet  = _get(R, "Tetracycline/Doxycycline")
    lino = _get(R, "Linezolid")

    # MSSA / methicillin-susceptible phenotype
    if ox == "Susceptible":
        if org in {"Staphylococcus aureus", "Staphylococcus lugdunensis"}:
            out.append("**MSSA phenotype** → use an anti-staphylococcal β-lactam (e.g., **nafcillin/oxacillin** or **cefazolin**) as first-line for serious infections.")
        elif org == "Coagulase-negative Staphylococcus":
            out.append("Oxacillin-susceptible CoNS → β-lactams (e.g., oxacillin/cefazolin) are appropriate if treatment is indicated.")

        # Penicillin option (only meaningful when methicillin-susceptible)
        if pen == "Susceptible":
            out.append("If **penicillinase-negative** is confirmed, **Penicillin G** may be used; many centers still prefer nafcillin/oxacillin/cefazolin for invasive disease.")

    # MRSA / methicillin-resistant phenotype
    if ox == "Resistant":
        # Vancomycin nuance (S vs I)
        if vanc == "Susceptible":
            out.append("**MRSA / methicillin-resistant staphylococci** → **Vancomycin** is standard for serious infections; consider **daptomycin** (non-pneumonia) or **linezolid** (especially pneumonia) when appropriate.")
        elif vanc == "Intermediate":
            out.append(
                "**Vancomycin Intermediate (VISA)** → avoid relying on vancomycin for invasive disease; "
                "consider alternatives (e.g., **daptomycin** for bacteremia/right-sided endocarditis; **linezolid** for pneumonia) based on susceptibility and site."
            )
        elif vanc == "Resistant":
            out.append("**Vancomycin resistant** → use non-glycopeptide options guided by susceptibility (e.g., **linezolid** or **daptomycin** where appropriate) and involve **ID**.")

        if lino == "Susceptible":
            out.append("When **Linezolid S**, it is a good option for **MRSA pneumonia** or when an oral agent is needed with high bioavailability.")

    # D-test / clindamycin
    if ery == "Resistant" and clin == "Susceptible":
        out.append("**Erythromycin R / Clindamycin S** → perform a **D-test**. Only use clindamycin if D-test negative (no inducible MLS_B).")

    # TMP-SMX as oral option (selected scenarios)
    if tmp == "Susceptible":
        out.append("**TMP-SMX susceptible** → reasonable **oral step-down** for selected infections (often SSTI; sometimes bone/joint with close follow-up) when susceptible and source is controlled. Avoid as monotherapy for severe bacteremia/endocarditis.")

    # Tetracycline/Doxycycline as oral option
    if tet == "Susceptible":
        out.append("**Tetracycline/Doxycycline susceptible** → may be used as an **oral option** for some skin/soft tissue infections when appropriate.")

    # Fluoroquinolones – caution
    if moxi == "Susceptible":
        out.append("If **Moxifloxacin S**, use with caution; fluoroquinolones are generally **not preferred** for staphylococcal infections due to rapid emergence of resistance and toxicity concerns.")

    return _dedup_list(out)

# ======================
# Per-organism registry
# ======================
ORGANISM_REGISTRY = {
    # Gram-negatives
    "Escherichia coli": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli
    },
    "Klebsiella pneumoniae": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli  # shares ESBL/TEM-SHV logic patterns
    },
    "Klebsiella oxytoca": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli
    },
    "Klebsiella aerogenes": {
        "mechanisms": mech_k_aerogenes, "therapy": tx_k_aerogenes
    },
    "Enterobacter cloacae complex": {
        "mechanisms": mech_ecloacae, "therapy": tx_ecloacae
    },
    "Citrobacter freundii complex": {
        "mechanisms": mech_cfreundii, "therapy": tx_cfreundii
    },
    "Citrobacter koseri": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli
    },
    "Serratia marcescens": {
        "mechanisms": mech_serratia, "therapy": tx_serratia
    },
    "Proteus mirabilis": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli
    },
    "Proteus vulgaris group": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli
    },
    "Morganella morganii": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli
    },
    "Salmonella enterica": {
        "mechanisms": mech_ecoli, "therapy": tx_ecoli
    },
    "Acinetobacter baumannii complex": {
        "mechanisms": mech_acinetobacter, "therapy": tx_acinetobacter
    },
    "Achromobacter xylosoxidans": {
        "mechanisms": mech_achromobacter, "therapy": tx_achromobacter
    },
    "Pseudomonas aeruginosa": {
        "mechanisms": mech_pseudomonas, "therapy": tx_pseudomonas
    },
    "Stenotrophomonas maltophilia": {
        "mechanisms": mech_steno, "therapy": tx_steno
    },

    # Enterococcus
    "Enterococcus faecalis": {
        "mechanisms": mech_efaecalis, "therapy": tx_efaecalis
    },
    "Enterococcus faecium": {
        "mechanisms": mech_efaecium, "therapy": tx_efaecium
    },

    # Streptococcus
    "Streptococcus pneumoniae": {
        "mechanisms": mech_spneumo, "therapy": tx_spneumo
    },
    "β-hemolytic Streptococcus (GAS/GBS)": {
        "mechanisms": mech_bhs, "therapy": tx_bhs
    },
    "Viridans group streptococci (VGS)": {
        "mechanisms": mech_vgs, "therapy": tx_vgs
    },

    #Staphylococcus
    "Staphylococcus aureus": {
        "mechanisms": lambda R: mech_staph("Staphylococcus aureus", R),
        "therapy":    lambda R: tx_staph("Staphylococcus aureus", R)
    },
    "Coagulase-negative Staphylococcus": {
        "mechanisms": lambda R: mech_staph("Coagulase-negative Staphylococcus", R),
        "therapy":    lambda R: tx_staph("Coagulase-negative Staphylococcus", R)
    },
    "Staphylococcus lugdunensis": {
        "mechanisms": lambda R: mech_staph("Staphylococcus lugdunensis", R),
        "therapy":    lambda R: tx_staph("Staphylococcus lugdunensis", R)
    },
}

# ======================
# Derived registries (mechanisms / therapy)
# ======================
MECH_REGISTRY = {
    org: cfg["mechanisms"]
    for org, cfg in ORGANISM_REGISTRY.items()
    if "mechanisms" in cfg
}

TX_REGISTRY = {
    org: cfg["therapy"]
    for org, cfg in ORGANISM_REGISTRY.items()
    if "therapy" in cfg
}


# ======================
# Adapter layer for UI
# ======================
def run_mechanisms_and_therapy_for(org, final_results):
    """
    Returns:
      mechs, banners, greens, therapy_notes
    """
    entry = ORGANISM_REGISTRY.get(org)
    if not entry:
        return [], [], [], []
    mechs, banners, greens = entry["mechanisms"](final_results)
    therapy = entry["therapy"](final_results)
    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens), _dedup_list(therapy)

# ======================
# UI: Title + group selector
# ======================
st.markdown("""
<h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
Select Pathogen Group
</h2>
""", unsafe_allow_html=True)
st.caption("Enter results only for antibiotics **actually tested** for the chosen organism. Non-tested agents are hidden.")

group_options = ["Gram-negatives", "Staphylococci", "Enterococcus", "Streptococcus", "Anaerobes"]
group = st.selectbox("Pathogen group", group_options, index=0, key="pathogen_group")

# ======================
# Gram-negatives UI (uses registry)
# ======================
if group == "Gram-negatives":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Gram Negatives
    </h2>
    """, unsafe_allow_html=True)

    organisms = sorted(GNR_CANON)
    organism = st.selectbox("Organism", organisms, key="gnr_org")

    panel = PANEL.get(organism, [])
    rules = RULES.get(organism, {"intrinsic_resistance": [], "cascade": []})

    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Susceptibility Inputs
    </h2>
    """, unsafe_allow_html=True)
    st.caption("Leave blank for untested/unknown.")

    user = {}
    choices = ["", "Susceptible", "Intermediate", "Resistant"]
    intrinsic = rules.get("intrinsic_resistance", [])
    for i, ab in enumerate(panel):
        if ab in intrinsic:
            _ = st.selectbox(
                ab + " (intrinsic)", choices, index=3, key=f"ab_{organism}_{i}", disabled=True,
                help="Intrinsic resistance by rule for this organism"
            )
            user[ab] = None
        else:
            val = st.selectbox(ab, choices, index=0, key=f"ab_{organism}_{i}")
            user[ab] = val if val else None

    if intrinsic:
        st.info("**Intrinsic resistance to:** " + ", ".join(intrinsic))

    # Apply cascade rules
    inferred = apply_cascade(rules, user)

    # Final result map (user + inferred + intrinsic)
    from collections import defaultdict
    final = defaultdict(lambda: None)
    for k, v in {**inferred, **user}.items():
        final[k] = v
    for ab in intrinsic:
        final[ab] = "Resistant"

    st.subheader("Consolidated results")
    rows = []
    for ab in panel:
        if final[ab] is None:
            continue
        src = "User-entered"
        if ab in intrinsic:
            src = "Intrinsic rule"
        elif ab in inferred and (ab not in user or user[ab] is None):
            src = "Cascade rule"
        rows.append({"Antibiotic": ab, "Result": final[ab], "Source": src})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
    else:
        st.write("No results yet. Enter at least one result above.")

    # ===== Mechanisms + Therapy via registry =====
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Mechanism of Resistance
    </h2>
    """, unsafe_allow_html=True)
    mechs, banners, greens, gnotes = run_mechanisms_and_therapy_for(organism, final)

    if mechs:
        for m in mechs:
            st.markdown(f"""
            <div style="border-left:4px solid #c62828; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#ffebee;">
            {badge("Mechanism", bg="#c62828")} {m}
             </div>
            """, unsafe_allow_html=True)

    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    if banners:
        for b in banners:
            st.markdown(f"""
            <div style="border-left:4px solid #f9a825; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#fffde7;">
            {badge("Caution", bg="#f9a825", fg="#000000")} {b}
            </div>
            """, unsafe_allow_html=True)

    if greens:
        for g in greens:
            st.markdown(f"""
            <div style="border-left:4px solid #2e7d32; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e8f5e9;">
            {badge("Favorable", bg="#2e7d32")} {g}
            </div>
            """, unsafe_allow_html=True)


    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Therapy Guidance
    </h2>
    """, unsafe_allow_html=True)
    if gnotes:
        for note in gnotes:
            st.markdown(f"""
            <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
            {badge("Therapy", bg="#00838f")} {note}
            </div>
            """, unsafe_allow_html=True)

    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    # --- References (bottom of organism output) ---
    refs = _collect_mech_ref_keys(organism, mechs, banners)
    if refs:
     fancy_divider()
     st.subheader("📚 References")
     for r in refs:
        st.markdown(f"- {r}")

# ======================
# Enterococcus module (uses registry)
# ======================
if group == "Enterococcus":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Enterococcus
    </h2>
    """, unsafe_allow_html=True)
    ENTERO_ORGS = ["Enterococcus faecalis", "Enterococcus faecium"]
    organism_e = st.selectbox("Organism (Enterococcus)", ENTERO_ORGS, key="enterococcus_org")

    PANEL_E = [
        "Penicillin", "Ampicillin",
        "Vancomycin",
        "Linezolid", "Daptomycin",
        "High-level Gentamicin", "High-level Streptomycin",
        "Ciprofloxacin",
        "Nitrofurantoin",
        "Ceftriaxone", "Cefepime"
    ]

    # Intrinsic map
    intrinsic_e = {ab: False for ab in PANEL_E}
    for ab in ["Ceftriaxone", "Cefepime"]:
        intrinsic_e[ab] = True
    if organism_e == "Enterococcus faecium":
        intrinsic_e["Ampicillin"] = True
        intrinsic_e["Penicillin"] = True

    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Susceptibility Inputs
    </h2>
    """, unsafe_allow_html=True)
    st.caption("Leave blank for untested/unknown.")
    user_e, final_e = _collect_panel_inputs(PANEL_E, intrinsic_e, keyprefix="E_ab")

    st.subheader("Consolidated results")
    rows_e = []
    for ab in PANEL_E:
        if final_e[ab] is None:
            continue
        src = "User-entered"
        if intrinsic_e.get(ab):
            src = "Intrinsic rule"
        rows_e.append({"Antibiotic": ab, "Result": final_e[ab], "Source": src})
    if rows_e:
        st.dataframe(pd.DataFrame(rows_e), use_container_width=True)

    # ===== Mechanisms + Therapy via registry =====
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Mechanism of Resistance
    </h2>
    """, unsafe_allow_html=True)
    mechs_e, banners_e, greens_e, gnotes_e = run_mechanisms_and_therapy_for(organism_e, final_e)

    if mechs_e:
        for m in mechs_e:
            st.markdown(f"""
            <div style="border-left:4px solid #c62828; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#ffebee;">
                {badge("Mechanism", bg="#c62828")} {m}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    for b in banners_e:
        st.markdown(f"""
        <div style="border-left:4px solid #f9a825; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#fffde7;">
            {badge("Caution", bg="#f9a825", fg="#000000")} {b}
        </div>
        """, unsafe_allow_html=True)

    for g in greens_e:
        st.markdown(f"""
        <div style="border-left:4px solid #2e7d32; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e8f5e9;">
            {badge("Favorable", bg="#2e7d32")} {g}
        </div>
        """, unsafe_allow_html=True)

    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Therapy Guidance
    </h2>
    """, unsafe_allow_html=True)
    if gnotes_e:
        for note in gnotes_e:
            st.markdown(f"""
            <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                {badge("Therapy", bg="#00838f")} {note}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    # --- References (bottom of organism output) ---
    refs_e = _collect_mech_ref_keys(organism_e, mechs_e, banners_e)
    if refs_e:
        fancy_divider()
        st.subheader("📚 References")
        for r in refs_e:
            st.markdown(f"- {r}")

    st.stop()

# ======================
# Staphylococci module
# ======================
if group == "Staphylococci":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Staphylococci
    </h2>
    """, unsafe_allow_html=True)

    STAPH_ORGS = [
        "Staphylococcus aureus",
        "Coagulase-negative Staphylococcus",
        "Staphylococcus lugdunensis",
    ]
    organism_st = st.selectbox("Organism (Staphylococcus)", STAPH_ORGS, key="staph_org")

    PANEL_ST = [
        "Penicillin",
        "Nafcillin/Oxacillin",
        "Vancomycin",
        "Erythromycin",
        "Clindamycin",
        "Gentamicin",
        "Trimethoprim/Sulfamethoxazole",
        "Moxifloxacin",
        "Tetracycline/Doxycycline",
        "Linezolid",
    ]
    intrinsic_st = {ab: False for ab in PANEL_ST}  # no forced intrinsic R here

    # Inputs
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Susceptibility Inputs
    </h2>
    """, unsafe_allow_html=True)
    st.caption("Leave blank for untested/unknown.")
    user_st, final_st = _collect_panel_inputs(PANEL_ST, intrinsic_st, keyprefix="STAPH_ab")

    # Consolidated results
    st.subheader("Consolidated results")
    rows_st = []
    for ab in PANEL_ST:
        if final_st[ab] is None:
            continue
        rows_st.append({"Antibiotic": ab, "Result": final_st[ab], "Source": "User-entered"})
    if rows_st:
        st.dataframe(pd.DataFrame(rows_st), use_container_width=True)

    # Mechanisms / banners / greens via registry
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Mechanism of Resistance
    </h2>
    """, unsafe_allow_html=True)
    # ---- Mechanisms & guidance via registry ----
    mechs_st, banners_st, greens_st = [], [], []

    mech_fn = MECH_REGISTRY.get(organism_st)
    if mech_fn is not None:
        mechs_st, banners_st, greens_st = mech_fn(final_st)

    if mechs_st:
        for m in mechs_st:
            st.error(f"• {m}")
    else:
        st.success("No major resistance mechanism identified based on current inputs.")
    for b in banners_st:
        st.warning(b)
    for g in greens_st:
        st.success(g)

    # Therapy guidance
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Therapy Guidance
    </h2>
    """, unsafe_allow_html=True)

    tx_fn = TX_REGISTRY.get(organism_st)
    if tx_fn is not None:
        gnotes_st = tx_fn(final_st)
    else:
        gnotes_st = []

    if gnotes_st:
        for note in gnotes_st:
            st.markdown(f"""
            <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
            {badge("Therapy", bg="#00838f")} {note}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")


    # References at the bottom
    refs_st = _collect_mech_ref_keys(organism_st, mechs_st, banners_st)
    if refs_st:
        fancy_divider()
        st.subheader("📚 References")
        for r in refs_st:
            st.markdown(f"- {r}")

    st.stop()

# ======================
# Streptococcus module (uses registry)
# ======================
if group == "Streptococcus":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Streptococcus
    </h2>
    """, unsafe_allow_html=True)
    STREP_GROUP = st.selectbox(
        "Strep group",
        ["Streptococcus pneumoniae", "β-hemolytic Streptococcus (GAS/GBS)", "Viridans group streptococci (VGS)"],
        key="strep_group"
    )

    if STREP_GROUP == "Streptococcus pneumoniae":
        PANEL_SPN = [
            "Penicillin", "Ceftriaxone", "Cefotaxime",
            "Erythromycin", "Clindamycin",
            "Levofloxacin",
            "Vancomycin"
        ]
        intrinsic_spn = {ab: False for ab in PANEL_SPN}

        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Susceptibility Inputs
        </h2>
        """, unsafe_allow_html=True)
        st.caption("Leave blank for untested/unknown.")
        user_s, final_s = _collect_panel_inputs(PANEL_SPN, intrinsic_spn, keyprefix="SPN_ab")

        st.subheader("Consolidated results")
        rows_s = []
        for ab in PANEL_SPN:
            if final_s[ab] is None:
                continue
            rows_s.append({"Antibiotic": ab, "Result": final_s[ab], "Source": "User-entered"})
        if rows_s:
            st.dataframe(pd.DataFrame(rows_s), use_container_width=True)

        # ===== Mechanisms + Therapy via registry =====
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Mechanism of Resistance
        </h2>
        """, unsafe_allow_html=True)
        mechs_s, banners_s, greens_s, gnotes_s = run_mechanisms_and_therapy_for("Streptococcus pneumoniae", final_s)

        if mechs_s:
            for m in mechs_s:
                st.error(f"• {m}")
        else:
            st.success("No major resistance mechanism identified based on current inputs.")
        for b in banners_s:
            st.warning(b)
        for g in greens_s:
            st.success(g)

        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Therapy Guidance
        </h2>
        """, unsafe_allow_html=True)
        if gnotes_s:
            for note in gnotes_s:
                st.markdown(f"""
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                {badge("Therapy", bg="#00838f")} {note}
                </div>
                """, unsafe_allow_html=True)

        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        
        # --- References (bottom of organism output) ---
        refs_s = _collect_mech_ref_keys("Streptococcus pneumoniae", mechs_s, banners_s)
        if refs_s:
         fancy_divider()
         st.subheader("📚 References")
         for r in refs_s:
           st.markdown(f"- {r}")

        st.stop()

    elif STREP_GROUP == "β-hemolytic Streptococcus (GAS/GBS)":
        PANEL_BHS = [
            "Penicillin",
            "Erythromycin", "Clindamycin",
            "Levofloxacin",
            "Vancomycin"
        ]
        intrinsic_bhs = {ab: False for ab in PANEL_BHS}

        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Susceptibility Inputs
        </h2>
        """, unsafe_allow_html=True)
        st.caption("Leave blank for untested/unknown.")
        user_b, final_b = _collect_panel_inputs(PANEL_BHS, intrinsic_bhs, keyprefix="BHS_ab")

        st.subheader("Consolidated results")
        rows_b = []
        for ab in PANEL_BHS:
            if final_b[ab] is None:
                continue
            rows_b.append({"Antibiotic": ab, "Result": final_b[ab], "Source": "User-entered"})
        if rows_b:
            st.dataframe(pd.DataFrame(rows_b), use_container_width=True)

        # ===== Mechanisms + Therapy via registry =====
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Mechanism of Resistance
        </h2>
        """, unsafe_allow_html=True)
        mechs_b, banners_b, greens_b, gnotes_b = run_mechanisms_and_therapy_for("β-hemolytic Streptococcus (GAS/GBS)", final_b)

        if mechs_b:
            for m in mechs_b:
                st.error(f"• {m}")
        else:
            st.success("No major resistance mechanism identified based on current inputs.")
        for b in banners_b:
            st.warning(b)
        for g in greens_b:
            st.success(g)

        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Therapy Guidance
        </h2>
        """, unsafe_allow_html=True)
        if gnotes_b:
            for note in gnotes_b:
                st.markdown(f"""
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                {badge("Therapy", bg="#00838f")} {note}
                </div>
                """, unsafe_allow_html=True)

        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        st.stop()

    elif STREP_GROUP == "Viridans group streptococci (VGS)":
        PANEL_VGS = [
            "Penicillin", "Ceftriaxone",
            "Erythromycin", "Clindamycin",
            "Levofloxacin",
            "Vancomycin"
        ]
        intrinsic_vgs = {ab: False for ab in PANEL_VGS}

        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Susceptibility Inputs
        </h2>
        """, unsafe_allow_html=True)
        st.caption("Leave blank for untested/unknown.")
        user_v, final_v = _collect_panel_inputs(PANEL_VGS, intrinsic_vgs, keyprefix="VGS_ab")

        st.subheader("Consolidated results")
        rows_v = []
        for ab in PANEL_VGS:
            if final_v[ab] is None:
                continue
            rows_v.append({"Antibiotic": ab, "Result": final_v[ab], "Source": "User-entered"})
        if rows_v:
            st.dataframe(pd.DataFrame(rows_v), use_container_width=True)

        # ===== Mechanisms + Therapy via registry =====
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Mechanism of Resistance
        </h2>
        """, unsafe_allow_html=True)
        mechs_v, banners_v, greens_v, gnotes_v = run_mechanisms_and_therapy_for("Viridans group streptococci (VGS)", final_v)

        if mechs_v:
            for m in mechs_v:
                st.error(f"• {m}")
        else:
            st.success("No major resistance mechanism identified based on current inputs.")
        for b in banners_v:
            st.warning(b)
        for g in greens_v:
            st.success(g)

        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #2f8059, #74b88f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Therapy Guidance
        </h2>
        """, unsafe_allow_html=True)
        if gnotes_v:
            for note in gnotes_v:
                st.markdown(f"""
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                {badge("Therapy", bg="#00838f")} {note}
                </div>
                """, unsafe_allow_html=True)

        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        st.stop()

fancy_divider()
st.markdown("""
<p style="text-align:center; font-size:0.8rem; color:#3f5649;">
<strong>MechID</strong> is a heuristic teaching tool for pattern recognition in antimicrobial resistance.<br>
Always interpret results in context of patient, local epidemiology, and formal guidance (IDSA, CLSI, EUCAST).<br>
© MechID · (ID)as &amp; O(ID)nions
</p>
""", unsafe_allow_html=True)
