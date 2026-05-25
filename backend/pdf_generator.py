"""
Module de génération PDF — Templates stricts EDITIONS FABS-CI.

Documents supportés :
- Facture Client       (FABS-FC)
- Facture Proforma     (FABS-FP)
- Bon de Commande      (FABS-BC)
- Bon de Livraison     (FABS-BL)
- Bon de Retour        (FABS-BR)

Chaque document respecte strictement la charte FABS-CI :
- En-tête  : raison sociale, adresse, téléphones, email
- Pied     : siège social + infos bancaires (CORIS BANK, SGBCI)
- QR Code  : en bas à gauche (encode la référence du document)
- Zone signature : en bas à droite
- Tableau articles : colonnes Classe / Code Article / Référence / Qté / PU / Montant
"""
from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Optional

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Image
)

# ---------------------------------------------------------------------------
# Constantes Charte FABS-CI
# ---------------------------------------------------------------------------
FABS_NAME = "EDITIONS FABS-CI"
FABS_ADDRESS_LINE = (
    "Siège social : Bingerville, Qt N'GOTTO, Immeuble cité Angan A. "
    "fils et petits-fils, Rez de chaussée. BP 693 Bingerville."
)
FABS_PHONE = "Tél : +225 27 22 28 00 99 / +225 07 59 73 71 23"
FABS_EMAIL = "E-mail : edition693fabs@gmail.com"
FABS_BANKS = (
    "Banques : CORIS BANK : CI16 01011 00763082410134 ; "
    "SGBCI : CI008 01123 012343259990 95."
)

NAVY = colors.HexColor("#0A2540")
ORANGE = colors.HexColor("#FF6200")
GREY = colors.HexColor("#6B7280")


def format_fcfa(montant: float) -> str:
    return f"{montant:,.0f} FCFA".replace(",", " ")


def _make_qr(data: str, box_size: int = 4) -> BytesIO:
    qr = qrcode.QRCode(version=1, box_size=box_size, border=1)
    qr.add_data(data or FABS_NAME)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
_styles = getSampleStyleSheet()
STYLE_COMPANY = ParagraphStyle(
    "company", parent=_styles["Heading2"], fontSize=14, textColor=NAVY,
    spaceAfter=2, leading=16, fontName="Helvetica-Bold",
)
STYLE_HEAD = ParagraphStyle(
    "head", parent=_styles["Normal"], fontSize=8, textColor=colors.black, leading=10,
)
STYLE_TITLE = ParagraphStyle(
    "title", parent=_styles["Heading1"], fontSize=18, textColor=ORANGE,
    alignment=TA_RIGHT, leading=22, fontName="Helvetica-Bold",
)
STYLE_NORMAL = ParagraphStyle(
    "n", parent=_styles["Normal"], fontSize=9, leading=11,
)
STYLE_NORMAL_B = ParagraphStyle(
    "nb", parent=STYLE_NORMAL, fontName="Helvetica-Bold",
)
STYLE_FOOTER = ParagraphStyle(
    "footer", parent=_styles["Normal"], fontSize=7, textColor=GREY,
    alignment=TA_CENTER, leading=9,
)


