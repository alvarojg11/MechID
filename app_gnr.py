import streamlit as st
2
import pandas as pd
3
from collections import defaultdict
4

5
# ======================
6
# Page setup
7
# ======================
8
st.set_page_config(
9
    page_title="MechID — Mechanism-Based Interpretation of Antibiograms",
10
    page_icon="🧫",
11
    layout="centered"
12
)
13
st.markdown("""
<h1 style='text-align:center; color:#1f6f4a; font-weight:800; margin-bottom:0.2rem;'>
MechID
16
</h1>
<h3 style='text-align:center; color:#155239; margin-top:0;'>
Mechanism-Based Interpretation of Antibiograms
19
</h3>
<p style='text-align:center; color:#3f5649; font-size:0.9rem;'>
From MIC patterns to likely resistance mechanisms and practical therapy notes.<br>
22
Heuristic output — always confirm with your microbiology lab, ID consult, and IDSA/CLSI guidance.
23
</p>
24
""", unsafe_allow_html=True)
25

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

84

85
# ======================
86
# Fancy Divider and helpers
87
# ======================
88
def fancy_divider():
89
    st.markdown("""
90
    <hr style="
91
        border:0;
92
        height:2px;
93
        margin:1.5rem 0 1rem 0;
        background: linear-gradient(to right, #1f6f4a, #155239, #4d8f6f);
    ">
96
    """, unsafe_allow_html=True)
97

98

99
def render_section_header(title):
100
    st.markdown(
101
        f"<h2 style='text-align:center; font-weight:800; "
102
        "background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f); "
103
        "-webkit-background-clip: text; -webkit-text-fill-color: transparent;'>"
104
        f"{title}</h2>",
105
        unsafe_allow_html=True,
106
    )
107

def badge(text, bg="#1f6f4a", fg="#ffffff"):
    html = f"""
110
    <span style="
111
        display:inline-block;
112
        padding:0.12rem 0.45rem;
113
        border-radius:999px;
114
        font-size:0.7rem;
115
        font-weight:600;
116
        letter-spacing:0.03em;
117
        background:{bg};
118
        color:{fg};
119
        margin-right:0.4rem;
120
        text-transform:uppercase;
121
    ">{text}</span>
122
    """
123
    return html
124

125

126
# ======================
127
# Reference mapping (auto-detected from mechanism text)
128
# ======================
129
MECH_REF_MAP = {
130
    "esbl": [
131
        "IDSA Guidance for ESBL-producing Enterobacterales (latest).",
132
        "Paterson DL, Bonomo RA. Extended-Spectrum β-Lactamases: a clinical update. Clin Microbiol Rev."
133
    ],
2025 unmodified lines
2159
TX_REGISTRY = {
2160
    org: cfg["therapy"]
2161
    for org, cfg in ORGANISM_REGISTRY.items()
2162
    if "therapy" in cfg
2163
}
2164

2165

2166
# ======================
2167
# Adapter layer for UI
2168
# ======================
2169
def run_mechanisms_and_therapy_for(org, final_results):
2170
    """
2171
    Returns:
2172
      mechs, banners, greens, therapy_notes
2173
    """
2174
    entry = ORGANISM_REGISTRY.get(org)
2175
    if not entry:
2176
        return [], [], [], []
2177
    mechs, banners, greens = entry["mechanisms"](final_results)
2178
    therapy = entry["therapy"](final_results)
2179
    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens), _dedup_list(therapy)
2180

2181
# ======================
2182
# UI: Title + group selector
2183
# ======================
st.markdown("""
<h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
Select Pathogen Group
</h2>
""", unsafe_allow_html=True)
st.caption("Enter results only for antibiotics **actually tested** for the chosen organism. Non-tested agents are hidden.")
2186

2187
group_options = ["Gram-negatives", "Staphylococci", "Enterococcus", "Streptococcus", "Anaerobes"]
2188
group = st.selectbox("Pathogen group", group_options, index=0, key="pathogen_group")
2189

