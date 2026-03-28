# QualityGate - Quality Control & Assurance System

A comprehensive, production-grade quality control system for manufacturing and production environments. QualityGate provides end-to-end quality management including inspection checklists, defect tracking, corrective and preventive actions (CAPA), statistical process control (SPC), audit management, and compliance reporting.

## Features

- **Inspection Management** -- Create and manage inspection checklists, record inspection results, assign inspectors, and track pass/fail rates across production lines.
- **Defect Tracking** -- Log defects with images, categorize by severity, perform root cause analysis (5-Why, Fishbone), and monitor defect trends over time.
- **CAPA (Corrective & Preventive Actions)** -- Full CAPA workflow with task assignments, due date tracking, effectiveness verification, and escalation via Celery-based notifications.
- **Statistical Process Control (SPC)** -- Real-time SPC charts (X-bar, R-chart, p-chart, c-chart) with control limit calculations, capability indices (Cp, Cpk), and out-of-control alerts.
- **Audit Management** -- Schedule and conduct internal/external quality audits, track findings, assign corrective actions, and manage audit cycles.
- **Compliance Reporting** -- Map compliance requirements to ISO 9001, ISO 13485, AS9100, IATF 16949, and other standards. Generate compliance status reports.
- **Quality Metrics Dashboard** -- Real-time dashboards showing first-pass yield, defect density, DPMO, cost of poor quality, and other key quality KPIs.

## Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Backend     | Django 5.x, Django REST Framework   |
| Frontend    | React 18, Redux Toolkit, Recharts   |
| Database    | PostgreSQL 16                       |
| Cache/Queue | Redis 7                             |
| Task Queue  | Celery 5.x                          |
| Web Server  | Nginx                               |
| Containers  | Docker, Docker Compose              |

## Architecture

```
                    +-------------------+
                    |      Nginx        |
                    | (Reverse Proxy)   |
                    +---------+---------+
                              |
                +-------------+-------------+
                |                           |
        +-------v-------+         +--------v--------+
        |   React SPA   |         |   Django API    |
        |  (port 3000)  |         |  (port 8000)    |
        +---------------+         +--------+--------+
                                           |
                              +------------+------------+
                              |            |            |
                       +------v--+  +------v--+  +-----v------+
                       |PostgreSQL|  |  Redis  |  |   Celery   |
                       | (5432)  |  | (6379)  |  |  (Worker)  |
                       +---------+  +---------+  +------------+
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/qualitygate.git
   cd qualitygate
   ```

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your configuration (database credentials, secret key, etc.).

4. Build and start all services:
   ```bash
   docker-compose up --build -d
   ```

5. Run database migrations:
   ```bash
   docker-compose exec backend python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

7. Access the application:
   - Frontend: http://localhost
   - API: http://localhost/api/
   - Admin: http://localhost/api/admin/

### Development (without Docker)

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

#### Frontend

```bash
cd frontend
npm install
npm start
```

## API Documentation

The API follows REST conventions. All endpoints are prefixed with `/api/v1/`.

| Endpoint                    | Methods                | Description                    |
|-----------------------------|------------------------|--------------------------------|
| `/api/v1/auth/login/`      | POST                   | Obtain JWT token pair          |
| `/api/v1/auth/refresh/`    | POST                   | Refresh JWT access token       |
| `/api/v1/accounts/users/`  | GET, POST              | List / create users            |
| `/api/v1/inspections/`     | GET, POST              | Inspection management          |
| `/api/v1/checklists/`      | GET, POST              | Inspection checklists          |
| `/api/v1/defects/`         | GET, POST              | Defect tracking                |
| `/api/v1/capa/corrective/` | GET, POST              | Corrective actions             |
| `/api/v1/capa/preventive/` | GET, POST              | Preventive actions             |
| `/api/v1/audits/`          | GET, POST              | Quality audits                 |
| `/api/v1/metrics/`         | GET, POST              | Quality metrics                |
| `/api/v1/metrics/spc/`     | GET                    | SPC chart data                 |
| `/api/v1/compliance/`      | GET, POST              | Compliance management          |

## Environment Variables

See `.env.example` for a complete list of configurable environment variables.

## Testing

```bash
# Backend tests
docker-compose exec backend python manage.py test

# Frontend tests
docker-compose exec frontend npm test
```

## License

This project is proprietary software. All rights reserved.
