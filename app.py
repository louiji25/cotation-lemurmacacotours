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
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; }
    .valider-btn { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

HIST_FILE = "historique_devis.csv"
DATA_FILE = "data.csv"
INFO_FILE = "infos.csv"
LOGO_FILE = "logo.png"

# --- INITIALISATION ---
if 'df_h' not in st.session_state:
    if os.path.exists(HIST_FILE):
        st.session_state.df_h = pd.read_csv(HIST_FILE)
    else:
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Total", "Circuit", "Options"])

def get_next_ref(prefix):
    count = len(st.session_state.df_h) + 1
    return f"{prefix}{count:06d}"

def clean_text(text):
    if not isinstance(text, str): return str(text)
    rep = {'é': 'e', 'è': 'e', 'à': 'a', 'ô': 'o', '’': "'", 'ê': 'e', 'ë': 'e', 'î': 'i', 'ï': 'i', 'û': 'u'}
    for old, new in rep.items(): text = text.replace(old, new)
    return text

# --- GÉNÉRATION DU TICKET STRUCTURÉ ---
def generate_thermal_ticket(type_doc, data, ref_full):
    pdf = FPDF(format=(80, 250)) # Format ticket long
    pdf.add_page()
    pdf.set_margins(6, 6, 6)
    
    # 1. EN-TÊTE
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=25, y=8, w=30)
        pdf.ln(25)
    
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(68, 7, "LAKA AM'LAY", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(68, 4, "Nosy Be, Madagascar", ln=True, align='C')
    pdf.cell(68, 4, "Contact: +261 34 00 000 00", ln=True, align='C')
    
    pdf.ln(3)
    pdf.cell(68, 0, "-"*40, ln=True, align='C')
    pdf.ln(2)
    
    # 2. INFOS DOCUMENT
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(68, 6, f"{type_doc.upper()}: {ref_full}", ln=True, align='C')
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(68, 5, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(68, 5, clean_text(f"Client: {data['Client']}"), ln=True)
    
    pdf.ln(2)
    pdf.cell(68, 0, "-"*40, ln=True, align='C')
    pdf.ln(2)
    
    # 3. DÉTAILS CIRCUIT
    pdf.set_font("Helvetica", 'B', 9)
    pdf.multi_cell(68, 5, clean_text(f"Circuit: {data['Circuit']}"))
    pdf.set_font("Helvetica", '', 8)
    pdf.cell(68, 5, f"Pax: {data['Pax']} | Jours: {data['Jours']}", ln=True)
    
    # 4. OPTIONS DÉTAILLÉES
    if data['Options']:
        pdf.ln(1)
        pdf.set_font("Helvetica", 'B', 8)
        pdf.cell(68, 5, "Options incluses:", ln=True)
        pdf.set_font("Helvetica", 'I', 7)
        pdf.multi_cell(68, 4, clean_text(data['Options']))
    
    pdf.ln(3)
    pdf.cell(68, 0, "-"*40, ln=True, align='C')
    pdf.ln(3)
    
    # 5. TOTAL
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(34, 8, "TOTAL EUR:", 0)
    pdf.cell(34, 8, f"{data['Total']:,.2f} EUR", 0, 1, 'R')
    
    pdf.set_text_color(200, 50, 0)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(34, 7, "TOTAL AR:", 0)
    pdf.cell(34, 7, f"{data['Total']*TAUX_AR_TO_EUR:,.0f} AR", 0, 1, 'R')
    
    # 6. PIED DE PAGE
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    pdf.set_font("Helvetica", 'I', 7)
    pdf.cell(68, 4, "Merci de votre confiance !", ln=True, align='C')
    pdf.cell(68, 4, "Laka Am'lay - Votre aventure commence ici.", ln=True, align='C')
    
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
        nom_c = c1.text_input("👤 Nom du Client", placeholder="Ex: Jean Dupont")
        type_e = c2.selectbox("🌍 Type de voyage", [""] + sorted(df_excu["Type"].unique().tolist()))
        
        if type_e:
            df_f = df_excu[df_excu["Type"] == type_e]
            circuit = st.selectbox("📍 Choisir le Circuit", df_f["Circuit"].unique())
            
            row = df_f[df_f["Circuit"] == circuit].iloc[0]
            col_a, col_b = st.columns(2)
            nb_pax = col_a.number_input("👥 Nombre de Pax", min_value=1, value=1)
            nb_jours = col_b.number_input("📅 Nombre de Jours", min_value=1, value=1)
            
            # --- TOUTES LES OPTIONS ---
            supp_ar = 0.0
            opts_selected = []

            st.write("### 🛠️ Personnalisation")
            
            # Sites
            with st.expander("🏞️ Frais d'entrée / Sites"):
                sites = {
                    "Montagne d'Ambre": 55000, "Tsingy Rouge": 35000, 
                    "Ankarana": 65000, "Trois Baies": 10000, 
                    "Montagne des Français": 30000, "Daraina": 60000
                }
                c_s1, c_s2 = st.columns(2)
                for i, (s, p) in enumerate(sites.items()):
                    if (c_s1 if i%2==0 else c_s2).checkbox(f"{s} ({p:,} Ar)"):
                        supp_ar += p; opts_selected.append(s)

            # Personnel
            with st.expander("👥 Personnel & Services"):
                persos = {"Guide Accompagnateur": 100000, "Cuisinier": 30000, "Porteur": 50000}
                c_p1, c_p2 = st.columns(2)
                for i, (p, v) in enumerate(persos.items()):
                    if (c_p1 if i%2==0 else c_p2).checkbox(f"{p} ({v:,} Ar/j)"):
                        supp_ar += (v * nb_jours); opts_selected.append(f"{p}({nb_jours}j)")

            # Logistique
            with st.expander("🚗 Logistique & Transport"):
                logis = {"Location 4x4": 300000, "Carburant (Forfait)": 1200000, "Transfert Vedette": 500000}
                for l, v in logis.items():
                    if st.checkbox(f"{l} ({v:,} Ar)"):
                        if "4x4" in l: supp_ar += (v * nb_jours)
                        else: supp_ar += v
                        opts_selected.append(l)

            marge = st.slider("📈 Marge bénéficiaire %", 0, 100, 20)
            prix_base = float(row['Prix'])
            total_eur = ((prix_base + (supp_ar/TAUX_AR_TO_EUR)) * nb_pax) * (1 + marge/100)

            # --- RÉSUMÉ VISUEL ---
            st.markdown("### 📋 RÉSUMÉ DU DEVIS")
            st.markdown(f"""
            <div class="resumé-box">
                <table style="width:100%">
                    <tr><td><b>Client:</b></td><td style="text-align:right">{nom_c}</td></tr>
                    <tr><td><b>Circuit:</b></td><td style="text-align:right">{circuit}</td></tr>
                    <tr><td><b>Pax/Jours:</b></td><td style="text-align:right">{nb_pax} Pax / {nb_jours} Jours</td></tr>
                    <tr><td><b>Options:</b></td><td style="text-align:right; font-size:11px">{", ".join(opts_selected) if opts_selected else "Base"}</td></tr>
                </table>
                <hr>
                <div style="display:flex; justify-content:space-between; align-items:center">
                    <span style="font-size:22px; color:#1e88e5"><b>TOTAL</b></span>
                    <div style="text-align:right">
                        <span style="font-size:22px; color:#1e88e5"><b>{total_eur:,.2f} €</b></span><br>
                        <span style="color:#e64a19">{total_eur*TAUX_AR_TO_EUR:,.0f} Ar</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🚀 VALIDER & GÉNÉRER LE TICKET", key="valider"):
                if not nom_c:
                    st.error("Saisissez le nom du client")
                else:
                    ref_id = get_next_ref("D")
                    ref_full = f"{ref_id}-{nom_c.upper()}"
                    
                    data_final = {
                        "Client": nom_c, "Circuit": circuit, "Pax": nb_pax,
                        "Jours": nb_jours, "Total": round(total_eur, 2),
                        "Options": ", ".join(opts_selected)
                    }
                    
                    # Sauvegarde
                    new_row = {"Date": datetime.now().strftime("%Y-%m-%d"), "Ref": ref_full, "Client": nom_c, "Total": round(total_eur, 2), "Circuit": circuit, "Options": data_final["Options"]}
                    st.session_state.df_h = pd.concat([st.session_state.df_h, pd.DataFrame([new_row])], ignore_index=True)
                    st.session_state.df_h.to_csv(HIST_FILE, index=False)
                    
                    # PDF
                    pdf_bytes = generate_thermal_ticket("DEVIS", data_final, ref_full)
                    st.download_button(f"📥 TÉLÉCHARGER LE TICKET {ref_id}", 
                                       data=pdf_bytes, file_name=f"{ref_full}.pdf", mime="application/pdf")

with tab2:
    st.subheader("🧾 Conversion en Facture")
    # Liste uniquement les devis
    df_devis = st.session_state.df_h[st.session_state.df_h['Ref'].str.contains('D')]
    if not df_devis.empty:
        selection = st.selectbox("Sélectionner un devis à facturer", df_devis['Ref'].tolist()[::-1])
        if selection:
            d = df_devis[df_devis['Ref'] == selection].iloc[0]
            ref_fact = selection.replace("D", "F")
            st.warning(f"Facturation de : {d['Client']} ({d['Total']} €)")
            
            if st.button("💎 ÉMETTRE LA FACTURE DEFINITIVE"):
                pdf_f = generate_thermal_ticket("FACTURE", d.to_dict(), ref_fact)
                st.download_button(f"📥 TÉLÉCHARGER FACTURE {ref_fact}", 
                                   data=pdf_f, file_name=f"{ref_fact}.pdf", mime="application/pdf")
    else:
        st.info("Aucun devis en attente.")

with tab3:
    st.subheader("⚙️ Paramètres & Historique")
    st.dataframe(st.session_state.df_h, use_container_width=True)
    if st.button("🗑️ Vider tout l'historique"):
        if os.path.exists(HIST_FILE): os.remove(HIST_FILE)
        st.session_state.df_h = pd.DataFrame(columns=["Date", "Ref", "Client", "Total", "Circuit", "Options"])
        st.rerun()
