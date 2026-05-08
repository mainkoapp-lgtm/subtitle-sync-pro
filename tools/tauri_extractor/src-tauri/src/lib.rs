use tauri::{command, State, Manager, AppHandle, Emitter};
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader, AsyncWriteExt};
use std::os::windows::process::CommandExt;
use std::sync::{Arc, Mutex};
use serde_json::Value;
use std::path::{Path, PathBuf};

struct AppState {
    ffmpeg_pid: Mutex<Option<u32>>,
    cancelled: Arc<Mutex<bool>>,
}

// [완료] 로그 기록 헬퍼 - AppData/logs/app.log 에 기록 (임의 수정 금지)
async fn log_to_file(app: &AppHandle, message: &str) {
    if let Ok(app_dir) = app.path().app_log_dir() {
        let _ = tokio::fs::create_dir_all(&app_dir).await;
        let log_path = app_dir.join("app.log");
        let now = chrono::Local::now().format("%Y-%m-%d %H:%M:%S");
        let log_line = format!("[{}] {}\n", now, message);
        
        if let Ok(mut file) = tokio::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&log_path)
            .await 
        {
            let _ = file.write_all(log_line.as_bytes()).await;
        }
    }
    println!("{}", message);
}

fn get_ffmpeg_path(bin_name: &str) -> String {
    let exe_dir = std::env::current_exe().map(|p| p.parent().unwrap().to_path_buf()).unwrap_or_default();
    let current_dir = std::env::current_dir().unwrap_or_default();
    
    let base_dirs = vec![
        exe_dir.clone(),
        current_dir.clone(),
        current_dir.join("../subtitle_extractor"),
        current_dir.join("../../subtitle_extractor"),
        current_dir.join("../../../subtitle_extractor"),
        std::path::PathBuf::from(r#"d:\Project Temporary\subtitle\subtitle_development\tools\subtitle_extractor"#),
        std::path::PathBuf::from(r#"C:\"#),
        std::path::PathBuf::from(r#"C:\Program Files"#),
        std::path::PathBuf::from(r#"C:\Program Files (x86)"#),
        std::path::PathBuf::from(std::env::var("USERPROFILE").unwrap_or_default()),
    ];

    let mut paths = vec![];
    for b_dir in base_dirs {
        paths.push(b_dir.join("ffmpeg").join("bin").join(format!("{}.exe", bin_name)));
        paths.push(b_dir.join("ffmpeg").join(format!("{}.exe", bin_name)));
        paths.push(b_dir.join(format!("{}.exe", bin_name)));
    }

    for path in paths {
        if path.exists() {
            return path.to_string_lossy().to_string();
        }
    }
    
    bin_name.to_string()
}

// Function to generate a unique filename by appending (2), (3), etc. if it exists
fn get_unique_save_path(path: &str) -> String {
    let path_obj = Path::new(path);
    if !path_obj.exists() {
        return path.to_string();
    }

    let parent = path_obj.parent().unwrap_or(Path::new(""));
    let stem = path_obj.file_stem().unwrap_or_default().to_string_lossy();
    let extension = path_obj.extension().unwrap_or_default().to_string_lossy();
    
    let mut counter = 2;
    loop {
        let new_name = format!("{} ({}).{}", stem, counter, extension);
        let new_path = parent.join(new_name);
        if !new_path.exists() {
            return new_path.to_string_lossy().to_string();
        }
        counter += 1;
    }
}

#[command]
async fn probe_video(path: String) -> Result<String, String> {
    let output = Command::new(get_ffmpeg_path("ffprobe"))
        .args(&[
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-select_streams", "s",
            &path,
        ])
        .creation_flags(0x08000000)
        .output()
        .await
        .map_err(|e| format!("Failed to execute ffprobe: {}", e))?;

    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        return Err(format!("ffprobe error: {}", err));
    }

    let json_output = String::from_utf8_lossy(&output.stdout);
    let parsed: Value = serde_json::from_str(&json_output)
        .map_err(|e| format!("Invalid JSON from ffprobe: {}", e))?;
    
    let streams = parsed.get("streams").cloned().unwrap_or(serde_json::json!([]));
    Ok(streams.to_string())
}

// [완료] 자막 추출 메인 핸들러 - 비동기 I/O 및 정밀 진행률 파싱 적용 (임의 수정 금지)
#[command]
async fn extract_subtitle(app: AppHandle, video_path: String, track_index: i32, output_path: String, state: State<'_, AppState>) -> Result<String, String> {
    *state.cancelled.lock().unwrap() = false;
    let final_output_path = get_unique_save_path(&output_path);
    let extension = final_output_path.split('.').last().unwrap_or("srt");
    let output_codec = if final_output_path.ends_with(".srt") || final_output_path.ends_with(".ass") || final_output_path.ends_with(".vtt") { 
        extension
    } else { 
        "copy" 
    };

    let temp_name = format!("nas_safe_{}_{}.{}", track_index, std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis(), extension);
    let temp_path = std::env::temp_dir().join(&temp_name);
    let temp_path_str = temp_path.to_string_lossy().to_string();

    log_to_file(&app, &format!("Starting extraction: {} -> {}", video_path, final_output_path)).await;

    let mut child = Command::new(get_ffmpeg_path("ffmpeg"))
        .args(&[
            "-y",
            "-progress", "pipe:1",
            "-nostats",
            "-analyzeduration", "1000000",
            "-probesize", "1000000",
            "-i", &video_path,
            "-map", &format!("0:{}", track_index),
            "-c:s", output_codec,
            "-f", extension,
            &temp_path_str,
        ])
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .creation_flags(0x08000000)
        .spawn()
        .map_err(|e| format!("Failed to spawn ffmpeg: {}", e))?;

    let child_id = child.id().unwrap_or(0);
    *state.ffmpeg_pid.lock().unwrap() = Some(child_id);

    let duration_shared = Arc::new(Mutex::new(0.0));
    let duration_clone = Arc::clone(&duration_shared);
    
    if let Some(stderr) = child.stderr.take() {
        tauri::async_runtime::spawn(async move {
            let mut reader = BufReader::new(stderr).lines();
            while let Ok(Some(line)) = reader.next_line().await {
                if let Some(dur_idx) = line.find("Duration: ") {
                    let dur_str_part = &line[dur_idx + 10 ..];
                    if let Some(comma_idx) = dur_str_part.find(",") {
                        let time_str = dur_str_part[..comma_idx].trim();
                        let d = parse_ffmpeg_time(time_str);
                        if d > 0.0 {
                            let mut dur = duration_clone.lock().unwrap();
                            *dur = d;
                        }
                    }
                }
            }
        });
    }

    if let Some(stdout) = child.stdout.take() {
        let mut reader = BufReader::new(stdout).lines();
        let mut last_emit_time = std::time::Instant::now();
        
        while let Ok(Some(line)) = reader.next_line().await {
            if *state.cancelled.lock().unwrap() { break; }
            if line.starts_with("out_time_us=") {
                let us_str = &line[12..];
                if let Ok(us) = us_str.parse::<f64>() {
                    let current_time = us / 1_000_000.0;
                    let dur = *duration_shared.lock().unwrap();
                    
                    if dur > 0.0 {
                        let p = ((current_time / dur) * 100.0) as i32;
                        let p = p.clamp(0, 99);
                        if last_emit_time.elapsed().as_millis() > 200 {
                            app.emit("extract-progress", p).ok();
                            last_emit_time = std::time::Instant::now();
                        }
                    }
                }
            }
        }
    }

    let status = child.wait().await.map_err(|e| format!("Failed to wait for ffmpeg: {}", e))?;
    *state.ffmpeg_pid.lock().unwrap() = None;

    if status.success() {
        tokio::fs::copy(&temp_path_str, &final_output_path).await.map_err(|e| format!("Failed to copy file: {}", e))?;
        let _ = tokio::fs::remove_file(&temp_path_str).await;
        app.emit("extract-progress", 100).ok();
        Ok(format!("Successfully extracted to {}", final_output_path))
    } else {
        let _ = tokio::fs::remove_file(&temp_path_str).await;
        // [완료] 중단 처리 로직 - 프로세스 종료 및 결과값 반환 (임의 수정 금지)
        if *state.cancelled.lock().unwrap() {
            return Err("Cancelled".to_string());
        }
        Err("Extraction process failed".to_string())
    }
}

// [완료] 추출 중단 핸들러 - 개별 PID 타겟팅 및 비동기 종료 (임의 수정 금지)
// [완료] 추출 중단 핸들러 - taskkill 완료 대기 및 Mutex 방어 로직 적용 (임의 수정 금지)
#[command]
async fn stop_extraction(state: State<'_, AppState>) -> Result<(), String> {
    *state.cancelled.lock().unwrap() = true;
    let pid = state.ffmpeg_pid.lock().unwrap().take();
    if let Some(pid) = pid {
        println!("Stopping extraction for PID: {}", pid);
        let _ = Command::new("taskkill")
            .args(&["/F", "/PID", &pid.to_string()])
            .creation_flags(0x08000000)
            .output()
            .await;
    }
    Ok(())
}

fn parse_ffmpeg_time(time_str: &str) -> f64 {
    let parts: Vec<&str> = time_str.split(':').collect();
    if parts.len() == 3 {
        let h = parts[0].parse::<f64>().unwrap_or(0.0);
        let m = parts[1].parse::<f64>().unwrap_or(0.0);
        let s = parts[2].parse::<f64>().unwrap_or(0.0);
        return h * 3600.0 + m * 60.0 + s;
    }
    0.0
}

// [완료] PGS 자막 추출 핸들러 - 전 과정 PID 추적 및 즉각 중단 체크 적용 (임의 수정 금지)
#[command]
async fn extract_pgs_subtitle(app: AppHandle, video_path: String, track_index: i32, output_path: String, language: String, state: State<'_, AppState>) -> Result<String, String> {
    *state.cancelled.lock().unwrap() = false;
    let final_output_path = get_unique_save_path(&output_path);
    let temp_dir = std::env::temp_dir().join(format!("subfast_ocr_{}", uuid::Uuid::new_v4()));
    let _ = std::fs::create_dir_all(&temp_dir);
    
    log_to_file(&app, &format!("PGS extraction started: {} -> {}", video_path, final_output_path)).await;

    if *state.cancelled.lock().unwrap() { return Err("Cancelled".to_string()); }

    // 1. Get timestamps using ffprobe
    let mut ffprobe_child = Command::new(get_ffmpeg_path("ffprobe"))
        .args(&["-v", "error", "-select_streams", &format!("{}", track_index), "-show_packets", "-show_entries", "packet=pts_time,duration_time", "-of", "json", &video_path])
        .stdout(std::process::Stdio::piped())
        .creation_flags(0x08000000)
        .spawn()
        .map_err(|e| format!("ffprobe 실행 실패: {}", e))?;

    let ffprobe_id = ffprobe_child.id().unwrap_or(0);
    *state.ffmpeg_pid.lock().unwrap() = Some(ffprobe_id);

    let is_cancelled = *state.cancelled.lock().unwrap();
    if is_cancelled {
        let _ = Command::new("taskkill").args(&["/F", "/PID", &ffprobe_id.to_string()]).creation_flags(0x08000000).output().await;
        return Err("Cancelled".to_string());
    }

    let ffprobe_output = ffprobe_child.wait_with_output().await.map_err(|e| format!("ffprobe 대기 실패: {}", e))?;
    *state.ffmpeg_pid.lock().unwrap() = None;

    if *state.cancelled.lock().unwrap() { return Err("Cancelled".to_string()); }

    let json: serde_json::Value = serde_json::from_slice(&ffprobe_output.stdout).map_err(|e| format!("JSON 파싱 실패: {}", e))?;
    let packets = json["packets"].as_array().ok_or("패킷 정보를 찾을 수 없습니다.")?;
    log_to_file(&app, &format!("Total packets found: {}", packets.len())).await;

    // 2. Extract frames
    let png_pattern = temp_dir.join("frame_%05d.png").to_string_lossy().to_string();
    let mut child = Command::new(get_ffmpeg_path("ffmpeg"))
        .args(&[
            "-y", 
            "-progress", "pipe:1",
            "-i", &video_path, 
            "-filter_complex", &format!("[0:{}]format=rgba,alphaextract,negate", track_index), 
            "-vsync", "0", 
            &png_pattern
        ])
        .stdout(std::process::Stdio::piped())
        .creation_flags(0x08000000)
        .spawn()
        .map_err(|e| format!("FFmpeg 실행 실패: {}", e))?;

    let child_id = child.id().unwrap_or(0);
    *state.ffmpeg_pid.lock().unwrap() = Some(child_id);

    let is_cancelled = *state.cancelled.lock().unwrap();
    if is_cancelled {
        let _ = Command::new("taskkill").args(&["/F", "/PID", &child_id.to_string()]).creation_flags(0x08000000).output().await;
        return Err("Cancelled".to_string());
    }

    let total_packets = packets.len() as f64;
    
    if let Some(stdout) = child.stdout.take() {
        let mut reader = BufReader::new(stdout).lines();
        let mut last_emit_time = std::time::Instant::now();
        while let Ok(Some(line)) = reader.next_line().await {
            if *state.cancelled.lock().unwrap() { break; }
            if line.starts_with("frame=") {
                let frame_str = &line[6..];
                if let Ok(frame) = frame_str.trim().parse::<f64>() {
                    let mut p = ((frame / total_packets) * 30.0) as i32;
                    p = p.clamp(0, 30);
                    if last_emit_time.elapsed().as_millis() > 500 {
                        app.emit("extract-progress", serde_json::json!({"status": "extracting", "percentage": p, "message": format!("영상을 분석 중입니다... ({}%)", p)})).ok();
                        last_emit_time = std::time::Instant::now();
                    }
                }
            }
        }
    }
    let _ = child.wait().await;
    *state.ffmpeg_pid.lock().unwrap() = None;

    if *state.cancelled.lock().unwrap() {
        let _ = tokio::fs::remove_dir_all(&temp_dir).await;
        return Err("Cancelled".to_string());
    }

    // 3. List PNGs
    let mut png_files = Vec::new();
    let mut entries = tokio::fs::read_dir(&temp_dir).await.map_err(|e| e.to_string())?;
    while let Ok(Some(entry)) = entries.next_entry().await {
        let path = entry.path();
        if path.extension().and_then(|s: &std::ffi::OsStr| s.to_str()) == Some("png") {
            png_files.push(path);
        }
    }
    png_files.sort();
    let total_png = png_files.len();
    if total_png == 0 { return Err("이미지 추출 실패".to_string()); }

    // 4. Tesseract Setup
    let tesseract_dir = app.path().resolve("resources/tesseract", tauri::path::BaseDirectory::Resource)
        .map_err(|e| format!("리소스 경로 해결 실패: {}", e))?;
    let tess_dir_clean = tesseract_dir.to_string_lossy().replace("\\\\?\\", "");
    let tesseract_cmd = std::path::Path::new(&tess_dir_clean).join("tesseract.exe").to_string_lossy().to_string();
    let tessdata_path = std::path::Path::new(&tess_dir_clean).join("tessdata").to_string_lossy().to_string();
    let tess_lang = if language == "한국어" { "kor" } else { "eng" };

    // 5. OCR & Grouping
    let mut subtitles = Vec::new();
    let mut current_text = String::new();
    let mut current_start = 0.0;
    
    for (i, png_path) in png_files.iter().enumerate() {
        let frame_idx = i + 1;
        let out_base = temp_dir.join(format!("out_{:05}", frame_idx));
        
        if *state.cancelled.lock().unwrap() {
            let _ = tokio::fs::remove_dir_all(&temp_dir).await;
            return Err("Cancelled".to_string());
        }

        let mut ocr_child = Command::new(&tesseract_cmd)
            .args(&[
                png_path.to_str().unwrap_or(""), 
                out_base.to_str().unwrap_or(""), 
                "-l", 
                tess_lang, 
                "--tessdata-dir", 
                tessdata_path.as_str(), 
                "--psm", 
                "6"
            ])
            .env("TESSDATA_PREFIX", &tessdata_path)
            .creation_flags(0x08000000)
            .spawn()
            .map_err(|e| format!("Tesseract 실행 실패: {}", e))?;

        let ocr_pid = ocr_child.id().unwrap_or(0);
        *state.ffmpeg_pid.lock().unwrap() = Some(ocr_pid);
        
        let is_cancelled = *state.cancelled.lock().unwrap();
        if is_cancelled {
            let _ = Command::new("taskkill").args(&["/F", "/PID", &ocr_pid.to_string()]).creation_flags(0x08000000).output().await;
            let _ = tokio::fs::remove_dir_all(&temp_dir).await;
            return Err("Cancelled".to_string());
        }

        let _ = ocr_child.wait().await;
        *state.ffmpeg_pid.lock().unwrap() = None;

        let txt_path = out_base.with_extension("txt");
        let text = std::fs::read_to_string(&txt_path).unwrap_or_default().trim().to_string();
        
        let p_idx = (i * packets.len()) / total_png;
        let pts = packets[p_idx]["pts_time"].as_str().unwrap_or("0").parse::<f64>().unwrap_or(0.0);

        if !text.is_empty() {
            if text != current_text {
                if !current_text.is_empty() {
                    subtitles.push((current_start, pts, current_text.clone()));
                }
                current_text = text;
                current_start = pts;
            }
        } else if !current_text.is_empty() {
            subtitles.push((current_start, pts, current_text.clone()));
            current_text = String::new();
        }

        let mut p = 30 + ((frame_idx as f64 / total_png as f64) * 70.0) as i32;
        p = p.clamp(30, 100);
        if frame_idx % 50 == 0 || frame_idx == total_png {
            let _ = app.emit("extract-progress", serde_json::json!({"status": "ocr_processing", "percentage": p, "message": format!("OCR 변환 중... ({}/{})", frame_idx, total_png)}));
        }
    }

    // 6. Finalize SRT
    let mut srt = String::new();
    for (idx, (start, end, txt)) in subtitles.iter().enumerate() {
        let end_t = if *end <= *start { start + 1.0 } else { *end };
        srt.push_str(&format!("{}\n{} --> {}\n{}\n\n", idx + 1, format_srt_time(*start), format_srt_time(end_t), txt));
    }

    std::fs::write(&final_output_path, srt).map_err(|e| e.to_string())?;
    log_to_file(&app, &format!("Completed: {}", final_output_path)).await;
    app.emit("extract-progress", serde_json::json!({"status": "completed", "percentage": 100, "message": "추출 완료!"})).ok();
    
    Ok(final_output_path)
}

fn format_srt_time(seconds: f64) -> String {
    let total_ms = (seconds * 1000.0) as u64;
    let h = total_ms / 3600000;
    let m = (total_ms % 3600000) / 60000;
    let s = (total_ms % 60000) / 1000;
    let ms = total_ms % 1000;
    format!("{:02}:{:02}:{:02},{:03}", h, m, s, ms)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            ffmpeg_pid: Mutex::new(None),
            cancelled: Arc::new(Mutex::new(false)),
        })
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![probe_video, extract_subtitle, stop_extraction, extract_pgs_subtitle])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
