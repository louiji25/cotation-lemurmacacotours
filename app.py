import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
from datetime import datetime
import qrcode
from io import BytesIO

# =========================
# CONFIGURATION
# =========================
st.set_page_config(page_title="Laka Am'lay POS", layout="centered")

TAUX_AR_TO_EUR = 5000
DATA_FILE = "data.csv"
HIST_FILE = "historique.csv"
LOGO_FILE = "logo.png"
FONT_FILE = "DejaVuSans.ttf"

# =========================
# INIT HISTORIQUE
# =========================
if "hist" not in st.session_state:
    st.session_state.hist = (
        pd.read_csv(HIST_FILE)
        if os.path.exists(HIST_FILE)
        else pd.DataFrame(columns=["Date", "Type", "Ref", "Client", "Total"])
    )

# =========================
# INFOS AGENCE
# =========================
def get_info_df():
    return pd.DataFrame({
        "Champ": ["Agence", "Adresse", "Téléphone"],
        "Valeur": [
            "Laka Am'lay",
            "Antsiranana – Madagascar",
            "+261 34 00 000 00"
        ]
    })

# =========================
# QR CODE
# =========================
def make_qr(data: str):
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

# =========================
# PDF THERMIQUE
# =========================
def generate_ticket(doc_type, data, client, ref, contact, options):
    pdf = FPDF(format=(80, 270))
    pdf.add_page()
    pdf.set_margins(4, 4, 4)

    # Police Unicode
    pdf.add_font("DV", "", FONT_FILE, uni=True)
    pdf.add_font("DV", "B", FONT_FILE, uni=True)
    pdf.add_font("DV", "I", FONT_FILE, uni=True)

    # LOGO
    if os.path.exists(LOGO_FILE):
        pdf.image(LOGO_FILE, x=22, y=4, w=36)
        pdf.ln(26)

    # INFOS AGENCE
    infos = get_info_df()
    pdf.set_font("DV", "B", 12)
    pdf.cell(72, 6, infos.iloc[0]["Valeur"], ln=True, align="C")

    pdf.set_font("DV", "", 8)
    for i in range(1, len(infos)):
        pdf.cell(72, 4, f"{infos.iloc[i]['Champ']} : {infos.iloc[i]['Valeur']}", ln=True, align="C")

    pdf.ln(2)
    pdf.cell(72, 0, "-" * 45, ln=True)
    pdf.ln(2)

    # TITRE
    pdf.set_font("DV", "B", 11)
    pdf.cell(72, 6, doc_type.upper(), ln=True, align="C")

    pdf.set_font("DV", "", 8)
    pdf.cell(72, 4, f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(72, 4, f"Ref : {ref}", ln=True)
    pdf.cell(72, 4, f"Client : {client}", ln=True)
    if contact:
        pdf.cell(72, 4, f"Contact : {contact}", ln=True)

    pdf.ln(1)
    pdf.cell(72, 0, "-" * 45, ln=True)
    pdf.ln(1)

    # DETAILS
    pdf.set_font("DV", "B", 9)
    pdf.multi_cell(72, 4, f"Circuit : {data['Circuit']}")

    pdf.set_font("DV", "", 8)
    pdf.cell(72, 4, f"Pax : {data['Pax']} | Jours : {data['Jours']}", ln=True)

    if options:
        pdf.set_font("DV", "I", 7)
        pdf.multi_cell(72, 3.5, f"Options : {options}")

    # TOTAL
    pdf.ln(1)
    pdf.set_font("DV", "B", 11)
    pdf.cell(72, 6, f"TOTAL : {data['Total']:,.2f} EUR", ln=True, align="R")

    pdf.set_text_color(220, 0, 0)
    pdf.cell(72, 5, f"Soit : {data['Total'] * TAUX_AR_TO_EUR:,.0f} Ar", ln=True, align="R")
    pdf.set_text_color(0, 0, 0)

    # QR CODE
    qr_data = f"{doc_type} | {ref} | {data['Total']:,.2f} EUR"
    qr_img = make_qr(qr_data)
    pdf.ln(3)
    pdf.image(qr_img, x=28, w=24)

    # SIGNATURE
    pdf.ln(22)
    pdf.set_font("DV", "", 8)
    pdf.cell(72, 4, "Signature client :", ln=True)
    pdf.ln(8)
    pdf.cell(72, 0, "_" * 30, ln=True, align="L")

    # FOOTER
    pdf.ln(6)
    pdf.set_font("DV", "I", 8)
    pdf.cell(72, 5, "Merci de votre confiance !", ln=True, align="C")

    out = pdf.output()
    return out.encode("latin-1") if isinstance(out, str) else bytes(out)

# =========================
# INTERFACE STREAMLIT
# =========================
st.title("🧾 Devis / Facture – Laka Am'lay")

if not os.path.exists(DATA_FILE):
    st.error("data.csv manquant")
    st.stop()

df = pd.read_csv(DATA_FILE)
df["Prix"] = pd.to_numeric(df["Prix"], errors="coerce").fillna(0)

doc_type = st.radio("Type de document", ["Devis", "Facture"], horizontal=True)

c1, c2 = st.columns(2)
client = c1.text_input("👤 Client")
contact = c2.text_input("📞 Contact")

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
        sorted(df_t[
            (df_t["Formule"] == formule) &
            (df_t["Transport"] == transport)
        ]["Circuit"].unique())
    )

    row = df_t[
        (df_t["Formule"] == formule) &
        (df_t["Transport"] == transport) &
        (df_t["Circuit"] == circuit)
    ].iloc[0]

    prix_base = float(row["Prix"])

    p1, p2 = st.columns(2)
    pax = p1.number_input("👥 Pax", 1, value=2)
    jours = p2.number_input("📅 Jours", 1, value=3)

    supp_ar = 0
    opts = []

    st.subheader("🛠️ Options")

    sites = {"Montagne d'Ambre": 55000, "Ankarana": 65000}
    for s, v in sites.items():
        if st.checkbox(s):
            supp_ar += v * pax
            opts.append(f"{s} ({pax} pax)")

    pers = {"Guide": 100000, "Cuisinier": 30000}
    for p, v in pers.items():
        if st.checkbox(p):
            supp_ar += v * jours
            opts.append(f"{p} ({jours}j)")

    if st.checkbox("Location voiture"):
        supp_ar += 300000 * jours
        opts.append(f"Location voiture ({jours}j)")

    marge = st.slider("📈 Marge (%)", 0, 100, 20)

    total_eur = ((prix_base + supp_ar / TAUX_AR_TO_EUR) * pax) * (1 + marge / 100)

    st.success(f"💰 Total : {total_eur:,.2f} € / {total_eur * TAUX_AR_TO_EUR:,.0f} Ar")

    if st.button("📥 Générer PDF"):
        ref = f"{doc_type[0]}{len(st.session_state.hist)+1:06d}"

        data = {
            "Circuit": circuit,
            "Pax": pax,
            "Jours": jours,
            "Total": total_eur
        }

        pdf = generate_ticket(
            doc_type, data, client, ref, contact, ", ".join(opts)
        )

        st.download_button(
            "Télécharger",
            data=pdf,
            file_name=f"{ref}.pdf",
            mime="application/pdf"
        )

        st.session_state.hist.loc[len(st.session_state.hist)] = [
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            doc_type, ref, client, total_eur
        ]
        st.session_state.hist.to_csv(HIST_FILE, index=False)
