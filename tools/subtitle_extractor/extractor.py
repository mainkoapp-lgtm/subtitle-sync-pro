# 자막 트랙 분석 및 추출 핵심 엔진
# FFmpeg/ffprobe를 활용하여 영상 내 자막 스트림만 고속 추출
import subprocess
import json
import os
import sys
import shutil
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SubtitleTrack:
    """영상 내 자막 트랙 정보"""
    stream_index: int       # 전체 스트림에서의 인덱스 (예: 0:2)
    subtitle_index: int     # 자막 전용 인덱스 (예: 0번째 자막)
    codec: str              # 코덱 (subrip, ass, hdmv_pgs_subtitle 등)
    language: str           # 언어 코드 (eng, kor, rus 등)
    title: str              # 트랙 제목 (있을 경우)
    is_text_based: bool     # 텍스트 기반 여부 (False면 이미지 기반 = OCR 필요)
    disposition: str        # 기본/강제 자막 여부


# 텍스트 기반 자막 코덱 목록 (SRT 변환 가능)
TEXT_CODECS = {
    'subrip', 'srt', 'ass', 'ssa', 'webvtt', 'mov_text',
    'microdvd', 'subviewer', 'realtext', 'sami', 'text'
}

# 이미지 기반 자막 코덱 목록 (OCR 없이는 텍스트 변환 불가)
IMAGE_CODECS = {
    'hdmv_pgs_subtitle', 'dvd_subtitle', 'dvb_subtitle',
    'pgssub', 'vobsub', 'xsub'
}

# 언어 코드 → 한글 매핑
LANGUAGE_MAP = {
    'eng': '영어', 'en': '영어',
    'kor': '한국어', 'ko': '한국어',
    'jpn': '일본어', 'ja': '일본어',
    'chi': '중국어', 'zh': '중국어', 'zho': '중국어',
    'rus': '러시아어', 'ru': '러시아어',
    'spa': '스페인어', 'es': '스페인어',
    'fre': '프랑스어', 'fr': '프랑스어', 'fra': '프랑스어',
    'ger': '독일어', 'de': '독일어', 'deu': '독일어',
    'por': '포르투갈어', 'pt': '포르투갈어',
    'ita': '이탈리아어', 'it': '이탈리아어',
    'ara': '아랍어', 'ar': '아랍어',
    'tha': '태국어', 'th': '태국어',
    'vie': '베트남어', 'vi': '베트남어',
    'hin': '힌디어', 'hi': '힌디어',
    'ind': '인도네시아어', 'id': '인도네시아어',
    'may': '말레이어', 'ms': '말레이어',
    'tur': '터키어', 'tr': '터키어',
    'pol': '폴란드어', 'pl': '폴란드어',
    'ukr': '우크라이나어', 'uk': '우크라이나어',
    'nld': '네덜란드어', 'nl': '네덜란드어', 'dut': '네덜란드어',
    'swe': '스웨덴어', 'sv': '스웨덴어',
    'nor': '노르웨이어', 'no': '노르웨이어',
    'dan': '덴마크어', 'da': '덴마크어',
    'fin': '핀란드어', 'fi': '핀란드어',
    'ces': '체코어', 'cs': '체코어', 'cze': '체코어',
    'ron': '루마니아어', 'ro': '루마니아어', 'rum': '루마니아어',
    'hun': '헝가리어', 'hu': '헝가리어',
    'ell': '그리스어', 'el': '그리스어', 'gre': '그리스어',
    'heb': '히브리어', 'he': '히브리어',
    'und': '알 수 없음',
}

# 지원 영상 확장자
VIDEO_EXTENSIONS = {
    '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv',
    '.webm', '.m4v', '.ts', '.m2ts', '.mpg', '.mpeg',
    '.ogv', '.3gp', '.vob'
}


