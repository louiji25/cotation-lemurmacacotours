import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime

# =========================
# CONFIGURATION & TAUX
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")
TAUX_AR_TO_EUR = 5000 

st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3.5em; font-size: 16px !important; border-radius: 10px; margin-top: 10px; }
    .resume-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .total-container { background-color: #1e88e5; color: white; padding: 15px; border-radius: 10px; text-align: center; font-size: 22px; font-weight: bold; margin: 10px 0; }
    .cat-title { color: #1e88e5; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #eee; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
DATA_FILE = "data.csv"
LOGO_FILE = "logo.png"

# --- INITIALISATION ---
if 'df_h' not in st.session_state:
    st.session_state.df_h = pd.read_csv(HIST_FILE) if os.path.exists(HIST_FILE) else pd.DataFrame(columns=["Date", "Ref", "Client", "Total"])

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
    
    # En-tête Agence (Centré)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(72, 6, "LEMUR MACACO TOURS", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(72, 4, "NOM DE VOTRE AGENCE", ln=True, align='C')
    pdf.cell(72, 4, "Adresse: Nosy Be - Madagascar", ln=True, align='C')
    pdf.cell(72, 4, "Contact: +261 32 00 000 00", ln=True, align='C')
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    # Infos Client (Gauche)
    pdf.set_font("Helvetica", '', 8)
    pdf.set_x(4)
    pdf.cell(72, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True, align='L')
    pdf.set_x(4)
    pdf.cell(72, 5, f"Ref: {clean_text(ref)}", ln=True, align='L')
    pdf.set_x(4)
    pdf.cell(72, 5, f"Client: {clean_text(client_name)}", ln=True, align='L')
    pdf.ln(1)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(72, 6, type_doc.upper(), ln=True, align='C')
    pdf.ln(1)
    
    # Détails Circuit (Gauche)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.set_x(4)
    pdf.multi_cell(72, 5, clean_text(f"Circuit: {data['Circuit']}"), align='L')
    
    pdf.set_font("Helvetica", '', 8)
    pdf.set_x(4)
    pdf.cell(72, 5, f"Pax: {data['Pax']} | Jours: {data['Jours']}", ln=True, align='L')
    
    pdf.ln(1)
    pdf.set_font("Helvetica", 'I', 7)
    pdf.set_x(4)
    pdf.multi_cell(72, 4, clean_text(f"Options: {options_txt}"), align='L')
    
    # Totaux (Droite)
    pdf.ln(3); pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(72, 8, f"TOTAL: {data['Total']:,.2f} EUR", ln=True, align='R')
    pdf.set_text_color(230, 74, 25)
    pdf.cell(72, 6, f"Soit: {data['Total'] * TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align='R')
    
    pdf.set_text_color(0, 0, 0); pdf.ln(5); pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(72, 5, "Merci de votre confiance!", ln=True, align='C')
    
    # Sortie sécurisée
    output = pdf.output()
    return bytes(output) if not isinstance(output, str) else output.encode('latin-1')

# =========================
# INTERFACE STREAMLIT
# =========================
if os.path.exists(DATA_FILE):
    df_excu = pd.read_csv(DATA_FILE)
    df_excu['Prix'] = pd.to_numeric(df_excu['Prix'], errors='coerce').fillna(0)

    st.title("📝 Nouveau Devis")
    c1, c2 = st.columns(2)
    nom_c = c1.text_input("👤 Nom du Client")
    cont_c = c2.text_input("📱 Contact Client")
    
    type_e = st.selectbox("🌍 Type de Voyage", [""] + sorted(df_excu["Type"].unique().tolist()))
    
    if type_e:
        df_f = df_excu[df_excu["Type"] == type_e]
        f1, f2 = st.columns(2)
        formule = f1.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()))
        transport = f2.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()))
        
        circuit = st.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()))
        
        row = df_f[df_f["Circuit"] == circuit].iloc[0]
        prix_base = float(row['Prix'])
        
        p1, p2 = st.columns(2)
        nb_pax = p1.number_input("👥 Nombre de Pax", min_value=1, value=2)
        nb_jours = p2.number_input("📅 Nombre de Jours", min_value=1, value=3)
        
        # --- OPTIONS SEPAREES ---
        supp_ar = 0.0
        opt_sites, opt_perso, opt_logis = [], [], []

        st.write("### 🛠️ Options du Devis")
        col_opt1, col_opt2, col_opt3 = st.columns(3)
        
        with col_opt1:
            st.markdown("**🏞️ SITES**")
            sites = {"Montagne des Français": 30000, "Trois Baies": 10000, "Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000, "Daraina": 60000, "Marojejy": 140000}
            for s, p in sites.items():
                if st.checkbox(s): supp_ar += p; opt_sites.append(s)

        with col_opt2:
            st.markdown("**👥 PERSONNEL**")
            persos = {"Guide": 100000, "Cuisinier": 30000, "Porteur": 20000}
            for p, v in persos.items():
                if st.checkbox(p): supp_ar += (v * nb_jours); opt_perso.append(f"{p} ({nb_jours}j)")

        with col_opt3:
            st.markdown("**🚚 LOGISTIQUE**")
            logis = {"Location 4x4": 300000, "Location voiture": 250000, "Carburant": 1200000, "Transfert hotel": 200000, "Ankify -> Nosy Be": 500000}
            for l, v in logis.items():
                if st.checkbox(l): 
                    supp_ar += (v * nb_jours) if "Location" in l else v
                    opt_logis.append(l)

        marge = st.slider("📈 Marge Bénéficiaire %", 0, 100, 20)
        total_eur = ((prix_base + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)
        total_ar = total_eur * TAUX_AR_TO_EUR

        # --- RÉSUMÉ ---
        st.markdown(f"""
            <div class="resume-box">
                <b>Client :</b> {nom_c} | <b>Circuit :</b> {circuit} [{formule}]<br>
                <div class="cat-title">SITES</div> <small>{', '.join(opt_sites) if opt_sites else 'Base'}</small>
                <div class="cat-title">PERSONNEL</div> <small>{', '.join(opt_perso) if opt_perso else 'Base'}</small>
                <div class="cat-title">LOGISTIQUE</div> <small>{', '.join(opt_logis) if opt_logis else 'Base'}</small>
                <hr>
                <div class="total-container">
                    {total_eur:,.2f} € / {total_ar:,.0f} Ar
                </div>
            </div>
        """, unsafe_allow_html=True)

        if st.button("✅ GÉNÉRER ET TÉLÉCHARGER LE TICKET"):
            if not nom_c: 
                st.error("Veuillez saisir le nom du client")
            else:
                ref_d = f"D{len(st.session_state.df_h)+1:06d}-{nom_c.upper()}"
                all_opts = f"Transp: {transport}, " + ", ".join(opt_sites + opt_perso + opt_logis)
                
                data_pdf = {"Circuit": circuit, "Pax": nb_pax, "Jours": nb_jours, "Total": total_eur}
                pdf_output = generate_thermal_ticket("Devis", data_pdf, nom_c, ref_d, all_opts)
                
                # Mise à jour historique
                new_row = pd.DataFrame([{"Date": datetime.now().strftime("%Y-%m-%d"), "Ref": ref_d, "Client": nom_c, "Total": total_eur}])
                st.session_state.df_h = pd.concat([st.session_state.df_h, new_row], ignore_index=True)
                st.session_state.df_h.to_csv(HIST_FILE, index=False)
                
                st.download_button(label="📥 Télécharger le Ticket PDF", 
                                   data=pdf_output, 
                                   file_name=f"{ref_d}.pdf", 
                                   mime="application/pdf")
else:
    st.error("Le fichier data.csv est manquant dans le répertoire.")
