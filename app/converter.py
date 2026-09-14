"""
PDF to Markdown Converter Module.

Wraps pymupdf4llm to extract structured Markdown from PDF files,
with error handling for corrupt or password-protected files.
Includes post-processing for PUA character sanitization,
page number noise removal, and empty image comment cleanup.
"""

import re
import os
import shutil
import tempfile

import pymupdf4llm
import pymupdf  # fitz — used for error type checking


# ---------------------------------------------------------------------------
# Post-processing: PUA (Private Use Area) → Standard Unicode Symbols
# ---------------------------------------------------------------------------

# Mapping of Word/Equation font PUA characters to standard math symbols.
# These are commonly emitted by legacy Equation Editor or Symbol font in
# Word-generated PDFs.
PUA_SYMBOL_MAPPING = {
    "\uf020": " ",   # Space (Symbol font)
    "\uf021": "!",   # Exclamation (Symbol font)
    "\uf022": "\u2200",  # ∀ For all
    "\uf023": "#",   # Number sign (Symbol font)
    "\uf024": "\u2203",  # ∃ Exists
    "\uf025": "%",   # Percent (Symbol font)
    "\uf026": "&",   # Ampersand (Symbol font)
    "\uf028": "(",   # Left paren (Symbol font)
    "\uf029": ")",   # Right paren (Symbol font)
    "\uf02a": "\u2217",  # ∗ Asterisk operator
    "\uf02b": "+",   # Plus sign (Symbol font)
    "\uf02d": "\u2212",  # − Minus sign
    "\uf02f": "/",   # Solidus (Symbol font)
    "\uf03c": "<",   # Less-than (Symbol font)
    "\uf03d": "=",   # Equals (Symbol font)
    "\uf03e": ">",   # Greater-than (Symbol font)
    "\uf040": "\u2245",  # ≅ Approximately equal
    "\uf044": "\u0394",  # Δ Delta
    "\uf046": "\u03A6",  # Φ Phi
    "\uf047": "\u0393",  # Γ Gamma
    "\uf04a": "\u03D1",  # ϑ Theta symbol
    "\uf04c": "\u039B",  # Λ Lambda
    "\uf050": "\u03A0",  # Π Pi
    "\uf051": "\u0398",  # Θ Theta
    "\uf053": "\u03A3",  # Σ Sigma
    "\uf057": "\u03A9",  # Ω Omega
    "\uf058": "\u039E",  # Ξ Xi
    "\uf059": "\u03A8",  # Ψ Psi
    "\uf05b": "[",   # Left bracket (Symbol font)
    "\uf05d": "]",   # Right bracket (Symbol font)
    "\uf05e": "\u22A5",  # ⊥ Perpendicular
    "\uf061": "\u03B1",  # α alpha
    "\uf062": "\u03B2",  # β beta
    "\uf063": "\u03C7",  # χ chi
    "\uf064": "\u03B4",  # δ delta
    "\uf065": "\u03B5",  # ε epsilon
    "\uf066": "\u03C6",  # φ phi
    "\uf067": "\u03B3",  # γ gamma
    "\uf068": "\u03B7",  # η eta
    "\uf069": "\u03B9",  # ι iota
    "\uf06b": "\u03BA",  # κ kappa
    "\uf06c": "\u03BB",  # λ lambda
    "\uf06d": "\u03BC",  # μ mu
    "\uf06e": "\u03BD",  # ν nu
    "\uf070": "\u03C0",  # π pi
    "\uf071": "\u03B8",  # θ theta
    "\uf072": "\u03C1",  # ρ rho
    "\uf073": "\u03C3",  # σ sigma
    "\uf074": "\u03C4",  # τ tau
    "\uf075": "\u03C5",  # υ upsilon
    "\uf077": "\u03C9",  # ω omega
    "\uf078": "\u03BE",  # ξ xi
    "\uf079": "\u03C8",  # ψ psi
    "\uf07a": "\u03B6",  # ζ zeta
    "\uf07b": "{",   # Left brace (Symbol font)
    "\uf07c": "|",   # Vertical bar (Symbol font)
    "\uf07d": "}",   # Right brace (Symbol font)
    "\uf07e": "~",   # ~ Negation / tilde
    "\uf0a3": "\u2264",  # ≤ Less-than or equal to
    "\uf0a5": "\u221E",  # ∞ Infinity
    "\uf0ab": "\u2194",  # ↔ Bi-implication / left-right arrow
    "\uf0ac": "\u2190",  # ← Left arrow
    "\uf0ad": "\u2191",  # ↑ Up arrow
    "\uf0ae": "\u2192",  # → Right arrow / implication
    "\uf0af": "\u2193",  # ↓ Down arrow
    "\uf0b0": "\u00B0",  # ° Degree sign
    "\uf0b1": "\u00B1",  # ± Plus-minus
    "\uf0b2": "\u2033",  # ″ Double prime
    "\uf0b3": "\u2265",  # ≥ Greater-than or equal to
    "\uf0b4": "\u00D7",  # × Multiplication sign
    "\uf0b5": "\u221D",  # ∝ Proportional to
    "\uf0b6": "\u2202",  # ∂ Partial differential
    "\uf0b7": "\u2022",  # • Bullet
    "\uf0b8": "\u00F7",  # ÷ Division sign
    "\uf0b9": "\u2260",  # ≠ Not equal to
    "\uf0ba": "\u2261",  # ≡ Identical to
    "\uf0bb": "\u2248",  # ≈ Almost equal to
    "\uf0bc": "\u2026",  # … Ellipsis
    "\uf0c0": "\u2135",  # ℵ Alef symbol
    "\uf0c1": "\u2111",  # ℑ Imaginary part
    "\uf0c2": "\u211C",  # ℜ Real part
    "\uf0c3": "\u2118",  # ℘ Weierstrass p
    "\uf0c4": "\u2297",  # ⊗ Circled times
    "\uf0c5": "\u2295",  # ⊕ Circled plus
    "\uf0c6": "\u2205",  # ∅ Empty set
    "\uf0c7": "\u2229",  # ∩ Intersection
    "\uf0c8": "\u222A",  # ∪ Union
    "\uf0c9": "\u2283",  # ⊃ Superset
    "\uf0ca": "\u2287",  # ⊇ Superset or equal
    "\uf0cb": "\u2284",  # ⊄ Not a subset
    "\uf0cc": "\u2282",  # ⊂ Subset
    "\uf0cd": "\u2286",  # ⊆ Subset or equal
    "\uf0ce": "\u2208",  # ∈ Element of
    "\uf0cf": "\u2209",  # ∉ Not an element of
    "\uf0d0": "\u2220",  # ∠ Angle
    "\uf0d1": "\u2207",  # ∇ Nabla / gradient
    "\uf0d2": "\u00AE",  # ® Registered
    "\uf0d3": "\u00A9",  # © Copyright
    "\uf0d4": "\u2122",  # ™ Trademark
    "\uf0d5": "\u220F",  # ∏ Product
    "\uf0d6": "\u221A",  # √ Square root
    "\uf0d7": "\u22C5",  # ⋅ Dot operator
    "\uf0d8": "\u00AC",  # ¬ Not sign
    "\uf0d9": "\u2227",  # ∧ Logical AND / conjunction
    "\uf0da": "\u2228",  # ∨ Logical OR / disjunction
    "\uf0db": "\u21D4",  # ⇔ Left-right double arrow
    "\uf0dc": "\u21D0",  # ⇐ Left double arrow
    "\uf0dd": "\u21D1",  # ⇑ Up double arrow
    "\uf0de": "\u21D2",  # ⇒ Right double arrow / implies
    "\uf0df": "\u21D3",  # ⇓ Down double arrow
    "\uf0e0": "\u25CA",  # ◊ Lozenge
    "\uf0e1": "\u2329",  # ⟨ Left angle bracket
    "\uf0e5": "\u2211",  # ∑ Summation
    "\uf0e8": "\u222B",  # ∫ Integral
    "\uf0f1": "\u232A",  # ⟩ Right angle bracket
}

