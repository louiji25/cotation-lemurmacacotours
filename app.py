import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
import base64

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")
TAUX_AR_TO_EUR = 5000 

st.markdown("""
    <style>
    .resumé-box { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; box-shadow: 2px 2px 15px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3em; }
    .cat-title { color: #1e88e5; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
DATA_FILE = "data.csv"
LOGO_FILE = "logo.png"

if 'df_h' not in st.session_state:
    if os.path.exists(HIST_FILE):
        st.session_state.df_h = pd.read_csv(HIST_FILE)
    else:
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Total", "Circuit", "Formule", "Transport", "Options"])

def get_next_ref(prefix):
    count = len(st.session_state.df_h) + 1
    return f"{prefix}{count:06d}"

def clean_text(text):
    if not isinstance(text, str): return str(text)
    rep = {'é': 'e', 'è': 'e', 'à': 'a', 'ô': 'o', '’': "'", 'ê': 'e', 'ë': 'e', 'î': 'i', 'ï': 'i', 'û': 'u', 'ù': 'u'}
    for old, new in rep.items(): text = text.replace(old, new)
    return text

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURES", "⚙️ CONFIG"])

with tab1:
    if os.path.exists(DATA_FILE):
        # Sécurité sur la lecture du prix pour éviter le "nan"
        df_excu = pd.read_csv(DATA_FILE)
        df_excu["Prix"] = pd.to_numeric(df_excu["Prix"], errors='coerce').fillna(0)
        
        c1, c2 = st.columns(2)
        nom_c = c1.text_input("👤 Nom du Client")
        cont_c = c2.text_input("📞 Numéro Client / WhatsApp")
        
        type_e = st.selectbox("🌍 Type de voyage", [""] + sorted(df_excu["Type"].unique().tolist()))
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            
            col1, col2, col3 = st.columns(3)
            formule = col1.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()))
            transport = col2.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()))
            circuit = col3.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()))
            
            row = df_f[df_f["Circuit"] == circuit].iloc[0]
            col_a, col_b = st.columns(2)
            nb_pax = col_a.number_input("👥 Pax", min_value=1, value=1)
            nb_jours = col_b.number_input("📅 Jours", min_value=1, value=1)
            
            # --- SEPARATION DES OPTIONS ---
            supp_ar = 0.0
            opt_sites, opt_perso, opt_logis = [], [], []

            st.write("### 🛠️ Options du Devis")
            
            with st.expander("🏞️ SITES (Frais d'entrée)"):
                sites = {"Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000, "Trois Baies": 10000}
                for s, p in sites.items():
                    if st.checkbox(f"{s} ({p:,} Ar)"):
                        supp_ar += p; opt_sites.append(s)

            with st.expander("👥 PERSONNEL (Par jour)"):
                persos = {"Guide": 100000, "Cuisinier": 30000, "Porteur": 20000}
                for p, v in persos.items():
                    if st.checkbox(f"{p} ({v:,} Ar/j)"):
                        supp_ar += (v * nb_jours); opt_perso.append(f"{p}")

            with st.expander("🚚 LOGISTIQUE"):
                logis = {"Location 4x4": 300000, "Carburant": 1200000, "Transfert Vedette": 500000}
                for l, v in logis.items():
                    if st.checkbox(f"{l} ({v:,} Ar)"):
                        supp_ar += (v * nb_jours) if "4x4" in l else v
                        opt_logis.append(l)

            marge = st.slider("📈 Marge %", 0, 100, 20)
            
            # Calcul sécurisé (évite le nan si Prix est nul)
            prix_base_eur = float(row['Prix'])
            total_eur = ((prix_base_eur + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)

            # --- RÉSUMÉ DÉTAILLÉ ---
            st.markdown(f"""
            <div class="resumé-box">
                <b>Client :</b> {nom_c if nom_c else "..."} | {cont_c}<br>
                <b>Circuit :</b> {circuit} ({formule})<br>
                <b>Transport :</b> {transport}<br>
                
                <div class="cat-title">SITES</div>
                <small>{", ".join(opt_sites) if opt_sites else "Aucun"}</small>
                
                <div class="cat-title">PERSONNEL</div>
                <small>{", ".join(opt_perso) if opt_perso else "Aucun"}</small>
                
                <div class="cat-title">LOGISTIQUE</div>
                <small>{", ".join(opt_logis) if opt_logis else "Aucune"}</small>
                
                <hr>
                <div style="display:flex; justify-content:space-between; align-items:center">
                    <span style="font-size:22px"><b>TOTAL</b></span>
                    <div style="text-align:right">
                        <span style="font-size:22px; color:#1e88e5"><b>{total_eur:,.2f} €</b></span><br>
                        <span style="font-size:18px; color:#e64a19"><b>{total_eur*TAUX_AR_TO_EUR:,.0f} Ar</b></span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚀 VALIDER & TÉLÉCHARGER"):
                if not nom_c: 
                    st.error("Veuillez saisir le nom du client")
                else:
                    ref_id = get_next_ref("D")
                    ref_full = f"{ref_id}-{nom_c.upper()}"
                    all_opts = f"SITES: {', '.join(opt_sites)} | PERSO: {', '.join(opt_perso)} | LOGIS: {', '.join(opt_logis)}"
                    # ... (Suite du code de sauvegarde et génération PDF identique)
