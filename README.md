# Homelab Monitor

LAN-only, read-only observability command center untuk homelab. Project ini memantau hierarchy Proxmox → VM/LXC → Docker/runtime → service/application, scheduled automation, artifact/report, dan delivery evidence.

## Prinsip

- **Read-only terhadap workload:** collector tidak melakukan restart, lifecycle action, arbitrary command, atau remediation otomatis.
- **Evidence-first:** status berasal dari observasi live, bukan asumsi dari nama Cron.
- **Delivery terpisah:** Cron selesai, report generated, GitHub sync, dan Discord delivery adalah state yang berbeda.
- **Secret-safe:** prompt mentah, command sensitif, token, password, webhook, private key, dan credential-bearing URL tidak dikirim ke monitor.
- **LAN-only:** dashboard dan API ditujukan untuk jaringan internal.

## Fitur

- Hierarchical resource inventory Proxmox, VM/LXC, Docker, service, dan aplikasi.
- Health/status overview dengan normalized logs dan incidents.
- Cron explorer dengan penjelasan bahasa manusia:
  - Cron ini mengerjakan apa;
  - siapa yang mengelola;
  - scope/target;
  - jadwal;
  - dampak jika gagal;
  - delivery target;
  - run/status history.
- **Artifacts & Delivery**:
  - safe report preview berbentuk Markdown/JSON terbatas;
  - source Cron dan profile;
  - artifact hash, ukuran, dan waktu generate;
  - GitHub path/commit verification;
  - Discord attempt/receipt evidence secara terpisah.
- Versioned JSON API di bawah `/api/v1`.

## Runtime topology

Production runtime berjalan di LXC `112`:

```text
Dashboard/Nginx : <monitoring-host>:18080
API             : 127.0.0.1:18000
Database        : PostgreSQL local-only via Unix socket
```

Collector/relay menggunakan akses read-only dan mengirim normalized metadata ke API. Report preview dibatasi ukuran dan disanitasi sebelum transport.

## Struktur repository

```text
backend/    FastAPI domain, collectors, persistence, migrations, tests
frontend/   React + TypeScript + Vite dashboard
docs/       evidence plans dan design notes
```

Runtime data, database dump, virtualenv, `node_modules`, `dist`, cache, credential, dan secret tidak termasuk repository.

## Menjalankan backend

Backend membutuhkan Python environment dan PostgreSQL sesuai konfigurasi deployment. Contoh lokal:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --host 127.0.0.1 --port 18000
```

Health endpoints:

```text
GET /api/v1/health
GET /api/v1/readiness
GET /api/v1/resources
GET /api/v1/automation-outputs
```

## Menjalankan frontend

```bash
cd frontend
npm ci
npm run dev
npm run build
```

Frontend menggunakan API contract typed di `src/api.ts` dan tidak mengakses host workload secara langsung.

## Verification

Backend:

```bash
cd backend
pytest
```

Frontend:

```bash
cd frontend
npm run build
```

Production verification minimal:

```bash
curl -fsS http://127.0.0.1:18000/api/v1/health
curl -fsS http://127.0.0.1:18000/api/v1/readiness
curl -fsS 'http://127.0.0.1:18000/api/v1/automation-outputs?limit=10'
```

## Evidence contract

Artifact metadata boleh memuat nama, kategori, tipe, ukuran, SHA-256, generated time, source Cron, provenance, safe GitHub label/path/commit, safe Discord target, dan normalized reason.

Artifact tidak boleh memuat report payload mentah yang belum disanitasi. Jika receipt GitHub atau Discord tidak tersedia, UI wajib menggunakan `Unverified`, `Attempt recorded`, `Not observed`, atau `Unknown`.

## Release/deployment

Deployment production dilakukan secara terkontrol ke LXC `112`, kemudian diverifikasi melalui:

1. backend compile/build;
2. service health/readiness;
3. API artifact contract;
4. frontend production build;
5. browser smoke test;
6. secret-marker scan;
7. relay completion dan error count.

Jangan melakukan merge/rebase otomatis pada checkout yang memiliki uncommitted work tanpa action plan dan rollback path.
