import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime

# =========================
# CONFIGURATION & TAUX
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="wide")
TAUX_AR_TO_EUR = 5000 

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    .resume-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .total-container { background-color: #1e88e5; color: white; padding: 10px; border-radius: 8px; text-align: center; font-size: 22px; font-weight: bold; }
    .cat-title { color: #1e88e5; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #eee; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# Fichiers de données
HIST_DEVIS = "historique_devis.csv"
HIST_FACTURES = "historique_factures.csv"
DATA_FILE = "data.csv"
LOGO_FILE = "logo.png"

# --- INITIALISATION DES FICHIERS ---
for f in [HIST_DEVIS, HIST_FACTURES]:
    if not os.path.exists(f):
        pd.DataFrame(columns=["Date", "Ref", "Client", "Circuit", "Total", "Options"]).to_csv(f, index=False, encoding='utf-8-sig')

def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'â': 'a', 'î': 'i', 'ï': 'i', 'ô': 'o', 'û': 'u', 'ù': 'u', '’': "'"}
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

# --- GÉNÉRATION DU TICKET PDF ---
def generate_thermal_ticket(type_doc, data, client_name, ref, options_txt):
    pdf = FPDF(format=(80, 280))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)
    
    # Logo
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=25, y=8, w=30)
        pdf.ln(32)
    
    # En-tête Agence
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(72, 5, "LEMUR MACACO TOURS", ln=True, align='C')
    pdf.set_font("Helvetica", '', 7)
    pdf.cell(72, 4, "Nosy Be - Madagascar", ln=True, align='C')
    pdf.cell(72, 4, "Contact: +261 32 00 000 00", ln=True, align='C')
    pdf.cell(72, 4, "NIF: 123456789 | STAT: 98765", ln=True, align='C')
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    # Type Document
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(72, 6, type_doc.upper(), ln=True, align='C')
    
    # Infos Client (Forcé à gauche)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_x(4)
    pdf.cell(72, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True, align='L')
    pdf.set_x(4)
    pdf.cell(72, 5, f"Ref: {clean_text(ref)}", ln=True, align='L')
    pdf.set_x(4)
    pdf.cell(72, 5, f"Client: {clean_text(client_name)}", ln=True, align='L')
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    # Détails Circuit (Forcé à gauche)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_x(4)
    pdf.multi_cell(72, 5, clean_text(f"Circuit: {data['Circuit']}"), align='L')
    
    pdf.set_font("Helvetica", '', 8)
    pdf.set_x(4)
    pdf.cell(72, 5, f"Pax: {data['Pax']} | Jours: {data['Jours']}", ln=True, align='L')
    
    pdf.ln(1); pdf.set_font("Helvetica", 'I', 7)
    pdf.set_x(4)
    pdf.multi_cell(72, 4, clean_text(f"Options: {options_txt}"), align='L')
    
    # Totaux (Droite)
    pdf.ln(3); pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(72, 8, f"TOTAL: {data['Total']:,.2f} EUR", ln=True, align='R')
    pdf.set_text_color(230, 74, 25)
    pdf.cell(72, 6, f"Soit: {data['Total'] * TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align='R')
    
    pdf.set_text_color(0, 0, 0); pdf.ln(5); pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(72, 5, "Merci de votre confiance!", ln=True, align='C')
    
    # Sortie binaire sécurisée
    return bytes(pdf.output())

# =========================
# NAVIGATION PAR ONGLETS
# =========================
tab1, tab2, tab3 = st.tabs(["📝 NOUVEAU DEVIS", "🧾 GÉNÉRER FACTURE", "📂 HISTORIQUES"])

# --- ONGLET 1 : DEVIS ---
with tab1:
    if os.path.exists(DATA_FILE):
        df_excu = pd.read_csv(DATA_FILE)
        df_excu['Prix'] = pd.to_numeric(df_excu['Prix'], errors='coerce').fillna(0)

        c1, c2 = st.columns(2)
        nom_c = c1.text_input("👤 Nom du Client", key="devis_nom")
        cont_c = c2.text_input("📱 Contact", key="devis_cont")
        
        type_e = st.selectbox("🌍 Type de Circuit", [""] + sorted(df_excu["Type"].unique().tolist()))
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            f1, f2 = st.columns(2)
            formule = f1.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()))
            transport = f2.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()))
            
            circuit = st.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()))
            
            row = df_f[df_f["Circuit"] == circuit].iloc[0]
            p1, p2 = st.columns(2)
            nb_pax = p1.number_input("👥 Pax", min_value=1, value=2)
            nb_jours = p2.number_input("📅 Jours", min_value=1, value=3)
            
            # Options détaillées
            supp_ar = 0.0
            opts_list = []
            col_o1, col_o2, col_o3 = st.columns(3)
            with col_o1:
                st.markdown("**🏞️ SITES**")
                sites = {"Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000, "Trois Baies": 10000}
                for s, p in sites.items():
                    if st.checkbox(s): supp_ar += p; opts_list.append(s)
            with col_o2:
                st.markdown("**👥 PERSONNEL**")
                persos = {"Guide": 100000, "Cuisinier": 30000, "Porteur": 20000}
                for s, p in persos.items():
                    if st.checkbox(s): supp_ar += (p * nb_jours); opts_list.append(f"{s}({nb_jours}j)")
            with col_o3:
                st.markdown("**🚚 LOGISTIQUE**")
                logis = {"Location 4x4": 300000, "Carburant": 1200000, "Transfert": 200000}
                for s, p in logis.items():
                    if st.checkbox(s): 
                        supp_ar += (p * nb_jours) if "Location" in s else p
                        opts_list.append(s)

            marge = st.slider("📈 Marge Bénéficiaire %", 0, 100, 20)
            total_eur = ((float(row['Prix']) + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)
            total_ar = total_eur * TAUX_AR_TO_EUR

            # Résumé visuel
            st.markdown(f"""
                <div class="resume-box">
                    <div class="total-container">{total_eur:,.2f} € / {total_ar:,.0f} Ar</div>
                    <div class="cat-title">RÉSUMÉ</div>
                    <small><b>Client:</b> {nom_c} | <b>Circuit:</b> {circuit} | <b>Options:</b> {', '.join(opts_list)}</small>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔥 GÉNÉRER LE DEVIS"):
                if nom_c:
                    df_h = pd.read_csv(HIST_DEVIS)
                    ref = f"D{len(df_h)+1:04d}-{nom_c.upper()}"
                    all_opts = f"Transp: {transport}, " + ", ".join(opts_list)
                    
                    # Sauvegarde CSV
                    new_data = pd.DataFrame([{"Date": datetime.now().strftime("%d/%m/%Y"), "Ref": ref, "Client": nom_c, "Circuit": circuit, "Total": round(total_eur, 2), "Options": all_opts}])
                    pd.concat([df_h, new_data]).to_csv(HIST_DEVIS, index=False, encoding='utf-8-sig')
                    
                    # PDF
                    pdf_bytes = generate_thermal_ticket("Devis", {"Circuit": circuit, "Pax": nb_pax, "Jours": nb_jours, "Total": total_eur}, nom_c, ref, all_opts)
                    st.download_button("📥 Télécharger le Devis", pdf_bytes, f"{ref}.pdf", "application/pdf")
                else:
                    st.error("Veuillez entrer le nom du client.")

# --- ONGLET 2 : FACTURE ---
with tab2:
    st.subheader("🧾 Transformation Devis en Facture")
    df_devis = pd.read_csv(HIST_DEVIS)
    if not df_devis.empty:
        choix_ref = st.selectbox("Sélectionner un Devis existant", [""] + df_devis["Ref"].tolist()[::-1])
        if choix_ref:
            d_info = df_devis[df_devis["Ref"] == choix_ref].iloc[0]
            st.info(f"📋 **Devis :** {choix_ref} | **Client :** {d_info['Client']} | **Montant :** {d_info['Total']} €")
            
            if st.button("✅ GÉNÉRER LA FACTURE"):
                df_f = pd.read_csv(HIST_FACTURES)
                ref_f = choix_ref.replace("D", "F")
                
                # Sauvegarde Historique Facture
                new_f = pd.DataFrame([d_info])
                new_f["Ref"] = ref_f
                new_f["Date"] = datetime.now().strftime("%d/%m/%Y")
                pd.concat([df_f, new_f]).to_csv(HIST_FACTURES, index=False, encoding='utf-8-sig')
                
                # PDF Facture (Note: les pax/jours sont mis à '-' car non stockés dans l'historique csv simplifié)
                pdf_f = generate_thermal_ticket("Facture", {"Circuit": d_info['Circuit'], "Pax": "-", "Jours": "-", "Total": d_info['Total']}, d_info['Client'], ref_f, d_info['Options'])
                st.download_button("📥 Télécharger la Facture", pdf_f, f"{ref_f}.pdf", "application/pdf")
    else:
        st.warning("Aucun devis trouvé dans l'historique.")

# --- ONGLET 3 : HISTORIQUES ---
with tab3:
    st.subheader("📂 Suivi des Activités")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📒 Historique Devis")
        st.dataframe(pd.read_csv(HIST_DEVIS), use_container_width=True)
        
    with col2:
        st.markdown("### 📗 Historique Factures")
        st.dataframe(pd.read_csv(HIST_FACTURES), use_container_width=True)