def find_ffmpeg() -> Tuple[Optional[str], Optional[str]]:
    """
    ffmpeg, ffprobe 경로를 탐색합니다.
    탐색 우선순위:
      1. 프로그램 실행 폴더 내 ffmpeg/ (포터블 동봉 방식)
      2. 시스템 PATH
      3. 일반적인 설치 경로
    """
    ffmpeg_path = None
    ffprobe_path = None

    # ── 1순위: 프로그램 폴더 내 동봉된 FFmpeg (포터블) ──
    # PyInstaller 빌드 시 _MEIPASS, 일반 실행 시 __file__ 기준
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    portable_paths = [
        os.path.join(base_dir, 'ffmpeg', 'bin'),    # ffmpeg/bin/ 하위
        os.path.join(base_dir, 'ffmpeg'),            # ffmpeg/ 바로 아래
        base_dir,                                     # 프로그램과 같은 폴더
    ]

    for path in portable_paths:
        ff = os.path.join(path, 'ffmpeg.exe')
        fp = os.path.join(path, 'ffprobe.exe')
        if os.path.isfile(ff) and os.path.isfile(fp):
            return ff, fp

    # ── 2순위: 시스템 PATH ──
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')

    if ffmpeg_path and ffprobe_path:
        return ffmpeg_path, ffprobe_path

    # ── 3순위: 일반적인 설치 경로 ──
    common_paths = [
        r'C:\ffmpeg\bin',
        r'C:\Program Files\ffmpeg\bin',
        r'C:\Program Files (x86)\ffmpeg\bin',
        os.path.join(os.path.expanduser('~'), 'ffmpeg', 'bin'),
    ]

    if not ffmpeg_path:
        for path in common_paths:
            candidate = os.path.join(path, 'ffmpeg.exe')
            if os.path.isfile(candidate):
                ffmpeg_path = candidate
                break

    if not ffprobe_path:
        for path in common_paths:
            candidate = os.path.join(path, 'ffprobe.exe')
            if os.path.isfile(candidate):
                ffprobe_path = candidate
                break

    return ffmpeg_path, ffprobe_path


def probe_subtitles(video_path: str, ffprobe_path: str = 'ffprobe') -> List[SubtitleTrack]:
    """
    영상 파일의 자막 트랙 정보를 분석합니다.
    네트워크 경로(NAS)에서도 헤더만 읽으므로 매우 빠릅니다.
    """
    try:
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 's',   # 자막 스트림만 선택 (핵심: 영상/오디오 데이터 읽지 않음)
            video_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,             # 네트워크 지연 대비 타임아웃
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe 실행 실패: {result.stderr.strip()}")

        data = json.loads(result.stdout)
        streams = data.get('streams', [])

        tracks = []
        subtitle_idx = 0
        for stream in streams:
            if stream.get('codec_type') != 'subtitle':
                continue

            codec = stream.get('codec_name', 'unknown').lower()
            tags = stream.get('tags', {})
            language = tags.get('language', 'und')
            title = tags.get('title', '')

            # 기본/강제 자막 여부 확인
            disposition = stream.get('disposition', {})
            disp_parts = []
            if disposition.get('default', 0):
                disp_parts.append('기본')
            if disposition.get('forced', 0):
                disp_parts.append('강제')
            disp_str = ', '.join(disp_parts) if disp_parts else ''

            is_text = codec in TEXT_CODECS

            tracks.append(SubtitleTrack(
                stream_index=stream.get('index', 0),
                subtitle_index=subtitle_idx,
                codec=codec,
                language=language,
                title=title,
                is_text_based=is_text,
                disposition=disp_str
            ))
            subtitle_idx += 1

        return tracks

    except subprocess.TimeoutExpired:
        raise RuntimeError("파일 분석 시간 초과 (30초). 네트워크 연결을 확인해주세요.")
    except json.JSONDecodeError:
        raise RuntimeError("ffprobe 출력을 파싱할 수 없습니다.")


def get_language_display(lang_code: str) -> str:
    """언어 코드를 한글 표시명으로 변환합니다."""
    return LANGUAGE_MAP.get(lang_code.lower(), lang_code)


def get_track_display_name(track: SubtitleTrack) -> str:
    """UI에 표시할 트랙 이름을 생성합니다."""
    lang = get_language_display(track.language)
    codec_display = track.codec.upper()

    # 이미지 기반 자막은 명시
    type_tag = "[텍스트]" if track.is_text_based else "[이미지/PGS]"

    parts = [f"#{track.subtitle_index + 1}", type_tag, lang]

    if track.title:
        parts.append(f'"{track.title}"')

    parts.append(f"({codec_display})")

    if track.disposition:
        parts.append(f"[{track.disposition}]")

    return "  ".join(parts)


