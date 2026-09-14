# Product Requirements Document (PRD)
# PDF to Markdown Converter (Monolith)

## 1. Project Overview & Objectives
* **Nama Proyek:** PDF to Markdown Converter (`pdf2md-app`)
* **Tujuan:** Aplikasi web mandiri (*self-hosted*) berarsitektur monolit berbasis Python untuk mengonversi file PDF menjadi dokumen Markdown (`.md`) dengan mempertahankan struktur heading, list, dan tabel secara optimal.
* **Target Deployment:** Container Docker tunggal yang berjalan di server AlmaLinux via automated pipeline **Jenkins**.

---

## 2. Tech Stack & Architecture
* **Arsitektur:** Monolit tunggal (Backend API + Frontend Serving dalam 1 container).
* **Backend Framework:** FastAPI (Python 3.11+).
* **PDF Conversion Engine:** `pymupdf4llm` (ringan, cepat, ekstraksi tabel & heading akurat tanpa kebutuhan GPU/model besar).
* **Frontend:** Single-page Web UI modern disajikan langsung oleh FastAPI (`StaticFiles`):
  * **Styling:** Tailwind CSS (via CDN).
  * **Markdown Parser (Client Preview):** `marked.js` (via CDN).
  * **Icons:** Lucide Icons / Heroicons (via SVG/CDN).
  * *Bebas dari Node.js/npm build pipeline untuk menjaga kesederhanaan monolit.*
* **Server / Runtime:** Uvicorn.
* **Container & CI/CD:** Dockerfile tunggal (`python:3.11-slim`), `docker-compose.yml`, dan `Jenkinsfile`.

---

## 3. Core Features & User Stories

### A. Fitur Aplikasi
1. **Drag & Drop Upload:**
   * Area dropzone interaktif dengan indikator visual saat file di-drag ke atas layar.
   * Validasi file sisi client dan server (hanya ekstensi `.pdf` dan MIME type `application/pdf`).
   * Tampilan metadata ringkas (nama file dan ukuran file).

2. **Mesin Konversi Cepat:**
   * Menggunakan endpoint `POST /api/convert`.
   * Penanganan file temporer yang aman (otomatis dibersihkan setelah proses selesai).
   * Error handling yang jelas jika file rusak atau terenkripsi password.

3. **Tampilan Hasil Interaktif (Dual View / Tabs):**
   * **Raw View:** Teks mentah Markdown dalam textarea/code-block dengan tombol *Copy to Clipboard*.
   * **Rendered Preview:** Tampilan visual hasil format Markdown (tabel, heading, list yang ter-render rapi).

4. **Ekspor & Download:**
   * Tombol satu-klik untuk mengunduh file `.md` dengan penamaan otomatis: `<nama_file_asli>.md`.

---

## 4. API Specification

### Endpoint 1: Healthcheck
* **Route:** `GET /api/health`
* **Method:** `GET`
* **Response (200 OK):**
  ```json
  {
    "status": "ok"
  }
  ```

### Endpoint 2: PDF Conversion
* **Route:** `POST /api/convert`
* **Method:** `POST`
* **Request:** `multipart/form-data`
  * Param: `file` (Binary PDF File)
* **Response Sukses (200 OK):**
  ```json
  {
    "success": true,
    "filename": "document.md",
    "markdown": "# Judul Dokumen\n\nIsi paragraf..."
  }
  ```
* **Response Gagal (400 / 500):**
  ```json
  {
    "detail": "Pesan error spesifik (misal: 'File bukan PDF' atau 'PDF terkunci password')"
  }
  ```

---

## 5. UI/UX Specifications
* **Layout:** Centered card layout minimalis bernuansa modern (Clean Dashboard style).
* **State Management:**
  1. *Idle State*: Area upload siap menerima file.
  2. *Uploading/Processing State*: Indikator spinner/loading dengan teks *"Mengonversi dokumen..."*, tombol dinonaktifkan sementara.
  3. *Result State*: Panel hasil muncul dengan toggle tab atau split view (Raw Markdown vs Preview), tombol Download dan Copy aktif.
  4. *Error State*: Alert visual (merah/oranye) menampilkan pesan kesalahan yang ramah pengguna.

