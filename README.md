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

## Media and static files

- During development (DEBUG=True) Django serves media files at `http://127.0.0.1:8000/media/`.
- Configure `MEDIA_ROOT` and `MEDIA_URL` in `backend/voting_system/settings.py`.

## Notable backend behaviors & developer notes

- Incident assignment (`POST /api/incidents/assign/`):
  - The endpoint is transactional (uses `select_for_update`) to avoid race conditions during assignment.
  - If a non-admin attempts to claim an incident already assigned to someone else, the API returns 403 and includes `assigned_to_name` and `assigned_to_id` in the JSON response so clients can show a friendly message.
  - Assigning an incident to the same official again is idempotent and returns success.

- Incident creation accepts multipart/form-data and the serializer reads `request.FILES` when needed.

- User roles are expressed via related profile models on the `User` model (e.g., `user.voter`, `user.inecofficial`, `user.admin`). Check `authentication/models.py` for the exact model shapes.

## Troubleshooting

- If migrations fail with locked DB errors, make sure no other manage.py process is running.
- If media files do not appear, verify `DEBUG=True` and that `MEDIA_ROOT` points to the correct folder.

## Next improvements (backend)

- Add unit tests covering assignment permission scenarios and transaction race conditions.
- Add `assigned_at` to the incident model and serialization for better audit trails.
- Add monitoring/alerts around long-running tasks and DB locks.
