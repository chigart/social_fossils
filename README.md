# MVP for Social Fossils

### For development
- cd frontend
- nvm install

- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- Python: Select Interpreter

- docker compose up --build -d
- docker compose exec backend alembic upgrade head

### Run Project
- docker compose up
- docker compose exec backend python -m app.importer /app/data/FILENAME.json

## PLAN
1. Development Docker
2. Prod Local Docker
3. Encrypted Web App
