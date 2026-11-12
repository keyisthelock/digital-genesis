from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent
OUT = ROOT/"output/pdf/HOMER_01_1_8_Build_Report.pdf"
styles = getSampleStyleSheet()
teal = colors.HexColor("#146B65")
styles["Title"].alignment = 0
styles["Title"].textColor = colors.HexColor("#172A37")
styles["Heading2"].textColor = teal
styles["BodyText"].leading = 14
styles["BodyText"].spaceAfter = 7


def block():
    pending=[]
    lines=(ROOT/"HOMER_1_8_BUILD_REPORT.md").read_text(encoding="utf-8").splitlines()
    for line in [*lines,""]:
        if line.startswith("|"):
            pending.append(line)
            continue
        if pending:
            rows=[[Paragraph(escape(c.strip()),styles["BodyText"]) for c in row.strip("|").split("|")]
                  for row in [pending[0],*pending[2:]]]
            table=Table(rows,colWidths=(157,111,111,111),repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E5F3EF")),
                ("LINEBELOW",(0,0),(-1,0),1,teal),
                ("LINEBELOW",(0,1),(-1,-1),.25,colors.HexColor("#D2E6E1")),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
            ]))
            yield table
            yield Spacer(1,7)
            pending.clear()
        if line.startswith("# "):
            yield Paragraph(escape(line[2:]),styles["Title"])
        elif line.startswith("## "):
            if line=="## What Homer did":
                yield PageBreak()
            yield Paragraph(escape(line[3:]),styles["Heading2"])
        elif line.strip():
            yield Paragraph(escape(line),styles["BodyText"])


def footer(canvas,doc):
    canvas.setFillColor(teal)
    canvas.setFont("Helvetica",9)
    canvas.drawString(54,34,"DIGITAL GENESIS   /   1.8")
    canvas.drawRightString(558,34,str(doc.page))


if __name__=="__main__":
    OUT.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(OUT),pagesize=(612,792),leftMargin=54,rightMargin=54,
                          topMargin=42,bottomMargin=53,title="HOMER-01 1.8 Build Report")
    doc.build(list(block()),onFirstPage=footer,onLaterPages=footer)
