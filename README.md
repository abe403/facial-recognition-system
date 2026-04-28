# FaceGym: Biometric Access Control System

FaceGym is a production-grade facial recognition platform designed for gym membership management. It combines a high-performance FastAPI backend with a modern Angular dashboard and a standalone Kiosk interface for automated entry verification.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Angular](https://img.shields.io/badge/Angular-DD0031?style=flat&logo=angular&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat&logo=opencv&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

---

## Key Features

### Administrative Security
- **JWT Authentication**: Stateless session management with secure token exchange.
- **Salted Hashing**: Passwords stored using bcrypt (cost factor 10) for maximum security.
- **Protected API**: All administrative routes are locked behind strict role-based dependencies.

### Member Management
- **Smart Registration**: Automated membership ID generation (e.g., GYM0001).
- **Face Enrollment**: Capture member biometrics directly from the browser using standard webcams.
- **Robust Detection**: Intelligent face detection that prioritizes the closest user and filters out background noise.

### High-Tech Kiosk
- **Automated Verification**: Real-time biometric scanning with the LBPH (Local Binary Patterns Histograms) algorithm.
- **Instant Feedback**: Visual overlays for "Access Granted," "Expired," or "Denied" states.
- **Publicly Accessible**: The Kiosk is designed to run on entrance hardware without requiring administrative login.

---

## Technical Stack

- **Backend**: Python 3.11, FastAPI, Uvicorn, SQLAlchemy (SQLite).
- **Computer Vision**: OpenCV (Haar Cascades + LBPH Recognizer).
- **Frontend**: Angular 17+, TypeScript, RxJS, Vanilla CSS (Custom Design System).
- **Infrastructure**: Docker, Docker Compose, Nginx.
- **Testing**: Playwright (E2E), Pytest (API).

---

## Quick Start

Ensure you have Docker and Docker Compose installed.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/abe403/facial-recognition-system.git
   cd facial-recognition-system
   ```

2. **Launch with Docker Compose**:
   ```bash
   docker compose up -d --build
   ```

3. **Access the Application**:
   - **Admin Dashboard**: http://localhost:3001/login
   - **Kiosk Interface**: http://localhost:3001/kiosk
   - **API Documentation**: http://localhost:3001/api/docs

**Default Credentials**:
- **Username**: admin
- **Password**: admin123

---

## Testing

The project includes a comprehensive E2E test suite using Playwright.

```bash
# Run all tests
npx playwright test
```

---

## Architecture

```text
.
├── backend/            # FastAPI Application & ML Logic
│   ├── database.py     # SQLite/SQLAlchemy schema
│   ├── security.py     # JWT & Bcrypt implementation
│   ├── recognizer.py   # OpenCV face detection & matching
│   └── main.py         # API Route definitions
├── frontend/           # Angular Application
│   ├── src/app/pages/  # Kiosk, Dashboard, Login components
│   └── src/app/core/   # Auth Guards & Interceptors
└── tests/              # Playwright E2E Test Suite
```

---

## License
Distributed under the MIT License. See LICENSE for more information.
