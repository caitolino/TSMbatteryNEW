# Nota's van wak moet onthouden
1:
cd c:\Users\CaitlinVanDenBlock\Documents\TSMgithub\fastAPIbackend

curl http://127.0.0.1:8000/health

Test-Path .venv
 
2:
 .\.venv\Scripts\Activate.ps1
 
 python main.py
 
3: 
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

.\.venv\Scripts\Activate.ps1; python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000