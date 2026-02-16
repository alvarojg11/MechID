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
<h1 style='text-align:center; font-size:3rem; letter-spacing:-0.02em; margin-bottom:0.2rem;'>
<span style='font-weight:800; color:var(--foreground);'>Mech</span><span style='font-weight:600; color:#0f1a13cc;'>ID</span>
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

def section_header(text):
    st.markdown(
        f"""
        <h2 style='text-align:center; font-weight:800; color:#0f1a13cc; margin:0.25rem 0 0.5rem 0;'>
        {text}
        </h2>
        """,
        unsafe_allow_html=True,
    )

def render_references(refs):
    if not refs:
        return
    fancy_divider()
    st.subheader("References")
    st.markdown("\n".join(f"{idx}. {ref}" for idx, ref in enumerate(refs, start=1)))


# ======================
# Reference mapping (auto-detected from mechanism text, Vancouver style)
# ======================
REF_CITATIONS = {
    "clsi_m100_2026": "Clinical and Laboratory Standards Institute. Performance Standards for Antimicrobial Susceptibility Testing. 36th ed. CLSI supplement M100. Wayne (PA): CLSI; 2026.",
    "clsi_m11_2018": "Clinical and Laboratory Standards Institute. Methods for Antimicrobial Susceptibility Testing of Anaerobic Bacteria. 9th ed. CLSI standard M11. Wayne (PA): CLSI; 2018 (reaffirmed 2025).",
    "idsa_amr_2024": "Tamma PD, Heil EL, Justo JA, Mathers AJ, Satlin MJ, Bonomo RA. Infectious Diseases Society of America 2024 Guidance on the Treatment of Antimicrobial-Resistant Gram-Negative Infections. Clin Infect Dis. 2024;ciae403. doi:10.1093/cid/ciae403.",
    "paterson_esbl_2005": "Paterson DL, Bonomo RA. Extended-spectrum beta-lactamases: a clinical update. Clin Microbiol Rev. 2005;18(4):657-686. doi:10.1128/CMR.18.4.657-686.2005.",
    "jacoby_ampc_2009": "Jacoby GA. AmpC beta-lactamases. Clin Microbiol Rev. 2009;22(1):161-182. doi:10.1128/CMR.00036-08.",
    "logan_cre_2017": "Logan LK, Weinstein RA. The epidemiology of carbapenem-resistant Enterobacteriaceae: the impact and evolution of a global menace. J Infect Dis. 2017;215(suppl_1):S28-S36. doi:10.1093/infdis/jiw282.",
    "queenan_sme_2000": "Queenan AM, Torres-Viera C, Gold HS, et al. SME-type carbapenem-hydrolyzing class A beta-lactamases from geographically diverse Serratia marcescens strains. Antimicrob Agents Chemother. 2000;44(11):3035-3039. doi:10.1128/AAC.44.11.3035-3039.2000.",
    "poole_pa_2011": "Poole K. Pseudomonas aeruginosa: resistance to the max. Front Microbiol. 2011;2:65. doi:10.3389/fmicb.2011.00065.",
    "lister_pa_2009": "Lister PD, Wolter DJ, Hanson ND. Antibacterial-resistant Pseudomonas aeruginosa: clinical impact and complex regulation of chromosomally encoded resistance mechanisms. Clin Microbiol Rev. 2009;22(4):582-610. doi:10.1128/CMR.00040-09.",
    "ramirez_ame_2010": "Ramirez MS, Tolmasky ME. Aminoglycoside modifying enzymes. Drug Resist Updat. 2010;13(6):151-171. doi:10.1016/j.drup.2010.08.003.",
    "hooper_fq_2015": "Hooper DC, Jacoby GA. Mechanisms of drug resistance: quinolone resistance. Ann N Y Acad Sci. 2015;1354(1):12-31. doi:10.1111/nyas.12830.",
    "skold_tmp_sul_2001": "Skold O. Resistance to trimethoprim and sulfonamides. Vet Res. 2001;32(3-4):261-273. doi:10.1051/vetres:2001123.",
    "chambers_mrsa_2009": "Chambers HF, DeLeo FR. Waves of resistance: Staphylococcus aureus in the antibiotic era. Nat Rev Microbiol. 2009;7(9):629-641. doi:10.1038/nrmicro2200.",
    "liu_mrsa_2011": "Liu C, Bayer A, Cosgrove SE, et al. Clinical practice guidelines by the Infectious Diseases Society of America for the treatment of methicillin-resistant Staphylococcus aureus infections in adults and children. Clin Infect Dis. 2011;52(3):e18-e55. doi:10.1093/cid/ciq146.",
    "leclercq_mls_2002": "Leclercq R. Mechanisms of resistance to macrolides and lincosamides: nature of the resistance elements and their clinical implications. Clin Infect Dis. 2002;34(4):482-492. doi:10.1086/324626.",
    "howden_visa_2010": "Howden BP, Davies JK, Johnson PDR, Stinear TP, Grayson ML. Reduced vancomycin susceptibility in Staphylococcus aureus, including VISA and hVISA: resistance mechanisms, laboratory detection, and clinical implications. Clin Microbiol Rev. 2010;23(1):99-139. doi:10.1128/CMR.00042-09.",
    "arias_enterococcus_2012": "Arias CA, Murray BE. The rise of the Enterococcus: beyond vancomycin resistance. Nat Rev Microbiol. 2012;10(4):266-278. doi:10.1038/nrmicro2761.",
    "munita_liafsr_2012": "Munita JM, Panesso D, Diaz L, et al. Correlation between mutations in liaFSR of Enterococcus faecium and MIC of daptomycin: revisiting daptomycin breakpoints. Antimicrob Agents Chemother. 2012;56(8):4354-4359. doi:10.1128/AAC.00509-12.",
    "wang_optra_2015": "Wang Y, Lv Y, Cai J, et al. A novel gene, optrA, that confers transferable resistance to oxazolidinones and phenicols and its presence in Enterococcus faecalis and Enterococcus faecium of human and animal origin. J Antimicrob Chemother. 2015;70(8):2182-2190. doi:10.1093/jac/dkv116.",
    "antonelli_poxta_2018": "Antonelli A, D'Andrea MM, Brenciani A, et al. Characterization of poxtA, a novel phenicol-oxazolidinone-tetracycline resistance gene from an MRSA of clinical origin. J Antimicrob Chemother. 2018;73(7):1763-1769. doi:10.1093/jac/dky088.",
    "peleg_acinetobacter_2008": "Peleg AY, Seifert H, Paterson DL. Acinetobacter baumannii: emergence of a successful pathogen. Clin Microbiol Rev. 2008;21(3):538-582. doi:10.1128/CMR.00058-07.",
    "brooke_steno_2012": "Brooke JS. Stenotrophomonas maltophilia: an emerging global opportunistic pathogen. Clin Microbiol Rev. 2012;25(1):2-41. doi:10.1128/CMR.00019-11.",
    "isler_achromobacter_2020": "Isler B, Kidd TJ, Stewart aminoglycoside, Harris P, Paterson DL. Achromobacter infections and treatment options. Antimicrob Agents Chemother. 2020;64(11):e01025-20. doi:10.1128/AAC.01025-20.",
    "hakenbeck_spn_2012": "Hakenbeck R, Bruckner R, Denapaite D, Maurer P. Molecular mechanisms of beta-lactam resistance in Streptococcus pneumoniae. Future Microbiol. 2012;7(3):395-410. doi:10.2217/fmb.12.2.",
    "wexler_bacteroides_2007": "Wexler HM. Bacteroides: the good, the bad, and the nitty-gritty. Clin Microbiol Rev. 2007;20(4):593-621. doi:10.1128/CMR.00008-07.",
    "jha_bfrag_2023": "Jha L, Lal YB, Ragupathi NKD, Veeraraghavan B, Prakash JAJ. Phenotypic and Genotypic Correlation of Antimicrobial Susceptibility of Bacteroides fragilis: Lessons Learnt. Cureus. 2023;15(3):e36268. doi:10.7759/cureus.36268.",
    "kato_cfia_2003": "Kato N, Yamazoe K, Han CG, Ohtsubo E. New insertion sequence elements in the upstream region of cfiA in imipenem-resistant Bacteroides fragilis strains. Antimicrob Agents Chemother. 2003;47(3):979-985. doi:10.1128/AAC.47.3.979-985.2003.",
    "cooley_anaerobes_2019": "Cooley L, Teng J. Anaerobic resistance: should we be worried? Curr Opin Infect Dis. 2019;32(6):523-530. doi:10.1097/QCO.0000000000000595.",
    "steininger_actinomyces_2016": "Steininger C, Willinger B. Resistance patterns in clinical isolates of pathogenic Actinomyces species. J Antimicrob Chemother. 2016;71(2):422-427. doi:10.1093/jac/dkv347.",
    "zhang_cutibacterium_2019": "Zhang N, Yuan R, Xin KZ, Lu Z, Ma Y. Antimicrobial Susceptibility, Biotypes and Phylotypes of Clinical Cutibacterium (Formerly Propionibacterium) acnes Strains Isolated from Acne Patients: An Observational Study. Dermatol Ther (Heidelb). 2019;9(4):735-746. doi:10.1007/s13555-019-00320-7.",
    "moubareck_bifidobacteria_2005": "Moubareck C, Gavini F, Vaugien L, Butel MJ, Doucet-Populaire F. Antimicrobial susceptibility of bifidobacteria. J Antimicrob Chemother. 2005;55(1):38-44. doi:10.1093/jac/dkh495.",
    "chow_metronidazole_1975": "Chow AW, Patten V, Guze LB. Susceptibility of Anaerobic Bacteria to Metronidazole: Relative Resistance of Non-Spore-Forming Gram-Positive Bacilli. J Infect Dis. 1975;131(2):182-185. doi:10.1093/infdis/131.2.182.",
    "stevens_ssti_2014": "Stevens DL, Bisno AL, Chambers HF, Dellinger EP, Goldstein EJC, Gorbach SL, Hirschmann JV, Kaplan SL, Montoya JG, Wade JC. Practice Guidelines for the Diagnosis and Management of Skin and Soft Tissue Infections: 2014 Update by the Infectious Diseases Society of America. Clin Infect Dis. 2014;59(2):e10-e52. doi:10.1093/cid/ciu296.",
    "nahid_tb_2016": "Nahid P, Dorman SE, Alipanah N, et al. Official American Thoracic Society/Centers for Disease Control and Prevention/Infectious Diseases Society of America Clinical Practice Guidelines: Treatment of Drug-Susceptible Tuberculosis. Clin Infect Dis. 2016;63(7):e147-e195. doi:10.1093/cid/ciw376.",
    "miotto_tb_mut_2017": "Miotto P, Tessema B, Tagliani E, et al. A standardised method for interpreting the association between mutations and phenotypic drug resistance in Mycobacterium tuberculosis. Eur Respir J. 2017;50(6):1701354. doi:10.1183/13993003.01354-2017.",
    "daley_ntm_2020": "Daley CL, Iaccarino JM, Lange C, et al. Treatment of Nontuberculous Mycobacterial Pulmonary Disease: An Official ATS/ERS/ESCMID/IDSA Clinical Practice Guideline. Clin Infect Dis. 2020;71(4):e1-e36. doi:10.1093/cid/ciaa1125.",
    "nash_erm41_2009": "Nash KA, Brown-Elliott BA, Wallace RJ Jr. A novel gene, erm(41), confers inducible macrolide resistance to clinical isolates of Mycobacterium abscessus but is absent from Mycobacterium chelonae. Antimicrob Agents Chemother. 2009;53(4):1367-1376. doi:10.1128/AAC.01275-08.",
}

