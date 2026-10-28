@echo off
chcp 65001 > nul
echo ========================================================
echo   แปลงวิดีโอ MP4 สำหรับ iPad mini 1 / อุปกรณ์รุ่นเก่า
echo   (H.264 High 4.1 / yuv420p / 30fps / AAC / FastStart)
echo ========================================================

set FFMPEG="ffmpeg.exe"
if not exist %FFMPEG% (
    set FFMPEG="%~dp0ffmpeg.exe"
)

if "%~1"=="" (
    echo.
    echo กรุณาลากไฟล์วิดีโอ .mp4 มาวางบนไฟล์นี้ (Drag and drop)
    echo หรือเรียกใช้: convert_for_ipad.bat "video.mp4"
    echo.
    pause
    exit /b
)

:loop
if "%~1"=="" goto end
echo.
echo กำลังประมวลผล: "%~nx1"
%FFMPEG% -y -i "%~1" -c:v libx264 -profile:v high -level 4.1 -pix_fmt yuv420p -r 30 -vf "scale='min(1920,iw)':-2" -c:a aac -b:a 160k -ar 44100 -movflags +faststart "%~dpn1_ipad.mp4"
if %errorlevel% equ 0 (
    echo [สำเร็จ] สร้างไฟล์สำหรับ iPad เรียบร้อย: "%~dpn1_ipad.mp4"
) else (
    echo [ล้มเหลว] เกิดข้อผิดพลาดในการแปลงไฟล์: "%~nx1"
)
shift
goto loop

:end
echo.
echo ========================================================
echo   แปลงไฟล์เสร็จสิ้นเรียบร้อยแล้ว!
echo ========================================================
pause

