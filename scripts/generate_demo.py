"""Rebuild the explicitly synthetic two-page demonstration PDF.

Optional development dependency: reportlab. Not needed to run the app.
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

ROOT = Path(__file__).parents[1]
OUT = ROOT / "examples" / "numerical-audit.pdf"
OUT.parent.mkdir(exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Note", fontSize=9, leading=13, textColor=colors.HexColor("#566780")))
styles.add(ParagraphStyle(name="BodyWide", fontSize=11, leading=17, spaceAfter=16))
story = []


def p(text, style="BodyWide"):
    story.append(Paragraph(text, styles[style]))


def footer(canvas, document):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#566780"))
    canvas.drawString(48, 32, "LitWeaver AI | Synthetic verification fixture - no real scientific findings")
    canvas.drawRightString(560, 32, str(document.page))


p("LITWEAVER AI / EVALUATION FIXTURE", "Note")
p("A numerical audit, with known errors", "Title")
p("Synthetic demonstration - not a real scientific paper", "Heading2")
p("This document intentionally contains correct and incorrect claims. It tests source tracking, arithmetic and abstention. The values are invented solely as labelled test data.")
p("Methods", "Heading2")
p("Context demo/test/run1 denotes the Demo dataset, held-out test split, first run, with the same classification setting for both models. The table below is machine-readable and has explicit context labels.")
p("Results", "Heading2")
data = [["Model", "Accuracy (%)", "Context"], ["Model A", "87.4", "demo/test/run1"], ["Model B", "84.2", "demo/test/run1"]]
table = Table(data, colWidths=[130, 140, 220], rowHeights=[32, 32, 32])
table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E6F2F4")), ("TEXTCOLOR", (0,0),(-1,-1),colors.HexColor("#172B4D")), ("FONTNAME", (0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE", (0,0),(-1,-1),10), ("GRID", (0,0),(-1,-1),0.6,colors.HexColor("#93A9BA")), ("VALIGN", (0,0),(-1,-1),"MIDDLE"), ("LEFTPADDING", (0,0),(-1,-1),12)]))
story.append(table)
story.append(Spacer(1, 24))
p("[context: demo/test/run1] Model A accuracy = 87.4%.")
p("[context: demo/test/run1] Model B accuracy = 84.2%.")
p("A separate arithmetic example uses a baseline accuracy of 80.0% and a new accuracy of 92.0%. These values are not the model-comparison experiment above.", "Note")
story.append(PageBreak())
p("Discussion", "Heading2")
p("[context: demo/test/run1] Model B achieved higher classification accuracy than Model A.")
p("[context: demo/test/run1] Model A achieved higher accuracy than Model B.")
p("Accuracy improved by 12% from 80.0% to 92.0%.")
p("Accuracy improved by 15% from 80.0% to 92.0%.")
p("Accuracy increased by 12 percentage points from 80.0% to 92.0%.")
p("Our findings prove that the approach generalizes to all hospitals.")
p("Limitations", "Heading2")
p("Only one synthetic dataset and one run are described. No independent replication or external validity evidence is supplied. The broad hospital claim has no supporting experiment.")
p("Expected audit behavior", "Heading2")
p("Flag the claim that Model B has higher accuracy. Distinguish the incorrect 12% relative change from the correct 15% relative change and 12 percentage-point change. Abstain on the broad generalization. Preserve the actual PDF page and evidence identifiers for each finding.", "Note")
SimpleDocTemplate(str(OUT), pagesize=(612,792), rightMargin=54, leftMargin=54, topMargin=48, bottomMargin=50, title="LitWeaver synthetic numerical audit", author="LitWeaver evaluation fixture").build(story, onFirstPage=footer, onLaterPages=footer)
print(OUT)
