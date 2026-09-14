# PDF to Markdown Converter

Aplikasi web mandiri (*self-hosted*) berarsitektur monolit berbasis Python untuk mengonversi file PDF menjadi dokumen Markdown (`.md`) dengan mempertahankan struktur heading, list, dan tabel secara optimal.

## ✨ Fitur

- **Drag & Drop Upload** — Area dropzone interaktif dengan validasi file (`.pdf` only, maks 50 MB).
- **Konversi Cepat** — Engine konversi berbasis `pymupdf4llm` (ringan, tanpa GPU).
- **Dual View** — Lihat hasil dalam mode *Raw Markdown* atau *Rendered Preview*.
- **Copy & Download** — Salin ke clipboard atau unduh langsung sebagai file `.md`.
- **Error Handling** — Penanganan file rusak dan PDF terenkripsi password.

## 🛠 Tech Stack

| Layer      | Teknologi                        |
|------------|----------------------------------|
| Backend    | FastAPI + Uvicorn (Python 3.11+) |
| Conversion | pymupdf4llm                      |
| Frontend   | Vanilla JS, Tailwind CSS (CDN), marked.js (CDN) |
| Deploy     | Docker, Docker Compose, Jenkins  |

## 📁 Project Structure

```
pdf2md/
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI entrypoint & static files
│   ├── converter.py         # PDF → Markdown conversion logic
│   └── static/
│       └── index.html       # Web UI (single-page)
├── Dockerfile
├── docker-compose.yml
├── Jenkinsfile
├── requirements.txt
├── PRD.md
└── README.md
```

## 🚀 Menjalankan Aplikasi

### Lokal (Development)

```bash
# 1. Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Jalankan server
uvicorn app.main:app --reload --port 8000
```

Akses aplikasi di **http://localhost:8000**

### Docker

```bash
# Build & run dengan Docker Compose
docker compose up -d --build

# Atau manual
docker build -t pdf2md-app:latest .
docker run -d --name pdf2md-app --restart always -p 3020:8000 pdf2md-app:latest
```

Akses aplikasi di **http://localhost:3020**

## 📡 API Reference

### Healthcheck

```http
GET /api/health
```

**Response:**

```json
{
  "status": "ok"
}
```

### Konversi PDF

```http
POST /api/convert
Content-Type: multipart/form-data
```

| Parameter | Tipe   | Deskripsi             |
|-----------|--------|-----------------------|
| `file`    | Binary | File PDF yang diunggah |

**Response Sukses (200):**

```json
{
  "success": true,
  "filename": "document.md",
  "markdown": "# Judul Dokumen\n\nIsi paragraf..."
}
```

**Response Gagal (400/500):**

```json
{
  "detail": "Pesan error spesifik"
}
```

## 🔄 CI/CD (Jenkins)

Pipeline Jenkins tersedia di `Jenkinsfile` dengan stage:

1. **Checkout** — Ambil kode dari SCM
2. **Build Image** — Build Docker image
3. **Deploy Container** — Rolling deploy (stop old → run new)
4. **Health Check** — Verifikasi endpoint `/api/health`

## 📄 Lisensi

Internal project — Lihat `PRD.md` untuk spesifikasi lengkap.