2190
# ======================
2191
# Gram-negatives UI (uses registry)
2192
# ======================
2193
if group == "Gram-negatives":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Gram Negatives
    </h2>
    """, unsafe_allow_html=True)

2196
    organisms = sorted(GNR_CANON)
2197
    organism = st.selectbox("Organism", organisms, key="gnr_org")
2198

2199
    panel = PANEL.get(organism, [])
2200
    rules = RULES.get(organism, {"intrinsic_resistance": [], "cascade": []})
2201

    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Susceptibility Inputs
    </h2>
    """, unsafe_allow_html=True)
    st.caption("Leave blank for untested/unknown.")
2204

2205
    user = {}
2206
    choices = ["", "Susceptible", "Intermediate", "Resistant"]
2207
    intrinsic = rules.get("intrinsic_resistance", [])
2208
    for i, ab in enumerate(panel):
2209
        if ab in intrinsic:
2210
            _ = st.selectbox(
2211
                ab + " (intrinsic)", choices, index=3, key=f"ab_{organism}_{i}", disabled=True,
2212
                help="Intrinsic resistance by rule for this organism"
2213
            )
2214
            user[ab] = None
2215
        else:
2216
            val = st.selectbox(ab, choices, index=0, key=f"ab_{organism}_{i}")
2217
            user[ab] = val if val else None
2218

2219
    if intrinsic:
2220
        st.info("**Intrinsic resistance to:** " + ", ".join(intrinsic))
2221

2222
    # Apply cascade rules
2223
    inferred = apply_cascade(rules, user)
2224

2225
    # Final result map (user + inferred + intrinsic)
2226
    from collections import defaultdict
2227
    final = defaultdict(lambda: None)
2228
    for k, v in {**inferred, **user}.items():
2229
        final[k] = v
2230
    for ab in intrinsic:
2231
        final[ab] = "Resistant"
2232

2233
    st.subheader("Consolidated results")
2234
    rows = []
2235
    for ab in panel:
2236
        if final[ab] is None:
2237
            continue
2238
        src = "User-entered"
2239
        if ab in intrinsic:
2240
            src = "Intrinsic rule"
2241
        elif ab in inferred and (ab not in user or user[ab] is None):
2242
            src = "Cascade rule"
2243
        rows.append({"Antibiotic": ab, "Result": final[ab], "Source": src})
2244
    if rows:
2245
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
2246
    else:
2247
        st.write("No results yet. Enter at least one result above.")
2248

2249
    # ===== Mechanisms + Therapy via registry =====
2250
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Mechanism of Resistance
    </h2>
    """, unsafe_allow_html=True)
    mechs, banners, greens, gnotes = run_mechanisms_and_therapy_for(organism, final)
2253

2254
    if mechs:
2255
        for m in mechs:
2256
            st.markdown(f"""
2257
            <div style="border-left:4px solid #c62828; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#ffebee;">
2258
            {badge("Mechanism", bg="#c62828")} {m}
2259
             </div>
2260
            """, unsafe_allow_html=True)
2261

2262
    else:
2263
        st.success("No major resistance mechanism identified based on current inputs.")
2264

2265
    if banners:
2266
        for b in banners:
2267
            st.markdown(f"""
2268
            <div style="border-left:4px solid #f9a825; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#fffde7;">
2269
            {badge("Caution", bg="#f9a825", fg="#000000")} {b}
2270
            </div>
2271
            """, unsafe_allow_html=True)
2272

2273
    if greens:
2274
        for g in greens:
2275
            st.markdown(f"""
2276
            <div style="border-left:4px solid #2e7d32; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e8f5e9;">
2277
            {badge("Favorable", bg="#2e7d32")} {g}
2278
            </div>
2279
            """, unsafe_allow_html=True)
2280

2281

2282
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Therapy Guidance
    </h2>
    """, unsafe_allow_html=True)
    if gnotes:
2285
        for note in gnotes:
2286
            st.markdown(f"""
2287
            <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
2288
            {badge("Therapy", bg="#00838f")} {note}
2289
            </div>
2290
            """, unsafe_allow_html=True)
2291

2292
    else:
2293
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")
2294