# ---------------------------------------------------------------------------
# Header / Footer (PageTemplate)
# ---------------------------------------------------------------------------
def _draw_header(canvas, doc, title: str, reference: str, date_str: str):
    canvas.saveState()
    w, h = A4

    # Logo placeholder (square multicolor box) — left
    x0, y0 = 1.5 * cm, h - 2.4 * cm
    canvas.setFillColor(ORANGE)
    canvas.rect(x0, y0, 1.2 * cm, 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(NAVY)
    canvas.rect(x0 + 0.6 * cm, y0, 0.6 * cm, 0.6 * cm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#FFC107"))
    canvas.rect(x0, y0 + 0.6 * cm, 0.6 * cm, 0.6 * cm, fill=1, stroke=0)

    # Company info — next to logo
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(x0 + 1.5 * cm, h - 1.55 * cm, FABS_NAME)
    canvas.setFillColor(colors.black)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(x0 + 1.5 * cm, h - 1.95 * cm, "Bingerville, Qt N'GOTTO, Imm. cité Angan A.")
    canvas.drawString(x0 + 1.5 * cm, h - 2.20 * cm, "BP 693 — Tél : +225 27 22 28 00 99")
    canvas.drawString(x0 + 1.5 * cm, h - 2.45 * cm, "edition693fabs@gmail.com")

    # Title (right)
    canvas.setFont("Helvetica-Bold", 16)
    canvas.setFillColor(ORANGE)
    canvas.drawRightString(w - 1.5 * cm, h - 1.55 * cm, title)

    # Reference + date (right, smaller)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawRightString(w - 1.5 * cm, h - 2.05 * cm, f"N° {reference}")
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.black)
    canvas.drawRightString(w - 1.5 * cm, h - 2.45 * cm, date_str)

    # Separator line
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(1.2)
    canvas.line(1.5 * cm, h - 2.7 * cm, w - 1.5 * cm, h - 2.7 * cm)

    canvas.restoreState()


def _draw_footer(canvas, doc, reference: str, show_qr: bool = True, signature_label: str = "Signature & Cachet"):
    canvas.saveState()
    w, h = A4

    # QR code bottom-left
    if show_qr:
        qr_buf = _make_qr(f"FABS-CI | {reference}")
        canvas.drawImage(
            __import__("reportlab.lib.utils", fromlist=["ImageReader"]).ImageReader(qr_buf),
            1.5 * cm, 1.5 * cm, width=2.2 * cm, height=2.2 * cm, mask="auto",
        )

    # Signature box bottom-right
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(0.5)
    canvas.rect(w - 6.5 * cm, 1.5 * cm, 5 * cm, 2.2 * cm, stroke=1, fill=0)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(NAVY)
    canvas.drawString(w - 6.3 * cm, 3.5 * cm, signature_label)

    # Footer text (bank + address)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(w / 2, 1.1 * cm, FABS_ADDRESS_LINE)
    canvas.drawCentredString(w / 2, 0.78 * cm, FABS_BANKS)
    # Page number
    canvas.drawRightString(w - 1.5 * cm, 0.5 * cm, f"Page {doc.page}")

    canvas.restoreState()


def _build_doc(buffer: BytesIO, title: str, reference: str, date_str: str,
               show_qr: bool = True, signature_label: str = "Signature & Cachet") -> BaseDocTemplate:
    doc = BaseDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=3.2 * cm, bottomMargin=4.2 * cm,
        title=f"{title} {reference}",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id="body", showBoundary=0,
    )

    def on_page(c, d):
        _draw_header(c, d, title, reference, date_str)
        _draw_footer(c, d, reference, show_qr=show_qr, signature_label=signature_label)

    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    return doc


# ---------------------------------------------------------------------------
# Client info block
# ---------------------------------------------------------------------------
def _client_block(client_data: Dict, extra_right: Optional[List[List[str]]] = None) -> Table:
    rows = [
        [Paragraph(f"<b>Client :</b> {client_data.get('nom', '-')}", STYLE_NORMAL),
         Paragraph(f"<b>Type :</b> {(client_data.get('type_client') or '-').upper()}", STYLE_NORMAL)],
        [Paragraph(f"<b>Ville :</b> {client_data.get('ville', '-')}", STYLE_NORMAL),
         Paragraph(f"<b>Tél. :</b> {client_data.get('telephone', '-')}", STYLE_NORMAL)],
        [Paragraph(f"<b>Adresse :</b> {client_data.get('adresse', '-')}", STYLE_NORMAL),
         Paragraph(f"<b>Représentant :</b> {client_data.get('representant', '-')}", STYLE_NORMAL)],
    ]
    if extra_right:
        for er in extra_right:
            rows.append([Paragraph(er[0], STYLE_NORMAL), Paragraph(er[1], STYLE_NORMAL)])
    t = Table(rows, colWidths=[9 * cm, 9 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("BOX", (0, 0), (-1, -1), 0.4, NAVY),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
    ]))
    return t


