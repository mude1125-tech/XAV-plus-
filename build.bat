@echo off
echo ============================================
echo   XAV 정산 프로그램 EXE 빌드 스크립트
echo ============================================
echo.

echo [1/2] 필요한 패키지 설치 중...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 패키지 설치 실패! Python과 pip이 설치되어 있는지 확인해주세요.
    pause
    exit /b 1
)

echo.
echo [2/2] EXE 파일 빌드 중...
pyinstaller --onefile --windowed --name "XAV_정산프로그램" main.py
if %errorlevel% neq 0 (
    echo 빌드 실패!
    pause
    exit /b 1
)

echo.
echo ============================================
echo   빌드 완료!
echo   dist 폴더에서 "XAV_정산프로그램.exe"를 확인하세요.
echo ============================================
pause
