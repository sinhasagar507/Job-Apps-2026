#!/usr/bin/env python3
"""
compile_cover_letter.py — generate a cover letter PDF directly via reportlab.

Usage:
    python3 compile_cover_letter.py <company> <role_short>

Example:
    python3 compile_cover_letter.py "RamaleyGroup" "JrBA"

The output PDF is saved to:
    /Applications/saggydev/Job Applications/JobSearch_2026/03_CoverLetters/<Company>_<Role>_SagarSinha.pdf

To add a new cover letter, edit the LETTERS dict at the bottom of this file.
"""

import sys
import os
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib import colors

COVER_LETTERS_DIR = "/Applications/saggydev/Job Applications/JobSearch_2026/03_CoverLetters"

CANDIDATE = {
    "name": "Sagar Sinha",
    "phone": "(602) 670-3742",
    "email": "sinhasagar507@gmail.com",
    "linkedin": "linkedin.com/in/sagarsinha2000",
}

# ---------------------------------------------------------------------------
# LETTER REGISTRY — add new entries here for each cover letter
# ---------------------------------------------------------------------------
LETTERS = {
    ("ramaleygroup", "jrba"): {
        "date": "June 21, 2026",
        "recipient": "Hiring Team\nRamaley Group LLC\ninfo@ramaleygroup.com",
        "salutation": "Dear Ramaley Group Hiring Team,",
        "paragraphs": [
            (
                "I am applying for the Junior Business Analyst role at Ramaley Group. "
                "Your firm's first core value - \"We do not automate broken processes\" - reflects exactly "
                "how I have approached every analytics engagement I have worked on, making this an opportunity "
                "I am genuinely motivated to pursue."
            ),
            (
                "As a Data Analyst at Arizona State University, I designed SQL ETL pipelines to standardize "
                "50,000+ health records and built interactive Tableau dashboards that surfaced root causes "
                "behind campus health trends for cross-functional leadership. Rather than treating data quality "
                "as a downstream cleanup task, I established automated QA checks and organizational data "
                "governance protocols that eliminated systemic process failures upstream - ensuring every "
                "stakeholder report rested on a reliable, repeatable foundation. This experience gave me "
                "direct practice in the kind of back-office business analysis work your Junior BAs focus on: "
                "translating messy operational inputs into structured, auditable outputs."
            ),
            (
                "In my AI Intern role at Extern, I worked closely with Product and Engineering teams to "
                "translate business requirements into a structured document retrieval workflow, then built "
                "stakeholder-facing monitoring tools that made process health and feature adoption visible "
                "in real time. I have worked in Agile delivery environments and am comfortable with "
                "iterative, feedback-driven cycles - which aligns with Ramaley Group's methodology pillars. "
                "My background also includes stakeholder communication across technical and non-technical "
                "audiences, root cause analysis on large behavioral datasets, and data-driven decision "
                "support for senior leadership, all of which translate directly to the responsibilities "
                "described in this role. I hold a Master of Science in Computer Science from Arizona State "
                "University and am authorized to work in the United States without sponsorship. I am open "
                "to the travel requirements and flexible across EMEA time zones."
            ),
            (
                "I am excited by the opportunity to learn Lean Six Sigma, Theory of Constraints, and "
                "Change Acceleration methodologies under experienced mentors while contributing immediately "
                "through structured analysis and clear documentation. If you are reviewing candidates for "
                "this role, I would welcome the chance to discuss my profile and learn more about the team "
                "- and if my background looks like a fit, I would be grateful if you could forward my "
                "application to whoever is leading the search."
            ),
        ],
        "closing": "Sincerely,",
    },
}


def build_styles():
    base = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "NameStyle",
        parent=base["Normal"],
        fontSize=16,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1a1a1a"),
        spaceAfter=2,
    )
    contact_style = ParagraphStyle(
        "ContactStyle",
        parent=base["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=colors.HexColor("#444444"),
        spaceAfter=0,
    )
    date_style = ParagraphStyle(
        "DateStyle",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica",
        spaceAfter=4,
    )
    recipient_style = ParagraphStyle(
        "RecipientStyle",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica",
        leading=14,
        spaceAfter=4,
    )
    salutation_style = ParagraphStyle(
        "SalutationStyle",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica",
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica",
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )
    closing_style = ParagraphStyle(
        "ClosingStyle",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica",
        spaceAfter=2,
    )
    sig_style = ParagraphStyle(
        "SigStyle",
        parent=base["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        spaceAfter=0,
    )
    return {
        "name": name_style,
        "contact": contact_style,
        "date": date_style,
        "recipient": recipient_style,
        "salutation": salutation_style,
        "body": body_style,
        "closing": closing_style,
        "sig": sig_style,
    }


def generate_pdf(letter_key: tuple, output_path: str) -> None:
    key = (letter_key[0].lower(), letter_key[1].lower())
    if key not in LETTERS:
        available = [f"{c}/{r}" for c, r in LETTERS]
        print(f"ERROR: No letter found for key {letter_key}. Available: {available}")
        sys.exit(1)

    data = LETTERS[key]
    styles = build_styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=LETTER,
        leftMargin=1.0 * inch,
        rightMargin=1.0 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
    )

    story = []

    # Header - name
    story.append(Paragraph(CANDIDATE["name"], styles["name"]))

    # Contact line
    contact_line = (
        f"{CANDIDATE['phone']}  |  "
        f'<a href="mailto:{CANDIDATE["email"]}" color="#0066cc">{CANDIDATE["email"]}</a>  |  '
        f'<a href="https://{CANDIDATE["linkedin"]}" color="#0066cc">{CANDIDATE["linkedin"]}</a>'
    )
    story.append(Paragraph(contact_line, styles["contact"]))

    # Horizontal rule via a thin colored rectangle - simulate with spacer + line approach
    story.append(Spacer(1, 6))
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cccccc")))
    story.append(Spacer(1, 10))

    # Date
    story.append(Paragraph(data["date"], styles["date"]))
    story.append(Spacer(1, 6))

    # Recipient block (multiline)
    for line in data["recipient"].split("\n"):
        story.append(Paragraph(line, styles["recipient"]))
    story.append(Spacer(1, 10))

    # Salutation
    story.append(Paragraph(data["salutation"], styles["salutation"]))
    story.append(Spacer(1, 4))

    # Body paragraphs
    for para in data["paragraphs"]:
        story.append(Paragraph(para, styles["body"]))

    # Closing
    story.append(Spacer(1, 6))
    story.append(Paragraph(data["closing"], styles["closing"]))
    story.append(Spacer(1, 30))
    story.append(Paragraph(CANDIDATE["name"], styles["sig"]))

    doc.build(story)
    print(f"PDF compiled: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 compile_cover_letter.py <company> <role_short>")
        print("Example: python3 compile_cover_letter.py RamaleyGroup JrBA")
        sys.exit(1)

    company = sys.argv[1]
    role = sys.argv[2]
    filename = f"{company}_{role}_SagarSinha.pdf"
    out_path = os.path.join(COVER_LETTERS_DIR, filename)
    os.makedirs(COVER_LETTERS_DIR, exist_ok=True)
    generate_pdf((company, role), out_path)
