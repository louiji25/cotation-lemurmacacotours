import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# =========================
# CONFIGURATION & CONNEXION
# =========================
st.set_page_config(page_title="LEMUR MACACO TOURS - COTATION", layout="wide")
TAUX_AR_TO_EUR = 5000 

# Connexion Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Colonnes standards pour initialisation
COLONNES = ["Date", "Ref", "Client", "Circuit", "Formule", "Pax", "Total", "Options"]

# --- STYLE CSS ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    .resume-box { background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .total-container { background-color: #1e88e5; color: white; padding: 10px; border-radius: 8px; text-align: center; font-size: 22px; font-weight: bold; }
    .cat-title { color: #1e88e5; font-weight: bold; margin-top: 10px; border-bottom: 1px solid #eee; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

DATA_FILE = "data.csv"
LOGO_FILE = "logo.png"

# --- FONCTIONS DE CACHE & SAUVEGARDE ---
@st.cache_data(ttl=600)  
def get_cached_data(worksheet_name):
    """Lit les données avec cache"""
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLONNES)
        # S'assurer que les colonnes sont dans le bon ordre
        for col in COLONNES:
            if col not in df.columns:
                df[col] = None
        return df[COLONNES]
    except Exception:
        return pd.DataFrame(columns=COLONNES)

def save_to_gsheets(new_row, worksheet_name):
    """Sauvegarde vers Google Sheets"""
    try:
        # Lire les données actuelles sans cache
        try:
            existing_data = conn.read(worksheet=worksheet_name, ttl=0)
            if existing_data is None: existing_data = pd.DataFrame(columns=COLONNES)
        except Exception:
            existing_data = pd.DataFrame(columns=COLONNES)
        
        # Concaténation propre pour éviter les FutureWarning
        if existing_data.empty:
            updated_df = new_row
        else:
            updated_df = pd.concat([existing_data.dropna(how='all', axis=1), new_row], ignore_index=True)
        
        # Mise à jour vers Google Sheets
        conn.update(worksheet=worksheet_name, data=updated_df)
        st.cache_data.clear() 
        return True
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")
        return False

# --- FONCTIONS UTILES ---
def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'â': 'a', 'î': 'i', 'ï': 'i', 'ô': 'o', 'û': 'u', 'ù': 'u', '’': "'"}
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

def reset_form():
    for key in ["devis_nom", "devis_cont", "type_v", "pax", "jours"]:
        if key in st.session_state:
            if key == "pax": st.session_state[key] = 2
            elif key == "jours": st.session_state[key] = 3
            else: st.session_state[key] = ""
    st.rerun()

