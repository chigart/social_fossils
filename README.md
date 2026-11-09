# Social Fossils

Python, FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, React, TypeScript, Vite, Airflow.

### Run Project
- docker compose up --build -d

### Overview 
- import messaging data from Telegram and Instagram and unite
- analyze locally, no private data leaves your pc
- get the whole picture of all your social connections, important friendships, people characters













### Development
- cd frontend
- nvm install
- npm install

- cd ..
- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt

- docker compose up --build -d
- docker compose exec backend alembic upgrade head

### Test
- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test`
