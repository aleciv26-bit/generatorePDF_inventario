import io
import os
import zipfile
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class NumberedCanvas(canvas.Canvas):

    def __init__(self, *args, logo_path="logo he.png", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.logo_path = logo_path

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()

        # Logo posizionato in alto a destra nel margine superiore
        if os.path.exists(self.logo_path):
            self.drawImage(
                self.logo_path,
                24.2 * cm,
                18.8 * cm,
                width=4.5 * cm,
                height=1.5 * cm,
                preserveAspectRatio=True,
                mask="auto",
            )

        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))
        page_text = f"Pagina {self._pageNumber} di {page_count}"
        self.drawRightString(28.7 * cm, 0.6 * cm, page_text)
        self.restoreState()


def pulisci(val):
    if pd.isna(val) or val is None or str(val).strip().lower() == "nan":
        return ""
    return str(val).strip()


def genera_singolo_pdf_bytes(
    df_ospedale, nome_ospedale, num_allegato, sottotitolo_libero, logo_path
) -> bytes:
    """Genera il report PDF per un singolo Presidio Ospedaliero restituendo i byte in memoria."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=2.8 * cm,
        bottomMargin=1.2 * cm,
    )

    styles = getSampleStyleSheet()

    cover_title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,  # Centrato
        textColor=colors.HexColor("#1A365D"),
    )

    cover_subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        alignment=1,  # Centrato
        textColor=colors.HexColor("#4A5568"),
    )

    title_summary_style = ParagraphStyle(
        "TitleSummary",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        alignment=1,  # Centrato
        textColor=colors.HexColor("#1A365D"),
    )

    header_cdc = ParagraphStyle(
        "HeaderCDC",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1A202C"),
        keepWithNext=True,
    )

    header_set = ParagraphStyle(
        "HeaderSet",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#2B6CB0"),
        keepWithNext=True,
    )

    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        splitByChar=0,
    )
    cell_bold = ParagraphStyle(
        "CellB",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        splitByChar=0,
    )
    cell_hdr = ParagraphStyle(
        "CellH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.white,
        splitByChar=0,
    )

    # Stili per la Sezione 2 con centratura orizzontale
    cell_center = ParagraphStyle(
        "CellCenter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        alignment=1,  # Centrato orizzontalmente
        splitByChar=0,
    )

    cell_hdr_center = ParagraphStyle(
        "CellHdrCenter",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=colors.white,
        alignment=1,  # Centrato orizzontalmente
        splitByChar=0,
    )

    elements = []

    # --- PRIMA PAGINA EXTRA (COPERTINA) ---
    elements.append(Spacer(1, 4 * cm))
    elements.append(
        Paragraph(
            "REPORT PERIZIA DOTAZIONE DISPOSITIVI MEDICI RIUTILIZZABILI",
            cover_title_style,
        )
    )
    elements.append(Spacer(1, 15))
    if sottotitolo_libero:
        elements.append(Paragraph(sottotitolo_libero, cover_subtitle_style))
    elements.append(PageBreak())

    # --- SEZIONE 1: RIEPILOGO SINTETICO ---
    elements.append(
        Paragraph(
            "RIEPILOGO DEI SET INVENTARIATI SUDDIVISI PER CENTRO DI COSTO (CDC) E PER SISTEMA BARRIERA STERILE (SBS)",
            title_summary_style,
        )
    )
    elements.append(Spacer(1, 15))

    tot_dmr = len(df_ospedale)
    tot_set = df_ospedale["_CodSet"].nunique()
    tot_cdc = df_ospedale["_CDC"].nunique()

    tot_data = [
        [
            Paragraph("<b>TOTALE CDC</b>", cell_style),
            Paragraph("<b>TOTALE SET</b>", cell_style),
            Paragraph("<b>TOTALE DMR</b>", cell_style),
        ],
        [
            Paragraph(str(tot_cdc), cell_bold),
            Paragraph(str(tot_set), cell_bold),
            Paragraph(str(tot_dmr), cell_bold),
        ],
    ]
    t_tot = Table(tot_data, colWidths=[4 * cm, 4 * cm, 4 * cm])
    t_tot.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF2F7")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(t_tot)
    elements.append(Spacer(1, 15))

    for cdc, group_cdc in df_ospedale.groupby("_CDC"):
        is_first_sbs = True

        for sbs, group_sbs in group_cdc.groupby("_SBS"):
            if is_first_sbs:
                elements.append(
                    Paragraph(
                        f"CDC: {cdc} - totale DMR: {len(group_cdc)}",
                        header_cdc,
                    )
                )
                elements.append(Spacer(1, 6))
                is_first_sbs = False

            set_summary = (
                group_sbs.groupby(["_CodSet", "_NomeSet"])
                .size()
                .reset_index(name="QtaDMR")
            )
            data_sbs = [
                [
                    Paragraph(f"<b>SBS: {sbs}</b>", cell_hdr),
                    Paragraph("<b>Q.tà DMR</b>", cell_hdr),
                ]
            ]
            for _, row in set_summary.iterrows():
                label = f"{row['_CodSet']} - {row['_NomeSet']}"
                data_sbs.append(
                    [
                        Paragraph(label, cell_style),
                        Paragraph(str(row["QtaDMR"]), cell_style),
                    ]
                )

            t_sbs = Table(data_sbs, colWidths=[23.7 * cm, 4.0 * cm], repeatRows=1)
            t_sbs.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )
            elements.append(t_sbs)
            elements.append(Spacer(1, 8))

        elements.append(Spacer(1, 6))

    elements.append(PageBreak())

    # --- SEZIONE 2: DETTAGLIO ANALITICO ---
    elements.append(
        Paragraph(
            "RIEPILOGO VALUTAZIONE DMR SUDDIVISI PER CENTRO DI COSTO E PER SET",
            title_summary_style,
        )
    )
    elements.append(Spacer(1, 15))

    col_widths = [
        2.4 * cm,  # Codice DMR
        3.0 * cm,  # Fabbricante
        7.2 * cm,  # Descrizione DMR
        2.3 * cm,  # Cod. Equivalente
        3.5 * cm,  # Descrizione Stato
        2.2 * cm,  # Assenza CE
        2.6 * cm,  # Manomesso
        4.5 * cm,  # Note
    ]

    for cdc, group_cdc in df_ospedale.groupby("_CDC"):
        first_set_of_cdc = True

        for (cod_set, nome_set, sbs), group_set in group_cdc.groupby(
            ["_CodSet", "_NomeSet", "_SBS"]
        ):
            set_elements = []

            if first_set_of_cdc:
                set_elements.append(Paragraph(f"CDC: {cdc}", header_cdc))
                set_elements.append(Spacer(1, 8))
                first_set_of_cdc = False

            hdr_text = f"{cod_set} - {nome_set} - SBS: {sbs} - Q.tà DMR: {len(group_set)}"
            set_elements.append(Paragraph(hdr_text, header_set))
            set_elements.append(Spacer(1, 4))

            table_data = [
                [
                    Paragraph("Codice DMR", cell_hdr_center),
                    Paragraph("Fabbricante", cell_hdr_center),
                    Paragraph("Descrizione DMR", cell_hdr_center),
                    Paragraph("Cod. Equivalente", cell_hdr_center),
                    Paragraph("Descrizione stato", cell_hdr_center),
                    Paragraph("Assenza CE", cell_hdr_center),
                    Paragraph("Manomesso", cell_hdr_center),
                    Paragraph("Note", cell_hdr_center),
                ]
            ]

            for _, row in group_set.iterrows():
                table_data.append(
                    [
                        Paragraph(row["_CodDMR"], cell_center),
                        Paragraph(row["_Fab"], cell_center),
                        Paragraph(row["_DescDMR"], cell_style),  # Allineato a sinistra, centrato solo in altezza
                        Paragraph(row["_Eq"], cell_center),
                        Paragraph(row["_Stato"], cell_center),
                        Paragraph(row["_CE"], cell_center),
                        Paragraph(row["_Man"], cell_center),
                        Paragraph(row["_Note"], cell_center),
                    ]
                )

            t_dmr = Table(table_data, colWidths=col_widths, repeatRows=1)
            t_dmr.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3748")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # Centrato in altezza per tutte le caselle
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]
                )
            )

            set_elements.append(t_dmr)
            set_elements.append(Spacer(1, 10))

            elements.append(KeepTogether(set_elements))

    def canvas_maker(*args, **kwargs):
        return NumberedCanvas(*args, logo_path=logo_path, **kwargs)

    doc.build(elements, canvasmaker=canvas_maker)
    return buffer.getvalue()


# --- INTERFACCIA STREAMLIT E ELABORAZIONE DATI ---
st.set_page_config(page_title="Generatore Report PDF", layout="centered")

st.title("📄 Generatore Report PDF Inventario")
st.write(
    "Carica il file Excel (`.xlsx`) e imposta le opzioni per generare automaticamente i PDF di riepilogo."
)

scelta_logo = st.selectbox(
    "Seleziona il logo da inserire nel PDF:",
    options=["HE", "SIS"],
    index=0
)
logo_path = "logo he.png" if scelta_logo == "HE" else "logo sis.png"

sottotitolo_libero = st.text_input(
    "Inserisci il sottotitolo per la prima pagina extra:",
    placeholder="Es. Perizia tecnica relativa al Presidio Ospedaliero X..."
)

uploaded_file = st.file_uploader("Carica il file Excel", type=["xlsx", "xls"])

if uploaded_file is not None:
    if st.button("🚀 Genera Report PDF", type="primary"):
        with st.spinner("Elaborazione dati e generazione PDF in corso..."):
            df = pd.read_excel(uploaded_file)

            df["_Ospedale"] = (
                df["Presidio Ospedaliero"].apply(pulisci)
                if "Presidio Ospedaliero" in df
                else "Generale"
            )
            df["_CDC"] = df["Centro di costo"].apply(pulisci)
            df["_Reparto"] = df["_CDC"]
            df["_SBS"] = df["Sbs_description"].apply(
                lambda x: pulisci(x) if pulisci(x) else "Non Definito"
            )
            df["_CodSet"] = df["m_sets.code"].apply(pulisci)
            df["_NomeSet"] = df["m_sets.name"].apply(pulisci)

            raw_fab = (
                df["manufacturers.name"].apply(pulisci)
                if "manufacturers.name" in df
                else ""
            )
            raw_cod_dmr = (
                df["articles.code"].apply(pulisci) if "articles.code" in df else ""
            )

            col_m_vals = (
                df.iloc[:, 12].apply(pulisci)
                if df.shape[1] > 12
                else pd.Series([""] * len(df))
            )

            df["_DescDMR"] = (
                df["description"].apply(pulisci) if "description" in df else ""
            )
            df["_Stato"] = (
                df["DescrizioneStato"].apply(pulisci)
                if "DescrizioneStato" in df
                else "OK"
            )

            raw_ce = df["MarcaturaCE"].apply(pulisci) if "MarcaturaCE" in df else ""
            df["_CE"] = raw_ce.apply(
                lambda x: "SI" if x.upper() in ["NO CE", "SI", "1"] else ""
            )

            raw_man = df["Manomissione"].apply(pulisci) if "Manomissione" in df else ""
            df["_Man"] = raw_man.apply(
                lambda x: "SI" if x.lower() in ["manomesso", "si", "1"] else ""
            )

            df["_Note"] = df["note"].apply(pulisci) if "note" in df else ""

            cod_dmr_list = []
            fab_list = []
            eq_list = []

            for c_dmr, f_val, col_m in zip(raw_cod_dmr, raw_fab, col_m_vals):
                if c_dmr.upper() == "NNNN":
                    cod_dmr_list.append("Non presente")
                    fab_list.append("Non presente")
                    eq_list.append("")
                elif col_m != "":
                    cod_dmr_list.append("Non presente")
                    fab_list.append("Non presente")
                    eq_val = " + ".join([v for v in [c_dmr, f_val] if v])
                    eq_list.append(eq_val)
                else:
                    cod_dmr_list.append(c_dmr)
                    fab_list.append(f_val)
                    eq_list.append("")

            df["_CodDMR"] = cod_dmr_list
            df["_Fab"] = fab_list
            df["_Eq"] = eq_list

            ospedali = [o for o in df["_Ospedale"].unique() if o]

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(
                zip_buffer, "w", zipfile.ZIP_DEFLATED
            ) as zip_file:
                for idx, ospedale in enumerate(ospedali, start=1):
                    df_ospedale = df[df["_Ospedale"] == ospedale]
                    pdf_bytes = genera_singolo_pdf_bytes(
                        df_ospedale,
                        ospedale,
                        idx,
                        sottotitolo_libero,
                        logo_path,
                    )

                    nome_file_sanificato = ospedale.replace(" ", "_").replace(
                        "/", "_"
                    )
                    pdf_filename = f"Allegato_{idx}_{nome_file_sanificato}.pdf"

                    zip_file.writestr(pdf_filename, pdf_bytes)

            zip_buffer.seek(0)

            st.success("✅ Generazione completata con successo!")
            st.download_button(
                label="📦 Scarica tutti i PDF (.zip)",
                data=zip_buffer,
                file_name="Report_PDF_Allegati.zip",
                mime="application/zip",
            )