# --- GÉNÉRATION DU TICKET PDF (Version fpdf2) ---
def generate_thermal_ticket(type_doc, data, client_name, ref, options_txt):
    pdf = FPDF(format=(80, 250)) # Hauteur ajustée
    pdf.add_page()
    pdf.set_margin(4)
    
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=25, y=8, w=30)
        pdf.ln(32)
    
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(72, 5, "LEMUR MACACO TOURS", ln=True, align='C')
    pdf.set_font("Helvetica", '', 7)
    pdf.cell(72, 4, "Andrekareka - Hell Ville - Nosy Be - Madagascar", ln=True, align='C')
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(72, 6, type_doc.upper(), ln=True, align='C')
    
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(72, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True)
    pdf.cell(72, 5, f"Ref: {clean_text(ref)}", ln=True)
    pdf.cell(72, 5, f"Client: {clean_text(client_name)}", ln=True)
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    
    pdf.set_font("Helvetica", 'B', 9)
    pdf.multi_cell(72, 5, clean_text(f"Circuit: {data['Circuit']}"))
    
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(72, 5, f"Pax: {data['Pax']} | Jours: {data['Jours']}", ln=True)
    
    pdf.ln(1); pdf.set_font("Helvetica", 'I', 7)
    pdf.multi_cell(72, 4, clean_text(f"Options: {options_txt}"))
    
    pdf.ln(3); pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(72, 8, f"TOTAL: {data['Total']:,.2f} EUR", ln=True, align='R')
    pdf.set_text_color(230, 74, 25)
    pdf.cell(72, 6, f"Soit: {data['Total'] * TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align='R')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4); pdf.cell(72, 5, "Merci de votre confiance!", ln=True, align='C')
    
    return bytes(pdf.output())

# =========================
# NAVIGATION PAR ONGLETS
# =========================
tab1, tab2, tab3 = st.tabs(["📝 NOUVEAU DEVIS", "🧾 GÉNÉRER FACTURE", "📂 HISTORIQUES"])

with tab1:
    if os.path.exists(DATA_FILE):
        df_excu = pd.read_csv(DATA_FILE)
        df_excu['Prix'] = pd.to_numeric(df_excu['Prix'], errors='coerce').fillna(0)

        col_new1, col_new2 = st.columns([1, 5])
        with col_new1:
            if st.button("🆕 Nouveau"): reset_form()

        c1, c2 = st.columns(2)
        nom_c = c1.text_input("👤 Nom du Client", key="devis_nom")
        cont_c = c2.text_input("📱 Contact", key="devis_cont")
        
        type_e = st.selectbox("🌍 Type de Circuit", [""] + sorted(df_excu["Type"].unique().tolist()), key="type_v")
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            f1, f2 = st.columns(2)
            formule = f1.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()))
            transport = f2.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()))
            circuit = st.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()))
            
            row = df_f[df_f["Circuit"] == circuit].iloc[0]
            p1, p2 = st.columns(2)
            nb_pax = p1.number_input("👥 Pax", min_value=1, key="pax")
            nb_jours = p2.number_input("📅 Jours", min_value=1, key="jours")
            
            # Calculs
            supp_ar = 0.0
            opts_list = []
            col_o1, col_o2, col_o3 = st.columns(3)
            with col_o1:
                st.markdown("**🏞️ SITES**")
                sites = {"Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000}
                for s, p in sites.items():
                    if st.checkbox(s): supp_ar += p; opts_list.append(s)
            with col_o2:
                st.markdown("**👥 PERS.**")
                persos = {"Guide": 100000, "Cuisinier": 30000}
                for s, p in persos.items():
                    if st.checkbox(s): supp_ar += (p * nb_jours); opts_list.append(f"{s}({nb_jours}j)")
            with col_o3:
                st.markdown("**🚚 LOG.**")
                if st.checkbox("Location voiture"): 
                    supp_ar += (300000 * nb_jours); opts_list.append("Loc. Voitur")

            marge = st.slider("📈 Marge %", 0, 100, 20)
            total_eur = ((float(row['Prix']) + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)
            total_ar = total_eur * TAUX_AR_TO_EUR

            st.markdown(f"""
                <div class="resume-box">
                    <div class="total-container">{total_eur:,.2f} € / {total_ar:,.0f} Ar</div>
                </div>
            """, unsafe_allow_html=True)

            if st.button("🔥 GÉNÉRER LE DEVIS"):
                if nom_c:
                    df_h = get_cached_data("devis")
                    ref = f"D{len(df_h)+1:04d}-{nom_c.upper()[:5]}"
                    all_opts = f"Transp: {transport}, " + ", ".join(opts_list)
                    
                    new_data = pd.DataFrame([{
                        "Date": datetime.now().strftime("%d/%m/%Y"), 
                        "Ref": ref, "Client": nom_c, "Circuit": circuit, 
                        "Formule": formule, "Pax": nb_pax, 
                        "Total": round(total_eur, 2), "Options": all_opts
                    }])
                    
                    if save_to_gsheets(new_data, "devis"):
                        pdf_bytes = generate_thermal_ticket("Devis", {"Circuit": circuit, "Pax": nb_pax, "Jours": nb_jours, "Total": total_eur}, nom_c, ref, all_opts)
                        st.download_button("📥 Télécharger PDF", pdf_bytes, f"{ref}.pdf", "application/pdf")
                else: st.error("Nom du client requis.")

with tab2:
    st.subheader("🧾 Conversion Devis -> Facture")
    df_devis = get_cached_data("devis")
    if not df_devis.empty:
        choix_ref = st.selectbox("Sélectionner Devis", [""] + df_devis["Ref"].tolist()[::-1])
        if choix_ref:
            d_info = df_devis[df_devis["Ref"] == choix_ref].iloc[0]
            if st.button("✅ GÉNÉRER FACTURE"):
                ref_f = choix_ref.replace("D", "F")
                new_f = pd.DataFrame([d_info])
                new_f["Ref"] = ref_f
                new_f["Date"] = datetime.now().strftime("%d/%m/%Y")
                if save_to_gsheets(new_f, "factures"):
                    pdf_f = generate_thermal_ticket("Facture", {"Circuit": d_info['Circuit'], "Pax": d_info['Pax'], "Jours": "-", "Total": d_info['Total']}, d_info['Client'], ref_f, d_info['Options'])
                    st.download_button("📥 Télécharger Facture", pdf_f, f"{ref_f}.pdf", "application/pdf")
    else: st.info("Aucun devis trouvé.")

with tab3:
    st.subheader("📂 Historiques")
    if st.button("🔄 Actualiser"): st.rerun()
    st.markdown("### 📒 Devis")
    st.dataframe(get_cached_data("devis"), width=1200) # Utilisation de width fixe pour éviter dépréciation
    st.markdown("### 📗 Factures")
    st.dataframe(get_cached_data("factures"), width=1200)
