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
    .stDownloadButton>button { background-color: #4CAF50 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
INFO_FILE = "infos.csv"
DATA_FILE = "data.csv"
LOGO_FILE = "logo.png"

# --- RÉINITIALISATION ---
def reset_formulaire():
    keys_to_reset = ["nom_c", "cont_c", "type_e", "formule", "transport", "circuit", "pax", "jours", "marge"]
    for key in keys_to_reset:
        if key in st.session_state:
            st.session_state[key] = "" if any(x in key for x in ["nom", "cont", "type"]) else 1
    if 'current_pdf' in st.session_state:
        del st.session_state['current_pdf']

# --- NETTOYAGE TEXTE ---
def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {
        '\u2192': "->", '\u2019': "'", '\u2013': "-", '\u2014': "-", '\xa0': " ",
        'é': 'e', 'è': 'e', 'ê': 'e', 'à': 'a', 'â': 'a', 'î': 'i', 'ï': 'i', 'ô': 'o', 'û': 'u', 'ù': 'u'
    }
    for old, new in replacements.items(): text = text.replace(old, new)
    return text

# --- INITIALISATION ---
if 'df_h' not in st.session_state:
    if os.path.exists(HIST_FILE):
        try: st.session_state.df_h = pd.read_csv(HIST_FILE, encoding='utf-8-sig')
        except: st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Pax", "Jours", "Total", "Formule", "Options"])
    else:
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Circuit", "Pax", "Jours", "Total", "Formule", "Options"])

def get_info_df():
    if os.path.exists(INFO_FILE): return pd.read_csv(INFO_FILE, encoding='utf-8-sig')
    return pd.DataFrame([["Nom", "LAKA AM'LAY"], ["Contact", "+261 34 00 000 00"]], columns=['Champ', 'Valeur'])

# --- GÉNÉRATION PDF ---
def generate_thermal_ticket(type_doc, data, client_name, ref, contact="", options_text=""):
    pdf = FPDF(format=(80, 270))
    pdf.add_page(); pdf.set_margins(4, 4, 4)
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=25, y=10, w=30); pdf.ln(35)
    
    df_infos = get_info_df()
    pdf.set_font("Helvetica", 'B', 12); pdf.cell(72, 8, clean_text(str(df_infos.iloc[0]['Valeur'])), ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    for i in range(1, len(df_infos)):
        pdf.cell(72, 4, clean_text(f"{df_infos.iloc[i]['Champ']}: {df_infos.iloc[i]['Valeur']}"), ln=True, align='C')
    
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 10); pdf.cell(72, 6, clean_text(type_doc.upper()), ln=True, align='C')
    
    pdf.set_font("Helvetica", '', 8); pdf.set_x(4)
    pdf.cell(72, 5, f"Date: {datetime.now().strftime('%d/%m/%y %H:%M')}", ln=True, align='L')
    pdf.cell(72, 5, f"Ref: {clean_text(ref)}", ln=True, align='L')
    pdf.cell(72, 5, f"Client: {clean_text(client_name)}", ln=True, align='L')
    
    pdf.ln(2); pdf.cell(72, 0, "-"*45, ln=True, align='C'); pdf.ln(2)
    pdf.set_font("Helvetica", 'B', 9); pdf.multi_cell(72, 5, clean_text(f"Circuit: {data.get('Circuit', 'N/A')}"))
    pdf.set_font("Helvetica", '', 8); pdf.cell(72, 5, f"Pax: {data.get('Pax', 1)} | Jours: {data.get('Jours', 1)}", ln=True)
    
    if options_text:
        pdf.set_font("Helvetica", 'I', 7); pdf.multi_cell(72, 4, clean_text(f"Options: {options_text}"))
    
    pdf.ln(2); pdf.set_font("Helvetica", 'B', 11)
    total_eur = float(data.get('Total', 0))
    pdf.cell(72, 8, f"TOTAL: {total_eur:,.2f} EUR", ln=True, align='R')
    pdf.set_text_color(230, 74, 25)
    pdf.cell(72, 6, f"Soit: {total_eur * TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align='R')
    
    pdf.set_text_color(0, 0, 0); pdf.ln(5); pdf.set_font("Helvetica", 'I', 8)
    pdf.cell(72, 5, "Merci de votre confiance !", ln=True, align='C')
    
    # Correction : Toujours forcer la sortie en bytes
    out = pdf.output(dest='S')
    return bytes(out) if isinstance(out, (bytearray, list)) else out.encode('latin-1', 'replace') if isinstance(out, str) else out

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURE", "⚙️ CONFIG"])

with tab1:
    if os.path.exists(DATA_FILE):
        df_excu = pd.read_csv(DATA_FILE, encoding='utf-8-sig')
        df_excu['Prix'] = pd.to_numeric(df_excu['Prix'], errors='coerce').fillna(0)
        
        nom_c = st.text_input("👤 Nom du Client", key="nom_c")
        cont_c = st.text_input("📱 WhatsApp / Email", key="cont_c")
        type_e = st.selectbox("🌍 Type", [""] + sorted(df_excu["Type"].unique().tolist()), key="type_e")
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            formule = st.selectbox("💎 Formule", sorted(df_f["Formule"].unique().tolist()), key="formule")
            transport = st.selectbox("🚗 Transport", sorted(df_f[df_f["Formule"] == formule]["Transport"].unique().tolist()), key="transport")
            circuit = st.selectbox("📍 Circuit", sorted(df_f[(df_f["Formule"] == formule) & (df_f["Transport"] == transport)]["Circuit"].unique().tolist()), key="circuit")
            
            selected_rows = df_f[df_f["Circuit"] == circuit]
            if not selected_rows.empty:
                row = selected_rows.iloc[0]
                c1, c2 = st.columns(2)
                nb_pax = c1.number_input("👥 Pax", min_value=1, value=1, key="pax")
                nb_jours = c2.number_input("📅 Jours", min_value=1, value=1, key="jours")
                
                supp_ar = 0.0
                opts_list = [f"Transp: {transport}"]

                if type_e == "Tours Nord":
                    st.subheader("🛠️ Options Tours Nord")
                    
                    # --- SECTION 1 : SITES ---
                    with st.expander("🏞️ FRAIS D'ENTRÉE (Sites)", expanded=True):
                        sites = {"Montagne des Français": 30000, "Trois Baies": 10000, "Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000, "Daraina": 60000, "Marojejy": 140000}
                        cols = st.columns(2)
                        for i, (site, prix) in enumerate(sites.items()):
                            if cols[i%2].checkbox(f"{site} ({prix:,} Ar)"):
                                supp_ar += prix; opts_list.append(site)

                    # --- SECTION 2 : PERSONNEL ---
                    with st.expander("👥 PERSONNEL (Par jour)", expanded=True):
                        perso = {"Guide Accompagnateur": 100000, "Cuisinier": 30000, "Porteur": 100000}
                        cols_p = st.columns(2)
                        for i, (p, prix) in enumerate(perso.items()):
                            if cols_p[i%2].checkbox(f"{p} ({prix:,} Ar/j)"):
                                supp_ar += (prix * nb_jours); opts_list.append(f"{p}({nb_jours}j)")

                    # --- SECTION 3 : LOGISTIQUE ---
                    with st.expander("🚚 LOGISTIQUE", expanded=False):
                        logis = {"Ankify -> Nosy Be": 500000, "Transfert Hôtel": 200000, "Carburant": 1200000, "Location voiture": 300000}
                        for item, prix in logis.items():
                            if st.checkbox(f"{item} ({prix:,} Ar)"):
                                if "voiture" in item.lower(): supp_ar += (prix * nb_jours)
                                else: supp_ar += prix
                                opts_list.append(item)
                
                marge = st.slider("📈 Marge %", 0, 100, 20, key="marge")
                total_ttc_eur = ((float(row['Prix']) + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)
                
                st.divider()
                st.metric("Total (EUR)", f"{total_ttc_eur:,.2f} €")
                st.metric("Total (ARIARY)", f"{total_ttc_eur*TAUX_AR_TO_EUR:,.0f} Ar")

                if st.button("🔥 GENERER LE TICKET"):
                    if not nom_c: st.error("Nom requis")
                    else:
                        ref_d = f"D{datetime.now().strftime('%y%m%d%H%M')}"
                        opts_txt = ", ".join(opts_list)
                        new_row = {"Date": datetime.now().strftime("%Y-%m-%d"), "Ref": ref_d, "Client": nom_c, "Contact": cont_c, "Circuit": circuit, "Pax": nb_pax, "Jours": nb_jours, "Total": round(total_ttc_eur, 2), "Formule": formule, "Options": opts_txt}
                        
                        # Sauvegarde historique
                        st.session_state.df_h = pd.concat([st.session_state.df_h, pd.DataFrame([new_row])], ignore_index=True)
                        st.session_state.df_h.to_csv(HIST_FILE, index=False, encoding='utf-8-sig')
                        
                        # Génération PDF
                        st.session_state.current_pdf = generate_thermal_ticket("Devis", new_row, nom_c, ref_d, cont_c, opts_txt)
                        st.session_state.current_ref = ref_d

                if 'current_pdf' in st.session_state:
                    st.download_button("📥 Télécharger le Ticket (PDF)", data=st.session_state.current_pdf, file_name=f"{st.session_state.current_ref}.pdf", mime="application/pdf")
                    b64 = base64.b64encode(st.session_state.current_pdf).decode('utf-8')
                    st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="500"></iframe>', unsafe_allow_html=True)
                
                st.button("➕ NOUVEAU DEVIS", on_click=reset_formulaire)

with tab2:
    st.subheader("🧾 Conversion Facture")
    if not st.session_state.df_h.empty:
        choix = st.selectbox("Choisir un Devis", [""] + st.session_state.df_h['Ref'].tolist()[::-1])
        if choix:
            d = st.session_state.df_h[st.session_state.df_h['Ref'] == choix].iloc[0]
            if st.button("📄 GENERER FACTURE"):
                ref_f = choix.replace("D", "F")
                pdf_f = generate_thermal_ticket("Facture", d.to_dict(), d['Client'], ref_f, d['Contact'], d['Options'])
                st.download_button("📥 Télécharger la Facture (PDF)", data=pdf_f, file_name=f"{ref_f}.pdf", mime="application/pdf")
                b64_f = base64.b64encode(pdf_f).decode('utf-8')
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64_f}" width="100%" height="500"></iframe>', unsafe_allow_html=True)

with tab3:
    st.subheader("⚙️ Configuration")
    df_i = get_info_df()
    new_i = st.data_editor(df_i, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Sauvegarder"): new_i.to_csv(INFO_FILE, index=False, encoding='utf-8-sig')
