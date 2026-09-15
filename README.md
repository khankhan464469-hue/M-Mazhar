# Event Portal

Event Portal is a FastAPI and Supabase project for managing event accounts and event records.

## Features

- Customer signup
- Admin signup with a private admin code
- Login with Supabase Auth
- Forgot password email flow
- Event create, read, update, and delete API
- Separate customer and admin profile records in Supabase
- Simple static frontend served by FastAPI

## Project Structure

```text
backend/
  main.py
  requirements.txt
  supabase_schema.sql
frontend/
  index.html
  styles.css
  app.js
```

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Copy `backend/.env.example` to `backend/.env` and add your Supabase values.
4. Run `backend/supabase_schema.sql` in the Supabase SQL Editor.
5. Start the API:

```bash
cd backend
uvicorn main:app --reload
```

6. Open the website:

```text
http://127.0.0.1:8000/
```

## Security Notes

Do not commit `.env`. It contains private Supabase credentials and the admin signup code.
