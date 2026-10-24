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
1. AI code review for speed/vulnerabilities. Test JSONs for injection. Try to break it with AI.
2. Fix timeline in insights tab.
3. Fix parallel import heavy files.
4. Add Facebook, VK
5. Web App with encryption
6. Hide Instagram Unidentified contact and Link status column in Contacts