# ---------------------------------------------------------------------------
# Articles table (Classe / Code Article / Référence / Qté / PU / Montant)
# ---------------------------------------------------------------------------
def _articles_table(lignes: List[Dict], include_prix: bool = True) -> Table:
    if include_prix:
        headers = ["Classe", "Code Article", "Référence", "Qté", "Prix Unitaire", "Montant"]
        col_widths = [3 * cm, 3 * cm, 5 * cm, 1.4 * cm, 2.6 * cm, 2.8 * cm]
    else:
        headers = ["Classe", "Code Article", "Référence", "Qté"]
        col_widths = [3.5 * cm, 4 * cm, 8 * cm, 2 * cm]

    data = [headers]
    for ligne in lignes:
        row = [
            Paragraph(str(ligne.get("classe", "")), STYLE_NORMAL),
            Paragraph(str(ligne.get("code_article") or ligne.get("produit_id", ""))[:14], STYLE_NORMAL),
            Paragraph(str(ligne.get("designation", "")), STYLE_NORMAL),
            str(ligne.get("quantite", 0)),
        ]
        if include_prix:
            row += [
                format_fcfa(float(ligne.get("prix_unitaire", 0))),
                format_fcfa(float(ligne.get("montant_ht", 0))),
            ]
        data.append(row)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("ALIGN", (3, 1), (3, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ])
    if include_prix:
        style.add("ALIGN", (4, 1), (-1, -1), "RIGHT")
    t.setStyle(style)
    return t


def _totaux_block(montant_ht: float, montant_tva: float, montant_ttc: float,
                  remise_globale: float = 0) -> Table:
    rows = [
        ["Montant HT", format_fcfa(montant_ht)],
        ["Remise globale", format_fcfa(remise_globale)],
        ["TVA (18%)", format_fcfa(montant_tva)],
        ["TOTAL TTC", format_fcfa(montant_ttc)],
    ]
    t = Table(rows, colWidths=[5 * cm, 4 * cm], hAlign="RIGHT")
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 11),
        ("BACKGROUND", (0, -1), (-1, -1), ORANGE),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D1D5DB")),
    ]))
    return t


