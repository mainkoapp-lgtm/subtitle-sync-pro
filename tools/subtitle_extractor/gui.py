# 자막 추출기 GUI (tkinter 기반)
# 영상에서 자막 트랙을 선택하여 고속 추출하는 데스크톱 인터페이스
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
from typing import List, Optional
from PIL import Image, ImageTk

from extractor import (
    find_ffmpeg, probe_subtitles, extract_subtitle, batch_extract,
    scan_directory, get_track_display_name,
    get_language_display, SubtitleTrack, VIDEO_EXTENSIONS
)
from app_updater import AppUpdateManager


class SubtitleExtractorApp:
    """자막 추출기 메인 애플리케이션"""

    def __init__(self, root: tk.Tk):
        self.root = root
        
        # 업데이트 매니저 초기화
        self.updater = AppUpdateManager()
        
        self.root.title(self.updater.get_string('title'))
        self.root.geometry("950x750")
        self.root.minsize(800, 600)

        # 상태 변수
        self.ffmpeg_path: Optional[str] = None
        self.ffprobe_path: Optional[str] = None
        self.current_video: Optional[str] = None
        self.tracks: List[SubtitleTrack] = []
        self.is_processing = False
        self.current_percent = 0  # 진행률 퍼센트 저장용

        # 스타일 설정
        self._setup_styles()

        # FFmpeg 탐색
        self._detect_ffmpeg()

        # UI 구성
        self._build_ui()

        # 드래그 앤 드롭 (tkdnd가 설치된 경우에만)
        self._setup_drag_drop()

        # 아이콘 설정
        self._set_app_icon()

        # [NEW] 서버 데이터 동기화 시작 (버전 체크, 공지)
        self._init_app_sync()

    def _setup_styles(self):
        """UI 스타일 초기 설정"""
        # [완료: 다크 모드 버튼 및 컴포넌트 스타일] 사용자의 요청 없이는 임의의 수정을 금지하며 상태를 유지해야 합니다.
        style = ttk.Style()
        style.theme_use('clam')

        # 색상 팔레트
        self.colors = {
            'bg': '#1e1e2e',
            'surface': '#2d2d44',
            'primary': '#7c3aed',
            'primary_hover': '#6d28d9',
            'success': '#10b981',
            'warning': '#f59e0b',
            'error': '#ef4444',
            'text': '#e2e8f0',
            'text_dim': '#94a3b8',
            'border': '#3d3d5c',
        }

        self.root.configure(bg=self.colors['bg'])

        # 폰트 설정 (맑은 고딕으로 통일)
        default_font = ('맑은 고딕', 10)
        bold_font = ('맑은 고딕', 10, 'bold')
        title_font = ('맑은 고딕', 16, 'bold')
        log_font = ('맑은 고딕', 9)

        # 커스텀 스타일
        style.configure('Title.TLabel',
                        background=self.colors['bg'],
                        foreground=self.colors['text'],
                        font=title_font)

        style.configure('Info.TLabel',
                        background=self.colors['bg'],
                        foreground=self.colors['text_dim'],
                        font=log_font)

        style.configure('Status.TLabel',
                        background=self.colors['surface'],
                        foreground=self.colors['success'],
                        font=log_font)

        style.configure('Dark.TFrame',
                        background=self.colors['bg'])

        style.configure('Surface.TFrame',
                        background=self.colors['surface'])

        # 기본 버튼 스타일
        style.configure('TButton',
                        background=self.colors['surface'],
                        foreground=self.colors['text'],
                        borderwidth=0,
                        focusthickness=3,
                        focuscolor='none')
        style.map('TButton',
                  background=[('active', self.colors['primary_hover'])],
                  foreground=[('active', 'white')])

        # 강조(액션) 버튼 디자인
        style.configure('Action.TButton',
                        font=bold_font,
                        padding=(15, 8),
                        background=self.colors['primary'],
                        foreground='white')
        style.map('Action.TButton',
                  background=[('active', self.colors['primary_hover'])])

        # 소형 버튼 디자인
        style.configure('Small.TButton',
                        font=log_font,
                        padding=(10, 5),
                        background=self.colors['surface'],
                        foreground=self.colors['text'])
        style.map('Small.TButton',
                  background=[('active', self.colors['primary_hover'])],
                  foreground=[('active', 'white')])

        style.configure('TCheckbutton',
                        background=self.colors['bg'],
                        foreground=self.colors['text'],
                        font=default_font)

        style.configure('Dark.TLabelframe',
                        background=self.colors['bg'],
                        foreground=self.colors['text'],
                        font=bold_font)

        style.configure('Dark.TLabelframe.Label',
                        background=self.colors['bg'],
                        foreground=self.colors['text'],
                        font=bold_font)
        
        # 프로그레스 바 스타일
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=self.colors['surface'],
                        background=self.colors['primary'],
                        thickness=10)

    def _set_app_icon(self):
        """애플리케이션 전용 아이콘 설정"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icon.png')
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                img = img.resize((32, 32), Image.Resampling.LANCZOS)
                self.app_icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(False, self.app_icon)
        except Exception as e:
            print(f"Failed to load app icon: {e}")

    def _detect_ffmpeg(self):
        """시스템에서 FFmpeg를 탐색합니다."""
        self.ffmpeg_path, self.ffprobe_path = find_ffmpeg()

    def _build_ui(self):
        """전체 UI를 레이아웃에 맞춰 구성합니다 (최적화 레이아웃) [COMPLETED: 2026-04-18]"""
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # ── 1. 최하단 고정 섹션 (광고 배너 및 컨트롤) ──
        # 이 영역들을 먼저 BOTTOM으로 배치하여 창이 작아져도 사라지지 않게 합니다.
        self._build_ad_banner(main_frame)
        self._build_controls(main_frame)

        # ── 2. 상단 고정 섹션 ──
        self._build_header(main_frame)
        self._build_file_selector(main_frame)

        # ── 3. 중앙 가변 섹션 (트랙 목록 + 로그) ──
        # 이 영역에 expand=True를 주어, 창 크기가 변할 때 이 영역이 늘어나거나 줄어들도록 합니다.
        middle_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 3a. 왼쪽: 자막 트랙 목록 (가변 높이)
        left_side = ttk.Frame(middle_frame, style='Dark.TFrame')
        left_side.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._build_track_list(left_side)

        # 3b. 오른쪽: 로그 (가변 높이, 고정 너비)
        right_side = ttk.Frame(middle_frame, style='Dark.TFrame', width=400)
        right_side.pack(side=tk.RIGHT, fill=tk.BOTH)
        right_side.pack_propagate(False) 
        
        log_container = ttk.Frame(right_side, style='Dark.TFrame')
        log_container.pack(fill=tk.BOTH, expand=True)
        self._build_log(log_container)

    def _build_header(self, parent):
        """헤더 영역 (로고 + 설정 버튼 통합)"""
        # [완료: 설정 버튼 단일 통합 레이아웃] 사용자의 요청 없이는 임의의 수정을 금지하며 상태를 유지해야 합니다.
        header = ttk.Frame(parent, style='Dark.TFrame')
        header.pack(fill=tk.X, pady=(0, 10))

        # 제목 및 버전 컨테이너
        title_container = ttk.Frame(header, style='Dark.TFrame')
        title_container.pack(side=tk.LEFT)

        # 제목 텍스트 표시
        self.title_label = ttk.Label(title_container, text=self.updater.get_string('header_title'),
                  style='Title.TLabel')
        self.title_label.pack(side=tk.LEFT)

        # 버전 표시 (제목과 어울리는 폰트 스타일로 변경)
        tk.Label(
            title_container, text=f"v{self.updater.current_version}",
            bg=self.colors['bg'], fg=self.colors['text_dim'],
            font=('맑은 고딕', 10, 'bold')).pack(side=tk.LEFT, padx=8, pady=(8, 0))

        # ── 설정 버튼 ──
        settings_frame = ttk.Frame(header, style='Dark.TFrame')
        settings_frame.pack(side=tk.RIGHT, padx=10)
        
        self.btn_settings = ttk.Button(settings_frame, text=self.updater.get_string('btn_settings'),
                                command=self._show_settings_modal,
                                style='Small.TButton')
        self.btn_settings.pack(side=tk.RIGHT)
        
        # 언어 변수 초기화
        self.lang_var = tk.StringVar(value=self.updater.language)

    def _show_settings_modal(self):
        """설정 창 (모달) 표시"""
        # [완료: 5개국어 지원 및 FFmpeg 설정 통합 모달] 사용자의 요청 없이는 임의의 수정을 금지하며 상태를 유지해야 합니다.
        dialog = tk.Toplevel(self.root)
        dialog.title(self.updater.get_string('settings_title'))
        dialog.geometry("450x300")
        dialog.configure(bg=self.colors['bg'])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        if hasattr(self, 'app_icon'):
            dialog.iconphoto(False, self.app_icon)

        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 225
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 150
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        content_frame = tk.Frame(dialog, bg=self.colors['bg'], padx=20, pady=20)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 언어 선택
        lang_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        lang_frame.pack(fill=tk.X, pady=(0, 15))
        lbl_lang = tk.Label(lang_frame, text=self.updater.get_string('label_language'), bg=self.colors['bg'], fg=self.colors['text'], font=('맑은 고딕', 10, 'bold'))
        lbl_lang.pack(side=tk.LEFT)
        
        langs = {'ko': '한국어', 'en': 'English', 'ja': '日本語', 'zh': '中文', 'hi': 'हिन्दी'}
        display_langs = list(langs.values())
        
        self.lang_cb = ttk.Combobox(lang_frame, values=display_langs, state='readonly', width=15)
        current_display = langs.get(self.updater.language, '한국어')
        self.lang_cb.set(current_display)
        self.lang_cb.pack(side=tk.RIGHT)
        
        def on_lang_select(event):
            selected_display = self.lang_cb.get()
            for code, display in langs.items():
                if display == selected_display:
                    self.lang_var.set(code)
                    self._change_language()
                    # 실시간 모달 텍스트 업데이트
                    dialog.title(self.updater.get_string('settings_title'))
                    lbl_lang.config(text=self.updater.get_string('label_language'))
                    btn_home.config(text=self.updater.get_string('btn_visit_home'))
                    btn_ffmpeg.config(text=self.updater.get_string('btn_locate_ffmpeg'))
                    self._update_modal_ffmpeg_status(lbl_ff_status)
                    break
        self.lang_cb.bind("<<ComboboxSelected>>", on_lang_select)

        # FFmpeg 상태 및 변경
        ff_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        ff_frame.pack(fill=tk.X, pady=15)
        
        lbl_ff_status = tk.Label(ff_frame, text="", bg=self.colors['bg'], font=('맑은 고딕', 9))
        lbl_ff_status.pack(side=tk.LEFT)
        self._update_modal_ffmpeg_status(lbl_ff_status)
        
        btn_ffmpeg = ttk.Button(ff_frame, text=self.updater.get_string('btn_locate_ffmpeg'), command=lambda: [self._locate_ffmpeg(), self._update_modal_ffmpeg_status(lbl_ff_status)])
        btn_ffmpeg.pack(side=tk.RIGHT)

        # 구분선
        tk.Frame(content_frame, height=1, bg=self.colors['border']).pack(fill=tk.X, pady=15)

        # 홈페이지 이동 버튼
        btn_home = ttk.Button(content_frame, text=self.updater.get_string('btn_visit_home'), command=lambda: os.startfile("https://subtitle.mainko.net/"), style='Action.TButton')
        btn_home.pack(pady=10)
        
    def _update_modal_ffmpeg_status(self, label):
        if self.ffmpeg_path and self.ffprobe_path:
            import sys
            base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            if self.ffmpeg_path.startswith(base_dir):
                status_key = 'status_ffmpeg_portable'
            else:
                status_key = 'status_ffmpeg_system'
            label.config(text=self.updater.get_string(status_key), fg=self.colors['success'])
        else:
            label.config(text=self.updater.get_string('status_ffmpeg_none'), fg=self.colors['error'])

    def _build_file_selector(self, parent):
        """파일 선택 영역"""
        self.frame_file = ttk.LabelFrame(parent, text=self.updater.get_string('group_file_select'),
                               style='Dark.TLabelframe')
        self.frame_file.pack(fill=tk.X, pady=(0, 10))

        inner = ttk.Frame(self.frame_file, style='Dark.TFrame')
        inner.pack(fill=tk.X, padx=10, pady=8)

        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(
            inner, textvariable=self.path_var,
            bg=self.colors['surface'], fg=self.colors['text'],
            insertbackground=self.colors['text'],
            font=('맑은 고딕', 10), relief='flat', bd=2)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        btn_frame = ttk.Frame(inner, style='Dark.TFrame')
        btn_frame.pack(side=tk.RIGHT, padx=(8, 0))

        self.btn_select = ttk.Button(btn_frame, text=self.updater.get_string('btn_select_file'),
                   command=self._select_file,
                   style='Small.TButton')
        self.btn_select.pack(side=tk.LEFT, padx=2)



    def _build_track_list(self, parent):
        """자막 트랙 목록 (체크박스 포함)"""
        self.frame_tracks = ttk.LabelFrame(parent, text=self.updater.get_string('group_track_list'),
                               style='Dark.TLabelframe')
        self.frame_tracks.pack(fill=tk.BOTH, expand=True)

        # 상단 버튼 (전체 선택/해제)
        btn_bar = ttk.Frame(self.frame_tracks, style='Dark.TFrame')
        btn_bar.pack(fill=tk.X, padx=10, pady=(8, 2))

        self.btn_select_all = ttk.Button(btn_bar, text=self.updater.get_string('btn_select_all'),
                   command=self._select_all_tracks,
                   style='Small.TButton')
        self.btn_select_all.pack(side=tk.LEFT, padx=2)

        self.btn_deselect_all = ttk.Button(btn_bar, text=self.updater.get_string('btn_deselect_all'),
                   command=self._deselect_all_tracks,
                   style='Small.TButton')
        self.btn_deselect_all.pack(side=tk.LEFT, padx=2)

        self.btn_select_text = ttk.Button(btn_bar, text=self.updater.get_string('btn_select_text'),
                   command=self._select_text_only,
                   style='Small.TButton')
        self.btn_select_text.pack(side=tk.LEFT, padx=2)

        self.track_count_label = tk.Label(
            btn_bar, text="",
            bg=self.colors['bg'], fg=self.colors['text_dim'],
            font=('맑은 고딕', 9))
        self.track_count_label.pack(side=tk.RIGHT)

        # 스크롤 가능한 체크박스 영역
        canvas_frame = ttk.Frame(self.frame_tracks, style='Dark.TFrame')
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        self.track_canvas = tk.Canvas(
            canvas_frame, bg=self.colors['bg'],
            highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL,
                                   command=self.track_canvas.yview)
        self.track_inner = ttk.Frame(self.track_canvas, style='Dark.TFrame')

        self.track_inner.bind(
            '<Configure>',
            lambda e: self.track_canvas.configure(
                scrollregion=self.track_canvas.bbox('all')))

        self.track_canvas.create_window((0, 0), window=self.track_inner,
                                        anchor='nw')
        self.track_canvas.configure(yscrollcommand=scrollbar.set)

        self.track_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.track_canvas.bind('<MouseWheel>',
                               lambda e: self.track_canvas.yview_scroll(
                                   int(-1 * (e.delta / 120)), 'units'))
        self.track_vars = []



    def _build_log(self, parent):
        """로그 영역 (우측 하단)"""
        self.frame_log = ttk.LabelFrame(parent, text=self.updater.get_string('group_log'),
                               style='Dark.TLabelframe')
        self.frame_log.pack(fill=tk.BOTH, expand=True)

        btn_bar = ttk.Frame(self.frame_log, style='Dark.TFrame')
        btn_bar.pack(fill=tk.X, padx=10, pady=(2, 0))
        
        self.btn_open_log = ttk.Button(btn_bar, text=self.updater.get_string('btn_open_log'),
                   command=self._open_log_folder,
                   style='Small.TButton')
        self.btn_open_log.pack(side=tk.RIGHT)

        self.log_text = tk.Text(
            self.frame_log, height=10,
            bg=self.colors['surface'], fg=self.colors['text_dim'],
            insertbackground=self.colors['text'],
            font=('맑은 고딕', 9), relief='flat', bd=2,
            wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # 성공/실패 텍스트 색상 태그
        self.log_text.tag_configure('success', foreground=self.colors['success'])
        self.log_text.tag_configure('error', foreground=self.colors['error'])
        self.log_text.tag_configure('warning', foreground=self.colors['warning'])
        self.log_text.tag_configure('info', foreground=self.colors['text'])

    def _build_controls(self, parent):
        """하단 고속 추출 컨트롤 영역"""
        frame = ttk.Frame(parent, style='Dark.TFrame')
        frame.pack(fill=tk.X, side=tk.BOTTOM)

        divider = ttk.Separator(frame, orient='horizontal')
        divider.pack(fill=tk.X, pady=(0, 10))

        # 좌측 설정 그룹 (형식, 저장소, 프로그레스)
        left_group = ttk.Frame(frame, style='Dark.TFrame')
        left_group.pack(side=tk.LEFT, fill=tk.X, expand=True)

        row1 = ttk.Frame(left_group, style='Dark.TFrame')
        row1.pack(fill=tk.X)

        self.lbl_format = tk.Label(row1, text=self.updater.get_string('label_format'),
                 bg=self.colors['bg'], fg=self.colors['text'],
                 font=('맑은 고딕', 9))
        self.lbl_format.pack(side=tk.LEFT, padx=(0, 5))

        self.format_var = tk.StringVar(value='srt')
        formats = ['srt', 'ass', 'webvtt']
        self.format_combo = ttk.Combobox(
            row1, textvariable=self.format_var,
            values=formats, state='readonly', width=8)
        self.format_combo.pack(side=tk.LEFT)

        self.lbl_save_path = tk.Label(row1, text=self.updater.get_string('label_save_path'),
                 bg=self.colors['bg'], fg=self.colors['text'],
                 font=('맑은 고딕', 9))
        self.lbl_save_path.pack(side=tk.LEFT, padx=(10, 5))

        self.save_mode_var = tk.StringVar(value='same')
        self.radio_same = tk.Radiobutton(row1, text=self.updater.get_string('radio_same_folder'),
                       variable=self.save_mode_var, value='same',
                       bg=self.colors['bg'], fg=self.colors['text'],
                       selectcolor=self.colors['surface'],
                       font=('맑은 고딕', 9))
        self.radio_same.pack(side=tk.LEFT)

        self.radio_custom = tk.Radiobutton(row1, text=self.updater.get_string('radio_custom_folder'),
                       variable=self.save_mode_var, value='custom',
                       bg=self.colors['bg'], fg=self.colors['text'],
                       selectcolor=self.colors['surface'],
                       font=('맑은 고딕', 9))
        self.radio_custom.pack(side=tk.LEFT)

        # 프로그레스 바
        prog_row = ttk.Frame(left_group, style='Dark.TFrame')
        prog_row.pack(fill=tk.X, pady=(5, 0))
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            prog_row, variable=self.progress_var,
            maximum=100, style="Custom.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))
        
        self.progress_label = tk.Label(
            prog_row, text="...",
            bg=self.colors['bg'], fg=self.colors['text_dim'],
            font=('맑은 고딕', 8), width=20, anchor='e')
        self.progress_label.pack(side=tk.RIGHT)

        # 우측 추출 버튼 (통합)
        right_group = ttk.Frame(frame, style='Dark.TFrame')
        right_group.pack(side=tk.RIGHT)

        self.extract_btn = ttk.Button(
            right_group, text=self.updater.get_string('btn_extract'),
            command=self._handle_extract_click,
            style='Action.TButton')
        self.extract_btn.pack(side=tk.RIGHT)

    def _build_ad_banner(self, parent):
        """최하단 광고 영역 (서버 동적 로드 대기) [2026-04-20 수정]"""
        # [완료: UI 찌그러짐 방지 및 동적 배너 뼈대 유지] 사용자의 요청 없이는 임의로 수정하지 마세요.
        banner_frame = ttk.Frame(parent, style='Dark.TFrame')
        banner_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))
        
        # 초기 상태: 빈 배너 영역 (900x110 크기 확보)
        self.ad_images = []
        self.ad_index = 0
        
        from PIL import Image, ImageTk
        placeholder_img = Image.new('RGB', (900, 110), color=self.colors['bg'])
        self.ad_placeholder = ImageTk.PhotoImage(placeholder_img)
        
        # 창 크기를 조절해도 찌그러지지 않도록 기본 이미지 사이즈를 강제로 부여해 레이아웃 붕괴 방지
        self.ad_label = tk.Label(banner_frame, image=self.ad_placeholder, bg=self.colors['bg'], bd=0, cursor="hand2")
        self.ad_label.pack(fill=tk.X)

    def _rotate_ad(self):
        """배너 이미지를 순환시킴 [COMPLETED: 2026-04-18]"""
        if not hasattr(self, 'ad_images') or not self.ad_images:
            return
            
        self.ad_index = (self.ad_index + 1) % len(self.ad_images)
        self.ad_label.configure(image=self.ad_images[self.ad_index])
        
        # 다음 로테이션 예약 (5초 후)
        self.root.after(5000, self._rotate_ad)

    # ═══════════════════════════════════════════
    #  애플리케이션 동기화 및 관리
    # ═══════════════════════════════════════════

    def _init_app_sync(self):
        """앱 시작 시 서버 설정 동기화"""
        self.updater.fetch_config(callback=self._on_config_loaded)

    def _on_config_loaded(self, config):
        """설정 로드 완료 시 콜백"""
        if not config:
            return

        # 1. 킬 스위치 체크
        if self.updater.check_kill_switch():
            self.root.after(0, self._show_kill_switch)
            return

        # 2. 업데이트 알림 체크
        if self.updater.check_update_available():
            # 업데이트 권유 (차단은 아님)
            latest = self.config.get('latest_version')
            self.root.after(1000, lambda: self._log(self.updater.get_string('update_msg', current=self.updater.current_version, latest=latest), 'warning'))

        # 3. 공지 사항 체크
        notice = self.updater.check_notice()
        if notice:
            self.root.after(500, lambda: self._show_notice(notice))

        # 4. [NEW] 파이어베이스 배너 관리 및 Cloudflare 클릭 수집 연동
        ad_config = config.get("ad_config")
        if ad_config and ad_config.get("active", False):
            self.root.after(0, lambda: self._update_dynamic_ad(ad_config))

    def _update_dynamic_ad(self, ad_config):
        """파이어베이스에서 설정한 동적 배너 노출 및 CF 트래커 연동 [2026-04-20]"""
        # [완료: 파이어베이스 동적 배너 비동기 로딩 및 CF 트래커 호출] 사용자의 요청 없이는 임의로 수정하지 마세요.
        image_url = ad_config.get("image_url")
        target_url = ad_config.get("target_url")
        tracker_base = ad_config.get("cf_tracker_url")
        ad_id = ad_config.get("ad_id", "fallback_ad")

        if not image_url or not target_url:
            return

        import urllib.parse
        # Cloudflare 트래커를 활용한 최종 리다이렉트 URL 생성
        if tracker_base:
            encoded_target = urllib.parse.quote(target_url, safe='')
            final_click_url = f"{tracker_base.rstrip('/')}/click?ad_id={ad_id}&target={encoded_target}"
        else:
            final_click_url = target_url

        def fetch_and_set():
            try:
                import requests
                from io import BytesIO
                from PIL import Image, ImageTk

                res = requests.get(image_url, timeout=5)
                if res.status_code == 200:
                    img = Image.open(BytesIO(res.content))
                    img = img.resize((900, 110), Image.Resampling.LANCZOS)
                    self.root.after(0, lambda: self._apply_dynamic_ad(img, final_click_url))
                else:
                    self.root.after(0, lambda: self._log("⚠️ 프로그램 실행시 문제가 발생하였습니다. (코드: ERR_BN_HTTP)", 'warning'))
            except Exception as e:
                # 네트워크 에러 시
                self.root.after(0, lambda: self._log("⚠️ 프로그램 실행시 문제가 발생하였습니다. (코드: ERR_BN_NET)", 'warning'))

        import threading
        threading.Thread(target=fetch_and_set, daemon=True).start()

    def _apply_dynamic_ad(self, img, click_url):
        # [완료: 동적 이미지 GUI 교체, 로그 출력] 사용자의 요청 없이는 임의로 수정하지 마세요.
        from PIL import ImageTk
        self.ad_dynamic_img = ImageTk.PhotoImage(img) # GC 방지 참조 유지
        # 기존 로컬 하드코딩 광고를 동적 광고 하나로 완전 덮어쓰기 (로테이션 중지 효과)
        self.ad_images = [self.ad_dynamic_img]
        self.ad_index = 0
        if hasattr(self, 'ad_label'):
            self.ad_label.configure(image=self.ad_images[0])
            self.ad_label.bind("<Button-1>", lambda e: os.startfile(click_url))
            self._log("✅ 프로그램이 정상적으로 실행되었습니다.", 'success')

    def _show_kill_switch(self):
        """업데이트 필수 안내 (차단 화면)"""
        # 메인 프레임 숨기기
        for widget in self.root.winfo_children():
            widget.pack_forget() if hasattr(widget, 'pack_forget') else widget.grid_forget()

        kill_frame = ttk.Frame(self.root, style='Dark.TFrame')
        kill_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(kill_frame, text=self.updater.get_string('update_required'),
                 bg=self.colors['bg'], fg=self.colors['error'],
                 font=('맑은 고딕', 20, 'bold')).pack(pady=(100, 20))

        latest = self.updater.config.get('latest_version', '?.?.?')
        tk.Label(kill_frame, text=self.updater.get_string('update_msg', current=self.updater.current_version, latest=latest),
                 bg=self.colors['bg'], fg=self.colors['text'],
                 font=('맑은 고딕', 12), justify=tk.CENTER).pack(pady=20)

        download_url = self.updater.config.get('download_url', '#')
        ttk.Button(kill_frame, text=self.updater.get_string('btn_download'),
                   command=lambda: os.startfile(download_url),
                   style='Action.TButton').pack(pady=20)

    def _show_notice(self, notice):
        """공지 사항 커스텀 다크 테마 팝업 표시"""
        dialog = tk.Toplevel(self.root)
        dialog.title(self.updater.get_string('notice_title'))
        dialog.geometry("400x320")
        dialog.configure(bg=self.colors['bg'])
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 아이콘 적용
        if hasattr(self, 'app_icon'):
            dialog.iconphoto(False, self.app_icon)

        # 화면 중앙 배치
        self.root.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 160
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

        # 콘텐츠 프레임
        content_frame = tk.Frame(dialog, bg=self.colors['bg'], padx=25, pady=25)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 공지 아이콘/타이틀 (상단)
        header_label = tk.Label(
            content_frame, text=notice.get('title', 'NOTICE'),
            bg=self.colors['bg'], fg=self.colors['primary'],
            font=('맑은 고딕', 14, 'bold'), wraplength=350, justify=tk.LEFT
        )
        header_label.pack(anchor=tk.W, pady=(0, 15))

        # 구분선
        line = tk.Frame(content_frame, height=1, bg=self.colors['surface'])
        line.pack(fill=tk.X, pady=(0, 15))

        # 공지 내용 (중앙)
        body_label = tk.Label(
            content_frame, text=notice.get('content', ''),
            bg=self.colors['bg'], fg=self.colors['text'],
            font=('맑은 고딕', 10), justify=tk.LEFT, wraplength=350,
            anchor="nw"
        )
        body_label.pack(fill=tk.BOTH, expand=True)

        # 닫기 버튼 (하단)
        btn_frame = tk.Frame(content_frame, bg=self.colors['bg'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        close_btn = tk.Button(
            btn_frame, text="OK",
            bg=self.colors['primary'], fg='white',
            activebackground=self.colors['primary_hover'],
            font=('맑은 고딕', 10, 'bold'),
            width=10, bd=0, padx=10, pady=5,
            command=dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT)
        
        # 버튼 호버 효과
        close_btn.bind("<Enter>", lambda e: close_btn.configure(bg=self.colors['primary_hover']))
        close_btn.bind("<Leave>", lambda e: close_btn.configure(bg=self.colors['primary']))

    def _change_language(self):
        """언어 변경 이벤트"""
        new_lang = self.lang_var.get()
        self.updater.set_language(new_lang)
        self._update_all_texts()
        self._log(f"Language changed to: {new_lang}", 'info')

    def _update_all_texts(self):
        """UI 내 모든 텍스트를 현재 언어에 맞게 갱신"""
        self.root.title(self.updater.get_string('title'))
        
        # 헤더
        # 헤더
        if hasattr(self, 'title_label'):
            self.title_label.configure(text=self.updater.get_string('header_title'))
        
        if hasattr(self, 'btn_settings'):
            self.btn_settings.configure(text=self.updater.get_string('btn_settings'))
        
        # FFmpeg 상태 (이미 계산된 상태에 따라)
        # (생략: 필요 시 상태 변수 저장하여 업데이트)
        
        # 파일 선택
        self.frame_file.configure(text=self.updater.get_string('group_file_select'))
        self.btn_select.configure(text=self.updater.get_string('btn_select_file'))

        
        # 트랙 목록
        self.frame_tracks.configure(text=self.updater.get_string('group_track_list'))
        self.btn_select_all.configure(text=self.updater.get_string('btn_select_all'))
        self.btn_deselect_all.configure(text=self.updater.get_string('btn_deselect_all'))
        self.btn_select_text.configure(text=self.updater.get_string('btn_select_text'))
        
        # 로그
        self.frame_log.configure(text=self.updater.get_string('group_log'))
        self.btn_open_log.configure(text=self.updater.get_string('btn_open_log'))
        
        # 컨트롤
        self.lbl_format.configure(text=self.updater.get_string('label_format'))
        self.lbl_save_path.configure(text=self.updater.get_string('label_save_path'))
        self.radio_same.configure(text=self.updater.get_string('radio_same_folder'))
        self.radio_custom.configure(text=self.updater.get_string('radio_custom_folder'))
        
        # 버튼 상태에 따라
        btn_text = 'btn_stop' if self.is_processing else 'btn_extract'
        self.extract_btn.configure(text=self.updater.get_string(btn_text))

    # ═══════════════════════════════════════════
    #  이벤트 핸들러
    # ═══════════════════════════════════════════

    def _setup_drag_drop(self):
        """드래그 앤 드롭 지원 (tkdnd 미설치 시 무시)"""
        try:
            self.root.drop_target_register('DND_Files')
            self.root.dnd_bind('<<Drop>>', self._on_drop)
        except Exception:
            pass  # tkdnd 미설치 시 조용히 무시

    def _on_drop(self, event):
        """파일 드롭 이벤트 처리"""
        path = event.data.strip('{}')
        if os.path.isfile(path):
            self.path_var.set(path)
            self._analyze_file()
        elif os.path.isdir(path):
            self.path_var.set(path)
            self._log("폴더가 드롭되었습니다. '분석' 버튼을 눌러 폴더 내 영상을 검색하세요.", 'info')

    def _locate_ffmpeg(self):
        """FFmpeg 수동 경로 지정"""
        path = filedialog.askopenfilename(
            title="ffmpeg.exe 파일을 선택하세요",
            filetypes=[("FFmpeg", "ffmpeg.exe"), ("All", "*.*")])

        if path:
            self.ffmpeg_path = path
            # 같은 폴더에서 ffprobe도 찾기
            ffprobe_candidate = os.path.join(os.path.dirname(path), 'ffprobe.exe')
            if os.path.isfile(ffprobe_candidate):
                self.ffprobe_path = ffprobe_candidate

            self.ffmpeg_status.configure(text="✅ FFmpeg 경로 지정됨",
                                          fg=self.colors['success'])
            self._log(f"FFmpeg 경로 설정: {path}", 'success')

    def _select_file(self):
        """파일 선택 대화상자"""
        exts = ' '.join(f'*{e}' for e in VIDEO_EXTENSIONS)
        path = filedialog.askopenfilename(
            title="영상 파일 선택",
            filetypes=[("영상 파일", exts), ("모든 파일", "*.*")])
        if path:
            self.path_var.set(path)
            self._analyze_file()

    def _analyze_file(self):
        """선택한 파일의 자막 트랙을 분석합니다."""
        path = self.path_var.get().strip()
        if not path:
            messagebox.showwarning("알림", "파일 경로를 입력하거나 선택하세요.")
            return

        if not os.path.exists(path):
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{path}")
            return

        if not self.ffprobe_path:
            messagebox.showerror("오류",
                                 "FFmpeg가 설치되어 있지 않습니다.\n"
                                 "https://ffmpeg.org 에서 다운로드 후\n"
                                 "'FFmpeg 경로 지정' 버튼을 사용하세요.")
            return

        # 비동기 분석 (UI 멈춤 방지)
        self._log(f"분석 중: {os.path.basename(path)}...", 'info')
        self.is_processing = True

        def analyze():
            try:
                self.tracks = probe_subtitles(path, self.ffprobe_path)
                self.current_video = path
                self.root.after(0, self._update_track_list)

                if self.tracks:
                    self.root.after(0, lambda: self._log(
                        f"✅ {len(self.tracks)}개의 자막 트랙을 발견했습니다.", 'success'))
                else:
                    self.root.after(0, lambda: self._log(
                        "⚠️ 이 영상에는 자막 트랙이 없습니다.", 'warning'))
            except Exception as e:
                self.root.after(0, lambda: self._log(f"❌ 분석 실패: {str(e)}", 'error'))
            finally:
                self.is_processing = False

        threading.Thread(target=analyze, daemon=True).start()

    def _update_track_list(self):
        """자막 트랙 목록 UI를 갱신합니다."""
        # 기존 체크박스 제거
        for widget in self.track_inner.winfo_children():
            widget.destroy()
        self.track_vars.clear()

        if not self.tracks:
            tk.Label(self.track_inner,
                     text="No subtitle tracks found." if self.updater.language == 'en' else "자막 트랙이 없습니다.",
                     bg=self.colors['bg'], fg=self.colors['text_dim'],
                     font=('맑은 고딕', 10)).pack(pady=20)
            self.track_count_label.configure(text="")
            return

        self.track_count_label.configure(
            text=self.updater.get_string('label_track_count', count=len(self.tracks)))

        for i, track in enumerate(self.tracks):
            # 첫 번째 자막 트랙(#1)만 기본 선택, 나머지는 해제
            is_selected = (i == 0)
            var = tk.BooleanVar(value=is_selected)
            self.track_vars.append(var)

            row = ttk.Frame(self.track_inner, style='Dark.TFrame')
            row.pack(fill=tk.X, pady=1)

            # 체크박스
            cb = tk.Checkbutton(
                row, variable=var,
                text=get_track_display_name(track),
                bg=self.colors['bg'], fg=self.colors['text'],
                selectcolor=self.colors['surface'],
                activebackground=self.colors['bg'],
                activeforeground=self.colors['text'],
                font=('맑은 고딕', 10),
                anchor='w')
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)





    def _select_all_tracks(self):
        for var in self.track_vars:
            var.set(True)

    def _deselect_all_tracks(self):
        for var in self.track_vars:
            var.set(False)

    def _select_text_only(self):
        for i, track in enumerate(self.tracks):
            self.track_vars[i].set(track.is_text_based)

    def _handle_extract_click(self):
        """추출 버튼 클릭 시 (추출 시작 또는 중단)"""
        if self.is_processing:
            self._stop_extract()
        else:
            self._extract_selected()

    def _extract_selected(self):
        """선택한 자막 트랙들을 추출합니다."""
        if not self.current_video:
            messagebox.showwarning(self.updater.get_string('notice_title'), self.updater.get_string('msg_select_file_first'))
            return

        if not self.ffmpeg_path:
            messagebox.showerror("Error", self.updater.get_string('msg_ffmpeg_missing'))
            return

        # 선택된 트랙 수집
        selected = [track for i, track in enumerate(self.tracks)
                     if i < len(self.track_vars) and self.track_vars[i].get()]

        if not selected:
            messagebox.showwarning(self.updater.get_string('notice_title'), self.updater.get_string('msg_select_track'))
            return

        # 저장 경로 결정
        if self.save_mode_var.get() == 'custom':
            output_dir = filedialog.askdirectory(title="저장할 폴더 선택")
            if not output_dir:
                return
        else:
            output_dir = os.path.dirname(self.current_video)

        # 비동기 추출 준비
        self.is_processing = True
        self.cancel_event = threading.Event()
        self.extract_btn.configure(text=self.updater.get_string('btn_stop'))
        output_format = self.format_var.get()

        self._log(self.updater.get_string('msg_extract_start', count=len(selected)), 'info')

        def do_extract():
            try:
                def on_track_done(current, total, filename, success):
                    """트랙 하나 완료 시 호출"""
                    tag = 'success' if success else 'error'
                    status = "✅ 완료" if success else "❌ 실패"
                    self.root.after(0, lambda: self._log(
                        f"  [{current}/{total}] {filename} - {status}", tag))

                def on_file_progress(percent):
                    """개별 파일 추출 중 실시간 진행률 (0~100%)"""
                    self.current_percent = percent
                    self.root.after(0, lambda: self.progress_var.set(percent))

                self.root.after(0, lambda: self.progress_var.set(0))
                self.current_percent = 0
                self.root.after(0, self._start_progress_animation)

                results = batch_extract(
                    self.current_video, selected, output_dir,
                    output_format, self.ffmpeg_path,
                    on_track_done, on_file_progress,
                    self.cancel_event, self.ffprobe_path)

                self.root.after(0, self._stop_progress_animation)

                if self.cancel_event.is_set():
                    self.root.after(0, lambda: self._log(
                        self.updater.get_string('msg_extract_cancelled'), 'warning'))
                else:
                    success_count = sum(1 for v in results.values()
                                         if not str(v).startswith('실패'))

                    self.root.after(0, lambda: self._log(
                        self.updater.get_string('msg_extract_done', success=success_count, total=len(selected)), 'success'))

                    # 완료 알림
                    msg = f"{success_count}/{len(selected)} subtitles extracted.\nLocation: {output_dir}" if self.updater.language == 'en' \
                          else f"{success_count}/{len(selected)}개 자막이 추출되었습니다.\n저장 위치: {output_dir}"
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Success", msg))

            except Exception as e:
                self.root.after(0, lambda: self._log(
                    self.updater.get_string('msg_error_occurred', error=str(e)), 'error'))
            finally:
                self.is_processing = False
                # 버튼 상태 복구
                self.root.after(0, lambda: self.extract_btn.configure(text=self.updater.get_string('btn_extract')))
                self.root.after(0, lambda: self.progress_label.configure(text="DONE" if self.updater.language == 'en' else "완료"))

        threading.Thread(target=do_extract, daemon=True).start()

    def _stop_extract(self):
        """추출 작업을 중단합니다."""
        if hasattr(self, 'cancel_event') and self.is_processing:
            self.cancel_event.set()
            self.extract_btn.configure(text=self.updater.get_string('btn_waiting'))
            self._log("⏹️ Stopping... Killing processes.", 'warning')

    def _animate_progress(self, count=0):
        """추출 중 '추출 중 (%%)...' 애니메이션 표시"""
        if not self.is_processing:
            return
        
        dots = "." * ((count % 3) + 1)
        self.progress_label.configure(text=f"추출 중 ({self.current_percent}%){dots}")
        self.root.after(500, lambda: self._animate_progress(count + 1))

    def _start_progress_animation(self):
        """애니메이션 시작"""
        self.progress_bar.configure(mode='indeterminate')
        self.progress_bar.start(10)
        self._animate_progress()

    def _stop_progress_animation(self):
        """애니메이션 중지"""
        self.progress_bar.stop()
        self.progress_bar.configure(mode='determinate')
        self.progress_var.set(100)
        self.progress_label.configure(text="완료")

    def _open_log_folder(self):
        """로그 파일이 있는 폴더를 엽니다."""
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extractor.log')
        if os.path.exists(log_path):
            os.startfile(os.path.dirname(log_path))
        else:
            messagebox.showinfo("알림", "아직 생성된 로그 파일이 없습니다.")

    def _log(self, message: str, tag: str = 'info'):
        """로그 메시지 추가 및 파일 저장"""
        # GUI 출력
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

        # 파일 저장 (AI 확인용)
        try:
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'extractor.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                import datetime
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] [{tag.upper()}] {message}\n")
        except Exception:
            pass


def main():
    # [NEW] PyInstaller Splash Screen Close
    try:
        import pyi_splash
        pyi_splash.update_text("UI Loading...")
        pyi_splash.close()
    except ImportError:
        pass

    root = tk.Tk()

    # 아이콘 설정 (있을 경우)
    try:
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass

    # DPI 인식 및 작업 표시줄 아이콘 분리 (Windows)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
        # [완료: 작업 표시줄 파이썬 로고를 프로그램 아이콘으로 교체] 사용자의 요청 없이는 임의의 수정을 금지하며 상태를 유지해야 합니다.
        windll.shell32.SetCurrentProcessExplicitAppUserModelID("mainko.subtitle.extractor.0.1")
    except Exception:
        pass

    app = SubtitleExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
