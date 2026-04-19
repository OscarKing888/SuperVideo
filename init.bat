python -m venv .venv
.venv\Scripts\activate.bat
python.exe -m pip install --upgrade pip
pipinst -r requirements_cuda.txt
python .\scripts\download_models.py