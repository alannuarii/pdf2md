"""
PDF to Markdown Converter — FastAPI Application.

Serves the API endpoints and the static frontend UI.
"""

import os
import shutil
import tempfile
import zipfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.converter import convert_pdf_to_markdown

app = FastAPI(
    title="PDF to Markdown Converter",
    description="Konversi file PDF ke dokumen Markdown dengan struktur heading, list, dan tabel.",
    version="1.1.0",
)

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@app.get("/api/health")
async def healthcheck():
    """Healthcheck endpoint for monitoring and CI/CD pipelines."""
    return {"status": "ok"}


@app.post("/api/convert")
async def convert_pdf(
    file: UploadFile = File(...),
    extract_images: bool = Form(False),
):
    """
    Convert an uploaded PDF file to Markdown.

    Accepts multipart/form-data with:
    - `file`: Binary PDF file
    - `extract_images`: Boolean flag (default false). If true, images are
      extracted and a ZIP file is returned instead of JSON.
    """
    # --- Validate file extension ---
    filename = file.filename or "document.pdf"
    _, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File bukan PDF. Ekstensi '{ext}' tidak diizinkan. Hanya file .pdf yang diterima.",
        )

    # --- Validate MIME type ---
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipe file tidak valid ({file.content_type}). Hanya file application/pdf yang diterima.",
        )

    # --- Read file content ---
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Gagal membaca file yang diunggah.",
        )

    # --- Validate file size ---
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Ukuran file melebihi batas maksimum ({MAX_FILE_SIZE // (1024 * 1024)} MB).",
        )

    # --- Convert using temp file ---
    tmp_path = None
    images_dir = None
    zip_path = None

    try:
        # Write to a secure temporary file
        with tempfile.NamedTemporaryFile(
            suffix=".pdf", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Perform conversion
        result = convert_pdf_to_markdown(
            tmp_path,
            extract_images=extract_images,
        )

        markdown_text = result["markdown"]
        images_dir = result["images_dir"]
        page_count = result["page_count"]

        # Build output filename
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}.md"

        # If images were extracted, package as ZIP
        if extract_images and images_dir:
            image_files = [
                f for f in os.listdir(images_dir)
                if os.path.isfile(os.path.join(images_dir, f))
            ]

            if image_files:
                # Create ZIP containing .md + images/
                zip_path = tempfile.mktemp(suffix=".zip", prefix="pdf2md_")
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Add the markdown file
                    zf.writestr(output_filename, markdown_text)
                    # Add images in an images/ subfolder
                    for img_file in image_files:
                        img_path = os.path.join(images_dir, img_file)
                        zf.write(img_path, f"images/{img_file}")

                # Clean up images dir immediately
                shutil.rmtree(images_dir, ignore_errors=True)
                images_dir = None

                zip_filename = f"{base_name}.zip"

                # Return ZIP as file download
                return FileResponse(
                    path=zip_path,
                    filename=zip_filename,
                    media_type="application/zip",
                    background=_cleanup_task(zip_path),
                )

            # No images found — clean up and fall through to JSON response
            shutil.rmtree(images_dir, ignore_errors=True)
            images_dir = None

        return JSONResponse(
            content={
                "success": True,
                "filename": output_filename,
                "markdown": markdown_text,
                "page_count": page_count,
            }
        )

    except ValueError as e:
        # Password-protected PDF
        raise HTTPException(status_code=400, detail=str(e))

    except RuntimeError as e:
        # Corrupt or unprocessable PDF
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan internal saat mengonversi file: {e}",
        )

    finally:
        # Always clean up the temporary PDF file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        # Clean up images dir if still present (error path)
        if images_dir and os.path.exists(images_dir):
            shutil.rmtree(images_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Background cleanup for temp ZIP files
# ---------------------------------------------------------------------------

class _cleanup_task:
    """Starlette BackgroundTask-compatible callable to delete temp files."""

    def __init__(self, path: str):
        self.path = path

    async def __call__(self):
        if self.path and os.path.exists(self.path):
            os.unlink(self.path)


# ---------------------------------------------------------------------------
# Static Files — Mount AFTER API routes so /api/* takes priority
# ---------------------------------------------------------------------------

static_dir = os.path.join(os.path.dirname(__file__), "static")
favicon_path = os.path.join(static_dir, "favicon.svg")


@app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
async def favicon():
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/svg+xml")
    return JSONResponse(status_code=404, content={"detail": "Not found"})


app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