2295
    # --- References (bottom of organism output) ---
2296
    refs = _collect_mech_ref_keys(organism, mechs, banners)
2297
    if refs:
2298
     fancy_divider()
2299
     st.subheader("📚 References")
2300
     for r in refs:
2301
        st.markdown(f"- {r}")
2302

2303
# ======================
2304
# Enterococcus module (uses registry)
2305
# ======================
2306
if group == "Enterococcus":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Enterococcus
    </h2>
    """, unsafe_allow_html=True)
    ENTERO_ORGS = ["Enterococcus faecalis", "Enterococcus faecium"]
2309
    organism_e = st.selectbox("Organism (Enterococcus)", ENTERO_ORGS, key="enterococcus_org")
2310

2311
    PANEL_E = [
2312
        "Penicillin", "Ampicillin",
2313
        "Vancomycin",
2314
        "Linezolid", "Daptomycin",
2315
        "High-level Gentamicin", "High-level Streptomycin",
2316
        "Ciprofloxacin",
2317
        "Nitrofurantoin",
2318
        "Ceftriaxone", "Cefepime"
2319
    ]
2320

2321
    # Intrinsic map
2322
    intrinsic_e = {ab: False for ab in PANEL_E}
2323
    for ab in ["Ceftriaxone", "Cefepime"]:
2324
        intrinsic_e[ab] = True
2325
    if organism_e == "Enterococcus faecium":
2326
        intrinsic_e["Ampicillin"] = True
2327
        intrinsic_e["Penicillin"] = True
2328

    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Susceptibility Inputs
    </h2>
    """, unsafe_allow_html=True)
    st.caption("Leave blank for untested/unknown.")
2331
    user_e, final_e = _collect_panel_inputs(PANEL_E, intrinsic_e, keyprefix="E_ab")
2332

2333
    st.subheader("Consolidated results")
2334
    rows_e = []
2335
    for ab in PANEL_E:
2336
        if final_e[ab] is None:
2337
            continue
2338
        src = "User-entered"
2339
        if intrinsic_e.get(ab):
2340
            src = "Intrinsic rule"
2341
        rows_e.append({"Antibiotic": ab, "Result": final_e[ab], "Source": src})
2342
    if rows_e:
2343
        st.dataframe(pd.DataFrame(rows_e), use_container_width=True)
2344

2345
    # ===== Mechanisms + Therapy via registry =====
2346
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Mechanism of Resistance
    </h2>
    """, unsafe_allow_html=True)
    mechs_e, banners_e, greens_e, gnotes_e = run_mechanisms_and_therapy_for(organism_e, final_e)
2349

2350
    if mechs_e:
2351
        for m in mechs_e:
2352
            st.markdown(f"""
2353
            <div style="border-left:4px solid #c62828; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#ffebee;">
2354
                {badge("Mechanism", bg="#c62828")} {m}
2355
            </div>
2356
            """, unsafe_allow_html=True)
2357
    else:
2358
        st.success("No major resistance mechanism identified based on current inputs.")
2359

2360
    for b in banners_e:
2361
        st.markdown(f"""
2362
        <div style="border-left:4px solid #f9a825; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#fffde7;">
2363
            {badge("Caution", bg="#f9a825", fg="#000000")} {b}
2364
        </div>
2365
        """, unsafe_allow_html=True)
2366

2367
    for g in greens_e:
2368
        st.markdown(f"""
2369
        <div style="border-left:4px solid #2e7d32; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e8f5e9;">
2370
            {badge("Favorable", bg="#2e7d32")} {g}
2371
        </div>
2372
        """, unsafe_allow_html=True)
2373

2374
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Therapy Guidance
    </h2>
    """, unsafe_allow_html=True)
    if gnotes_e:
2377
        for note in gnotes_e:
2378
            st.markdown(f"""
2379
            <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
2380
                {badge("Therapy", bg="#00838f")} {note}
2381
            </div>
2382
            """, unsafe_allow_html=True)
2383
    else:
2384
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")
2385

2386
    # --- References (bottom of organism output) ---
