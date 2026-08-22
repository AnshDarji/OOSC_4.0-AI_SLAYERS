@echo off
echo Starting NYAAY AI Backend...
cd BACKEND
start cmd /k "venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
cd ..

echo Starting NYAAY AI Frontend...
cd FRONTEND
start cmd /k "npm run dev"
cd ..

echo App launched in separate windows!
