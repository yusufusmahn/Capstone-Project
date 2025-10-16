# Backend - Digital Voting System (Django)

This document contains focused developer instructions for the backend portion of the Digital Voting System.

## Location

All backend code is in the `backend/` folder. The Django project `manage.py` file is inside this folder.

## Quick Start (Windows PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser  # optional
python manage.py runserver 127.0.0.1:8000
```

## Important management commands

- Run system checks:

```powershell
python manage.py check
```

- Trigger election status checks (used by the frontend admin "Check Status" button):

```powershell
python manage.py check_election_status
```

- Run tests:

```powershell
python manage.py test
```

```markdown
# Backend — Digital Voting System (Django)

Backend code lives in `backend/`. Run Django management commands from that folder (where `manage.py` resides).

## Quick start (Windows PowerShell)

```powershell
cd backend

# (first-run) create + activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py makemigrations
python manage.py migrate

# (Optional) create a superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver 127.0.0.1:8000
```

## Useful management commands

- Run checks:

```powershell
python manage.py check
```

- Trigger election status checks (used by the admin UI):

```powershell
python manage.py check_election_status
```

- Run tests:

```powershell
python manage.py test
```

## Media and static files

- During development (`DEBUG=True`) Django serves media at `http://127.0.0.1:8000/media/`.
- Configure `MEDIA_ROOT` and `MEDIA_URL` in `backend/voting_system/settings.py`.

## Notable backend behaviors

- Incident assignment (`POST /api/incidents/assign/`):
  - The endpoint uses a DB transaction and `select_for_update` to avoid race conditions.
  - If a non-admin tries to claim an incident already assigned, the API returns `403` and may include `assigned_to_name` and `assigned_to_id` for a friendly UI message.
  - Re-assigning an incident to the same official is idempotent and returns success.

- Incident statistics: `GET /api/incidents/stats/` returns aggregated incident counts for use in admin reports (admin/INEC-only access).

- Voting statistics: `GET /api/voting/stats/` — voting totals and related metrics.

- File uploads: endpoints that accept files (e.g., incident creation) expect `multipart/form-data`; serializers read `request.FILES`.

## Model / role notes

- The `User` model is extended with related profile models to represent roles: `user.voter`, `user.inecofficial`, `user.admin`. See `backend/authentication/models.py` for details.

## Troubleshooting

- If migrations fail with DB lock errors, ensure no other Django processes are running.
- If media files do not appear, confirm `DEBUG=True` and that `MEDIA_ROOT` is correct in settings.

## Next improvements (suggestions)

- Add unit tests for assignment permission and transaction behavior.
- Add an `assigned_at` timestamp to `IncidentReport` and surface it in the API and UI.
- Provide a single admin analytics endpoint that aggregates election/voter/incident stats and returns one payload for the frontend.

```