def _get_video_duration(video_path: str, ffprobe_path: str = 'ffprobe') -> float:
    """영상 전체 길이(초)를 가져옵니다. 진행률 계산에 사용."""
    try:
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            video_path
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            encoding='utf-8', errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data.get('format', {}).get('duration', 0))
    except Exception:
        pass
    return 0.0


def _parse_ffmpeg_time(time_str: str) -> float:
    """FFmpeg의 'HH:MM:SS.xx' 시간 문자열을 초 단위로 변환"""
    try:
        parts = time_str.split(':')
        h, m = int(parts[0]), int(parts[1])
        s = float(parts[2])
        return h * 3600 + m * 60 + s
    except Exception:
        return 0.0


def extract_subtitle(
    video_path: str,
    track: SubtitleTrack,
    output_path: str,
    output_format: str = 'srt',
    ffmpeg_path: str = 'ffmpeg',
    on_progress: callable = None,
    cancel_event=None,
    ffprobe_path: str = 'ffprobe'
) -> bool:
    """
    선택한 자막 트랙을 파일로 추출합니다.
    - Popen 기반 실시간 진행률 표시
    - cancel_event를 통한 중단 지원
    - NAS 경로(UNC) 직접 쓰기 실패 방지 (로컬 임시 파일 활용)
    """
    import tempfile
    import re
    temp_file = None
    process = None

    try:
        # 이미지 기반 자막은 원본 형태로만 추출 가능
        if not track.is_text_based:
            if track.codec in ('hdmv_pgs_subtitle', 'pgssub'):
                output_format = 'sup'
            else:
                output_format = 'sub'
            base, _ = os.path.splitext(output_path)
            output_path = f"{base}.{output_format}"

        # 영상 길이 가져오기 (진행률 계산용)
        duration = _get_video_duration(video_path, ffprobe_path)

        # ── 로컬 임시 파일 사용 (NAS 쓰기 실패 방지) ──
        temp_fd, temp_path = tempfile.mkstemp(suffix=f'.{output_format}')
        os.close(temp_fd)
        temp_file = temp_path

        cmd = [
            ffmpeg_path,
            '-y',
            '-analyzeduration', '1000000',   # 1초로 단축 - NAS 초고속 분석
            '-probesize', '1000000',
            '-i', video_path,
            '-map', f'0:{track.stream_index}',
            '-c:s', output_format if track.is_text_based else 'copy',
            temp_file
        ]

        # ── FFmpeg 실행 (stderr에서 진행률 읽기) ──
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1, # Line buffering
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        # ── 실시간 상황 모니터링 (stderr) ──
        # FFmpeg은 진행률 정보를 stderr에 씁니다.
        time_pattern = re.compile(r'time=(\d{2}:\d{2}:\d{2}\.\d+)')

        import time as pytime
        last_check_time = pytime.time()

        while True:
            # 중단 여부 즉시 확인
            if cancel_event and cancel_event.is_set():
                process.terminate() # 먼저 점잖게 종료 시도
                pytime.sleep(0.1)
                if process.poll() is None:
                    process.kill()   # 안 죽으면 강제 종료
                raise RuntimeError("사용자에 의해 중단되었습니다.")

            # Non-blocking에 가까운 한 줄 읽기 시도
            line = process.stderr.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue

            # 진행률 파싱 (time=00:00:00.00)
            match = time_pattern.search(line)
            if match and duration > 0 and on_progress:
                current_time = _parse_ffmpeg_time(match.group(1))
                percent = min(int((current_time / duration) * 100), 99)
                on_progress(percent)

        process.wait()

        if process.returncode != 0 and not (cancel_event and cancel_event.is_set()):
            error_msg = process.stderr.read().strip()
            # 이미 읽었으므로 비어있을 수 있음
            raise RuntimeError(f"FFmpeg 실행 실패 (코드: {process.returncode})")

        # 파일 생성 확인
        if not os.path.isfile(temp_file) or os.path.getsize(temp_file) == 0:
            raise RuntimeError("추출된 임시 파일이 비어있습니다.")

        # ── 임시 파일을 실제 목적지로 복사 ──
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(temp_file, output_path)

        # 최종 100% 콜백
        if on_progress:
            on_progress(100)

        return True

    except Exception as e:
        raise e
    finally:
        # 프로세스 안전 종료
        if process and process.poll() is None:
            try:
                process.kill()
            except Exception:
                pass
        # 임시 파일 삭제
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


