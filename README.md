# MVP for Social Fossils

### Development
- cd frontend
- nvm install
- npm install

- cd ..
- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- Python: Select Interpreter

- docker compose up --build -d
- docker compose exec backend alembic upgrade head

### Test
- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test`

### Run Project
- docker compose up
- docker compose exec backend python -m app.importer /app/data/FILENAME.json

### Full Reset
- docker compose down -v

## PLAN
1. Development Docker
2. Prod Local Docker
3. Multiple social media
4. Interactive contacts merge
5. Encrypted Web App (Mock JSON testing)

## TODO
1. Mobile adaptive
2. Design
3. Chats analytics
4. AI code review for speed/vulnerabilities. Test JSONs for injection. Try to break it with AI.

## BUGS
1. Image/sticker doesn't count at all in text volume