2387
    refs_e = _collect_mech_ref_keys(organism_e, mechs_e, banners_e)
2388
    if refs_e:
2389
        fancy_divider()
2390
        st.subheader("📚 References")
2391
        for r in refs_e:
2392
            st.markdown(f"- {r}")
2393

2394
    st.stop()
2395

2396
# ======================
2397
# Staphylococci module
2398
# ======================
2399
if group == "Staphylococci":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Staphylococci
    </h2>
    """, unsafe_allow_html=True)

2402
    STAPH_ORGS = [
2403
        "Staphylococcus aureus",
2404
        "Coagulase-negative Staphylococcus",
2405
        "Staphylococcus lugdunensis",
2406
    ]
2407
    organism_st = st.selectbox("Organism (Staphylococcus)", STAPH_ORGS, key="staph_org")
2408

2409
    PANEL_ST = [
2410
        "Penicillin",
2411
        "Nafcillin/Oxacillin",
2412
        "Vancomycin",
2413
        "Erythromycin",
2414
        "Clindamycin",
2415
        "Gentamicin",
2416
        "Trimethoprim/Sulfamethoxazole",
2417
        "Moxifloxacin",
2418
        "Tetracycline/Doxycycline",
2419
        "Linezolid",
2420
    ]
2421
    intrinsic_st = {ab: False for ab in PANEL_ST}  # no forced intrinsic R here
2422

2423
    # Inputs
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Susceptibility Inputs
    </h2>
    """, unsafe_allow_html=True)
    st.caption("Leave blank for untested/unknown.")
2426
    user_st, final_st = _collect_panel_inputs(PANEL_ST, intrinsic_st, keyprefix="STAPH_ab")
2427

2428
    # Consolidated results
2429
    st.subheader("Consolidated results")
2430
    rows_st = []
2431
    for ab in PANEL_ST:
2432
        if final_st[ab] is None:
2433
            continue
2434
        rows_st.append({"Antibiotic": ab, "Result": final_st[ab], "Source": "User-entered"})
2435
    if rows_st:
2436
        st.dataframe(pd.DataFrame(rows_st), use_container_width=True)
2437

2438
    # Mechanisms / banners / greens via registry
2439
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Mechanism of Resistance
    </h2>
    """, unsafe_allow_html=True)
    # ---- Mechanisms & guidance via registry ----
2442
    mechs_st, banners_st, greens_st = [], [], []
2443

2444
    mech_fn = MECH_REGISTRY.get(organism_st)
2445
    if mech_fn is not None:
2446
        mechs_st, banners_st, greens_st = mech_fn(final_st)
2447

2448
    if mechs_st:
2449
        for m in mechs_st:
2450
            st.error(f"• {m}")
2451
    else:
2452
        st.success("No major resistance mechanism identified based on current inputs.")
2453
    for b in banners_st:
2454
        st.warning(b)
2455
    for g in greens_st:
2456
        st.success(g)
2457

2458
    # Therapy guidance
2459
    fancy_divider()
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Therapy Guidance
    </h2>
    """, unsafe_allow_html=True)

2462
    tx_fn = TX_REGISTRY.get(organism_st)
2463
    if tx_fn is not None:
2464
        gnotes_st = tx_fn(final_st)
2465
    else:
2466
        gnotes_st = []
2467

2468
    if gnotes_st:
2469
        for note in gnotes_st:
2470
            st.markdown(f"""
2471
            <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
2472
            {badge("Therapy", bg="#00838f")} {note}
2473
            </div>
2474
            """, unsafe_allow_html=True)
2475
    else:
2476
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")
2477

2478

2479
    # References at the bottom
2480
    refs_st = _collect_mech_ref_keys(organism_st, mechs_st, banners_st)
2481
    if refs_st:
2482
        fancy_divider()
2483
        st.subheader("📚 References")
2484
        for r in refs_st:
2485
            st.markdown(f"- {r}")
2486

2487
    st.stop()
2488

