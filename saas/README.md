# vaultit SaaS

Django 5 web application for vaultit.ai — dashboard, hosted API, GitHub OAuth, Stripe billing.

## Local Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Copy env file and configure:
   ```
   cp .env.example .env
   ```

3. Run migrations:
   ```
   python manage.py migrate --settings=vaultit_saas.settings.local
   ```

4. Create a superuser:
   ```
   python manage.py createsuperuser --settings=vaultit_saas.settings.local
   ```

5. Run the dev server:
   ```
   python manage.py runserver --settings=vaultit_saas.settings.local
   ```

## Tests

```
python manage.py test --settings=vaultit_saas.settings.local
```
