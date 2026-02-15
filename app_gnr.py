import streamlit as st
import pandas as pd
from collections import defaultdict

# ======================
# Page setup
# ======================
st.set_page_config(
    page_title="MechID — Mechanism-Based Interpretation of Antibiograms",
    page_icon="🧫",
    layout="centered",
)

st.markdown(
    """
    <h1 style='text-align:center; color:#1f6f4a; font-weight:800; margin-bottom:0.2rem;'>
      MechID
    </h1>
    <h3 style='text-align:center; color:#155239; margin-top:0;'>
      Mechanism-Based Interpretation of Antibiograms
    </h3>
    <p style='text-align:center; color:#3f5649; font-size:0.9rem;'>
      From MIC patterns to likely resistance mechanisms and practical therapy notes.<br>
      Heuristic output — always confirm with your microbiology lab, ID consult, and IDSA/CLSI guidance.
    </p>
    """,
    unsafe_allow_html=True,
)

IDHUB_THEME_CSS = """
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

    [data-theme="dark"], [data-theme="light"], .stApp {
        color-scheme: light !important;
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

    .stMarkdown, .stText, .stCaption, .stMetric, label, p, li, span {
        color: var(--foreground);
    }

    section[data-testid="stSidebar"] {
        background: var(--card);
        color: var(--foreground);
        border-right: 1px solid var(--border);
    }

    div[data-baseweb="select"] > div,
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background: var(--card2) !important;
        color: var(--foreground) !important;
        border: 1px solid var(--border) !important;
    }

    .stButton button {
        background: var(--primary) !important;
        color: #ffffff !important;
        border: 1px solid var(--primary) !important;
    }
</style>
"""
st.markdown(IDHUB_THEME_CSS, unsafe_allow_html=True)

# ======================
# Helpers
# ======================
def fancy_divider():
    st.markdown(
        """
        <hr style="
            border:0;
            height:2px;
            margin:1.5rem 0 1rem 0;
            background: linear-gradient(to right, #1f6f4a, #155239, #4d8f6f);
        ">
        """,
        unsafe_allow_html=True,
    )

def render_section_header(title: str):
    st.markdown(
        f"""
        <h2 style='text-align:center; font-weight:800;
          background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;'>
          {title}
        </h2>
        """,
        unsafe_allow_html=True,
    )

