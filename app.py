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
    .resumé-box { background-color: #f9f9f9; padding: 15px; border-radius: 10px; border-left: 5px solid #1e88e5; margin-bottom: 20px; }
    .stButton>button { width: 100%; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
DATA_FILE = "data.csv"
INFO_FILE = "infos.csv"
LOGO_FILE = "logo.png"

# --- INITIALISATION HISTORIQUE ---
if 'df_h' not in st.session_state:
    if os.path.exists(HIST_FILE):
        st.session_state.df_h = pd.read_csv(HIST_FILE)
    else:
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Total", "Circuit", "Options"])

def get_next_ref(prefix):
    """Génère une référence type D000001 ou F000001"""
    count = len(st.session_state.df_h) + 1
    return f"{prefix}{count:06d}"

def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {'é': 'e', 'è': 'e', 'à': 'a', 'ô': 'o', '’': "'", 'ê': 'e'}
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

# --- GÉNÉRATION PDF (BACK-END UNIQUEMENT) ---
def generate_pdf_bytes(type_doc, data, ref_complet):
    pdf = FPDF(format=(80, 200))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(72, 8, "LAKA AM'LAY", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(72, 4, f"Ref: {ref_complet}", ln=True, align='C')
    pdf.cell(72, 4, f"Date: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 9)
    pdf.multi_cell(72, 5, clean_text(f"Client: {data['Client']}"))
    pdf.multi_cell(72, 5, clean_text(f"Circuit: {data['Circuit']}"))
    pdf.ln(2)
    pdf.set_font("Helvetica", '', 7)
    pdf.multi_cell(72, 4, clean_text(f"Options: {data['Options']}"))
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 11)
    pdf.cell(72, 8, f"TOTAL: {data['Total']:,.2f} EUR", ln=True, align='R')
    pdf.cell(72, 8, f"Soit: {data['Total']*TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align='R')
    out = pdf.output(dest='S')
    return bytes(out) if isinstance(out, (bytearray, bytes)) else out.encode('latin-1')

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 NOUVEAU DEVIS", "🧾 FACTURATION", "⚙️ CONFIG"])

with tab1:
    if os.path.exists(DATA_FILE):
        df_excu = pd.read_csv(DATA_FILE)
        
        c1, c2 = st.columns(2)
        nom_c = c1.text_input("👤 Nom du Client")
        type_e = c2.selectbox("🌍 Type", [""] + sorted(df_excu["Type"].unique().tolist()))
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            circuit = st.selectbox("📍 Circuit", df_f["Circuit"].unique())
            
            row = df_f[df_f["Circuit"] == circuit].iloc[0]
            col_a, col_b = st.columns(2)
            nb_pax = col_a.number_input("👥 Pax", min_value=1, value=1)
            nb_jours = col_b.number_input("📅 Jours", min_value=1, value=1)
            
            supp_ar = 0.0
            opts_selected = []

            if type_e == "Tours Nord":
                st.write("---")
                col_opt1, col_opt2 = st.columns(2)
                with col_opt1:
                    st.markdown("**🏞️ Sites**")
                    sites = {"Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000}
                    for s, p in sites.items():
                        if st.checkbox(f"{s}"): 
                            supp_ar += p; opts_selected.append(s)
                with col_opt2:
                    st.markdown("**👥 Personnel**")
                    persos = {"Guide": 100000, "Cuisinier": 30000}
                    for p, v in persos.items():
                        if st.checkbox(f"{p}"): 
                            supp_ar += (v * nb_jours); opts_selected.append(f"{p}({nb_jours}j)")

            marge = st.slider("📈 Marge %", 0, 100, 20)
            total_eur = ((float(row['Prix']) + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)

            # --- RÉSUMÉ DU DEVIS (PAS DE PDF ICI) ---
            st.markdown("### 📋 RÉSUMÉ DU DEVIS")
            st.markdown(f"""
            <div class="resumé-box">
                <b>Client :</b> {nom_c if nom_c else "<i>Non renseigné</i>"}<br>
                <b>Circuit :</b> {circuit}<br>
                <b>Détails :</b> {nb_pax} Pax / {nb_jours} Jours<br>
                <b>Options :</b> {", ".join(opts_selected) if opts_selected else "Aucune"}<br><br>
                <span style="font-size: 20px; color: #1e88e5;"><b>TOTAL : {total_eur:,.2f} €</b></span><br>
                <span style="color: #e64a19;">Soit {total_eur*TAUX_AR_TO_EUR:,.0f} Ar</span>
            </div>
            """, unsafe_allow_html=True)

            if st.button("✅ VALIDER ET TÉLÉCHARGER LE TICKET"):
                if not nom_c:
                    st.error("⚠️ Veuillez saisir le nom du client.")
                else:
                    ref_id = get_next_ref("D")
                    ref_full = f"{ref_id}-{nom_c.upper()}"
                    
                    data_devis = {
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Ref": ref_full,
                        "Client": nom_c,
                        "Total": round(total_eur, 2),
                        "Circuit": circuit,
                        "Options": ", ".join(opts_selected)
                    }
                    
                    # Enregistrement
                    st.session_state.df_h = pd.concat([st.session_state.df_h, pd.DataFrame([data_devis])], ignore_index=True)
                    st.session_state.df_h.to_csv(HIST_FILE, index=False)
                    
                    # Génération et téléchargement automatique
                    pdf_bytes = generate_pdf_bytes("DEVIS", data_devis, ref_full)
                    st.download_button("📩 Cliquez ici pour récupérer le ticket", 
                                       data=pdf_bytes, 
                                       file_name=f"{ref_full}.pdf", 
                                       mime="application/pdf")
                    st.success(f"Devis {ref_full} enregistré !")

with tab2:
    st.subheader("🧾 Transformer un Devis en Facture")
    if not st.session_state.df_h.empty:
        # On ne prend que les devis (ceux qui commencent par D)
        devis_list = st.session_state.df_h[st.session_state.df_h['Ref'].str.startswith('D')]
        choix = st.selectbox("Sélectionner le Devis", devis_list['Ref'].tolist()[::-1])
        
        if choix:
            d_data = st.session_state.df_h[st.session_state.df_h['Ref'] == choix].iloc[0].to_dict()
            new_ref_f = choix.replace("D", "F")
            
            st.info(f"Facture pour {d_data['Client']} - Montant: {d_data['Total']} €")
            
            if st.button("📄 GÉNÉRER LA FACTURE"):
                pdf_f = generate_pdf_bytes("FACTURE", d_data, new_ref_f)
                st.download_button("📩 Télécharger la Facture", 
                                   data=pdf_f, 
                                   file_name=f"{new_ref_f}.pdf", 
                                   mime="application/pdf")
    else:
        st.write("Aucun devis disponible.")

with tab3:
    st.subheader("⚙️ Gestion des données")
    st.dataframe(st.session_state.df_h, use_container_width=True)
    if st.button("🗑️ Vider l'historique"):
        if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Total", "Circuit", "Options"])
        st.rerun()