MECH_REF_MAP = {
    "core_ast": ["clsi_m100_2026"],
    "gram_negative_guidance": ["idsa_amr_2024"],
    "esbl": ["paterson_esbl_2005"],
    "ampc": ["jacoby_ampc_2009"],
    "cre": ["logan_cre_2017"],
    "serr_sme": ["queenan_sme_2000"],
    "pseudomonas_resistance": ["poole_pa_2011", "lister_pa_2009"],
    "aminoglycoside_mod": ["ramirez_ame_2010"],
    "fq_qrdr": ["hooper_fq_2015"],
    "tmpsmx_folate": ["skold_tmp_sul_2001"],
    "staph_mrsa": ["chambers_mrsa_2009", "liu_mrsa_2011"],
    "staph_dtest": ["leclercq_mls_2002"],
    "staph_visa": ["howden_visa_2010"],
    "enterococcus_vre": ["arias_enterococcus_2012"],
    "enterococcus_advanced": ["munita_liafsr_2012", "wang_optra_2015", "antonelli_poxta_2018"],
    "acinetobacter": ["peleg_acinetobacter_2008"],
    "stenotrophomonas": ["brooke_steno_2012"],
    "achromobacter": ["isler_achromobacter_2020"],
    "streptococcus_pbp": ["hakenbeck_spn_2012", "leclercq_mls_2002"],
    "anaerobe_core": ["clsi_m11_2018", "cooley_anaerobes_2019"],
    "anaerobe_bacteroides": ["wexler_bacteroides_2007", "jha_bfrag_2023"],
    "anaerobe_cfia": ["kato_cfia_2003", "jha_bfrag_2023"],
    "anaerobe_metronidazole": ["jha_bfrag_2023", "steininger_actinomyces_2016", "zhang_cutibacterium_2019", "moubareck_bifidobacteria_2005", "chow_metronidazole_1975"],
    "anaerobe_clostridium_therapy": ["stevens_ssti_2014"],
    "myco_tb_guidance": ["nahid_tb_2016", "miotto_tb_mut_2017"],
    "myco_ntm_guidance": ["daley_ntm_2020"],
    "myco_abscessus_macrolide": ["nash_erm41_2009", "daley_ntm_2020"],
}

def _collect_mech_ref_keys(org: str, mechs: list, banners: list) -> list:
    """Map mechanism/banners text to ordered reference citations."""
    texts = " ".join((mechs or []) + (banners or [])).lower()
    org = org or ""
    org_l = org.lower()
    keys = []

    def add_key(key: str):
        if key not in keys:
            keys.append(key)

    if texts.strip():
        add_key("core_ast")
    if org in {
        "Escherichia coli", "Klebsiella pneumoniae", "Klebsiella oxytoca", "Klebsiella aerogenes",
        "Enterobacter cloacae complex", "Citrobacter freundii complex", "Citrobacter koseri",
        "Serratia marcescens", "Proteus mirabilis", "Proteus vulgaris group", "Morganella morganii",
        "Salmonella enterica", "Acinetobacter baumannii complex", "Achromobacter xylosoxidans",
        "Pseudomonas aeruginosa", "Stenotrophomonas maltophilia"
    }:
        add_key("gram_negative_guidance")

    if "esbl" in texts or "extended-spectrum" in texts or "tem-1/shv" in texts:
        add_key("esbl")
    if "ampc" in texts or "cefoxitin" in texts or "cefotetan" in texts:
        add_key("ampc")
    if "carbapenemase" in texts or "carbapenem-resistant" in texts or "carbapenem resistance" in texts or "cre" in texts:
        add_key("cre")
    if org == "Serratia marcescens" and ("sme" in texts or "carbapenem" in texts):
        add_key("serr_sme")
    if org == "Pseudomonas aeruginosa" and ("oprd" in texts or "porin" in texts or "mex" in texts or "efflux" in texts):
        add_key("pseudomonas_resistance")
    if ("aminoglycoside" in texts or "gentamicin/tobramycin" in texts or "16s rrna methylase" in texts) and (
        "enzyme" in texts or "modifying" in texts or "ame" in texts or "methylase" in texts
    ):
        add_key("aminoglycoside_mod")
    if "fluoroquinolone" in texts or "qrdr" in texts or ("gyr" in texts and "par" in texts):
        add_key("fq_qrdr")
    if "tmp-smx" in texts or "trimethoprim" in texts or "sulfamethoxazole" in texts or "dfr" in texts or "sul1" in texts or "sul2" in texts:
        add_key("tmpsmx_folate")
    if "mrsa" in texts or "meca" in texts or "mecc" in texts or "pbp2a" in texts or "methicillin-resistant" in texts:
        add_key("staph_mrsa")
    if "d-test" in texts or "d test" in texts or "mls_b" in texts or ("erythromycin" in texts and "clindamycin" in texts):
        add_key("staph_dtest")
    if "visa" in texts or "hvisa" in texts or "heteroresistance" in texts or "vancomycin intermediate" in texts:
        add_key("staph_visa")
    if org.startswith("Enterococcus") or "vre" in texts or "vana" in texts or "vanb" in texts:
        add_key("enterococcus_vre")
    if "linezolid resistance" in texts or "optra" in texts or "poxta" in texts or "daptomycin resistance" in texts or "liafsr" in texts:
        add_key("enterococcus_advanced")
    if org == "Acinetobacter baumannii complex" or "acinetobacter" in texts or "adeabc" in texts or "oxa-type" in texts:
        add_key("acinetobacter")
    if org == "Stenotrophomonas maltophilia" or "s. maltophilia" in texts or "smedef" in texts:
        add_key("stenotrophomonas")
    if org == "Achromobacter xylosoxidans" or "achromobacter" in texts:
        add_key("achromobacter")
    if "streptococcus" in org_l or "streptococci" in org_l or "pbp" in texts or "mosaic pbp" in texts:
        add_key("streptococcus_pbp")
    if any(x in org_l for x in ["anaerob", "bacteroides", "clostridium", "actinomyces", "cutibacterium", "lactobacillus", "bifidobacterium"]):
        add_key("anaerobe_core")
    if "bacteroides" in org_l or "cfxa" in texts or "cepa" in texts or "b. fragilis" in texts:
        add_key("anaerobe_bacteroides")
    if "cfia" in texts or "insertion sequence" in texts:
        add_key("anaerobe_cfia")
    if "metronidazole" in texts or "nitroimidazole" in texts or "nim" in texts:
        add_key("anaerobe_metronidazole")
    if "clostridium" in org_l or "myonecrosis" in texts or "gas gangrene" in texts:
        add_key("anaerobe_clostridium_therapy")
    if "mycobacterium tuberculosis complex" in org_l:
        add_key("myco_tb_guidance")
    if any(x in org_l for x in ["mycobacterium avium complex", "mycobacterium kansasii", "mycobacterium abscessus", "rapid-growing ntm"]):
        add_key("myco_ntm_guidance")
    if any(x in texts for x in ["rpob", "katg", "inha", "pnca", "embb", "rrs", "rrl", "gyra", "gyrb"]):
        add_key("myco_tb_guidance")
    if "erm(41)" in texts or "inducible macrolide" in texts or "mycobacterium abscessus" in org_l:
        add_key("myco_abscessus_macrolide")

    refs, seen = [], set()
    for k in keys:
        for citation_id in MECH_REF_MAP.get(k, []):
            citation = REF_CITATIONS.get(citation_id)
            if citation and citation not in seen:
                refs.append(citation)
                seen.add(citation)
    return refs

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

def _has_carbapenem_resistance(R):
    return any(_get(R, ab) == "Resistant" for ab in ["Ertapenem", "Imipenem", "Meropenem", "Doripenem"])

