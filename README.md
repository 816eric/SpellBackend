# Spell Practice Backend
Run `main.py` with uvicorn to start the API.

Option1 (Better):
fly.io deployment steps:
1. install fly.io if needed: iwr https://fly.io/install.ps1 -useb | iex
2. flyctl auth signup   # or: fly auth login if haven't login
3. flyctl deploy --local-only #if docker is installed and running. 


option2:
render.com
simply connect to the github. Automatically deployment.
Cons: it will stop clean the database for free version.