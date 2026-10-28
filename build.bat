@echo off
chcp 65001 > nul
echo ========================================================
echo   Building YouTube Downloader Portable (Single .exe)
echo ========================================================

echo 1. ตรวจสอบการติดตั้ง Library ที่จำเป็น...
pip install --upgrade yt-dlp pyinstaller

echo.
echo 2. ตรวจสอบไฟล์ ffmpeg.exe...
if not exist "ffmpeg.exe" (
    echo ไม่พบ ffmpeg.exe กำลังคัดลอก/ดาวน์โหลด...
    python -c "import shutil, imageio_ffmpeg; shutil.copy(imageio_ffmpeg.get_ffmpeg_exe(), 'ffmpeg.exe')" 2>nul
)
if not exist "ffmpeg.exe" (
    echo กำลังดาวน์โหลด ffmpeg จาก GitHub...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip' -OutFile 'ffmpeg.zip'"
    powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'ffmpeg_temp' -Force"
    powershell -Command "Get-ChildItem -Path 'ffmpeg_temp' -Recurse -Filter 'ffmpeg.exe' | Copy-Item -Destination '.\ffmpeg.exe'"
    powershell -Command "Remove-Item -Recurse -Force 'ffmpeg_temp', 'ffmpeg.zip'"
)

echo.
echo 3. เริ่มคอมไพล์เป็น Single Portable EXE...
pyinstaller --noconfirm --onefile --windowed --add-binary "ffmpeg.exe;." --name "YouTube_Downloader_Portable" app.py

echo.
echo ========================================================
echo   คอมไพล์เสร็จเรียบร้อย!
echo   ไฟล์เปิดใช้งานอยู่ที่: dist\YouTube_Downloader_Portable.exe
echo ========================================================
pause