# Build a single-pass regex from all PUA keys
_pua_pattern = re.compile(
    "|".join(re.escape(k) for k in sorted(PUA_SYMBOL_MAPPING.keys(), key=len, reverse=True))
)


def _sanitize_pua_characters(text: str) -> str:
    """Replace Private Use Area characters with standard Unicode equivalents."""
    # Also catch any remaining PUA chars not in our map — replace with placeholder
    result = _pua_pattern.sub(lambda m: PUA_SYMBOL_MAPPING[m.group()], text)

    # Remove any remaining PUA characters (U+E000–U+F8FF) that weren't mapped
    result = re.sub(r"[\uE000-\uF8FF]", "", result)

    return result


# ---------------------------------------------------------------------------
# Post-processing: Remove isolated page numbers & header/footer noise
# ---------------------------------------------------------------------------

# Pattern: a line containing ONLY a standalone number (e.g. "1", "23", "105")
# optionally surrounded by whitespace — but NOT inside a table row (no pipes)
_PAGE_NUMBER_PATTERNS = [
    # Plain standalone number on its own line: "\n  42  \n"
    re.compile(r"(?m)^\s*\d{1,4}\s*$"),
    # Dashed page numbers: "- 13 -", "-A1-", "- B2 -"
    re.compile(r"(?m)^\s*-\s*[A-Z]?\d{1,4}\s*-\s*$"),
]