def render_cre_carbapenemase_module(organism, final_results):
    """Optional CRE submodule for class-specific guidance after carbapenemase testing."""
    if organism not in ENTEROBACTERALES:
        return
    if not _has_carbapenem_resistance(final_results):
        return

    fancy_divider()
    section_header("CRE Carbapenemase Module")
    st.caption(
        "For carbapenem-resistant Enterobacterales, add carbapenemase results from your microbiology lab "
        "to refine therapy options (IDSA-oriented heuristic)."
    )

    org_key = organism.lower().replace(" ", "_").replace(".", "")
    test_result = st.selectbox(
        "Carbapenemase testing result",
        ["Not tested / pending", "Negative", "Positive"],
        key=f"cre_cp_result_{org_key}",
    )

    if test_result == "Not tested / pending":
        st.info(
            "Recommended next step: request carbapenemase testing (phenotypic and/or molecular) because treatment differs by enzyme class."
        )
        return

    if test_result == "Negative":
        st.markdown(
            "- Likely non-carbapenemase CRE phenotype (often porin loss plus ESBL/AmpC interplay).\n"
            "- If **Imipenem** or **Meropenem** is still susceptible and MIC/site support use, consider optimized extended-infusion dosing.\n"
            "- If all carbapenems are non-susceptible, prioritize another confirmed active agent and involve ID early."
        )
        return

    carb_class = st.selectbox(
        "Carbapenemase class",
        ["KPC", "OXA-48-like", "NDM", "VIM", "IMP", "Other / Unknown"],
        key=f"cre_cp_class_{org_key}",
    )

    if carb_class == "KPC":
        st.markdown(
            "- Mechanism: **KPC is an Ambler class A serine carbapenemase**.\n"
            "- Inhibitor profile: usually inhibited by **Avibactam**, **Vaborbactam**, and **Relebactam**.\n"
            "- Preferred options (if susceptible): **Meropenem/Vaborbactam**, **Ceftazidime/Avibactam**, or **Imipenem/Cilastatin/Relebactam**.\n"
            "- Choose based on site, severity, renal function, and local formulary/susceptibility reporting."
        )
    elif carb_class == "OXA-48-like":
        st.markdown(
            "- Mechanism: **OXA-48-like is an Ambler class D serine carbapenemase**.\n"
            "- Inhibitor profile: usually inhibited by **Avibactam**, but **not inhibited by Vaborbactam or Relebactam**.\n"
            "- Preferred option (if susceptible): **Ceftazidime/Avibactam**.\n"
            "- Alternative option: **Cefiderocol** (if susceptible and appropriate for infection site).\n"
            "- Confirm full susceptibility panel because co-produced mechanisms can narrow active options."
        )
    elif carb_class in {"NDM", "VIM", "IMP"}:
        mbl_label = {
            "NDM": "NDM",
            "VIM": "VIM",
            "IMP": "IMP",
        }[carb_class]
        st.markdown(
            f"- Mechanism: **{mbl_label} is an Ambler class B metallo-beta-lactamase (MBL)**.\n"
            "- Inhibitor profile: **not inhibited** by **Avibactam**, **Vaborbactam**, or **Relebactam**.\n"
            "- Preferred option: **Ceftazidime/Avibactam plus Aztreonam**.\n"
            "- Alternative option: **Cefiderocol** (if susceptible and clinically appropriate).\n"
            "- Avoid relying on **Ceftazidime/Avibactam alone** for metallo-beta-lactamase producers."
        )
    else:
        st.markdown(
            "- Carbapenemase detected but class uncertain: confirm genotype/class with the lab if possible.\n"
            "- Base therapy on full susceptibility data, infection site/severity, and ID consultation.\n"
            "- If a metallo-beta-lactamase is suspected, **Ceftazidime/Avibactam plus Aztreonam** is often considered."
        )

    st.caption(
        "Heuristic output: verify against current IDSA AMR guidance, local susceptibility data, and microbiology/ID consultation."
    )

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
        mechs.append("ESBL pattern (third-generation cephalosporin resistance).")

    # Cefazolin Resistant + Ceftriaxone Susceptible with Ampicillin Resistant → TEM/SHV pattern (not ESBL)
    if not carp_R and cefazolin_R and ctx_S and amp_R and (caz not in {"Resistant", "Intermediate"}):
        banners.append("β-lactam pattern **Ampicillin Resistant + Cefazolin Resistant + Ceftriaxone Susceptible** → **broad-spectrum β-lactamase (TEM-1/SHV)**, not ESBL.")

    # Uncommon: Cefepime Resistant with Ceftriaxone Susceptible
    if not carp_R and cefepime_R and ctx_S:
        mechs.append("Uncommon: **Cefepime Resistant** with **Ceftriaxone Susceptible** — consider ESBL variant/porin–efflux/testing factors.")

    # Ertapenem Resistant with Imipenem/Meropenem Susceptible
    if _get(R, "Ertapenem") == "Resistant" and (_get(R, "Imipenem") == "Susceptible" or _get(R, "Meropenem") == "Susceptible"):
        banners.append("**Ertapenem Resistant** with **Imipenem/Meropenem Susceptible** → often ESBL or AmpC + porin loss.")

    # ---- Fluoroquinolones ----
    cip = _get(R, "Ciprofloxacin")
    lev = _get(R, "Levofloxacin")

    # Generic fluoroquinolone resistance mechanism when either fluoroquinolone is Resistant
    if cip == "Resistant" or lev == "Resistant":
        mechs.append(
            "Fluoroquinolone resistance: typically **QRDR mutations** in **gyrA/parC** ± **efflux upregulation** "
            "(AcrAB–TolC / OqxAB) and sometimes **plasmid-mediated qnr / AAC(6')-Ib-cr**."
        )

    # Special discordance — Ciprofloxacin Resistant / Levofloxacin Susceptible
    if cip == "Resistant" and lev == "Susceptible":
        mechs.append(
            "Fluoroquinolone discordance: **Ciprofloxacin Resistant** with **Levofloxacin Susceptible** — suggests **low-level, non–target-mediated resistance** "
            "such as **PMQR** (e.g., **qnr** target protection or **AAC(6')-Ib-cr** acetylation) and/or **efflux upregulation (AcrAB–TolC / OqxAB)** "
            "± porin changes. These mechanisms can **step up to high-level fluoroquinolone resistance during therapy**."
        )
        banners.append(
            "Caution using **levofloxacin** despite apparent susceptibility — PMQR/efflux phenotypes carry a **higher risk of on-therapy failure** "
            "via stepwise QRDR mutations."
        )

    # Trimethoprim/Sulfamethoxazole resistance mechanism
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Resistant":
        mechs.append(
            "Trimethoprim/Sulfamethoxazole resistance: **dfrA** (trimethoprim-resistant DHFR), **sul1/sul2** (sulfonamide-resistant DHPS), "
            "often on **class 1 integrons**; efflux and target mutation can contribute."
        )

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_ecoli(R):
    out = []

    # Fluoroquinolone Resistant but beta-lactam Susceptible → use beta-lactam
    if _any_S(R, ["Piperacillin/Tazobactam", "Ceftriaxone", "Cefepime", "Aztreonam",
                  "Imipenem", "Meropenem", "Ertapenem"]) and \
       _any_R(R, ["Ciprofloxacin", "Levofloxacin", "Moxifloxacin"]):
        out.append("**Fluoroquinolone Resistant but beta-lactam Susceptible** → prefer a **β-lactam** that is susceptible.")

    # ESBL
    if _any_R(R, THIRD_GENS) and not _any_R(R, CARBAPENEMS):
        out.append("**ESBL pattern** → use a **carbapenem** for serious infections.")

    # Ertapenem Resistant / others Susceptible
    if _get(R, "Ertapenem") == "Resistant" and (_get(R, "Imipenem") == "Susceptible" or _get(R, "Meropenem") == "Susceptible"):
        out.append("**Ertapenem Resistant / Imipenem or Meropenem Susceptible** → consider **extended-infusion meropenem**.")

    # CRE signal
    if _get(R, "Meropenem") == "Resistant" and _get(R, "Ertapenem") == "Resistant":
        out.append("**CRE phenotype** → isolate should be tested for **carbapenemase**.\n")

    # TEM/SHV broad beta-lactam pattern
    if (_get(R, "Cefazolin") == "Resistant") and (_get(R, "Ceftriaxone") == "Susceptible") and \
       (_get(R, "Ampicillin") in {"Resistant", "Intermediate"}) and (_get(R, "Ceftazidime") not in {"Resistant", "Intermediate"}):
        out.append("**TEM-1/SHV pattern** → **Ceftriaxone is preferred** when susceptible; Piperacillin/Tazobactam often active; amoxicillin clavulanate may also be considered for non-severe *E. coli*.")

    # Special fluoroquinolone discordance message (Ciprofloxacin Resistant / Levofloxacin Susceptible)
    cip = _get(R, "Ciprofloxacin")
    lev = _get(R, "Levofloxacin")
    if cip == "Resistant" and lev == "Susceptible":
        out.append(
            "**Ciprofloxacin Resistant / Levofloxacin Susceptible** → if a fluoroquinolone is considered, **levofloxacin** may be used based on susceptibility, "
            "but **failure risk is higher** with **PMQR/efflux** phenotypes. Prefer a confirmed-active **β-lactam** (or other class) "
            "for **severe/invasive** infections; reserve levofloxacin for **low-risk sites** with close follow-up."
        )

    # Generic: avoid fluoroquinolones when all tested fluoroquinolones are Resistant
    if _any_R(R, ["Ciprofloxacin", "Levofloxacin", "Moxifloxacin"]) and \
       not _any_S(R, ["Ciprofloxacin", "Levofloxacin", "Moxifloxacin"]):
        out.append(
            "**All tested fluoroquinolones are resistant** → avoid fluoroquinolones; choose a non-fluoroquinolone agent that is susceptible."
        )

    # Trimethoprim/Sulfamethoxazole susceptible → oral step-down option
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Susceptible":
        out.append(
            "**Trimethoprim/Sulfamethoxazole susceptible** → reasonable **oral step-down** option in selected scenarios "
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
            "Interpret third-generation cephalosporins carefully in serious infections."
        )

    # ---- ESBL pattern (not the main baseline issue for Serratia, but can happen) ----
    if third_R and not carp_R:
        mechs.append("third-generation cephalosporin resistance pattern — consider **ESBL** and/or **AmpC derepression**; confirm per lab policy.")

    # ---- Carbapenem resistance: include SME/chromosomal possibility + preserved cephalosporins ----
    if carp_R:
        mechs.append(
            "Carbapenem resistance in *Serratia*: evaluate for **carbapenemase**. "
            "This can be due to **chromosomal SME-type carbapenemase**, or acquired enzymes (e.g., **KPC**) depending on epidemiology."
        )

        # Key phenotype you asked for: carbapenem Resistant but some cephalosporins still Susceptible
        if ctx_S or fep_S or caz_S:
            banners.append(
                "Carbapenem Resistant with **some cephalosporins still susceptible** can occur in *Serratia* "
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

    # ---- Ertapenem Resistant with Imipenem/Meropenem Susceptible pattern (less common in Serratia than Enterobacterales generally, but keep if you like) ----
    if ept == "Resistant" and (imi == "Susceptible" or mero == "Susceptible"):
        banners.append(
            "**Ertapenem Resistant** with **Imipenem/Meropenem Susceptible** → can reflect **β-lactamase + permeability changes**; "
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
            "Fluoroquinolone discordance (**Ciprofloxacin Resistant / Levofloxacin Susceptible**) suggests **low-level non-target mechanisms** "
            "(e.g., **PMQR** such as **qnr** or **AAC(6')-Ib-cr**) and/or **efflux**. "
            "These can **step up during therapy** with additional QRDR mutations."
        )
        banners.append(
            "Use **levofloxacin** cautiously despite Susceptible — higher risk of **on-therapy failure** with PMQR/efflux phenotypes, "
            "especially for invasive disease."
        )

    # ---- Trimethoprim/Sulfamethoxazole ----
    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Resistant":
        mechs.append(
            "Trimethoprim/Sulfamethoxazole resistance: **dfrA** (DHFR) and/or **sul1/sul2** (DHPS), often on **class 1 integrons**."
        )
    elif tmpsmx == "Susceptible":
        greens.append("Trimethoprim/Sulfamethoxazole is **susceptible** — may be an oral option depending on site/severity.")

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

    # Prefer β-lactam when fluoroquinolone resistant and beta-lactam susceptible
    if _any_S(R, ["Ceftriaxone","Cefepime","Ceftazidime","Piperacillin/Tazobactam","Aztreonam","Imipenem","Meropenem","Ertapenem"]) and \
       _any_R(R, ["Ciprofloxacin","Levofloxacin","Moxifloxacin"]):
        out.append("**Fluoroquinolone Resistant but beta-lactam Susceptible** → prefer a **β-lactam** that is susceptible.")

    # ESBL / third-generation resistance without carbapenem resistance
    if _any_R(R, THIRD_GENS) and not carp_R:
        out.append("third-generation cephalosporin resistance → for serious infections, choose a **reliably active agent** (often **cefepime** if susceptible/MIC appropriate or a **carbapenem** depending on local guidance).")

    # Carbapenem resistance but cephalosporins still susceptible (SME-like phenotype)
    if carp_R and any_ceph_S:
        choices = []
        if ctx == "Susceptible": choices.append("**ceftriaxone**")
        if fep == "Susceptible": choices.append("**cefepime**")
        if caz == "Susceptible": choices.append("**ceftazidime**")
        out.append(
            "**Carbapenem Resistant with cephalosporin Susceptible** can occur in *Serratia* (e.g., **SME-type chromosomal carbapenemase** phenotypes). "
            f"Use a susceptible cephalosporin: {', '.join(choices)} (dose by site/MIC/severity) and confirm mechanism with lab/ID."
        )
    elif carp_R:
        out.append("**Carbapenem resistance present** → prioritize confirmed actives; request **carbapenemase workup** and involve **ID** for invasive disease.")

    # Ertapenem Resistant / Imipenem or Meropenem Susceptible
    if ept == "Resistant" and (imi == "Susceptible" or mero == "Susceptible"):
        out.append("**Ertapenem Resistant / Imipenem or Meropenem Susceptible** → select based on **tested MICs**; consider **optimized meropenem dosing** when appropriate.")

    # fluoroquinolone discordance: Ciprofloxacin Resistant / Levofloxacin Susceptible
    if cip == "Resistant" and lev == "Susceptible":
        out.append(
            "**Ciprofloxacin Resistant / Levofloxacin Susceptible** → levofloxacin *may* be used for selected **low-risk** scenarios if no better oral options, "
            "but **failure risk is higher** (PMQR/efflux). Prefer a confirmed-active **β-lactam** for **severe/invasive** infections."
        )

    # Trimethoprim/Sulfamethoxazole oral step-down
    if tmpsmx == "Susceptible":
        out.append(
            "**Trimethoprim/Sulfamethoxazole susceptible** → possible **oral step-down** in selected cases once improving and source controlled "
            "(site/severity dependent; avoid as sole therapy for uncontrolled bacteremia/severe sepsis)."
        )

    return _dedup_list(out)

def mech_k_aerogenes(R):
    """
    Klebsiella aerogenes (formerly Enterobacter aerogenes)
    - Chromosomal AmpC: inducible/derepressible → avoid third-generation cephalosporins/Piperacillin/Tazobactam for serious infections
    - Can acquire ESBL + porin loss → ertapenem-R with Meropenem/Imipenem-S
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
        "**third-generation cephalosporins** and sometimes **Piperacillin/Tazobactam** in serious infections."
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

    # “Ertapenem Resistant / Imipenem or Meropenem Susceptible” often porin loss + AmpC/ESBL (non-carbapenemase CRE mechanism)
    if ept == "Resistant" and (imi == "Susceptible" or mero == "Susceptible"):
        banners.append(
            "**Ertapenem Resistant** with **Imipenem/Meropenem Susceptible** → commonly **AmpC/ESBL + porin loss** (non-carbapenemase) phenotype."
        )

    # ----------------------------
    # ESBL overlay (possible, but AmpC organism complicates interpretation)
    # ----------------------------
    # If third-generation cephalosporins are Resistant (or Ceftazidime Resistant) and no carbapenem resistance, call out ESBL possibility *in addition* to AmpC.
    if (third_R or caz == "Resistant") and not carp_R:
        mechs.append(
            "β-lactam pattern with **third-generation cephalosporin resistance** could reflect **AmpC derepression** and/or **acquired ESBL**; "
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
            "Fluoroquinolone discordance (**Ciprofloxacin Resistant / Levofloxacin Susceptible**) suggests **low-level non–target-mediated resistance** "
            "(e.g., **PMQR** such as **qnr** or **AAC(6')-Ib-cr**) and/or **efflux**. These can **evolve to high-level resistance on therapy**."
        )
        banners.append(
            "Caution: **Levofloxacin** may test susceptible but has **higher risk of failure/on-therapy resistance** with PMQR/efflux phenotypes."
        )

    # ----------------------------
    # Trimethoprim/Sulfamethoxazole
    # ----------------------------
    if tmpsmx == "Resistant":
        mechs.append(
            "Trimethoprim/Sulfamethoxazole resistance: **dfrA** (trimethoprim-resistant DHFR) and/or **sul1/sul2** (sulfonamide-resistant DHPS), "
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
        out.append("**AmpC inducer** → **Cefepime (MIC ≤4) preferred**; avoid third-generation cephalosporins/Piperacillin/Tazobactam for serious infections.")
    elif fep in {"Intermediate","Resistant"}:
        out.append("AmpC with cefepime not Susceptible → **Carbapenem** preferred for serious infections.")

    # ---- Fluoroquinolones ----

    # If β-lactams are Susceptible but fluoroquinolones are Resistant → don’t chase the fluoroquinolone
    if _any_S(R, ["Cefepime","Piperacillin/Tazobactam","Imipenem","Meropenem"]) and \
       _any_R(R, ["Ciprofloxacin","Levofloxacin"]):
        out.append("**Fluoroquinolone Resistant but beta-lactam Susceptible** → prefer a **β-lactam** that is susceptible (avoid fluoroquinolones).")

    # Special discordance: Ciprofloxacin Resistant / Levofloxacin Susceptible
    if cip == "Resistant" and lev == "Susceptible":
        out.append(
            "**Ciprofloxacin Resistant / Levofloxacin Susceptible** → if a fluoroquinolone is considered, **levofloxacin** may be used based on susceptibility, "
            "but **failure risk is higher** with **PMQR/efflux** phenotypes. Prefer a confirmed-active **β-lactam** "
            "for **severe/invasive** infections; reserve levofloxacin for **low-risk sites** with close follow-up."
        )

    # If all tested fluoroquinolones are Resistant → explicitly tell them to avoid fluoroquinolones
    if _any_R(R, ["Ciprofloxacin","Levofloxacin"]) and \
       not _any_S(R, ["Ciprofloxacin","Levofloxacin"]):
        out.append("**All tested fluoroquinolones are resistant** → avoid fluoroquinolones; use a non-fluoroquinolone agent that is susceptible.")

    # ---- Trimethoprim/Sulfamethoxazole: oral step-down ----
    if tmpsmx == "Susceptible":
        out.append(
            "**Trimethoprim/Sulfamethoxazole susceptible** → reasonable **oral step-down** option for selected cases "
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
        mechs.append("Broad beta-lactam Resistant without carbapenem Resistant → **AmpC overproduction ± efflux**.")
    if carb_R and bl_S:
        mechs.append("Carbapenem Resistant with other beta-lactams Susceptible → **OprD porin loss** (non-carbapenemase) likely.")

    # Specific β-lactam banners
    if piptazo == "Resistant":
        banners.append("**Piperacillin/Tazobactam Resistant** → consider **AmpC derepression** and/or **efflux**.")
    if fep == "Resistant":
        banners.append("**Cefepime Resistant** → consider **MexXY-OprM efflux** and/or **AmpC**.")
    if caz == "Resistant":
        banners.append("**Ceftazidime Resistant** → consider **AmpC**, **ESBLs (VEB/PER/GES/TEM/SHV)**, and/or **efflux**.")

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
            "**fluoroquinolone discordance: Ciprofloxacin Resistant / Levofloxacin Susceptible** → most consistent with **efflux/stepwise resistance**. "
            "Even if levo tests susceptible, there is a **high risk of on-therapy resistance and clinical failure**, especially in invasive infections."
        )

    # ----------------------------
    # Aminoglycosides (mechanisms)
    # ----------------------------
    if ag_R:
        # Common pattern: Gentamicin/Tobramycin Resistant, amikacin Susceptible
        if (genta == "Resistant" or tobra == "Resistant") and (amik == "Susceptible"):
            mechs.append(
                "Aminoglycoside resistance pattern (**Gentamicin/Tobramycin Resistant, Amikacin Susceptible**) → consistent with **aminoglycoside-modifying enzymes (AMEs)**; "
                "**amikacin** may retain activity."
            )
        else:
            mechs.append(
                "Aminoglycoside resistance: **AMEs** and/or **efflux**; less commonly **16S rRNA methylases** (broad high-level resistance)."
            )

    # If all aminoglycoside are resistant, add a stronger banner
    if (genta in {"Resistant","Intermediate"} and tobra in {"Resistant","Intermediate"} and amik in {"Resistant","Intermediate"}):
        banners.append("**All aminoglycosides non-susceptible** → consistent with multiple AMEs/efflux or rarely **16S rRNA methylase**; avoid aminoglycoside reliance.")

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
    # If fluoroquinolone Resistant but β-lactam Susceptible → prefer β-lactam
    # ----------------------------
    if any_bl_S and fq_any_R:
        out.append("**Fluoroquinolone Resistant but beta-lactam Susceptible** → prefer a **susceptible anti-pseudomonal β-lactam** (avoid relying on fluoroquinolones).")

    # ----------------------------
    # Special OprD pattern: carbapenem Resistant but other β-lactams Susceptible
    # ----------------------------
    if carb_R and any_bl_S:
        choices = []
        if fep == "Susceptible":
            choices.append("**cefepime**")
        if piptazo == "Susceptible":
            choices.append("**Piperacillin/Tazobactam**")
        if caz == "Susceptible":
            choices.append("**ceftazidime**")
        if aztre == "Susceptible":
            choices.append("**aztreonam**")

        if choices:
            out.append(
                "**Carbapenem Resistant with other beta-lactams Susceptible** → pattern consistent with **OprD porin loss (non-carbapenemase)**. "
                f"Use a susceptible β-lactam: {', '.join(choices)} (site/MIC/severity dependent)."
            )
    else:
        # Carbapenem-R path only when no other β-lactam is susceptible
        if carb_R and not any_bl_S:
            out.append(
                "**Carbapenem Resistant present** → prioritize confirmed actives; consider **Ceftolozane/Tazobactam** or "
                "**Ceftazidime/Avibactam** if tested susceptible; consider ID input for severe infections."
            )
        else:
            # No carbapenem resistance → phenotype-based suggestions
            if fep == "Susceptible" and piptazo == "Resistant":
                out.append("**Cefepime Susceptible / Piperacillin/Tazobactam Resistant** → choose **cefepime** (phenotype compatible with **AmpC derepression**).")
            if fep == "Resistant" and piptazo == "Susceptible":
                out.append("**Cefepime Resistant / Piperacillin/Tazobactam Susceptible** → choose **Piperacillin/Tazobactam** (compatible with **MexXY-OprM efflux**).")

    # ----------------------------
    # Ceftazidime refinement
    # ----------------------------
    if caz == "Resistant":
        if fep == "Susceptible":
            out.append("**Ceftazidime Resistant / Cefepime Susceptible** → prefer **cefepime** (AmpC-compatible pattern).")
        elif piptazo == "Susceptible":
            out.append("**Ceftazidime Resistant / Piperacillin/Tazobactam Susceptible** → prefer **Piperacillin/Tazobactam**; confirm susceptibility.")
        elif (fep == "Resistant") and (piptazo == "Resistant"):
            out.append("**Ceftazidime, Cefepime, and Piperacillin/Tazobactam all Resistant** → consider **Ceftolozane/Tazobactam** if tested susceptible; evaluate combinations for severe infections.")
        else:
            out.append("**Ceftazidime Resistant** → choose among confirmed susceptible β-lactams; consider novel agents if none.")

    # ----------------------------
    # Fluoroquinolone discordance therapy note (Ciprofloxacin Resistant / Levofloxacin Susceptible)
    # ----------------------------
    if (cipro == "Resistant") and (levo == "Susceptible"):
        out.append(
            "**Ciprofloxacin Resistant / Levofloxacin Susceptible** → **levofloxacin may appear usable**, but discordance suggests **efflux/stepwise resistance** with **high failure risk**, "
            "especially for bacteremia, pneumonia, CNS, or deep-seated infection. If used at all, reserve for **limited/low-inoculum situations** and "
            "ensure close clinical monitoring."
        )

    # ----------------------------
    # Aminoglycosides therapy notes
    # ----------------------------
    if ag_any_S:
        # Prefer amikacin if it is the only Susceptible agent
        if (amik == "Susceptible") and (genta in {None,"Resistant","Intermediate"}) and (tobra in {None,"Resistant","Intermediate"}):
            out.append("**Aminoglycosides**: **amikacin susceptible** while Gentamicin/Tobramycin not Susceptible → **amikacin** may be the best aminoglycoside option (often as adjunct depending on site).")
        else:
            out.append("**Aminoglycosides**: if one is susceptible, it can be considered (often **adjunctive** in severe infections depending on site/toxicity).")

    if ag_any_R and not ag_any_S:
        out.append("**Aminoglycosides non-susceptible** → avoid relying on aminoglycoside therapy; consider alternative active classes/novel agents when available.")

    return _dedup_list(out)


def mech_achromobacter(R):
    # Start with the pseudomonas-style β-lactam/efflux heuristics
    mechs, banners, greens = mech_pseudomonas(R)

    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Resistant":
        mechs.append(
            "Trimethoprim/Sulfamethoxazole resistance: usually **folate-pathway target changes** (e.g., **dfrA** for trimethoprim, **sul1/sul2** for sulfonamides) "
            "and/or **efflux**."
        )
    elif tmpsmx == "Susceptible":
        greens.append("Trimethoprim/Sulfamethoxazole is **susceptible** — often a key active option for **Achromobacter** (site/severity dependent).")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_achromobacter(R):
    out = tx_pseudomonas(R)

    tmpsmx = _get(R, "Trimethoprim/Sulfamethoxazole")
    if tmpsmx == "Susceptible":
        out.append(
            "**Trimethoprim/Sulfamethoxazole susceptible** → consider **Trimethoprim/Sulfamethoxazole** as a primary option (including **oral step-down** when clinically appropriate: "
            "source controlled, stable patient, adequate absorption, and a non–high-inoculum site)."
        )
    elif tmpsmx == "Resistant":
        out.append(
            "**Trimethoprim/Sulfamethoxazole resistant** → do **not** rely on Trimethoprim/Sulfamethoxazole; select among other confirmed susceptible agents."
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
    # We keep this as a general mechanism line when there is broad beta-lactam resistance.
    if bl_any_R:
        mechs.append(
            "β-lactam resistance is often driven by **β-lactamases** (including **AmpC** and sometimes **ESBLs**) "
            "plus **efflux** and **outer-membrane/porin (OMP) permeability** changes."
        )

    # Efflux emphasis if multi-class phenotype (beta-lactam + fluoroquinolone and/or aminoglycoside resistance)
    fq_R = _any_R(R, ["Ciprofloxacin","Levofloxacin"])
    ag_R = _any_R(R, ["Gentamicin","Tobramycin","Amikacin"])
    if bl_any_R and (fq_R or ag_R):
        mechs.append(
            "Multidrug phenotype suggests contribution from **RND efflux pumps (e.g., AdeABC)** in addition to enzyme-mediated resistance."
        )

    # Porin/OMP emphasis if carbapenem-resistant but some other beta-lactam remain Susceptible (permeability + enzyme interplay)
    if carb_R and bl_any_S:
        banners.append(
            "Carbapenem Resistant with some other beta-lactams Susceptible can reflect **permeability/OMP (porin) changes** plus variable β-lactamase expression."
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
            banners.append("Aminoglycoside pattern: **amikacin may retain activity** despite Gentamicin/Tobramycin resistance (agent-specific).")

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

    # fluoroquinolone + aminoglycoside stewardship guidance
    if fq_R:
        out.append("**Fluoroquinolone resistant** → avoid fluoroquinolones unless a specific agent is tested susceptible and clinically appropriate.")
    if ag_R:
        if amik == "Susceptible" and (genta == "Resistant" or tobra == "Resistant"):
            out.append("Aminoglycosides: **amikacin susceptible** while Gentamicin/Tobramycin resistant → amikacin may be the preferred aminoglycoside (agent-specific).")
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

    # Trimethoprim/Sulfamethoxazole
    if tmpsmx == "Resistant":
        mechs.append(
            "Trimethoprim/Sulfamethoxazole resistance: often via **sul1** (and related folate-pathway resistance determinants) carried on "
            "**class 1 integrons**; resistance has increased globally."
        )
    elif tmpsmx == "Susceptible":
        greens.append("Trimethoprim/Sulfamethoxazole is **susceptible** — historically the mainstay with strong in-vitro activity against *S. maltophilia*.")

    # Fluoroquinolones
    if (lev == "Resistant") or (moxi == "Resistant"):
        mechs.append(
            "Fluoroquinolone resistance: commonly due to **efflux pump overexpression** (e.g., **SmeDEF** and other RND pumps; **MfsA**), "
            "sometimes via regulatory mutations (e.g., derepression of SmeDEF)."
        )
    # Susceptible fluoroquinolone but still caution for emergence
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
        out.append("**Preferred**: **Trimethoprim/Sulfamethoxazole** when susceptible (often used as backbone).")
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
        "Consider **combination therapy** (often Trimethoprim/Sulfamethoxazole-based when susceptible) for higher-risk scenarios: "
        "**endovascular infection**, **CNS infection**, **bone/joint infection**, **severe neutropenia/immune defect**, "
        "or **multifocal lung disease** (align with local/ID team guidance)."
    )

    # Warn about fluoroquinolone monotherapy resistance emergence
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
        out.append("**Penicillin Resistant / Ampicillin Susceptible** → treat with **ampicillin** (preferred) rather than penicillin.")

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
    # sometimes with increased MICs for both penicillin and third-generation cephs.
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
            "Erythromycin Resistant with clindamycin Susceptible → supports **mef(A/E)** efflux or inducible mechanisms; "
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
            "For **suspected/confirmed meningitis**, use **vancomycin + a high-dose third-generation cephalosporin** initially; "
            "if cephalosporin resistance is present, continue **vancomycin** and consider adding **rifampin** per institutional guidance."
        )

    # If both penicillin and ceftriaxone not susceptible, highlight meningitis-style approach
    if (pen in {"Intermediate", "Resistant"}) and (ctx in {"Intermediate", "Resistant"}):
        out.append(
            "**Penicillin and Ceftriaxone non-susceptible** → pattern consistent with significant PBP alteration. "
            "For severe/invasive disease (especially CNS), prioritize **vancomycin-based** therapy guided by MICs and ID input."
        )

    # Vancomycin role (mostly relevant in meningitis or severe disease; susceptibility usually reported as Susceptible)
    if vanc == "Susceptible":
        # Don't always spam; only add if Ceftriaxone non-susceptible (above) or user wants meningitis framing.
        pass
    elif vanc in {"Intermediate", "Resistant"}:
        out.append("Vancomycin non-susceptible is very uncommon → confirm MIC and involve **ID** urgently.")

    # ----------------------------
    # Macrolides & fluoroquinolones
    # ----------------------------
    if ery == "Resistant":
        out.append("Avoid macrolides when **Erythromycin Resistant** unless a specific macrolide is tested susceptible.")
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
        banners.append("**Erythromycin Resistant / Clindamycin Susceptible** → perform **D-test** to assess inducible MLS_B; avoid clindamycin if D-test positive.")
    elif ery == "Susceptible" and cli == "Resistant":
        banners.append(
            "Clindamycin Resistant with erythromycin Susceptible is uncommon; consider repeat testing / lab confirmation "
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

    # Avoid macrolides when Resistant
    if ery == "Resistant":
        out.append("Avoid macrolides when **Erythromycin Resistant** unless a specific macrolide is tested susceptible.")

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
        banners.append("**Erythromycin Resistant / Clindamycin Susceptible** → consider **D-test** where applicable; avoid clindamycin if inducible MLS_B is present.")

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
        out.append("Avoid macrolides when **Erythromycin Resistant** unless a specific macrolide is tested susceptible.")
    if ery == "Resistant" and cli == "Susceptible":
        out.append("If considering clindamycin, consider **D-test** where applicable; avoid clindamycin if inducible MLS_B is present.")

    # fluoroquinolone caution
    if lvo == "Susceptible":
        out.append("If a fluoroquinolone is considered, use only if **the specific agent is susceptible**; avoid class assumptions.")
    elif lvo in {"Intermediate", "Resistant"}:
        out.append("Fluoroquinolone non-susceptible → avoid fluoroquinolones; select a susceptible β-lactam or vancomycin per site/severity.")

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
                banners.append("Pattern **Penicillin Resistant + Oxacillin Susceptible** → strongly supports **penicillinase (blaZ)** production.")

    # ---- Macrolide / lincosamide (D-test pattern) ----
    if ery == "Resistant" and clin == "Resistant":
        mechs.append("Macrolide/Lincosamide resistance: likely **erm-mediated MLS_B** (constitutive).")
    elif ery == "Resistant" and clin == "Susceptible":
        banners.append(
            "**Erythromycin Resistant / Clindamycin Susceptible** → perform **D-test** for inducible MLS_B (erm). "
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

    # ---- Trimethoprim/Sulfamethoxazole ----
    if tmp == "Resistant":
        mechs.append("**Trimethoprim/Sulfamethoxazole resistance**: mutations or acquired **dfr** (DHFR) and/or **sul** (DHPS) genes.")

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
            out.append("When **Linezolid Susceptible**, it is a good option for **MRSA pneumonia** or when an oral agent is needed with high bioavailability.")

    # D-test / clindamycin
    if ery == "Resistant" and clin == "Susceptible":
        out.append("**Erythromycin Resistant / Clindamycin Susceptible** → perform a **D-test**. Only use clindamycin if D-test negative (no inducible MLS_B).")

    # Trimethoprim/Sulfamethoxazole as oral option (selected scenarios)
    if tmp == "Susceptible":
        out.append("**Trimethoprim/Sulfamethoxazole susceptible** → reasonable **oral step-down** for selected infections (often SSTI; sometimes bone/joint with close follow-up) when susceptible and source is controlled. Avoid as monotherapy for severe bacteremia/endocarditis.")

    # Tetracycline/Doxycycline as oral option
    if tet == "Susceptible":
        out.append("**Tetracycline/Doxycycline susceptible** → may be used as an **oral option** for some skin/soft tissue infections when appropriate.")

    # Fluoroquinolones – caution
    if moxi == "Susceptible":
        out.append("If **Moxifloxacin Susceptible**, use with caution; fluoroquinolones are generally **not preferred** for staphylococcal infections due to rapid emergence of resistance and toxicity concerns.")

    return _dedup_list(out)

# ======================
# Anaerobes: mechanisms & therapy
# ======================
ANAEROBE_ORGS = [
    "Bacteroides fragilis",
    "Bacteroides non-fragilis group",
    "Gram-negative anaerobic rods (Fusobacterium / Prevotella / Porphyromonas)",
    "Clostridium perfringens",
    "Clostridium sordellii",
    "Clostridium septicum",
    "Other Clostridium spp. (non-perfringens)",
    "Gram-positive anaerobic non-sporeforming rods (including Actinomyces)",
    "Gram-positive anaerobic cocci",
    "Bifidobacterium spp.",
    "Lactobacillus spp.",
    "Cutibacterium spp.",
]

ANAEROBE_PANEL = [
    "Penicillin",
    "Ampicillin/Sulbactam",
    "Meropenem",
    "Clindamycin",
    "Metronidazole",
]

ANAEROBE_BFRAG_GROUP = {"Bacteroides fragilis", "Bacteroides non-fragilis group"}
ANAEROBE_NON_PERFRINGENS_CLOSTRIDIA = {
    "Clostridium sordellii",
    "Clostridium septicum",
    "Other Clostridium spp. (non-perfringens)",
}
ANAEROBE_METRO_INTRINSIC_OR_POOR = {
    "Gram-positive anaerobic non-sporeforming rods (including Actinomyces)",
    "Lactobacillus spp.",
    "Cutibacterium spp.",
}
ANAEROBE_METRO_VARIABLE = {"Bifidobacterium spp."}

def anaerobe_intrinsic_map(org: str):
    intrinsic = {ab: False for ab in ANAEROBE_PANEL}
    if org in ANAEROBE_BFRAG_GROUP:
        intrinsic["Penicillin"] = True
    if org in {"Lactobacillus spp.", "Cutibacterium spp."}:
        intrinsic["Metronidazole"] = True
    return intrinsic


def mech_anaerobe(org: str, R: dict):
    mechs, banners, greens = [], [], []

    pen = _get(R, "Penicillin")
    amp_sul = _get(R, "Ampicillin/Sulbactam")
    mero = _get(R, "Meropenem")
    cli = _get(R, "Clindamycin")
    metro = _get(R, "Metronidazole")

    if org in ANAEROBE_BFRAG_GROUP:
        banners.append(
            "Baseline for Bacteroides fragilis group: penicillin is usually unreliable because of beta-lactamase production."
        )
    if org in ANAEROBE_METRO_INTRINSIC_OR_POOR:
        banners.append(
            "Metronidazole activity is often poor/unreliable for this group (especially Actinomyces, Cutibacterium, and Lactobacillus)."
        )
    elif org in ANAEROBE_METRO_VARIABLE:
        banners.append(
            "Metronidazole activity can be variable for this group; avoid assuming class-wide susceptibility."
        )

    # Penicillin
    if pen == "Resistant":
        if org in ANAEROBE_BFRAG_GROUP or org == "Gram-negative anaerobic rods (Fusobacterium / Prevotella / Porphyromonas)":
            mechs.append(
                "Penicillin resistance: beta-lactamase production (commonly cepA/cfxA-family enzymes in anaerobic gram-negative rods)."
            )
        else:
            mechs.append(
                "Penicillin resistance: usually beta-lactamase production and/or reduced PBP affinity."
            )
    elif pen == "Susceptible":
        if org in {"Clostridium perfringens", "Gram-positive anaerobic cocci"}:
            greens.append("Penicillin remains a useful backbone when susceptible.")

    # Ampicillin/Sulbactam
    if amp_sul == "Resistant":
        mechs.append(
            "Ampicillin/Sulbactam resistance: high-level beta-lactamase expression, inhibitor-insensitive beta-lactamases, and/or altered PBPs/permeability."
        )
    elif amp_sul == "Susceptible":
        greens.append("Ampicillin/Sulbactam is active and often useful for mixed anaerobic infection coverage.")

    # Meropenem
    if mero == "Resistant":
        if org in ANAEROBE_BFRAG_GROUP:
            mechs.append(
                "Meropenem resistance in B. fragilis group: cfiA metallo-beta-lactamase, often enhanced by upstream insertion sequences."
            )
        else:
            mechs.append(
                "Meropenem resistance: uncommon in many anaerobes, but may involve carbapenemase activity and permeability/efflux contributions."
            )
    elif mero == "Susceptible":
        greens.append("Meropenem remains a strong option for severe polymicrobial anaerobic infections when susceptible.")

    # Clindamycin
    if cli == "Resistant":
        mechs.append(
            "Clindamycin resistance: usually ribosomal target methylation (erm genes, especially ermF/ermB) with MLS_B phenotype."
        )
    elif cli == "Susceptible":
        banners.append("Clindamycin is only reliable when isolate-specific susceptibility is confirmed.")

    # Metronidazole
    if metro == "Resistant":
        if org in ANAEROBE_METRO_INTRINSIC_OR_POOR:
            mechs.append(
                "Metronidazole resistance is expected/intrinsic for this group due to poor nitroimidazole activation."
            )
        elif org in ANAEROBE_METRO_VARIABLE:
            mechs.append(
                "Metronidazole resistance can occur in this group and should be interpreted as species-dependent rather than uniform."
            )
        else:
            mechs.append(
                "Metronidazole resistance: nim-encoded nitroimidazole reductase and/or reduced intracellular drug activation (redox pathway changes)."
            )
    elif metro == "Susceptible":
        if org in ANAEROBE_METRO_INTRINSIC_OR_POOR:
            banners.append(
                "Metronidazole susceptible result in this group is unusual; confirm identification and AST method before relying on it."
            )
        elif org in ANAEROBE_METRO_VARIABLE:
            banners.append(
                "Metronidazole is susceptible in this isolate, but group-level variability is common; avoid broad extrapolation."
            )
        else:
            greens.append("Metronidazole remains active when susceptible, especially for gram-negative anaerobic rods.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_anaerobe(org: str, R: dict):
    out = []

    pen = _get(R, "Penicillin")
    amp_sul = _get(R, "Ampicillin/Sulbactam")
    mero = _get(R, "Meropenem")
    cli = _get(R, "Clindamycin")
    metro = _get(R, "Metronidazole")

    if mero == "Susceptible":
        out.append("Meropenem susceptible: preferred for severe/invasive anaerobic infection or high-risk polymicrobial disease.")
    elif mero == "Resistant":
        out.append("Meropenem resistant: avoid empiric carbapenem reliance; request full anaerobe panel and involve ID.")

    if amp_sul == "Susceptible":
        out.append("Ampicillin/Sulbactam susceptible: good targeted option for many anaerobic and mixed intra-abdominal/soft-tissue infections.")
    elif amp_sul == "Resistant":
        out.append("Ampicillin/Sulbactam resistant: do not rely on beta-lactamase inhibition alone; choose another tested-active agent.")

    if pen == "Susceptible":
        if org == "Clostridium perfringens":
            out.append(
                "Clostridium perfringens: penicillin is active when susceptible; for toxin-mediated disease, combine with urgent surgery and consider clindamycin if susceptible."
            )
        elif org in ANAEROBE_NON_PERFRINGENS_CLOSTRIDIA:
            out.append(
                "Non-perfringens Clostridium: use a susceptible beta-lactam/carbapenem and prioritize source control; in toxin-mediated disease, clindamycin may be added if susceptible."
            )
        elif org in {"Gram-positive anaerobic cocci", "Gram-positive anaerobic non-sporeforming rods (including Actinomyces)"}:
            out.append("Penicillin susceptible: use as a focused option when site/source control is adequate.")
    elif pen == "Resistant":
        out.append("Penicillin resistant: avoid penicillin monotherapy.")

    if cli == "Susceptible":
        out.append("Clindamycin susceptible: can be used as an oral/step-down option in selected sites; avoid empiric use without susceptibility data.")
    elif cli == "Resistant":
        out.append("Clindamycin resistant: avoid for definitive therapy.")

    if metro == "Susceptible":
        if org in ANAEROBE_METRO_INTRINSIC_OR_POOR:
            out.append("Metronidazole susceptible result is unusual for this group; confirm before relying on it, and prefer beta-lactam options when susceptible.")
        elif org in ANAEROBE_METRO_VARIABLE:
            out.append("Metronidazole susceptible in this isolate, but group-level variability is common; do not extrapolate to all species/isolates.")
        else:
            out.append("Metronidazole susceptible: suitable anaerobe-active option when source control is achieved.")
    elif metro == "Resistant":
        out.append("Metronidazole resistant: avoid metronidazole and treat with another confirmed-active agent.")

    if not _any_S(R, ANAEROBE_PANEL):
        out.append("No tested susceptible option identified in the selected panel; request expanded AST and urgent ID input.")

    return _dedup_list(out)

# ======================
# Mycobacteria: mechanisms & therapy
# ======================
MYCO_MTBC_ORG = "Mycobacterium tuberculosis complex"

MYCO_MTBC_PANEL = [
    "Rifampin",
    "Isoniazid",
    "Fluoroquinolone (Levofloxacin/Moxifloxacin)",
    "Bedaquiline",
    "Linezolid",
    "Pyrazinamide",
    "Ethambutol",
]

MYCO_NTM_ORGS = [
    "Mycobacterium avium complex (MAC)",
    "Mycobacterium kansasii",
    "Mycobacterium abscessus complex",
    "Rapid-growing NTM (e.g., M. fortuitum group)",
]

MYCO_NTM_PANEL = {
    "Mycobacterium avium complex (MAC)": [
        "Clarithromycin/Azithromycin",
        "Amikacin",
        "Rifampin",
        "Ethambutol",
        "Moxifloxacin",
        "Linezolid",
    ],
    "Mycobacterium kansasii": [
        "Rifampin",
        "Ethambutol",
        "Isoniazid",
        "Clarithromycin/Azithromycin",
        "Moxifloxacin",
        "Amikacin",
    ],
    "Mycobacterium abscessus complex": [
        "Clarithromycin/Azithromycin",
        "Amikacin",
        "Cefoxitin",
        "Imipenem",
        "Linezolid",
        "Clofazimine",
    ],
    "Rapid-growing NTM (e.g., M. fortuitum group)": [
        "Clarithromycin/Azithromycin",
        "Amikacin",
        "Moxifloxacin",
        "Linezolid",
        "Trimethoprim/Sulfamethoxazole",
        "Doxycycline",
    ],
}

def myco_intrinsic_map(panel):
    return {ab: False for ab in panel}


def mech_mtbc(R):
    mechs, banners, greens = [], [], []

    rif = _get(R, "Rifampin")
    inh = _get(R, "Isoniazid")
    fq = _get(R, "Fluoroquinolone (Levofloxacin/Moxifloxacin)")
    bdq = _get(R, "Bedaquiline")
    lzd = _get(R, "Linezolid")
    pza = _get(R, "Pyrazinamide")
    emb = _get(R, "Ethambutol")
    rpob = _get(R, "rpoB mutation")
    katg = _get(R, "katG mutation")
    inha = _get(R, "inhA promoter mutation")
    gyr = _get(R, "gyrA/gyrB mutation")

    if rpob == "Detected":
        mechs.append("rpoB mutation detected: strong molecular signal of rifampin resistance (RR-TB risk).")
    elif rpob == "Not detected" and rif == "Resistant":
        banners.append("Rifampin phenotypic resistance with no rpoB mutation detected: verify isolate identity, repeat DST, and broaden molecular review.")
    if rpob == "Detected" and rif == "Susceptible":
        banners.append("rpoB mutation detected but rifampin is phenotypically susceptible: possible heteroresistance or assay discordance; treat cautiously.")

    if katg == "Detected" and inha == "Detected":
        mechs.append("Isoniazid resistance genotype includes both katG and inhA promoter mutations.")
    elif katg == "Detected":
        mechs.append("katG mutation detected: typically high-level isoniazid resistance signal.")
    elif inha == "Detected":
        mechs.append("inhA promoter mutation detected: low-level isoniazid resistance signal and possible ethionamide cross-resistance.")
    if inh == "Resistant" and katg == "Not detected" and inha == "Not detected":
        banners.append("Isoniazid resistance without katG/inhA mutations entered: consider expanded molecular review.")

    if gyr == "Detected":
        mechs.append("gyrA/gyrB mutation detected: molecular fluoroquinolone resistance signal.")
    elif gyr == "Not detected" and fq == "Resistant":
        banners.append("Fluoroquinolone phenotypic resistance without gyrA/gyrB mutation entered: verify and consider alternative mechanisms/testing factors.")
    if gyr == "Detected" and fq == "Susceptible":
        banners.append("gyrA/gyrB mutation detected with fluoroquinolone susceptibility: possible emerging resistance/heteroresistance.")

    if rif == "Resistant":
        mechs.append("Rifampin resistance: usually rpoB mutations (RRDR), and this should trigger rapid molecular confirmation.")
    if inh == "Resistant":
        mechs.append("Isoniazid resistance: commonly katG loss-of-activation and/or inhA promoter mutations.")
    if rif == "Resistant" and inh == "Resistant":
        banners.append("Rifampin + Isoniazid resistance phenotype is consistent with MDR-TB risk.")
    elif rif == "Resistant":
        banners.append("Rifampin resistance should be managed as RR/MDR-risk until full molecular and phenotypic DST is available.")

    if fq == "Resistant":
        mechs.append("Fluoroquinolone resistance: typically gyrA/gyrB target mutations.")
        if rif == "Resistant":
            banners.append("RR/MDR phenotype with fluoroquinolone resistance suggests pre-XDR risk and requires expert regimen design.")

    if bdq == "Resistant":
        mechs.append("Bedaquiline resistance: often atpE target changes and/or efflux-regulatory variants (e.g., Rv0678).")
        banners.append("Bedaquiline resistance narrows all-oral MDR options substantially.")

    if lzd == "Resistant":
        mechs.append("Linezolid resistance: most often rrl and/or rplC mutations.")

    if pza == "Resistant":
        mechs.append("Pyrazinamide resistance: most commonly pncA pathway mutations.")
    if emb == "Resistant":
        mechs.append("Ethambutol resistance: frequently associated with embB alterations.")

    if rif == "Susceptible" and inh == "Susceptible":
        greens.append("Rifampin and Isoniazid susceptible pattern supports a drug-susceptible TB backbone.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_mtbc(R):
    out = []

    rif = _get(R, "Rifampin")
    inh = _get(R, "Isoniazid")
    fq = _get(R, "Fluoroquinolone (Levofloxacin/Moxifloxacin)")
    bdq = _get(R, "Bedaquiline")
    lzd = _get(R, "Linezolid")
    rpob = _get(R, "rpoB mutation")
    katg = _get(R, "katG mutation")
    inha = _get(R, "inhA promoter mutation")
    gyr = _get(R, "gyrA/gyrB mutation")

    if rif == "Susceptible" and inh == "Susceptible":
        out.append("Drug-susceptible pattern: use standard first-line TB regimen per TB program guidance (RIPE-style induction then continuation).")
    if inh == "Resistant" and rif == "Susceptible":
        out.append("Isoniazid-resistant / Rifampin-susceptible TB: use an Hr-TB regimen (typically rifampin-ethambutol-pyrazinamide plus fluoroquinolone) per local/national protocol.")
    if rif is None and rpob == "Detected":
        out.append("rpoB mutation detected without phenotypic rifampin result: manage as probable RR-TB risk while confirmatory testing is finalized.")
    if inh is None and (katg == "Detected" or inha == "Detected"):
        out.append("katG/inhA mutation detected without phenotypic INH result: manage as likely INH-resistant until full DST confirms.")
    if inha == "Detected" and katg != "Detected":
        out.append("inhA-only signal can represent lower-level INH resistance; regimen selection should be expert-guided and genotype-aware.")
    if rif == "Resistant":
        out.append("Rifampin-resistant pattern: treat as RR/MDR-risk TB, obtain full rapid molecular DST, and involve TB/ID/public-health experts early.")
        if fq == "Susceptible":
            out.append("If fluoroquinolone remains susceptible, this may support all-oral MDR regimen construction with other active agents.")
        elif fq == "Resistant":
            out.append("RR/MDR with fluoroquinolone resistance: highly resistant pattern; urgent individualized regimen design is needed.")
    if fq is None and gyr == "Detected":
        out.append("gyrA/gyrB mutation detected without phenotypic fluoroquinolone result: avoid relying on fluoroquinolones until resolved.")

    if bdq == "Resistant" or lzd == "Resistant":
        out.append("Bedaquiline/Linezolid resistance present: prioritize expert consultation because core MDR backbone options are reduced.")

    if not _any_S(R, MYCO_MTBC_PANEL):
        out.append("No susceptible result entered in the panel; verify DST method and coordinate urgent expert review.")

    out.append("Therapy should always be aligned with regional TB control program guidance and drug-interaction/toxicity monitoring.")
    return _dedup_list(out)


def mech_ntm(org: str, R: dict):
    mechs, banners, greens = [], [], []

    mac = _get(R, "Clarithromycin/Azithromycin")
    amk = _get(R, "Amikacin")
    rif = _get(R, "Rifampin")
    moxi = _get(R, "Moxifloxacin")
    abs_subsp = _get(R, "M. abscessus subspecies")
    abs_erm41 = _get(R, "erm(41) status")
    abs_mac_ext = _get(R, "Extended-incubation macrolide")

    if mac == "Resistant":
        if org == "Mycobacterium abscessus complex":
            mechs.append("Macrolide resistance in M. abscessus complex: inducible erm(41) expression and/or acquired 23S rRNA (rrl) mutations.")
            banners.append("For M. abscessus, check both early and extended-incubation macrolide results to detect inducible resistance.")
        else:
            mechs.append("Macrolide resistance: often due to 23S rRNA (rrl) target mutations and predicts poor oral backbone options.")
    elif mac == "Susceptible":
        if org == "Mycobacterium avium complex (MAC)":
            greens.append("Macrolide susceptibility is a key favorable predictor for MAC regimen success.")
        elif org == "Mycobacterium abscessus complex":
            banners.append("Macrolide susceptible result in M. abscessus should still be interpreted with inducible-resistance testing context.")
            if abs_mac_ext == "Resistant":
                mechs.append("Inducible macrolide resistance pattern: early susceptible but extended-incubation resistant, consistent with functional erm(41).")

    if org == "Mycobacterium abscessus complex":
        if abs_subsp == "subsp. massiliense":
            greens.append("Subspecies is M. abscessus subsp. massiliense, which often has non-functional erm(41) and better macrolide activity.")
        elif abs_subsp in {"subsp. abscessus", "subsp. bolletii"}:
            banners.append("Subspecies is abscessus/bolletii, where functional erm(41) and inducible macrolide resistance are more likely.")
        if abs_erm41 == "Functional/inducible":
            mechs.append("erm(41) functional genotype predicts inducible macrolide resistance in M. abscessus complex.")
        elif abs_erm41 == "Non-functional":
            greens.append("erm(41) non-functional status supports more durable macrolide activity when phenotypically susceptible.")
        if abs_mac_ext == "Resistant":
            banners.append("Extended-incubation macrolide resistance indicates inducible resistance; do not treat macrolide as a reliably active drug.")
        elif abs_mac_ext == "Susceptible" and abs_erm41 == "Non-functional":
            greens.append("Extended-incubation macrolide susceptibility plus non-functional erm(41) supports macrolide inclusion.")

    if amk == "Resistant":
        mechs.append("Amikacin resistance: usually associated with 16S rRNA (rrs) target mutations.")
    elif amk == "Susceptible":
        greens.append("Amikacin remains an active companion option when needed for severe/refractory disease.")

    if org == "Mycobacterium kansasii":
        if rif == "Resistant":
            mechs.append("Rifampin resistance in M. kansasii usually reflects rpoB changes and predicts more complex therapy.")
        elif rif == "Susceptible":
            greens.append("Rifampin susceptibility supports standard rifampin-based M. kansasii therapy.")

    if moxi == "Resistant":
        mechs.append("Fluoroquinolone resistance: usually gyrA/gyrB target changes.")

    return _dedup_list(mechs), _dedup_list(banners), _dedup_list(greens)


def tx_ntm(org: str, R: dict):
    out = []

    mac = _get(R, "Clarithromycin/Azithromycin")
    amk = _get(R, "Amikacin")
    rif = _get(R, "Rifampin")
    abs_subsp = _get(R, "M. abscessus subspecies")
    abs_erm41 = _get(R, "erm(41) status")
    abs_mac_ext = _get(R, "Extended-incubation macrolide")

    if org == "Mycobacterium avium complex (MAC)":
        if mac == "Susceptible":
            out.append("MAC: use a macrolide-based multidrug regimen (typically macrolide + ethambutol + rifamycin) when clinically indicated.")
        elif mac == "Resistant":
            out.append("MAC with macrolide resistance: outcomes are poorer; use expert-guided multidrug strategy and avoid macrolide-only reliance.")
    elif org == "Mycobacterium kansasii":
        if rif == "Susceptible":
            out.append("M. kansasii: rifampin-based regimen is the anchor when susceptible (with companion agents per guideline).")
        elif rif == "Resistant":
            out.append("M. kansasii rifampin resistance: requires alternative multidrug regimen and specialist input.")
    elif org == "Mycobacterium abscessus complex":
        inducible_signal = (
            abs_erm41 == "Functional/inducible"
            or abs_mac_ext == "Resistant"
            or abs_subsp in {"subsp. abscessus", "subsp. bolletii"}
        )
        favorable_signal = (
            abs_subsp == "subsp. massiliense"
            or abs_erm41 == "Non-functional"
            or abs_mac_ext == "Susceptible"
        )

        if mac == "Susceptible" and favorable_signal and not inducible_signal:
            out.append("M. abscessus complex: macrolide can be part of the active backbone when subspecies/erm(41)/extended-incubation profile supports true susceptibility.")
        elif mac == "Susceptible":
            out.append("M. abscessus complex: macrolide may be present in regimen for immunomodulatory benefit, but do not assume it is reliably active without favorable subspecies/erm(41)/extended-incubation profile.")
        elif mac == "Resistant":
            out.append("M. abscessus complex with macrolide resistance: use non-macrolide multidrug backbone; prolonged therapy and specialist oversight are essential.")
        if amk == "Susceptible":
            out.append("Amikacin susceptible result can support intensive-phase therapy in severe M. abscessus disease.")
    else:
        out.append("Rapid-growing NTM: treat only if clinically significant disease is established; use at least two active agents based on species-level AST.")

    out.append("NTM treatment should be species-specific, site-specific, and coordinated with mycobacterial reference lab interpretation.")
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

    # Anaerobes
    "Bacteroides fragilis": {
        "mechanisms": lambda R: mech_anaerobe("Bacteroides fragilis", R),
        "therapy": lambda R: tx_anaerobe("Bacteroides fragilis", R)
    },
    "Bacteroides non-fragilis group": {
        "mechanisms": lambda R: mech_anaerobe("Bacteroides non-fragilis group", R),
        "therapy": lambda R: tx_anaerobe("Bacteroides non-fragilis group", R)
    },
    "Gram-negative anaerobic rods (Fusobacterium / Prevotella / Porphyromonas)": {
        "mechanisms": lambda R: mech_anaerobe("Gram-negative anaerobic rods (Fusobacterium / Prevotella / Porphyromonas)", R),
        "therapy": lambda R: tx_anaerobe("Gram-negative anaerobic rods (Fusobacterium / Prevotella / Porphyromonas)", R)
    },
    "Clostridium perfringens": {
        "mechanisms": lambda R: mech_anaerobe("Clostridium perfringens", R),
        "therapy": lambda R: tx_anaerobe("Clostridium perfringens", R)
    },
    "Clostridium sordellii": {
        "mechanisms": lambda R: mech_anaerobe("Clostridium sordellii", R),
        "therapy": lambda R: tx_anaerobe("Clostridium sordellii", R)
    },
    "Clostridium septicum": {
        "mechanisms": lambda R: mech_anaerobe("Clostridium septicum", R),
        "therapy": lambda R: tx_anaerobe("Clostridium septicum", R)
    },
    "Other Clostridium spp. (non-perfringens)": {
        "mechanisms": lambda R: mech_anaerobe("Other Clostridium spp. (non-perfringens)", R),
        "therapy": lambda R: tx_anaerobe("Other Clostridium spp. (non-perfringens)", R)
    },
    "Gram-positive anaerobic non-sporeforming rods (including Actinomyces)": {
        "mechanisms": lambda R: mech_anaerobe("Gram-positive anaerobic non-sporeforming rods (including Actinomyces)", R),
        "therapy": lambda R: tx_anaerobe("Gram-positive anaerobic non-sporeforming rods (including Actinomyces)", R)
    },
    "Gram-positive anaerobic cocci": {
        "mechanisms": lambda R: mech_anaerobe("Gram-positive anaerobic cocci", R),
        "therapy": lambda R: tx_anaerobe("Gram-positive anaerobic cocci", R)
    },
    "Bifidobacterium spp.": {
        "mechanisms": lambda R: mech_anaerobe("Bifidobacterium spp.", R),
        "therapy": lambda R: tx_anaerobe("Bifidobacterium spp.", R)
    },
    "Lactobacillus spp.": {
        "mechanisms": lambda R: mech_anaerobe("Lactobacillus spp.", R),
        "therapy": lambda R: tx_anaerobe("Lactobacillus spp.", R)
    },
    "Cutibacterium spp.": {
        "mechanisms": lambda R: mech_anaerobe("Cutibacterium spp.", R),
        "therapy": lambda R: tx_anaerobe("Cutibacterium spp.", R)
    },

    # Mycobacteria
    "Mycobacterium tuberculosis complex": {
        "mechanisms": mech_mtbc, "therapy": tx_mtbc
    },
    "Mycobacterium avium complex (MAC)": {
        "mechanisms": lambda R: mech_ntm("Mycobacterium avium complex (MAC)", R),
        "therapy": lambda R: tx_ntm("Mycobacterium avium complex (MAC)", R)
    },
    "Mycobacterium kansasii": {
        "mechanisms": lambda R: mech_ntm("Mycobacterium kansasii", R),
        "therapy": lambda R: tx_ntm("Mycobacterium kansasii", R)
    },
    "Mycobacterium abscessus complex": {
        "mechanisms": lambda R: mech_ntm("Mycobacterium abscessus complex", R),
        "therapy": lambda R: tx_ntm("Mycobacterium abscessus complex", R)
    },
    "Rapid-growing NTM (e.g., M. fortuitum group)": {
        "mechanisms": lambda R: mech_ntm("Rapid-growing NTM (e.g., M. fortuitum group)", R),
        "therapy": lambda R: tx_ntm("Rapid-growing NTM (e.g., M. fortuitum group)", R)
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
section_header("Select Pathogen Group")
st.caption("Enter results only for antibiotics **actually tested** for the chosen organism. Non-tested agents are hidden.")

group_options = ["Gram-negatives", "Staphylococci", "Enterococcus", "Streptococcus", "Anaerobes", "Mycobacteria"]
group = st.selectbox("Pathogen group", group_options, index=0, key="pathogen_group")

# ======================
# Gram-negatives UI (uses registry)
# ======================
if group == "Gram-negatives":
    section_header("Gram Negatives")

    organisms = sorted(GNR_CANON)
    organism = st.selectbox("Organism", organisms, key="gnr_org")

    panel = PANEL.get(organism, [])
    rules = RULES.get(organism, {"intrinsic_resistance": [], "cascade": []})

    section_header("Susceptibility Inputs")
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
    section_header("Mechanism of Resistance")
    mechs, banners, greens, gnotes = run_mechanisms_and_therapy_for(organism, final)

    if mechs:
        for m in mechs:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Mechanism", bg="var(--primary)")} {m}
             </div>
            """, unsafe_allow_html=True)

    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    if banners:
        for b in banners:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Caution", bg="var(--muted)", fg="#ffffff")} {b}
            </div>
            """, unsafe_allow_html=True)

    if greens:
        for g in greens:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Favorable", bg="var(--primary)")} {g}
            </div>
            """, unsafe_allow_html=True)


    fancy_divider()
    section_header("Therapy Guidance")
    if gnotes:
        for note in gnotes:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Therapy", bg="var(--primary)")} {note}
            </div>
            """, unsafe_allow_html=True)

    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    render_cre_carbapenemase_module(organism, final)

    # --- References (bottom of organism output) ---
    refs = _collect_mech_ref_keys(organism, mechs, banners)
    render_references(refs)

# ======================
# Enterococcus module (uses registry)
# ======================
if group == "Enterococcus":
    section_header("Enterococcus")
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

    section_header("Susceptibility Inputs")
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
    section_header("Mechanism of Resistance")
    mechs_e, banners_e, greens_e, gnotes_e = run_mechanisms_and_therapy_for(organism_e, final_e)

    if mechs_e:
        for m in mechs_e:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
                {badge("Mechanism", bg="var(--primary)")} {m}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    for b in banners_e:
        st.markdown(f"""
        <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Caution", bg="var(--muted)", fg="#ffffff")} {b}
        </div>
        """, unsafe_allow_html=True)

    for g in greens_e:
        st.markdown(f"""
        <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Favorable", bg="var(--primary)")} {g}
        </div>
        """, unsafe_allow_html=True)

    fancy_divider()
    section_header("Therapy Guidance")
    if gnotes_e:
        for note in gnotes_e:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
                {badge("Therapy", bg="var(--primary)")} {note}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    # --- References (bottom of organism output) ---
    refs_e = _collect_mech_ref_keys(organism_e, mechs_e, banners_e)
    render_references(refs_e)

    st.stop()

# ======================
# Staphylococci module
# ======================
if group == "Staphylococci":
    section_header("Staphylococci")

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
    section_header("Susceptibility Inputs")
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
    section_header("Mechanism of Resistance")
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
    section_header("Therapy Guidance")

    tx_fn = TX_REGISTRY.get(organism_st)
    if tx_fn is not None:
        gnotes_st = tx_fn(final_st)
    else:
        gnotes_st = []

    if gnotes_st:
        for note in gnotes_st:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Therapy", bg="var(--primary)")} {note}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")


    # References at the bottom
    refs_st = _collect_mech_ref_keys(organism_st, mechs_st, banners_st)
    render_references(refs_st)

    st.stop()

# ======================
# Streptococcus module (uses registry)
# ======================
if group == "Streptococcus":
    section_header("Streptococcus")
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

        section_header("Susceptibility Inputs")
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
        section_header("Mechanism of Resistance")
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
        section_header("Therapy Guidance")
        if gnotes_s:
            for note in gnotes_s:
                st.markdown(f"""
                <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
                {badge("Therapy", bg="var(--primary)")} {note}
                </div>
                """, unsafe_allow_html=True)

        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        
        # --- References (bottom of organism output) ---
        refs_s = _collect_mech_ref_keys("Streptococcus pneumoniae", mechs_s, banners_s)
        render_references(refs_s)

        st.stop()

    elif STREP_GROUP == "β-hemolytic Streptococcus (GAS/GBS)":
        PANEL_BHS = [
            "Penicillin",
            "Erythromycin", "Clindamycin",
            "Levofloxacin",
            "Vancomycin"
        ]
        intrinsic_bhs = {ab: False for ab in PANEL_BHS}

        section_header("Susceptibility Inputs")
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
        section_header("Mechanism of Resistance")
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
        section_header("Therapy Guidance")
        if gnotes_b:
            for note in gnotes_b:
                st.markdown(f"""
                <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
                {badge("Therapy", bg="var(--primary)")} {note}
                </div>
                """, unsafe_allow_html=True)

        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        refs_b = _collect_mech_ref_keys("β-hemolytic Streptococcus (GAS/GBS)", mechs_b, banners_b)
        render_references(refs_b)

        st.stop()

    elif STREP_GROUP == "Viridans group streptococci (VGS)":
        PANEL_VGS = [
            "Penicillin", "Ceftriaxone",
            "Erythromycin", "Clindamycin",
            "Levofloxacin",
            "Vancomycin"
        ]
        intrinsic_vgs = {ab: False for ab in PANEL_VGS}

        section_header("Susceptibility Inputs")
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
        section_header("Mechanism of Resistance")
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
        section_header("Therapy Guidance")
        if gnotes_v:
            for note in gnotes_v:
                st.markdown(f"""
                <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
                {badge("Therapy", bg="var(--primary)")} {note}
                </div>
                """, unsafe_allow_html=True)

        else:
            st.caption("No specific guidance triggered yet — enter more susceptibilities.")

        refs_v = _collect_mech_ref_keys("Viridans group streptococci (VGS)", mechs_v, banners_v)
        render_references(refs_v)

        st.stop()

if group == "Mycobacteria":
    section_header("Mycobacteria")
    st.caption("Use reference-lab AST/molecular data when available. Mycobacterial interpretation differs from routine pyogenic bacteriology.")

    myco_group = st.selectbox(
        "Mycobacteria group",
        ["Mycobacterium tuberculosis complex (MTBC)", "Non-tuberculous mycobacteria (NTM)"],
        key="myco_group"
    )

    if myco_group == "Mycobacterium tuberculosis complex (MTBC)":
        organism_m = MYCO_MTBC_ORG
        panel_m = MYCO_MTBC_PANEL
        st.info("MTBC module: phenotype should be integrated with rapid molecular resistance markers (rpoB, katG/inhA, gyrA/gyrB, etc.).")
        keyprefix_m = "MYCO_MTBC_ab"
    else:
        organism_m = st.selectbox("NTM organism", MYCO_NTM_ORGS, key="myco_ntm_org")
        panel_m = MYCO_NTM_PANEL[organism_m]
        st.info("NTM module: management is species-specific and often requires prolonged multidrug therapy.")
        keyprefix_m = f"MYCO_NTM_ab_{MYCO_NTM_ORGS.index(organism_m)}"

    intrinsic_m = myco_intrinsic_map(panel_m)

    section_header("Susceptibility Inputs")
    st.caption("Leave blank for untested/unknown.")
    user_m, final_m = _collect_panel_inputs(panel_m, intrinsic_m, keyprefix=keyprefix_m)
    extra_rows_m = []

    if myco_group == "Mycobacterium tuberculosis complex (MTBC)":
        st.markdown("**Optional molecular markers**")
        mtbc_gene_choices = ["", "Detected", "Not detected", "Indeterminate/Pending"]
        rpob_val = st.selectbox("rpoB mutation", mtbc_gene_choices, index=0, key="MYCO_MTBC_gene_rpob")
        katg_val = st.selectbox("katG mutation", mtbc_gene_choices, index=0, key="MYCO_MTBC_gene_katg")
        inha_val = st.selectbox("inhA promoter mutation", mtbc_gene_choices, index=0, key="MYCO_MTBC_gene_inha")
        gyr_val = st.selectbox("gyrA/gyrB mutation", mtbc_gene_choices, index=0, key="MYCO_MTBC_gene_gyr")

        for marker, value in [
            ("rpoB mutation", rpob_val),
            ("katG mutation", katg_val),
            ("inhA promoter mutation", inha_val),
            ("gyrA/gyrB mutation", gyr_val),
        ]:
            if value:
                final_m[marker] = value
                extra_rows_m.append({"Antibiotic": marker, "Result": value, "Source": "Molecular"})

    if myco_group == "Non-tuberculous mycobacteria (NTM)" and organism_m == "Mycobacterium abscessus complex":
        st.markdown("**M. abscessus subspecies / inducible-macrolide context (optional)**")
        abs_subsp = st.selectbox(
            "M. abscessus subspecies",
            ["", "subsp. abscessus", "subsp. massiliense", "subsp. bolletii", "Unknown"],
            index=0,
            key="MYCO_ABS_subspecies",
        )
        abs_erm41 = st.selectbox(
            "erm(41) status",
            ["", "Functional/inducible", "Non-functional", "Unknown"],
            index=0,
            key="MYCO_ABS_erm41",
        )
        abs_mac_ext = st.selectbox(
            "Extended-incubation macrolide",
            ["", "Susceptible", "Resistant", "Unknown"],
            index=0,
            key="MYCO_ABS_macrolide_extended",
        )

        for marker, value in [
            ("M. abscessus subspecies", abs_subsp),
            ("erm(41) status", abs_erm41),
            ("Extended-incubation macrolide", abs_mac_ext),
        ]:
            if value:
                final_m[marker] = value
                extra_rows_m.append({"Antibiotic": marker, "Result": value, "Source": "Molecular"})

    st.subheader("Consolidated results")
    rows_m = []
    for ab in panel_m:
        if final_m[ab] is None:
            continue
        rows_m.append({"Antibiotic": ab, "Result": final_m[ab], "Source": "User-entered"})
    rows_m.extend(extra_rows_m)
    if rows_m:
        st.dataframe(pd.DataFrame(rows_m), use_container_width=True)

    fancy_divider()
    section_header("Mechanism of Resistance")
    mechs_m, banners_m, greens_m, gnotes_m = run_mechanisms_and_therapy_for(organism_m, final_m)

    if mechs_m:
        for m in mechs_m:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Mechanism", bg="var(--primary)")} {m}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    for b in banners_m:
        st.markdown(f"""
        <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
        {badge("Caution", bg="var(--muted)", fg="#ffffff")} {b}
        </div>
        """, unsafe_allow_html=True)

    for g in greens_m:
        st.markdown(f"""
        <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
        {badge("Favorable", bg="var(--primary)")} {g}
        </div>
        """, unsafe_allow_html=True)

    fancy_divider()
    section_header("Therapy Guidance")
    if gnotes_m:
        for note in gnotes_m:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Therapy", bg="var(--primary)")} {note}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    refs_m = _collect_mech_ref_keys(organism_m, mechs_m, banners_m)
    render_references(refs_m)

    st.stop()

if group == "Anaerobes":
    section_header("Anaerobes")
    organism_a = st.selectbox("Organism (Anaerobes)", ANAEROBE_ORGS, key="anaerobe_org")

    intrinsic_a = anaerobe_intrinsic_map(organism_a)

    section_header("Susceptibility Inputs")
    st.caption("Panel requested: Penicillin, Ampicillin/Sulbactam, Meropenem, Clindamycin, Metronidazole.")
    user_a, final_a = _collect_panel_inputs(ANAEROBE_PANEL, intrinsic_a, keyprefix="ANA_ab")

    st.subheader("Consolidated results")
    rows_a = []
    for ab in ANAEROBE_PANEL:
        if final_a[ab] is None:
            continue
        src = "Intrinsic rule" if intrinsic_a.get(ab) else "User-entered"
        rows_a.append({"Antibiotic": ab, "Result": final_a[ab], "Source": src})
    if rows_a:
        st.dataframe(pd.DataFrame(rows_a), use_container_width=True)

    fancy_divider()
    section_header("Mechanism of Resistance")
    mechs_a, banners_a, greens_a, gnotes_a = run_mechanisms_and_therapy_for(organism_a, final_a)

    if mechs_a:
        for m in mechs_a:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Mechanism", bg="var(--primary)")} {m}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No major resistance mechanism identified based on current inputs.")

    for b in banners_a:
        st.markdown(f"""
        <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
        {badge("Caution", bg="var(--muted)", fg="#ffffff")} {b}
        </div>
        """, unsafe_allow_html=True)

    for g in greens_a:
        st.markdown(f"""
        <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
        {badge("Favorable", bg="var(--primary)")} {g}
        </div>
        """, unsafe_allow_html=True)

    fancy_divider()
    section_header("Therapy Guidance")
    if gnotes_a:
        for note in gnotes_a:
            st.markdown(f"""
            <div style="border-left:4px solid var(--primary); border:1px solid var(--border); padding:0.4rem 0.6rem; margin-bottom:0.4rem; background:var(--card2);">
            {badge("Therapy", bg="var(--primary)")} {note}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No specific guidance triggered yet — enter more susceptibilities.")

    refs_a = _collect_mech_ref_keys(organism_a, mechs_a, banners_a)
    render_references(refs_a)

    st.stop()

fancy_divider()
st.markdown("""
<p style="text-align:center; font-size:0.8rem; color:#3f5649;">
<strong>MechID</strong> is a heuristic teaching tool for pattern recognition in antimicrobial resistance.<br>
Always interpret results in context of patient, local epidemiology, and formal guidance (IDSA, CLSI, EUCAST).<br>
© MechID · (ID)as &amp; O(ID)nions
</p>
""", unsafe_allow_html=True)