def batch_extract(
    video_path: str,
    tracks: List[SubtitleTrack],
    output_dir: str,
    output_format: str = 'srt',
    ffmpeg_path: str = 'ffmpeg',
    on_progress: callable = None,
    on_file_progress: callable = None,
    cancel_event=None,
    ffprobe_path: str = 'ffprobe'
) -> Dict[int, str]:
    """
    여러 자막 트랙을 한 번에 추출합니다.
    각 트랙별로 언어 코드를 포함한 파일명으로 저장합니다.
    on_progress: 트랙 단위 완료 콜백 (current, total, filename, success)
    on_file_progress: 개별 파일 내 실시간 진행률 콜백 (percent)
    cancel_event: threading.Event - set 시 즉시 중단
    """
    results = {}
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    for i, track in enumerate(tracks):
        # 중단 확인
        if cancel_event and cancel_event.is_set():
            break

        lang = track.language if track.language != 'und' else f'track{track.subtitle_index}'
        ext = output_format if track.is_text_based else ('sup' if 'pgs' in track.codec else 'sub')
        output_filename = f"{video_name}.{lang}.{ext}"
        output_path = os.path.join(output_dir, output_filename)

        # 동일한 파일명 충돌 방지
        counter = 1
        while os.path.exists(output_path):
            output_filename = f"{video_name}.{lang}_{counter}.{ext}"
            output_path = os.path.join(output_dir, output_filename)
            counter += 1

        try:
            extract_subtitle(
                video_path, track, output_path, output_format,
                ffmpeg_path, on_file_progress, cancel_event, ffprobe_path)
            results[track.subtitle_index] = output_path

            if on_progress:
                on_progress(i + 1, len(tracks), output_filename, True)

        except Exception as e:
            error_msg = str(e)
            if "중단" in error_msg:
                results[track.subtitle_index] = f"실패: 사용자 중단"
                break
            results[track.subtitle_index] = f"실패: {error_msg}"
            if on_progress:
                on_progress(i + 1, len(tracks), output_filename, False)

    return results


def preview_subtitle(
    video_path: str,
    track: SubtitleTrack,
    ffmpeg_path: str = 'ffmpeg',
    max_lines: int = 10
) -> str:
    """
    자막 트랙의 앞부분 미리보기를 제공합니다.
    (텍스트 기반 자막만 가능)
    """
    if not track.is_text_based:
        return "[이미지 기반 자막은 미리보기를 지원하지 않습니다]"

    try:
        cmd = [
            ffmpeg_path,
            '-i', video_path,
            '-map', f'0:{track.stream_index}',
            '-c:s', 'srt',
            '-f', 'srt',
            'pipe:1'               # stdout으로 출력 (파일 생성 없이 미리보기)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            return f"[미리보기 실패: {result.stderr.strip()[:200]}]"

        # SRT 블록 단위로 분리하여 max_lines 블록만 반환
        blocks = result.stdout.strip().split('\n\n')
        preview_blocks = blocks[:max_lines]
        return '\n\n'.join(preview_blocks)

    except subprocess.TimeoutExpired:
        return "[미리보기 시간 초과]"
    except Exception as e:
        return f"[미리보기 오류: {str(e)}]"


def scan_directory(dir_path: str) -> List[str]:
    """디렉토리 내 영상 파일 목록을 반환합니다."""
    video_files = []
    try:
        for entry in os.scandir(dir_path):
            if entry.is_file():
                _, ext = os.path.splitext(entry.name)
                if ext.lower() in VIDEO_EXTENSIONS:
                    video_files.append(entry.path)
    except PermissionError:
        pass

    video_files.sort()
    return video_files
