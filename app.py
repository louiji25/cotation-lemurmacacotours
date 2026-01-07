import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")

TAUX_AR_TO_EUR = 5000
DATA_FILE = "data.csv"
HIST_FILE = "historique_devis.csv"
LOGO_FILE = "logo.png"

# =========================
# INITIALISATION
# =========================
if "df_h" not in st.session_state:
    st.session_state.df_h = (
        pd.read_csv(HIST_FILE)
        if os.path.exists(HIST_FILE)
        else pd.DataFrame(columns=["Date", "Ref", "Client", "Total"])
    )

# =========================
# UTILITAIRES
# =========================
def clean_text(text):
    if not isinstance(text, str):
        return str(text)
    repl = {
        "é": "e", "è": "e", "ê": "e",
        "à": "a", "â": "a",
        "î": "i", "ï": "i",
        "ô": "o",
        "ù": "u", "û": "u",
        "’": "'"
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text

def get_info_df():
    return pd.DataFrame({
        "Champ": ["Agence", "Adresse", "Téléphone"],
        "Valeur": ["Laka Am'lay", "Antsiranana – Madagascar", "+261 34 00 000 00"]
    })

# =========================
# PDF THERMIQUE
# =========================
def generate_thermal_ticket(type_doc, data, client_name, ref, contact="", options_text=""):
    pdf = FPDF(format=(80, 270))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)

    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=25, y=6, w=30)
        pdf.ln(28)

    infos = get_info_df()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(72, 7, clean_text(infos.iloc[0]["Valeur"]), ln=True, align="C")

    pdf.set_font("Helvetica", "", 8)
    for i in range(1, len(infos)):
        pdf.cell(72, 4, clean_text(f"{infos.iloc[i]['Champ']} : {infos.iloc[i]['Valeur']}"), ln=True, align="C")

    pdf.ln(2)
    pdf.cell(72, 0, "-" * 45, ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(72, 6, type_doc.upper(), ln=True, align="C")

    pdf.set_font("Helvetica", "", 8)
    pdf.cell(72, 5, f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(72, 5, f"Ref : {clean_text(ref)}", ln=True)
    pdf.cell(72, 5, f"Client : {clean_text(client_name)}", ln=True)
    if contact:
        pdf.cell(72, 5, f"Contact : {clean_text(contact)}", ln=True)

    pdf.ln(2)
    pdf.cell(72, 0, "-" * 45, ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 9)
    pdf.multi_cell(72, 5, f"Circuit : {clean_text(data['Circuit'])}")

    pdf.set_font("Helvetica", "", 8)
    pdf.cell(72, 5, f"Pax : {data['Pax']} | Jours : {data['Jours']}", ln=True)

    if options_text:
        pdf.set_font("Helvetica", "I", 7)
        pdf.multi_cell(72, 4, clean_text(f"Options : {options_text}"))

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(72, 7, f"TOTAL : {data['Total']:,.2f} EUR", ln=True, align="R")

    pdf.set_text_color(220, 50, 50)
    pdf.cell(72, 6, f"Soit : {data['Total'] * TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align="R")

    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(72, 5, "Merci de votre confiance !", ln=True, align="C")

    output = pdf.output()
    return output.encode("latin-1", "replace") if isinstance(output, str) else bytes(output)

# =========================
# INTERFACE
# =========================
st.title("📝 Nouveau Devis")

if not os.path.exists(DATA_FILE):
    st.error("data.csv manquant")
    st.stop()

df = pd.read_csv(DATA_FILE)
df["Prix"] = pd.to_numeric(df["Prix"], errors="coerce").fillna(0)

required_cols = {"Type", "Formule", "Transport", "Circuit", "Prix"}
if not required_cols.issubset(df.columns):
    st.error("Colonnes manquantes dans data.csv")
    st.stop()

c1, c2 = st.columns(2)
nom_c = c1.text_input("👤 Nom du client")
contact_c = c2.text_input("📞 Contact")

type_e = st.selectbox("🌍 Type", [""] + sorted(df["Type"].unique()))

if type_e:
    df_t = df[df["Type"] == type_e]

    f1, f2 = st.columns(2)
    formule = f1.selectbox("💎 Formule", sorted(df_t["Formule"].unique()))
    transport = f2.selectbox(
        "🚗 Transport",
        sorted(df_t[df_t["Formule"] == formule]["Transport"].unique())
    )

    circuit = st.selectbox(
        "📍 Circuit",
        sorted(
            df_t[
                (df_t["Formule"] == formule) &
                (df_t["Transport"] == transport)
            ]["Circuit"].unique()
        )
    )

    row = df_t[
        (df_t["Formule"] == formule) &
        (df_t["Transport"] == transport) &
        (df_t["Circuit"] == circuit)
    ].iloc[0]

    prix_base = float(row["Prix"])

    p1, p2 = st.columns(2)
    nb_pax = p1.number_input("👥 Pax", min_value=1, value=2)
    nb_jours = p2.number_input("📅 Jours", min_value=1, value=3)

    supp_ar = 0
    opt_sites, opt_perso, opt_logis = [], [], []

    st.subheader("🛠️ Options")

    col1, col2, col3 = st.columns(3)

    # SITES (PAR PAX)
    with col1:
        st.markdown("**🏞️ Sites (par pax)**")
        sites = {
            "Montagne d'Ambre": 55000,
            "Tsingy Rouge": 35000,
            "Ankarana": 65000
        }
        for s, v in sites.items():
            if st.checkbox(s):
                supp_ar += v * nb_pax
                opt_sites.append(f"{s} ({nb_pax} pax)")

    # PERSONNEL (PAR JOUR)
    with col2:
        st.markdown("**👥 Personnel (par jour)**")
        persos = {"Guide": 100000, "Cuisinier": 30000}
        for p, v in persos.items():
            if st.checkbox(p):
                supp_ar += v * nb_jours
                opt_perso.append(f"{p} ({nb_jours}j)")

    # LOGISTIQUE
    with col3:
        st.markdown("**🚚 Logistique**")
        logis = {
            "Location voiture": ("jour", 300000),
            "Carburant": ("forfait", 1200000),
            "Transfert hôtel": ("forfait", 200000)
        }
        for l, (t, v) in logis.items():
            if st.checkbox(l):
                supp_ar += v * nb_jours if t == "jour" else v
                opt_logis.append(l)

    marge = st.slider("📈 Marge (%)", 0, 100, 20)

    supp_eur = supp_ar / TAUX_AR_TO_EUR
    sous_total = (prix_base + supp_eur) * nb_pax
    total_eur = sous_total * (1 + marge / 100)

    st.markdown(f"### 💰 **Total : {total_eur:,.2f} € / {total_eur * TAUX_AR_TO_EUR:,.0f} Ar**")

    if st.button("✅ Valider et télécharger"):
        if not nom_c:
            st.error("Nom du client requis")
        else:
            safe_name = clean_text(nom_c).replace(" ", "_").upper()
            ref = f"D{len(st.session_state.df_h)+1:06d}-{safe_name}"

            options_txt = ", ".join(opt_sites + opt_perso + opt_logis)

            data_final = {
                "Circuit": circuit,
                "Pax": nb_pax,
                "Jours": nb_jours,
                "Total": total_eur
            }

            pdf = generate_thermal_ticket(
                "Devis", data_final, nom_c, ref, contact_c, options_txt
            )

            st.download_button(
                "📥 Télécharger le ticket",
                data=pdf,
                file_name=f"{ref}.pdf",
                mime="application/pdf"
            )

            new_row = {
                "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Ref": ref,
                "Client": nom_c,
                "Total": total_eur
            }
            st.session_state.df_h = pd.concat(
                [st.session_state.df_h, pd.DataFrame([new_row])],
                ignore_index=True
            )
            st.session_state.df_h.to_csv(HIST_FILE, index=False)
