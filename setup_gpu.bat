@echo off
echo ============================================
echo LinguaNotebook GPU Setup (Intel Arc XPU)
echo Per HPD-PARSING-GUIDE.md Section 2.2 Path B
echo ============================================

echo.
echo Step 1: Install PyTorch for Intel XPU...
C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu

echo.
echo Step 2: Install Python dependencies...
C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe -m pip install "transformers>=4.46,<5" accelerate einops timm sentencepiece safetensors
C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe -m pip install celery redis sqlalchemy pydantic pydantic-settings pymupdf pillow
C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe -m pip install python-jose passlib "bcrypt==4.0.1" structlog boto3 httpx asyncpg psycopg2-binary

echo.
echo ============================================
echo Setup complete! Run the GPU worker with:
echo   C:\Users\ASUS\AppData\Local\Programs\Python\Python312\python.exe backend\run_worker_gpu.py
echo ============================================
pause