def badge(text, bg="#1f6f4a", fg="#ffffff"):
    return f"""
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

def _dedup_list(items):
    seen = set()
    out = []
    for x in items or []:
        if x is None:
            continue
        s = str(x).strip()
        if not s:
            continue
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

def apply_cascade(rules: dict, user_map: dict) -> dict:
    """
    Placeholder cascade engine.
    Your real version likely contains organism-specific logical implications.
    This stub just returns {} so the app runs.
    """
    _ = rules
    _ = user_map
    return {}

def _collect_panel_inputs(panel, intrinsic_map, keyprefix: str):
    """
    Collect S/I/R inputs for a given panel.
    intrinsic_map[ab] == True means forced intrinsic Resistant (disabled UI).
    Returns:
      user_map, final_map (defaultdict)
    """
    choices = ["", "Susceptible", "Intermediate", "Resistant"]
    user = {}
    final = defaultdict(lambda: None)

    for i, ab in enumerate(panel):
        if intrinsic_map.get(ab):
            st.selectbox(
                f"{ab} (intrinsic)",
                choices,
                index=3,
                key=f"{keyprefix}_{i}",
                disabled=True,
                help="Intrinsic resistance by rule for this organism",
            )
            user[ab] = None
            final[ab] = "Resistant"
        else:
            val = st.selectbox(ab, choices, index=0, key=f"{keyprefix}_{i}")
            user[ab] = val if val else None
            final[ab] = user[ab]

    return user, final

# ======================
# References mapping (auto-detected from mechanism text)
# ======================
MECH_REF_MAP = {
    "esbl": [
        "IDSA Guidance for ESBL-producing Enterobacterales (latest).",
        "Paterson DL, Bonomo RA. Extended-Spectrum β-Lactamases: a clinical update. Clin Microbiol Rev.",
    ],
    "ampc": [
        "IDSA Guidance for AmpC-producing Enterobacterales (latest).",
        "Jacoby GA. AmpC β-lactamases. Clin Microbiol Rev.",
    ],
    "mecA": [
        "CLSI: Staphylococci oxacillin/cefoxitin and mecA interpretation (current edition).",
    ],
}

def _collect_mech_ref_keys(organism: str, mechs: list[str], banners: list[str]):
    """
    Placeholder: in your full app you likely parse mechanism strings
    to decide which ref blocks to show.
    Here we do a simple keyword scan.
    """
    _ = organism
    text = " ".join((mechs or []) + (banners or [])).lower()
    refs = []
    for key, items in MECH_REF_MAP.items():
        if key in text:
            refs.extend(items)
    return _dedup_list(refs)

def render_references(refs):
    """Reusable renderer with correct indentation (prevents your prior bug)."""
    if not refs:
        return
    fancy_divider()
    st.subheader("📚 References")
    for r in refs:
        st.markdown(f"- {r}")

# ======================
# Minimal runnable registries (REPLACE with yours)
# ======================
GNR_CANON = [
    "Escherichia coli",
    "Klebsiella pneumoniae",
    "Pseudomonas aeruginosa",
]

PANEL = {
    "Escherichia coli": [
        "Ceftriaxone",
        "Cefepime",
        "Piperacillin/Tazobactam",
        "Ertapenem",
        "Meropenem",
        "Ciprofloxacin",
        "Trimethoprim/Sulfamethoxazole",
    ],
    "Klebsiella pneumoniae": [
        "Ceftriaxone",
        "Cefepime",
        "Piperacillin/Tazobactam",
        "Ertapenem",
        "Meropenem",
        "Ciprofloxacin",
    ],
    "Pseudomonas aeruginosa": [
        "Cefepime",
        "Piperacillin/Tazobactam",
        "Ceftazidime",
        "Meropenem",
        "Ciprofloxacin",
    ],
}

RULES = {
    "Escherichia coli": {"intrinsic_resistance": [], "cascade": []},
    "Klebsiella pneumoniae": {"intrinsic_resistance": [], "cascade": []},
    "Pseudomonas aeruginosa": {"intrinsic_resistance": ["Ertapenem"], "cascade": []},
}

def demo_mechanisms(final_results):
    mechs, banners, greens = [], [], []
    # silly demo logic so you can see output
    if final_results.get("Ceftriaxone") == "Resistant":
        mechs.append("Pattern suggests ESBL (demo heuristic).")
        banners.append("Avoid ceftriaxone/most 3rd-gen cephalosporins if ESBL suspected.")
    if final_results.get("Meropenem") == "Susceptible":
        greens.append("Carbapenem remains active (demo).")
    return mechs, banners, greens

def demo_therapy(final_results):
    notes = []
    if "Pattern suggests ESBL" in " ".join(demo_mechanisms(final_results)[0]):
        notes.append("If invasive ESBL infection: consider a carbapenem (demo note).")
    if final_results.get("Ciprofloxacin") == "Susceptible":
        notes.append("Oral step-down may be possible if clinically appropriate (demo note).")
    return notes

ORGANISM_REGISTRY = {
    "Escherichia coli": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Klebsiella pneumoniae": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Pseudomonas aeruginosa": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Enterococcus faecalis": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Enterococcus faecium": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Staphylococcus aureus": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Coagulase-negative Staphylococcus": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Staphylococcus lugdunensis": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Streptococcus pneumoniae": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "β-hemolytic Streptococcus (GAS/GBS)": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
    "Viridans group streptococci (VGS)": {"mechanisms": demo_mechanisms, "therapy": demo_therapy},
}

def run_mechanisms_and_therapy_for(org, final_results):
    entry = ORGANISM_REGISTRY.get(org)
    if not entry:
        return [], [], [], []
    mechs, banners, greens = entry["mechanisms"](final_results)
    therapy = entry["therapy"](final_results)
    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens), _dedup_list(therapy)

# ======================
# UI: Title + group selector
# ======================
render_section_header("Select Pathogen Group")
st.caption("Enter results only for antibiotics **actually tested** for the chosen organism. Non-tested agents are hidden.")

group_options = ["Gram-negatives", "Staphylococci", "Enterococcus", "Streptococcus", "Anaerobes"]
group = st.selectbox("Pathogen group", group_options, index=0, key="pathogen_group")

# ======================
# Gram-negatives UI
# ======================
if group == "Gram-negatives":
    render_section_header("Gram Negatives")

    organisms = sorted(GNR_CANON)
    organism = st.selectbox("Organism", organisms, key="gnr_org")

    panel = PANEL.get(organism, [])
    rules = RULES.get(organism, {"intrinsic_resistance": [], "cascade": []})

    render_section_header("Susceptibility Inputs")
    st.caption("Leave blank for untested/unknown.")

    user = {}
    choices = ["", "Susceptible", "Intermediate", "Resistant"]
    intrinsic = rules.get("intrinsic_resistance", [])

    for i, ab in enumerate(panel):
        if ab in intrinsic:
            st.selectbox(
                ab + " (intrinsic)",
                choices,
                index=3,
                key=f"ab_{organism}_{i}",
                disabled=True,
                help="Intrinsic resistance by rule for this organism",
            )
            user[ab] = None
        else:
            val = st.selectbox(ab, choices, index=0, key=f"ab_{organism}_{i}")
            user[ab] = val if val else None

    if intrinsic:
        st.info("**Intrinsic resistance to:** " + ", ".join(intrinsic))

    inferred = apply_cascade(rules, user)

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

    # Mechanisms + Therapy
    fancy_divider()
    render_section_header("Mechanism of Resistance")
    mechs, banners, greens, gnotes = run_mechanisms_and_therapy_for(organism, final)

    if mechs:
        for m in mechs:
            st.markdown(
                f"""
                <div style="border-left:4px solid #c62828; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#ffebee;">
                  {badge("Mechanism", bg="#c62828")} {m}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    if banners:
        for b in banners:
            st.markdown(
                f"""
                <div style="border-left:4px solid #f9a825; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#fffde7;">
                  {badge("Caution", bg="#f9a825", fg="#000000")} {b}
                </div>
                """,
                unsafe_allow_html=True,
            )

    if greens:
        for g in greens:
            st.markdown(
                f"""
                <div style="border-left:4px solid #2e7d32; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e8f5e9;">
                  {badge("Favorable", bg="#2e7d32")} {g}
                </div>
                """,
                unsafe_allow_html=True,
            )

    fancy_divider()
    render_section_header("Therapy Guidance")
    if gnotes:
        for note in gnotes:
            st.markdown(
                f"""
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                  {badge("Therapy", bg="#00838f")} {note}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    # References (FIXED indentation)
    render_references(_collect_mech_ref_keys(organism, mechs, banners))

# ======================
# Enterococcus module
# ======================
if group == "Enterococcus":
    render_section_header("Enterococcus")
    ENTERO_ORGS = ["Enterococcus faecalis", "Enterococcus faecium"]
    organism_e = st.selectbox("Organism (Enterococcus)", ENTERO_ORGS, key="enterococcus_org")

    PANEL_E = [
        "Penicillin", "Ampicillin",
        "Vancomycin",
        "Linezolid", "Daptomycin",
        "High-level Gentamicin", "High-level Streptomycin",
        "Ciprofloxacin",
        "Nitrofurantoin",
        "Ceftriaxone", "Cefepime",
    ]

    intrinsic_e = {ab: False for ab in PANEL_E}
    for ab in ["Ceftriaxone", "Cefepime"]:
        intrinsic_e[ab] = True
    if organism_e == "Enterococcus faecium":
        intrinsic_e["Ampicillin"] = True
        intrinsic_e["Penicillin"] = True

    render_section_header("Susceptibility Inputs")
    st.caption("Leave blank for untested/unknown.")
    user_e, final_e = _collect_panel_inputs(PANEL_E, intrinsic_e, keyprefix="E_ab")

    st.subheader("Consolidated results")
    rows_e = []
    for ab in PANEL_E:
        if final_e[ab] is None:
            continue
        src = "User-entered" if not intrinsic_e.get(ab) else "Intrinsic rule"
        rows_e.append({"Antibiotic": ab, "Result": final_e[ab], "Source": src})
    if rows_e:
        st.dataframe(pd.DataFrame(rows_e), use_container_width=True)

    fancy_divider()
    render_section_header("Mechanism of Resistance")
    mechs_e, banners_e, greens_e, gnotes_e = run_mechanisms_and_therapy_for(organism_e, final_e)

    if mechs_e:
        for m in mechs_e:
            st.markdown(
                f"""
                <div style="border-left:4px solid #c62828; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#ffebee;">
                  {badge("Mechanism", bg="#c62828")} {m}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    for b in banners_e:
        st.markdown(
            f"""
            <div style="border-left:4px solid #f9a825; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#fffde7;">
              {badge("Caution", bg="#f9a825", fg="#000000")} {b}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for g in greens_e:
        st.markdown(
            f"""
            <div style="border-left:4px solid #2e7d32; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e8f5e9;">
              {badge("Favorable", bg="#2e7d32")} {g}
            </div>
            """,
            unsafe_allow_html=True,
        )

    fancy_divider()
    render_section_header("Therapy Guidance")
    if gnotes_e:
        for note in gnotes_e:
            st.markdown(
                f"""
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                  {badge("Therapy", bg="#00838f")} {note}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    render_references(_collect_mech_ref_keys(organism_e, mechs_e, banners_e))
    st.stop()

# ======================
# Staphylococci module
# ======================
if group == "Staphylococci":
    render_section_header("Staphylococci")

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
    intrinsic_st = {ab: False for ab in PANEL_ST}

    render_section_header("Susceptibility Inputs")
    st.caption("Leave blank for untested/unknown.")
    user_st, final_st = _collect_panel_inputs(PANEL_ST, intrinsic_st, keyprefix="STAPH_ab")

    st.subheader("Consolidated results")
    rows_st = []
    for ab in PANEL_ST:
        if final_st[ab] is None:
            continue
        rows_st.append({"Antibiotic": ab, "Result": final_st[ab], "Source": "User-entered"})
    if rows_st:
        st.dataframe(pd.DataFrame(rows_st), use_container_width=True)

    fancy_divider()
    render_section_header("Mechanism of Resistance")
    mechs_st, banners_st, greens_st, gnotes_st = run_mechanisms_and_therapy_for(organism_st, final_st)

    if mechs_st:
        for m in mechs_st:
            st.markdown(
                f"""
                <div style="border-left:4px solid #c62828; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#ffebee;">
                  {badge("Mechanism", bg="#c62828")} {m}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    for b in banners_st:
        st.markdown(
            f"""
            <div style="border-left:4px solid #f9a825; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#fffde7;">
              {badge("Caution", bg="#f9a825", fg="#000000")} {b}
            </div>
            """,
            unsafe_allow_html=True,
        )

    for g in greens_st:
        st.markdown(
            f"""
            <div style="border-left:4px solid #2e7d32; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e8f5e9;">
              {badge("Favorable", bg="#2e7d32")} {g}
            </div>
            """,
            unsafe_allow_html=True,
        )

    fancy_divider()
    render_section_header("Therapy Guidance")
    if gnotes_st:
        for note in gnotes_st:
            st.markdown(
                f"""
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                  {badge("Therapy", bg="#00838f")} {note}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    render_references(_collect_mech_ref_keys(organism_st, mechs_st, banners_st))
    st.stop()

# ======================
# Streptococcus module
# ======================
if group == "Streptococcus":
    render_section_header("Streptococcus")
    STREP_GROUP = st.selectbox(
        "Strep group",
        [
            "Streptococcus pneumoniae",
            "β-hemolytic Streptococcus (GAS/GBS)",
            "Viridans group streptococci (VGS)",
        ],
        key="strep_group",
    )

    if STREP_GROUP == "Streptococcus pneumoniae":
        PANEL_SPN = ["Penicillin", "Ceftriaxone", "Cefotaxime", "Erythromycin", "Clindamycin", "Levofloxacin", "Vancomycin"]
        intrinsic_spn = {ab: False for ab in PANEL_SPN}

        render_section_header("Susceptibility Inputs")
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

        fancy_divider()
        render_section_header("Mechanism of Resistance")
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
        render_section_header("Therapy Guidance")
        if gnotes_s:
            for note in gnotes_s:
                st.markdown(
                    f"""
                    <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                      {badge("Therapy", bg="#00838f")} {note}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        # References (FIXED indentation)
        render_references(_collect_mech_ref_keys("Streptococcus pneumoniae", mechs_s, banners_s))
        st.stop()

    elif STREP_GROUP == "β-hemolytic Streptococcus (GAS/GBS)":
        PANEL_BHS = ["Penicillin", "Erythromycin", "Clindamycin", "Levofloxacin", "Vancomycin"]
        intrinsic_bhs = {ab: False for ab in PANEL_BHS}

        render_section_header("Susceptibility Inputs")
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

        fancy_divider()
        render_section_header("Mechanism of Resistance")
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
        render_section_header("Therapy Guidance")
        if gnotes_b:
            for note in gnotes_b:
                st.markdown(
                    f"""
                    <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                      {badge("Therapy", bg="#00838f")} {note}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        render_references(_collect_mech_ref_keys("β-hemolytic Streptococcus (GAS/GBS)", mechs_b, banners_b))
        st.stop()

    elif STREP_GROUP == "Viridans group streptococci (VGS)":
        PANEL_VGS = ["Penicillin", "Ceftriaxone", "Erythromycin", "Clindamycin", "Levofloxacin", "Vancomycin"]
        intrinsic_vgs = {ab: False for ab in PANEL_VGS}

        render_section_header("Susceptibility Inputs")
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

        fancy_divider()
        render_section_header("Mechanism of Resistance")
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
        render_section_header("Therapy Guidance")
        if gnotes_v:
            for note in gnotes_v:
                st.markdown(
                    f"""
                    <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
                      {badge("Therapy", bg="#00838f")} {note}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        render_references(_collect_mech_ref_keys("Viridans group streptococci (VGS)", mechs_v, banners_v))
        st.stop()

# ======================
# Footer
# ======================
fancy_divider()
st.markdown(
    """
    <p style="text-align:center; font-size:0.8rem; color:#90a4ae;">
      <strong>MechID</strong> is a heuristic teaching tool for pattern recognition in antimicrobial resistance.<br>
      Always interpret results in context of patient, local epidemiology, and formal guidance (IDSA, CLSI, EUCAST).<br>
      © MechID · (ID)as &amp; O(ID)nions
    </p>
    """,
    unsafe_allow_html=True,
)