# ---------------------------------------------------------------------------
# PUBLIC GENERATORS
# ---------------------------------------------------------------------------
def generate_facture_pdf(facture: Dict, lignes: List[Dict], client: Dict) -> BytesIO:
    """Facture Client. Référence attendue ex: FABS-FC-26-27-0001."""
    is_avoir = facture.get("type_facture") == "avoir"
    title = "AVOIR CLIENT" if is_avoir else "FACTURE CLIENT"
    reference = facture.get("reference", "—")
    date_str = facture.get("date_facture") or facture.get("created_at", "")[:10]

    buffer = BytesIO()
    doc = _build_doc(buffer, title, reference, date_str)

    story: list = []
    story.append(_client_block(client, extra_right=[
        ["<b>Date :</b> " + (date_str or "-"), f"<b>Échéance :</b> {facture.get('date_echeance', '-') or '-'}"],
        ["<b>Mode de paiement :</b> Paiement à la livraison", ""],
    ]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(_articles_table(lignes, include_prix=True))
    story.append(Spacer(1, 0.4 * cm))
    story.append(_totaux_block(
        float(facture.get("montant_ht", 0)),
        float(facture.get("montant_tva", 0)),
        float(facture.get("montant_ttc", 0)),
        float(facture.get("remise_globale", 0)),
    ))
    if facture.get("notes"):
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(f"<b>Notes :</b> {facture['notes']}", STYLE_NORMAL))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_proforma_pdf(facture: Dict, lignes: List[Dict], client: Dict) -> BytesIO:
    """Facture Proforma — identique à la facture mais marquée PROFORMA."""
    reference = facture.get("reference", "—")
    date_str = facture.get("date_facture") or facture.get("created_at", "")[:10]
    buffer = BytesIO()
    doc = _build_doc(buffer, "FACTURE PROFORMA", reference, date_str)

    story = [
        _client_block(client, extra_right=[
            ["<b>Date :</b> " + (date_str or "-"), "<b>Validité :</b> 30 jours"],
            ["<b>Mode de paiement :</b> À convenir", ""],
        ]),
        Spacer(1, 0.5 * cm),
        _articles_table(lignes, include_prix=True),
        Spacer(1, 0.4 * cm),
        _totaux_block(
            float(facture.get("montant_ht", 0)),
            float(facture.get("montant_tva", 0)),
            float(facture.get("montant_ttc", 0)),
            float(facture.get("remise_globale", 0)),
        ),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "<i>Ce document est une <b>Facture Proforma</b> — il n'a pas valeur fiscale.</i>",
            STYLE_NORMAL),
    ]
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_commande_pdf(commande: Dict, lignes: List[Dict], client: Dict) -> BytesIO:
    """Bon de Commande."""
    reference = commande.get("reference", "—")
    date_str = commande.get("date_commande") or commande.get("created_at", "")[:10]
    buffer = BytesIO()
    doc = _build_doc(buffer, "BON DE COMMANDE", reference, date_str)

    story = [
        _client_block(client, extra_right=[
            ["<b>Date commande :</b> " + (date_str or "-"),
             f"<b>Statut :</b> {(commande.get('statut') or '-').upper()}"],
            [f"<b>Date livraison :</b> {commande.get('date_livraison_prevue', '-') or '-'}",
             f"<b>Mode paiement :</b> {commande.get('mode_paiement', 'À la livraison')}"],
        ]),
        Spacer(1, 0.5 * cm),
        _articles_table(lignes, include_prix=True),
        Spacer(1, 0.4 * cm),
        _totaux_block(
            float(commande.get("montant_ht", commande.get("montant_total", 0))),
            float(commande.get("montant_tva", 0)),
            float(commande.get("montant_ttc", commande.get("montant_total", 0))),
            float(commande.get("remise_globale", 0)),
        ),
    ]
    if commande.get("notes"):
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(f"<b>Commentaires :</b> {commande['notes']}", STYLE_NORMAL))

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_bl_pdf(bl: Dict, lignes: List[Dict], client: Dict, commande_ref: Optional[str] = None) -> BytesIO:
    """Bon de Livraison (sans prix)."""
    reference = bl.get("reference", "—")
    date_str = bl.get("date_livraison") or bl.get("created_at", "")[:10]
    buffer = BytesIO()
    doc = _build_doc(buffer, "BON DE LIVRAISON", reference, date_str,
                     signature_label="Signature du Réceptionnaire")

    extra = [
        ["<b>Date livraison :</b> " + (date_str or "-"),
         f"<b>BC N° :</b> {commande_ref or bl.get('commande_ref', '-')}"],
    ]
    story = [
        _client_block(client, extra_right=extra),
        Spacer(1, 0.5 * cm),
        _articles_table(lignes, include_prix=False),
    ]
    if bl.get("notes"):
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(f"<b>Observations :</b> {bl['notes']}", STYLE_NORMAL))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_retour_pdf(retour: Dict, lignes: List[Dict], client: Dict) -> BytesIO:
    """Bon de Retour."""
    reference = retour.get("reference", "—")
    date_str = retour.get("date_retour") or retour.get("created_at", "")[:10]
    buffer = BytesIO()
    doc = _build_doc(buffer, "BON DE RETOUR", reference, date_str,
                     signature_label="Signature du Réceptionnaire FABS-CI")

    extra = [
        ["<b>Date retour :</b> " + (date_str or "-"),
         f"<b>Motif :</b> {retour.get('motif', '-') or '-'}"],
    ]
    story = [
        _client_block(client, extra_right=extra),
        Spacer(1, 0.5 * cm),
        _articles_table(lignes, include_prix=True),
    ]
    if retour.get("notes"):
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(f"<b>Observations :</b> {retour['notes']}", STYLE_NORMAL))
    doc.build(story)
    buffer.seek(0)
    return buffer
