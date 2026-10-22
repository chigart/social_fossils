# MVP for Social Fossils

### Development
- cd frontend
- nvm install
- npm install

- cd ..
- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- Python: Select Interpreter (IDE)

- docker compose up --build -d
- docker compose exec backend alembic upgrade head

### Test
- Backend: `cd backend && pytest`
- Frontend: `cd frontend && npm test`

### Run Project
- docker compose up

### Finish Work
- docker compose down 

## TODO
1. Chats analytics
2. AI code review for speed/vulnerabilities. Test JSONs for injection. Try to break it with AI.
3. Split all ingestion into DAG tasks.
4. Interactive contacts merge

## BUGS
1. Image/sticker doesn't count at all in text volume