def _remove_page_number_noise(text: str) -> str:
    """
    Remove isolated page numbers that appear on their own lines.
    Preserves numbers inside table rows (lines containing '|').
    """
    lines = text.split("\n")
    cleaned = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Track table context — don't clean inside tables
        if stripped.startswith("|"):
            in_table = True
            cleaned.append(line)
            continue
        elif in_table and not stripped.startswith("|") and stripped != "":
            in_table = False

        # Skip empty lines normally
        if stripped == "":
            cleaned.append(line)
            continue

        # Check if this line is an isolated page number
        is_page_number = False
        if not in_table:
            for pattern in _PAGE_NUMBER_PATTERNS:
                if pattern.fullmatch(stripped):
                    is_page_number = True
                    break

        if not is_page_number:
            cleaned.append(line)

    return "\n".join(cleaned)


# ---------------------------------------------------------------------------
# Post-processing: Clean empty image comment tags
# ---------------------------------------------------------------------------

_EMPTY_IMAGE_COMMENT_PATTERN = re.compile(
    r"\s*<!--\s*Start of picture text\s*-->.*?<!--\s*End of picture text\s*-->\s*",
    re.DOTALL,
)


def _clean_empty_image_comments(text: str) -> str:
    """Remove empty <!-- Start of picture text --> ... <!-- End of picture text --> blocks."""
    return _EMPTY_IMAGE_COMMENT_PATTERN.sub("\n", text)


# ---------------------------------------------------------------------------
# Post-processing: Clean excessive blank lines
# ---------------------------------------------------------------------------

def _clean_excessive_blanks(text: str) -> str:
    """Collapse 3+ consecutive blank lines down to 2."""
    return re.sub(r"\n{4,}", "\n\n\n", text)


# ---------------------------------------------------------------------------
# Main conversion function
# ---------------------------------------------------------------------------

def convert_pdf_to_markdown(
    file_path: str,
    extract_images: bool = False,
) -> dict:
    """
    Convert a PDF file to Markdown text.

    Args:
        file_path: Absolute path to the PDF file on disk.
        extract_images: If True, extract images and return them alongside markdown.

    Returns:
        A dict with keys:
            - "markdown": The cleaned Markdown text.
            - "images_dir": Path to extracted images directory (or None).
            - "page_count": Number of pages in the PDF.

    Raises:
        ValueError: If the PDF is password-protected or encrypted.
        RuntimeError: If the PDF is corrupt or cannot be processed.
    """
    images_dir = None

    try:
        # Get page count for progress info
        doc = pymupdf.open(file_path)
        page_count = doc.page_count
        doc.close()

        # Prepare conversion kwargs
        kwargs = {}

        if extract_images:
            # Create a temporary directory for images
            images_dir = tempfile.mkdtemp(prefix="pdf2md_images_")
            kwargs["write_images"] = True
            kwargs["image_path"] = images_dir
            kwargs["image_format"] = "png"

        # pymupdf4llm.to_markdown handles heading, list, and table extraction
        markdown_text = pymupdf4llm.to_markdown(file_path, **kwargs)

        # --- Post-processing pipeline ---
        markdown_text = _sanitize_pua_characters(markdown_text)
        markdown_text = _remove_page_number_noise(markdown_text)

        if not extract_images:
            markdown_text = _clean_empty_image_comments(markdown_text)

        markdown_text = _clean_excessive_blanks(markdown_text)

        return {
            "markdown": markdown_text,
            "images_dir": images_dir,
            "page_count": page_count,
        }

    except pymupdf.FileDataError:
        # Clean up images dir on error
        if images_dir and os.path.exists(images_dir):
            shutil.rmtree(images_dir, ignore_errors=True)
        raise RuntimeError(
            "File PDF rusak atau tidak dapat dibaca. "
            "Pastikan file tidak corrupt."
        )

    except Exception as e:
        # Clean up images dir on error
        if images_dir and os.path.exists(images_dir):
            shutil.rmtree(images_dir, ignore_errors=True)

        error_msg = str(e).lower()

        # Detect password-protected / encrypted PDFs
        if "password" in error_msg or "encrypt" in error_msg:
            raise ValueError(
                "File PDF terkunci dengan password. "
                "Silakan buka kunci PDF terlebih dahulu sebelum mengonversi."
            )

        # Detect corrupt or unreadable files
        if "cannot open" in error_msg or "corrupt" in error_msg:
            raise RuntimeError(
                "File PDF rusak atau tidak dapat dibaca. "
                "Pastikan file tidak corrupt."
            )

        # Re-raise unexpected errors with context
        raise RuntimeError(
            f"Gagal mengonversi PDF: {e}"
        )
