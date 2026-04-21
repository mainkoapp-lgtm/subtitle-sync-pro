use tauri::{command, State, Manager, AppHandle, Emitter};
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader};
use std::os::windows::process::CommandExt;
use std::sync::{Arc, Mutex};
use serde_json::Value;
use std::path::Path;

struct AppState {
    ffmpeg_pid: Mutex<Option<u32>>,
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
    // Generate unique path if exists
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

    println!("Starting extraction: {} -> {}", video_path, final_output_path);

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
        Err("Extraction process failed".to_string())
    }
}

// [완료] 추출 중단 핸들러 - 개별 PID 타겟팅 및 비동기 종료 (임의 수정 금지)
#[command]
async fn stop_extraction(state: State<'_, AppState>) -> Result<(), String> {
    if let Some(pid) = state.ffmpeg_pid.lock().unwrap().take() {
        println!("Stopping extraction for PID: {}", pid);
        let _ = Command::new("taskkill")
            .args(&["/F", "/PID", &pid.to_string()])
            .creation_flags(0x08000000)
            .spawn()
            .ok();
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            ffmpeg_pid: Mutex::new(None),
        })
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![probe_video, extract_subtitle, stop_extraction])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
