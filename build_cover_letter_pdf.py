"""
build_cover_letter_pdf.py — render paper/cover_letter.md to a clean PDF for
portal upload (Elsevier's submission system does not accept .md).
This is a submission-time convenience script, not part of the manuscript
build; it does light Markdown-to-PDF rendering (headings, bold, italics,
bullets, paragraphs) sufficient for a cover letter's simple formatting.
"""
import re
import os
from fpdf import FPDF

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "paper", "cover_letter.md")
OUT = os.path.join(ROOT, "submission_package", "cover_letter.pdf")

# fpdf2's core Helvetica font is latin-1 only; map common Unicode punctuation
# to safe ASCII equivalents instead of letting it silently degrade to "?".
_CHAR_MAP = {
    "\u2014": "--",   # em dash
    "\u2013": "-",    # en dash
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2026": "...",  # ellipsis
    "\u00e1": "a", "\u00e9": "e", "\u00ed": "i", "\u00f3": "o", "\u00fa": "u",
}


def clean(text):
    for k, v in _CHAR_MAP.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


def strip_emphasis(text):
    """Remove markdown ** / * markers for contexts (headings) that render as
    a single styled block rather than mixed inline runs."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text


def render_line(pdf, line, size=11):
    """Render a line handling **bold** and *italic* spans."""
    tokens = re.split(r"(\*\*.*?\*\*|\*[^*]+\*)", line)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            pdf.set_font("Helvetica", "B", size)
            pdf.write(6, clean(tok[2:-2]))
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 1:
            pdf.set_font("Helvetica", "I", size)
            pdf.write(6, clean(tok[1:-1]))
        else:
            pdf.set_font("Helvetica", "", size)
            pdf.write(6, clean(tok))
    pdf.ln(6)


def main():
    with open(SRC, encoding="utf-8") as f:
        lines = f.read().splitlines()

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    in_hr = False
    for raw in lines:
        line = raw.rstrip()
        if line.strip() == "---":
            pdf.ln(2)
            continue
        if line.startswith("<!--"):
            in_hr = True
            continue
        if in_hr:
            if "-->" in line:
                in_hr = False
            continue
        if not line.strip():
            pdf.ln(3)
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 16)
            pdf.multi_cell(0, 8, clean(strip_emphasis(line[2:])), align="L")
            pdf.ln(2)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.multi_cell(0, 7, clean(strip_emphasis(line[3:])), align="L")
            pdf.ln(1)
        elif line.startswith("- ") or re.match(r"^\d+\.\s", line):
            text = re.sub(r"^(-|\d+\.)\s", "", line)
            pdf.set_x(24)
            render_line(pdf, "- " + text)
        else:
            render_line(pdf, line)

    pdf.output(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
