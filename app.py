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
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
DATA_FILE = "data.csv"
LOGO_FILE = "logo.png"

# --- INITIALISATION ---
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

# --- GÉNÉRATION DU TICKET ---
def generate_thermal_ticket(type_doc, data, ref_full):
    pdf = FPDF(format=(80, 260))
    pdf.add_page()
    pdf.set_margins(6, 6, 6)
    
    # LOGO & ENTETE
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=25, y=8, w=30); pdf.ln(25)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(68, 7, "LAKA AM'LAY", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(68, 4, "Nosy Be, Madagascar", ln=True, align='C')
    pdf.ln(2); pdf.cell(68, 0, "-"*40, ln=True, align='C'); pdf.ln(2)
    
    # INFOS DOCUMENT
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(68, 6, f"{type_doc.upper()}: {ref_full}", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(68, 5, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(68, 5, clean_text(f"Client: {data['Client']}"), ln=True)
    pdf.cell(68, 5, f"Contact: {data['Contact']}", ln=True)
    
    pdf.ln(2); pdf.cell(68, 0, "-"*40, ln=True, align='C'); pdf.ln(2)
    
    # DETAILS VOYAGE
    pdf.set_font("Helvetica", 'B', 9)
    pdf.multi_cell(68, 5, clean_text(f"Circuit: {data['Circuit']}"))
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(68, 5, f"Formule: {data['Formule']}", ln=True)
    pdf.cell(68, 5, f"Transport: {data['Transport']}", ln=True)
    pdf.cell(68, 5, f"Pax: {data['Pax']} | Jours: {data['Jours']}", ln=True)
    
    # OPTIONS
    if data['Options']:
        pdf.ln(1); pdf.set_font("Helvetica", 'B', 8); pdf.cell(68, 5, "Options:", ln=True)
        pdf.set_font("Helvetica", 'I', 7); pdf.multi_cell(68, 4, clean_text(data['Options']))
    
    pdf.ln(3); pdf.cell(68, 0, "-"*40, ln=True, align='C'); pdf.ln(3)
    
    # TOTAL
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(34, 8, "TOTAL EUR:", 0); pdf.cell(34, 8, f"{data['Total']:,.2f} EUR", 0, 1, 'R')
    pdf.set_text_color(200, 50, 0)
    pdf.cell(34, 7, "TOTAL AR:", 0); pdf.cell(34, 7, f"{data['Total']*TAUX_AR_TO_EUR:,.0f} AR", 0, 1, 'R')
    
    pdf.set_text_color(0, 0, 0); pdf.ln(10); pdf.set_font("Helvetica", 'I', 7)
    pdf.cell(68, 4, "Merci de votre confiance !", ln=True, align='C')
    
    out = pdf.output(dest='S')
    return bytes(out) if isinstance(out, (bytearray, bytes)) else out.encode('latin-1')

# =========================
# INTERFACE
# =========================
tab1, tab2, tab3 = st.tabs(["📝 DEVIS", "🧾 FACTURES", "⚙️ CONFIG"])

with tab1:
    if os.path.exists(DATA_FILE):
        df_excu = pd.read_csv(DATA_FILE)
        
        c1, c2 = st.columns(2)
        nom_c = c1.text_input("👤 Nom du Client")
        cont_c = c2.text_input("📞 Numero Client / WhatsApp")
        
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
            
            # --- OPTIONS TOURS NORD ---
            supp_ar = 0.0; opts_list = []
            if type_e == "Tours Nord":
                with st.expander("🏞️ Sites & Personnel & Logistique"):
                    sites = {"Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, "Ankarana": 65000, "Trois Baies": 10000}
                    persos = {"Guide": 100000, "Cuisinier": 30000}
                    logis = {"Location 4x4": 300000, "Carburant": 1200000}
                    
                    for s, p in sites.items():
                        if st.checkbox(s): supp_ar += p; opts_list.append(s)
                    for p, v in persos.items():
                        if st.checkbox(p): supp_ar += (v * nb_jours); opts_list.append(f"{p}({nb_jours}j)")
                    for l, v in logis.items():
                        if st.checkbox(l): 
                            if "4x4" in l: supp_ar += (v * nb_jours)
                            else: supp_ar += v
                            opts_list.append(l)

            marge = st.slider("📈 Marge %", 0, 100, 20)
            total_eur = ((float(row['Prix']) + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)

            # --- RÉSUMÉ ---
            st.markdown(f"""
            <div class="resumé-box">
                <b>Client :</b> {nom_c} ({cont_c})<br>
                <b>Circuit :</b> {circuit} [{formule} - {transport}]<br>
                <b>Options :</b> {", ".join(opts_list) if opts_list else "Base"}<br>
                <hr>
                <div style="display:flex; justify-content:space-between">
                    <span style="font-size:20px"><b>TOTAL : {total_eur:,.2f} €</b></span>
                    <span style="font-size:18px; color:#e64a19"><b>{total_eur*TAUX_AR_TO_EUR:,.0f} Ar</b></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚀 VALIDER & TÉLÉCHARGER"):
                if not nom_c: st.error("Nom requis")
                else:
                    ref_id = get_next_ref("D")
                    ref_full = f"{ref_id}-{nom_c.upper()}"
                    data_f = {"Client": nom_c, "Contact": cont_c, "Circuit": circuit, "Formule": formule, "Transport": transport, "Pax": nb_pax, "Jours": nb_jours, "Total": round(total_eur, 2), "Options": ", ".join(opts_list)}
                    
                    # Sauvegarde
                    st.session_state.df_h = pd.concat([st.session_state.df_h, pd.DataFrame([data_f | {"Date": datetime.now().strftime("%Y-%m-%d"), "Ref": ref_full}])], ignore_index=True)
                    st.session_state.df_h.to_csv(HIST_FILE, index=False)
                    
                    pdf = generate_thermal_ticket("DEVIS", data_f, ref_full)
                    st.download_button(f"📥 Télécharger Ticket {ref_id}", data=pdf, file_name=f"{ref_full}.pdf", mime="application/pdf")

with tab2:
    st.subheader("🧾 Facturation")
    df_devis = st.session_state.df_h[st.session_state.df_h['Ref'].str.contains('D')]
    if not df_devis.empty:
        sel = st.selectbox("Devis à facturer", df_devis['Ref'].tolist()[::-1])
        if sel:
            d = df_devis[df_devis['Ref'] == sel].iloc[0]
            if st.button("📄 ÉMETTRE FACTURE"):
                ref_f = sel.replace("D", "F")
                pdf_f = generate_thermal_ticket("FACTURE", d.to_dict(), ref_f)
                st.download_button(f"📥 Télécharger Facture {ref_f}", data=pdf_f, file_name=f"{ref_f}.pdf", mime="application/pdf")

with tab3:
    st.subheader("⚙️ Historique")
    st.dataframe(st.session_state.df_h, use_container_width=True)
    if st.button("🗑️ Reset"):
        if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Contact", "Total", "Circuit", "Formule", "Transport", "Options"])
        st.rerun()
