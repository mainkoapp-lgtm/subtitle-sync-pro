import json
import os
import sys
import threading
import requests
from typing import Dict, Any, Optional

# 애플리케이션 정보
APP_VERSION = "0.1"
# Firebase Hosting 기반 원격 설정 URL (subfast-manager 프로젝트)
CONFIG_URL = "https://subfast-manager.web.app/latest_version.json"

# 다국어 사전
TRANSLATIONS = {
    'ko': {
        'title': "SubFast Extractor - 초고속 자막 추출기",
        'header_title': "🎬 SubFast Extractor",
        'status_ffmpeg_portable': "✅ FFmpeg (포터블 동봉)",
        'status_ffmpeg_system': "✅ FFmpeg (시스템 설치)",
        'status_ffmpeg_none': "❌ FFmpeg 없음 - ffmpeg 폴더에 넣어주세요",
        'btn_locate_ffmpeg': "FFmpeg 경로 변경",
        'group_file_select': "📂 영상 파일 선택",
        'btn_select_file': "📄 파일 선택",
        'btn_analyze': "🔍 분석",
        'group_track_list': "📋 자막 트랙 목록",
        'btn_select_all': "전체 선택",
        'btn_deselect_all': "전체 해제",
        'btn_select_text': "텍스트만 선택",
        'label_track_count': "총 {count}개 트랙",
        'group_preview': "👁️ 미리보기",
        'group_log': "📝 작업 로그",
        'btn_open_log': "로그 폴더 열기",
        'label_format': "출력 형식:",
        'label_save_path': "   저장 위치:",
        'radio_same_folder': "원본 폴더",
        'radio_custom_folder': "폴더 지정",
        'btn_extract': "🚀 선택한 자막 추출",
        'btn_stop': "⏹ 추출 중단",
        'btn_waiting': "⌛ 중단 대기 중",
        'msg_select_file_first': "먼저 영상 파일을 분석하세요.",
        'msg_ffmpeg_missing': "FFmpeg가 설치되어 있지 않습니다.",
        'msg_select_track': "추출할 자막 트랙을 선택하세요.",
        'msg_extract_start': "📤 {count}개 트랙 추출 시작...",
        'msg_extract_done': "🎉 추출 완료! ({success}/{total} 성공)",
        'msg_extract_cancelled': "⛔ 사용자에 의해 추출이 중단되었습니다.",
        'msg_error_occurred': "❌ 추출 중 오류 발생: {error}",
        'notice_title': "📢 공지사항",
        'update_required': "⚠️ 업데이트 필수",
        'update_msg': "현재 버전({current})은 더 이상 지원되지 않습니다.\n최신 버전({latest})으로 업데이트 후 사용해주세요.",
        'btn_download': "최신 버전 다운로드",
    },
    'en': {
        'title': "SubFast Extractor - High Speed Subtitle Extractor",
        'header_title': "🎬 SubFast Extractor",
        'status_ffmpeg_portable': "✅ FFmpeg (Portable)",
        'status_ffmpeg_system': "✅ FFmpeg (System Installed)",
        'status_ffmpeg_none': "❌ FFmpeg Missing - Please put in ffmpeg folder",
        'btn_locate_ffmpeg': "Change FFmpeg Path",
        'group_file_select': "📂 Select Video File",
        'btn_select_file': "📄 Select File",
        'btn_analyze': "🔍 Analyze",
        'group_track_list': "📋 Subtitle Track List",
        'btn_select_all': "Select All",
        'btn_deselect_all': "Deselect All",
        'btn_select_text': "Text Only",
        'label_track_count': "Total {count} tracks",
        'group_preview': "👁️ Preview",
        'group_log': "📝 Work Log",
        'btn_open_log': "Open Log Folder",
        'label_format': "Output Format:",
        'label_save_path': "   Save Location:",
        'radio_same_folder': "Original Folder",
        'radio_custom_folder': "Select Folder",
        'btn_extract': "🚀 Extract Selected",
        'btn_stop': "⏹ Stop Extraction",
        'btn_waiting': "⌛ Waiting for Stop",
        'msg_select_file_first': "Please analyze a video file first.",
        'msg_ffmpeg_missing': "FFmpeg is not installed.",
        'msg_select_track': "Please select subtitle tracks to extract.",
        'msg_extract_start': "📤 Starting extraction of {count} tracks...",
        'msg_extract_done': "🎉 Extraction complete! ({success}/{total} success)",
        'msg_extract_cancelled': "⛔ Extraction stopped by user.",
        'msg_error_occurred': "❌ Error during extraction: {error}",
        'notice_title': "📢 Notice",
        'update_required': "⚠️ Update Required",
        'update_msg': "Current version ({current}) is no longer supported.\nPlease update to the latest version ({latest}).",
        'btn_download': "Download Latest",
    }
}

class AppUpdateManager:
    def __init__(self, current_version: str = APP_VERSION):
        self.current_version = current_version
        self.config: Dict[str, Any] = {}
        self.is_checked = False
        self.language = 'ko'  # 기본값 한국어

    def fetch_config(self, callback: Optional[callable] = None):
        """Firebase Hosting에서 원격 설정을 비동기로 가져옵니다."""
        def run():
            try:
                response = requests.get(CONFIG_URL, timeout=5)
                if response.status_code == 200:
                    self.config = response.json()
                    self.is_checked = True
                else:
                    print(f"[AppUpdateManager] Server returned status {response.status_code}")
            except requests.exceptions.ConnectionError:
                print("[AppUpdateManager] Network unavailable - offline mode")
            except requests.exceptions.Timeout:
                print("[AppUpdateManager] Server timeout - offline mode")
            except Exception as e:
                print(f"[AppUpdateManager] Error fetching remote config: {e}")
                pass
            
            if callback:
                callback(self.config)

        threading.Thread(target=run, daemon=True).start()

    def check_kill_switch(self) -> bool:
        """킬 스위치 작동 여부 (최소 버전 미달) 확인"""
        if not self.config:
            return False
        min_ver = self.config.get("min_version", "0.01")
        return self._compare_versions(self.current_version, min_ver) < 0

    def check_update_available(self) -> bool:
        """새 버전 지원 여부 확인"""
        if not self.config:
            return False
        latest_ver = self.config.get("latest_version", self.current_version)
        return self._compare_versions(self.current_version, latest_ver) < 0

    def check_notice(self) -> Optional[Dict[str, Any]]:
        """서버 공지 사항 유효성 확인"""
        notice = self.config.get("notice")
        if not notice or not notice.get("active", False):
            return None
        return notice

    def _compare_versions(self, v1: str, v2: str) -> int:
        """버전 비교 (v1 > v2: 1, v1 == v2: 0, v1 < v2: -1)
        0.XX 형식 지원
        """
        try:
            val1 = float(v1)
            val2 = float(v2)
            if val1 > val2: return 1
            if val1 < val2: return -1
            return 0
        except ValueError:
            return 0

    def get_string(self, key: str, **kwargs) -> str:
        """현재 언어에 맞는 문자열 반환"""
        text = TRANSLATIONS.get(self.language, TRANSLATIONS['ko']).get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    def set_language(self, lang: str):
        if lang in TRANSLATIONS:
            self.language = lang
