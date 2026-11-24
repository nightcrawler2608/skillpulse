"""Read text from a resume, entirely in memory.

Privacy: the file's bytes are read from memory and the text is returned to the
caller. Nothing is written to disk or to the database.
"""

from __future__ import annotations

import io
import re

MAX_BYTES = 5 * 1024 * 1024   # 5 MB
MAX_PAGES = 6                  # resumes are 1-3 pages; this stops huge uploads
MIN_CHARS = 200                # less than this usually means a scanned (image) PDF


class ResumeError(ValueError):
    """A problem the user can fix (shown to them as a friendly message)."""


def clean_text(text: str) -> str:
    text = text.replace(" ", " ").replace("•", " • ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)      # no spaces around line breaks
    text = re.sub(r"\n{2,}", "\n", text)       # no blank lines
    return text.strip()


def pdf_to_text(data: bytes) -> str:
    import pdfplumber  # imported here so the core package doesn't need it

    if len(data) > MAX_BYTES:
        raise ResumeError("That file is bigger than 5 MB. Please upload a smaller PDF.")
    if not data.startswith(b"%PDF"):
        raise ResumeError("That doesn't look like a PDF file.")
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise ResumeError(f"Resumes longer than {MAX_PAGES} pages aren't supported.")
            text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    except ResumeError:
        raise
    except Exception as e:
        raise ResumeError("Couldn't read this PDF. Try exporting it again, or paste the text.") from e
    text = clean_text(text)
    if len(text) < MIN_CHARS:
        raise ResumeError("Couldn't find text in this PDF. It may be a scanned image. "
                          "Please paste your resume text instead.")
    return text
