#!/usr/bin/env python3
"""
compile_resume.py — compile a tailored LaTeX resume to PDF and place it in 02_Resumes_Tailored.

Usage:
    python3 compile_resume.py <path_to_tex_file> <output_pdf_name>

Example:
    python3 compile_resume.py \
        "/Applications/saggydev/Job Applications/JobSearch_2026/02_Resumes_Tailored/Plaid_SWE_Backend_SagarSinha.tex" \
        "Plaid_SWE_Backend_SagarSinha"

The output PDF is saved to:
    /Applications/saggydev/Job Applications/JobSearch_2026/02_Resumes_Tailored/<output_pdf_name>.pdf
"""

import subprocess
import sys
import os
import shutil
import tempfile

TAILORED_DIR = "/Applications/saggydev/Job Applications/JobSearch_2026/02_Resumes_Tailored"


def compile_resume(tex_path: str, output_name: str) -> None:
    tex_path = os.path.abspath(tex_path)

    if not os.path.exists(tex_path):
        print(f"ERROR: .tex file not found: {tex_path}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Two pdflatex passes for stable layout
        for pass_num in range(1, 3):
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    f"-output-directory={tmpdir}",
                    tex_path,
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"ERROR: pdflatex failed on pass {pass_num}.")
                # Show last 3000 chars of log for diagnosis
                print(result.stdout[-3000:])
                sys.exit(1)

        tex_basename = os.path.splitext(os.path.basename(tex_path))[0]
        tmp_pdf = os.path.join(tmpdir, tex_basename + ".pdf")

        if not os.path.exists(tmp_pdf):
            print(f"ERROR: PDF not generated at expected path: {tmp_pdf}")
            sys.exit(1)

        os.makedirs(TAILORED_DIR, exist_ok=True)
        out_pdf = os.path.join(TAILORED_DIR, output_name + ".pdf")
        shutil.copy2(tmp_pdf, out_pdf)
        print(f"PDF compiled: {out_pdf}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 compile_resume.py <tex_file_path> <output_pdf_name>")
        sys.exit(1)
    compile_resume(sys.argv[1], sys.argv[2])
