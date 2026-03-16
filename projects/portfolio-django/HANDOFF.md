# portfolio-django — Project Handoff
schema_version: vaultit-v1.0

## What It Is
Django 5 portfolio site. Python 3.13. Strict frontend-only variant architecture. Personal portfolio for Steven Wazlavek / Originami.com.

## Where It Is
- Local: C:\Users\Steven\Portfolio
- Environment: .venv, Python 3.13, Django 5

## Current Status
State machine: IDLE. No active task.

## Daily Restart Sequence
cd C:\Users\Steven\Portfolio
.venv\Scripts\Activate.ps1
python manage.py check
python manage.py test
python manage.py runserver
Verify: http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/

## Gates
- python manage.py check
- python manage.py test
- Smoke test: localhost:8000 loads, /admin/ loads
