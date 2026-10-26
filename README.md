# Social Fossils

### Run Project
- docker compose up --build -d

### Finish Work
- docker compose down

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

## TODO
- LOW: AI code review for speed/vulnerabilities. Test JSONs for injection. Try to break it with AI.
- LOW: Add Facebook, VK
- LOW: Web App with encryption
- MED: Order links suggestions by FullName length
- LOW: Instagram group chats analytics
- LOW: Show file upload progress in UI
- MED: Fix lagging search - make it universal dropdown link in link contacts with platform filter
- MED: chats, contacts delete service_message columns
