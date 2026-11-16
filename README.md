# Social Fossils

Python, FastAPI, SQLAlchemy 2, PostgreSQL, Alembic, React, TypeScript, Vite, Airflow.

### Run Project
- docker compose up --build -d

### Optional: Local Ollama
- Install Ollama on the host and pull a model, for example `ollama pull qwen3:8b`.
- The backend container must reach Ollama through the Docker network gateway. On Linux, get the gateway with `docker network inspect social_fossils_default --format '{{(index .IPAM.Config 0).Gateway}}'`.
- Run `sudo systemctl edit ollama`; add `[Service]` and `Environment="OLLAMA_HOST=<gateway>:11434"` using the gateway above.
- Set `OLLAMA_BASE_URL=http://<gateway>:11434` in `.env`. Keep Ollama restricted to trusted local traffic.
- Apply the setting with `sudo systemctl daemon-reload && sudo systemctl restart ollama`, then recreate the backend with `docker compose up -d --force-recreate backend`.

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