2489
# ======================
2490
# Streptococcus module (uses registry)
2491
# ======================
2492
if group == "Streptococcus":
    st.markdown("""
    <h2 style='text-align:center;
    font-weight:800;
    background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;'>
    Streptococcus
    </h2>
    """, unsafe_allow_html=True)
    STREP_GROUP = st.selectbox(
2495
        "Strep group",
2496
        ["Streptococcus pneumoniae", "β-hemolytic Streptococcus (GAS/GBS)", "Viridans group streptococci (VGS)"],
2497
        key="strep_group"
2498
    )
2499

2500
    if STREP_GROUP == "Streptococcus pneumoniae":
2501
        PANEL_SPN = [
2502
            "Penicillin", "Ceftriaxone", "Cefotaxime",
2503
            "Erythromycin", "Clindamycin",
2504
            "Levofloxacin",
2505
            "Vancomycin"
2506
        ]
2507
        intrinsic_spn = {ab: False for ab in PANEL_SPN}
2508

        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Susceptibility Inputs
        </h2>
        """, unsafe_allow_html=True)
        st.caption("Leave blank for untested/unknown.")
2511
        user_s, final_s = _collect_panel_inputs(PANEL_SPN, intrinsic_spn, keyprefix="SPN_ab")
2512

2513
        st.subheader("Consolidated results")
2514
        rows_s = []
2515
        for ab in PANEL_SPN:
2516
            if final_s[ab] is None:
2517
                continue
2518
            rows_s.append({"Antibiotic": ab, "Result": final_s[ab], "Source": "User-entered"})
2519
        if rows_s:
2520
            st.dataframe(pd.DataFrame(rows_s), use_container_width=True)
2521

2522
        # ===== Mechanisms + Therapy via registry =====
2523
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Mechanism of Resistance
        </h2>
        """, unsafe_allow_html=True)
        mechs_s, banners_s, greens_s, gnotes_s = run_mechanisms_and_therapy_for("Streptococcus pneumoniae", final_s)
2526

2527
        if mechs_s:
2528
            for m in mechs_s:
2529
                st.error(f"• {m}")
2530
        else:
2531
            st.success("No major resistance mechanism identified based on current inputs.")
2532
        for b in banners_s:
2533
            st.warning(b)
2534
        for g in greens_s:
2535
            st.success(g)
2536

2537
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Therapy Guidance
        </h2>
        """, unsafe_allow_html=True)
        if gnotes_s:
2540
            for note in gnotes_s:
2541
                st.markdown(f"""
2542
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
2543
                {badge("Therapy", bg="#00838f")} {note}
2544
                </div>
2545
                """, unsafe_allow_html=True)
2546

2547
        else:
2548
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")
2549

2550
        
2551
        # --- References (bottom of organism output) ---
2552
        refs_s = _collect_mech_ref_keys("Streptococcus pneumoniae", mechs_s, banners_s)
2553
        if refs_s:
2554
         fancy_divider()
2555
         st.subheader("📚 References")
2556
         for r in refs_s:
2557
           st.markdown(f"- {r}")
2558

2559
        st.stop()
2560

2561
    elif STREP_GROUP == "β-hemolytic Streptococcus (GAS/GBS)":
2562
        PANEL_BHS = [
2563
            "Penicillin",
2564
            "Erythromycin", "Clindamycin",
2565
            "Levofloxacin",
2566
            "Vancomycin"
2567
        ]
2568
        intrinsic_bhs = {ab: False for ab in PANEL_BHS}
2569

        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Susceptibility Inputs
        </h2>
        """, unsafe_allow_html=True)
        st.caption("Leave blank for untested/unknown.")
2572
        user_b, final_b = _collect_panel_inputs(PANEL_BHS, intrinsic_bhs, keyprefix="BHS_ab")
2573

2574
        st.subheader("Consolidated results")
2575
        rows_b = []
2576
        for ab in PANEL_BHS:
2577
            if final_b[ab] is None:
2578
                continue
2579
            rows_b.append({"Antibiotic": ab, "Result": final_b[ab], "Source": "User-entered"})
2580
        if rows_b:
2581
            st.dataframe(pd.DataFrame(rows_b), use_container_width=True)
