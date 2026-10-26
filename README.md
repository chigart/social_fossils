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
1. LOW: AI code review for speed/vulnerabilities. Test JSONs for injection. Try to break it with AI.
2. HIGH: Fix timeline in insights tab.
3. MED: Fix parallel import heavy files.
4. LOW: Add Facebook, VK
5. LOW: Web App with encryption
6. MED: Order links suggestions by FullName length
7. LOW: Instagram group chats analytics
8. MED: Show file upload progress in UI
9. MED: Fix lagging search
