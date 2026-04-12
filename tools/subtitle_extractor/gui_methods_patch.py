    def _handle_extract_click(self):
        """추출 버튼 클릭 시 (추출 시작 또는 중단)"""
        if self.is_processing:
            self._stop_extract()
        else:
            self._extract_selected()

    def _extract_selected(self):
        """선택된 자막 트랙들을 추출합니다."""
        if not self.current_video:
            messagebox.showwarning("알림", "먼저 영상 파일을 선택하고 분석하세요.")
            return

        if not self.ffmpeg_path:
            messagebox.showerror("오류", "FFmpeg가 설치되어 있지 않습니다.")
            return

        # 선택된 트랙 수집
        selected = [track for i, track in enumerate(self.tracks)
                     if i < len(self.track_vars) and self.track_vars[i].get()]

        if not selected:
            messagebox.showwarning("알림", "추출할 자막 트랙을 선택하세요.")
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
        self.extract_btn.configure(text="⏹ 추출 중단")
        output_format = self.format_var.get()

        self._log(f"📤 {len(selected)}개 트랙 추출 시작...", 'info')

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
                        "⛔ 사용자에 의해 추출이 중단되었습니다.", 'warning'))
                else:
                    success_count = sum(1 for v in results.values()
                                         if not str(v).startswith('실패'))

                    self.root.after(0, lambda: self._log(
                        f"🎉 추출 완료! ({success_count}/{len(selected)} 성공)", 'success'))

                    # 완료 알림
                    self.root.after(0, lambda: messagebox.showinfo(
                        "추출 완료",
                        f"{success_count}/{len(selected)}개 자막이 추출되었습니다.\n"
                        f"저장 위치: {output_dir}"))

            except Exception as e:
                self.root.after(0, lambda: self._log(
                    f"❌ 추출 중 오류 발생: {str(e)}", 'error'))
            finally:
                self.is_processing = False
                self.root.after(0, lambda: self.extract_btn.configure(text="🚀 선택한 자막 추출"))
                self.root.after(0, lambda: self.progress_label.configure(text="완료"))

        threading.Thread(target=do_extract, daemon=True).start()

    def _stop_extract(self):
        """추출 작업을 중단합니다."""
        if hasattr(self, 'cancel_event') and self.is_processing:
            self.cancel_event.set()
            self.extract_btn.configure(text="⌛ 중단 대기 중")
            self._log("⏹️ 중단 신호 전송됨... 프로세스를 종료하고 있습니다.", 'warning')

    def _animate_progress(self, count=0):