---

## 6. Deployment & CI/CD Specification (AlmaLinux + Jenkins)

### A. Docker Configuration
* **Port Mapping:** `3020:8000` (Port host `3020` diarahkan ke port `8000` di dalam container).
* **Restart Policy:** `always`.
* **Container Name:** `pdf2md-app`.
* **Base Image:** `python:3.11-slim`.

### B. Docker Compose (`docker-compose.yml`)
```yaml
version: '3.8'

services:
  pdf2md:
    build: .
    container_name: pdf2md-app
    restart: always
    ports:
      - "3020:8000"
```

### C. Jenkinsfile Pipeline Stages
Pipeline Declarative untuk build dan rolling deploy otomatis di server AlmaLinux:
```groovy
pipeline {
    agent any

    environment {
        CONTAINER_NAME = 'pdf2md-app'
        IMAGE_NAME     = 'pdf2md-app:latest'
        HOST_PORT      = '3020'
        CONTAINER_PORT = '8000'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME} .'
            }
        }

        stage('Deploy Container') {
            steps {
                sh '''
                    # Hentikan dan hapus container lama jika ada
                    if [ $(docker ps -a -q -f name=^/${CONTAINER_NAME}$) ]; then
                        docker stop ${CONTAINER_NAME} || true
                        docker rm ${CONTAINER_NAME} || true
                    fi

                    # Jalankan container baru
                    docker run -d \
                      --name ${CONTAINER_NAME} \
                      --restart always \
                      -p ${HOST_PORT}:${CONTAINER_PORT} \
                      ${IMAGE_NAME}
                '''
            }
        }

        stage('Health Check') {
            steps {
                sleep 5
                sh 'curl -f http://localhost:${HOST_PORT}/api/health || exit 1'
            }
        }
    }

    post {
        always {
            sh 'docker image prune -f'
        }
    }
}
```

---

## 7. Project Structure Plan
```text
pdf2md/
├── app/
│   ├── __init__.py
│   ├── main.py             # Entrypoint FastAPI & static files mounting
│   ├── converter.py        # Logika ekstraksi PDF ke Markdown (pymupdf4llm)
│   └── static/
│       └── index.html      # UI interaktif tunggal (Tailwind CDN, marked.js, vanilla JS)
├── Dockerfile              # Single-stage Python 3.11-slim
├── docker-compose.yml      # Port 3020:8000 & restart: always
├── Jenkinsfile             # Declarative CI/CD pipeline
├── requirements.txt        # fastapi, uvicorn, pymupdf4llm, python-multipart
├── PRD.md                  # Dokumen referensi spesifikasi ini
└── README.md               # Dokumentasi instalasi dan penggunaan
```

---

## 8. Implementation Steps for Antigravity AI
1. Inisialisasi folder proyek sesuai struktur pada bagian 7.
2. Buat `requirements.txt` dengan dependency FastAPI, Uvicorn, pymupdf4llm, dan python-multipart.
3. Buat modul konversi `app/converter.py` yang membungkus fungsi `pymupdf4llm.to_markdown()`.
4. Buat aplikasi utama `app/main.py` dengan endpoint `/api/health`, `/api/convert`, dan mount folder `app/static/`.
5. Buat frontend modern responsif pada `app/static/index.html` lengkap dengan fitur Drag & Drop, Copy to Clipboard, Split/Tab View, dan Download `.md`.
6. Buat `Dockerfile` dengan image dasar `python:3.11-slim`.
7. Buat `docker-compose.yml` dengan konfigurasi port `3020:8000` dan restart `always`.
8. Buat `Jenkinsfile` untuk deployment otomatis.
9. Buat `README.md` sebagai petunjuk operasional.