2582

2583
        # ===== Mechanisms + Therapy via registry =====
2584
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Mechanism of Resistance
        </h2>
        """, unsafe_allow_html=True)
        mechs_b, banners_b, greens_b, gnotes_b = run_mechanisms_and_therapy_for("β-hemolytic Streptococcus (GAS/GBS)", final_b)
2587

2588
        if mechs_b:
2589
            for m in mechs_b:
2590
                st.error(f"• {m}")
2591
        else:
2592
            st.success("No major resistance mechanism identified based on current inputs.")
2593
        for b in banners_b:
2594
            st.warning(b)
2595
        for g in greens_b:
2596
            st.success(g)
2597

2598
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Therapy Guidance
        </h2>
        """, unsafe_allow_html=True)
        if gnotes_b:
2601
            for note in gnotes_b:
2602
                st.markdown(f"""
2603
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
2604
                {badge("Therapy", bg="#00838f")} {note}
2605
                </div>
2606
                """, unsafe_allow_html=True)
2607

2608
        else:
2609
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")
2610

2611
        st.stop()
2612

2613
    elif STREP_GROUP == "Viridans group streptococci (VGS)":
2614
        PANEL_VGS = [
2615
            "Penicillin", "Ceftriaxone",
2616
            "Erythromycin", "Clindamycin",
2617
            "Levofloxacin",
2618
            "Vancomycin"
2619
        ]
2620
        intrinsic_vgs = {ab: False for ab in PANEL_VGS}
2621

        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Susceptibility Inputs
        </h2>
        """, unsafe_allow_html=True)
        st.caption("Leave blank for untested/unknown.")
2624
        user_v, final_v = _collect_panel_inputs(PANEL_VGS, intrinsic_vgs, keyprefix="VGS_ab")
2625

2626
        st.subheader("Consolidated results")
2627
        rows_v = []
2628
        for ab in PANEL_VGS:
2629
            if final_v[ab] is None:
2630
                continue
2631
            rows_v.append({"Antibiotic": ab, "Result": final_v[ab], "Source": "User-entered"})
2632
        if rows_v:
2633
            st.dataframe(pd.DataFrame(rows_v), use_container_width=True)
2634

2635
        # ===== Mechanisms + Therapy via registry =====
2636
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Mechanism of Resistance
        </h2>
        """, unsafe_allow_html=True)
        mechs_v, banners_v, greens_v, gnotes_v = run_mechanisms_and_therapy_for("Viridans group streptococci (VGS)", final_v)
2639

2640
        if mechs_v:
2641
            for m in mechs_v:
2642
                st.error(f"• {m}")
2643
        else:
2644
            st.success("No major resistance mechanism identified based on current inputs.")
2645
        for b in banners_v:
2646
            st.warning(b)
2647
        for g in greens_v:
2648
            st.success(g)
2649

2650
        fancy_divider()
        st.markdown("""
        <h2 style='text-align:center;
        font-weight:800;
        background: -webkit-linear-gradient(45deg, #1f6f4a, #155239, #4d8f6f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;'>
        Therapy Guidance
        </h2>
        """, unsafe_allow_html=True)
        if gnotes_v:
2653
            for note in gnotes_v:
2654
                st.markdown(f"""
2655
                <div style="border-left:4px solid #00838f; padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:#e0f7fa;">
2656
                {badge("Therapy", bg="#00838f")} {note}
2657
                </div>
2658
                """, unsafe_allow_html=True)
2659

2660
        else:
2661
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")
2662

2663
        st.stop()
2664

2665
fancy_divider()
2666
st.markdown("""
2667
<p style="text-align:center; font-size:0.8rem; color:#90a4ae;">
2668
<strong>MechID</strong> is a heuristic teaching tool for pattern recognition in antimicrobial resistance.<br>
2669
Always interpret results in context of patient, local epidemiology, and formal guidance (IDSA, CLSI, EUCAST).<br>
2670
© MechID · (ID)as &amp; O(ID)nions
2671
</p>
2672
""", unsafe_allow_html=True)
