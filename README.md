# Spell Practice Backend
Run `main.py` with uvicorn to start the API.

fly.io deployment steps:
1. install fly.io if needed: iwr https://fly.io/install.ps1 -useb | iex
2. flyctl auth signup   # or: fly auth login if haven't login
3. flyctl deploy --local-only #if docker is installed and running. 