import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
import base64

# =========================
# CONFIGURATION & TAUX
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")
TAUX_AR_TO_EUR = 5000 

st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px !important; border-radius: 10px; margin-top: 10px; }
    .resume-box { background-color: #fdfdfd; padding: 20px; border-radius: 10px; border-left: 5px solid #1e88e5; box-shadow: 0px 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .total-container { background-color: #1e88e5; color: white; padding: 15px; border-radius: 10px; text-align: center; font-size: 22px; font-weight: bold; margin: 10px 0; }
    .cat-title { color: #1e88e5; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #eee; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
INFO_FILE = "infos.csv"
DATA_FILE = "data.csv"
LOGO_FILE = "logo.png"

# --- INITIALISATION ---
if 'df_h' not in st.session_state:
    if os.path.exists(HIST_FILE):
        st.session_state.df_h = pd.read_csv(HIST_FILE, encoding='utf-8-sig')
    else:
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Total"])

def get_info_df():
    if os.path.exists(INFO_FILE): return pd.read_csv(INFO_FILE, encoding='utf-8-sig')
    return pd.DataFrame([["Nom", "LAKA AM'LAY"], ["Contact", "+261 34 00 000 00"]], columns=['Champ', 'Valeur'])

def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'â': 'a', 'î': 'i', 'ï': 'i', 'ô': 'o', 'û': 'u', 'ù': 'u', '’': "'"}
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

# --- CORRECTION DE L'ERREUR ATTRIBUTERROR ---
def generate_thermal_ticket(type_doc, data, client_name, ref, contact="", options_text=""):
    pdf = FPDF(format=(80, 270))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)
    
    # En-tête
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(72, 8, "LAKA AM'LAY", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(72, 4, f"Ref: {clean_text(ref)}", ln=True, align='C')
    pdf.cell(72, 4, f"Client: {clean_text(client_name)}", ln=True, align='C')
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True); pdf.ln(2)
    
    # Détails
    pdf.set_font("Helvetica", 'B', 9)
    pdf.multi_cell(72, 5, clean_text(f"Circuit: {data.get('Circuit', 'N/A')}"))
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(72, 5, f"Pax: {data.get('Pax', 1)} | Jours: {data.get('Jours', 1)}", ln=True)
    
    if options_text:
        pdf.set_font("Helvetica", 'I', 7)
        pdf.multi_cell(72, 4, clean_text(f"Options: {options_text}"))
    
    # Total
    pdf.ln(2); pdf.set_font("Helvetica", 'B', 11)
    total_eur = float(data.get('Total', 0))
    pdf.cell(72, 8, f"TOTAL: {total_eur:,.2f} EUR", ln=True, align='R')
    pdf.cell(72, 6, f"Soit: {total_eur * TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align='R')
    
    # Sortie sécurisée pour FPDF2
    output_pdf = pdf.output()
    if isinstance(output_pdf, str):
        return output_pdf.encode('latin-1', 'replace')
    return bytes(output_pdf)

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURE", "⚙️ CONFIG"])

with tab1:
    if os.path.exists(DATA_FILE):
        df_excu = pd.read_csv(DATA_FILE, encoding='utf-8-sig')
        df_excu['Prix'] = pd.to_numeric(df_excu['Prix'], errors='coerce').fillna(0)
        
        c1, c2 = st.columns(2)
        nom_c = c1.text_input("👤 Nom du Client")
        cont_c = c2.text_input("📱 WhatsApp / Email")
        
        type_e = st.selectbox("🌍 Type", [""] + sorted(df_excu["Type"].unique().tolist()))
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            f1, f2 = st.columns(2)
            formule = f1.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()))
            transport = f2.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()))
            
            circuit = st.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()))
            
            row = df_f[df_f["Circuit"] == circuit].iloc[0]
            prix_base = float(row['Prix'])
            
            p1, p2 = st.columns(2)
            nb_pax = p1.number_input("👥 Pax", min_value=1, value=1)
            nb_jours = p2.number_input("📅 Jours", min_value=1, value=1)
            
            # --- OPTIONS ---
            supp_ar = 0.0
            opt_sites, opt_perso, opt_logis = [], [], []

            st.write("### 🛠️ Options additionnelles")
            col_opt1, col_opt2, col_opt3 = st.columns(3)
            with col_opt1:
                st.markdown("**🏞️ SITES**")
                sites = {"Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000}
                for s, p in sites.items():
                    if st.checkbox(s): supp_ar += p; opt_sites.append(s)
            with col_opt2:
                st.markdown("**👥 PERSONNEL**")
                persos = {"Guide": 100000, "Cuisinier": 30000}
                for p, v in persos.items():
                    if st.checkbox(p): supp_ar += (v * nb_jours); opt_perso.append(f"{p}({nb_jours}j)")
            with col_opt3:
                st.markdown("**🚚 LOGISTIQUE**")
                logis = {"Carburant": 1200000, "Transfert": 200000}
                for l, v in logis.items():
                    if st.checkbox(l): supp_ar += v; opt_logis.append(l)

            marge = st.slider("📈 Marge %", 0, 100, 20)
            total_eur = ((prix_base + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)
            total_ar = total_eur * TAUX_AR_TO_EUR

            # --- AFFICHAGE TOTAL SIMPLE ---
            st.markdown(f"""<div class="total-container">{total_eur:,.2f} € / {total_ar:,.0f} Ar</div>""", unsafe_allow_html=True)

            # --- RÉSUMÉ & VALIDATION ---
            if st.button("✅ VALIDER ET GENERER LE TICKET"):
                if not nom_c:
                    st.error("Veuillez saisir le nom du client")
                else:
                    ref_d = f"D{datetime.now().strftime('%y%m%d%H%M')}-{nom_c.upper()}"
                    opts_txt = ", ".join(opt_sites + opt_perso + opt_logis)
                    
                    # Affichage du résumé
                    st.markdown(f"""
                    <div class="resume-box">
                        <h4 style="margin-top:0;">📋 Résumé du Devis</h4>
                        <b>Référence :</b> {ref_d}<br>
                        <b>Client :</b> {nom_c} ({cont_c})<br>
                        <b>Circuit :</b> {circuit} [{formule}]<br>
                        <div class="cat-title">OPTIONS SÉLECTIONNÉES</div>
                        <small>{opts_txt if opts_txt else "Aucune"}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Génération et Téléchargement
                    data_save = {"Circuit": circuit, "Pax": nb_pax, "Jours": nb_jours, "Total": total_eur}
                    pdf_bytes = generate_thermal_ticket("Devis", data_save, nom_c, ref_d, cont_c, opts_txt)
                    
                    st.download_button(label="📥 TÉLÉCHARGER LE TICKET", 
                                       data=pdf_bytes, 
                                       file_name=f"{ref_d}.pdf", 
                                       mime="application/pdf")
    else:
        st.error("Fichier data.csv introuvable.")

# Onglets Facture et Config restent fonctionnels avec la même logique de téléchargement...
