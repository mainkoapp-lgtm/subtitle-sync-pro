# SubFast Extractor Portable Build Script (PowerShell)

$ErrorActionPreference = "Stop"

$TAURI_DIR = "d:\Project Temporary\subtitle\subtitle_development\tools\tauri_extractor"
$FFMPEG_SRC = "d:\Project Temporary\subtitle\subtitle_development\tools\subtitle_extractor\ffmpeg"
$DIST_PORTABLE = "$TAURI_DIR\dist_portable"

Write-Host ">>> [1/5] 빌드 폴더 초기화 중..." -ForegroundColor Cyan
if (Test-Path $DIST_PORTABLE) {
    Remove-Item -Path $DIST_PORTABLE -Recurse -Force
}
New-Item -ItemType Directory -Path $DIST_PORTABLE | Out-Null

Write-Host ">>> [2/5] Tauri 앱 빌드 중 (Release 모드)..." -ForegroundColor Cyan
Set-Location $TAURI_DIR
npm run tauri build

Write-Host ">>> [3/5] 실행 파일 및 리소스 수집 중..." -ForegroundColor Cyan
$EXE_SRC = "$TAURI_DIR\src-tauri\target\release\toolstauri_extractor.exe"
if (Test-Path $EXE_SRC) {
    Copy-Item -Path $EXE_SRC -Destination "$DIST_PORTABLE\SubFast Extractor.exe"
} else {
    Write-Error "실행 파일을 찾을 수 없습니다: $EXE_SRC"
}

# Tesseract 리소스 복사 (Tauri 빌드 결과물에서 가져오거나 원본에서 복사)
# Tauri v2 빌드 시 resources는 EXE 내부에 포함되거나 별도 폴더로 나옴.
# 여기서는 원본 resources/tesseract 폴더를 명시적으로 복사하여 포터블 구조 유지.
$TESS_SRC = "$TAURI_DIR\src-tauri\resources\tesseract"
if (Test-Path $TESS_SRC) {
    $TESS_DEST = "$DIST_PORTABLE\resources\tesseract"
    New-Item -ItemType Directory -Path "$DIST_PORTABLE\resources" -Force | Out-Null
    Copy-Item -Path $TESS_SRC -Destination $TESS_DEST -Recurse
}

Write-Host ">>> [4/5] FFmpeg 바이너리 복사 중..." -ForegroundColor Cyan
if (Test-Path $FFMPEG_SRC) {
    $FFMPEG_DEST = "$DIST_PORTABLE\ffmpeg"
    New-Item -ItemType Directory -Path $FFMPEG_DEST -Force | Out-Null
    Copy-Item -Path "$FFMPEG_SRC\bin" -Destination "$FFMPEG_DEST\bin" -Recurse
}

Write-Host ">>> [5/5] 불필요한 파일 정리 및 최적화..." -ForegroundColor Cyan
# 빌드 중간 파일 삭제 (Release 모드라 이미 최소화되어 있음)
# .pdb 파일 등이 생성되었다면 삭제
Get-ChildItem -Path $DIST_PORTABLE -Filter "*.pdb" -Recurse | Remove-Item -Force

Write-Host "==========================================" -ForegroundColor Green
Write-Host " 포터블 빌드가 성공적으로 완료되었습니다!" -ForegroundColor Green
Write-Host " 경로: $DIST_PORTABLE" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
