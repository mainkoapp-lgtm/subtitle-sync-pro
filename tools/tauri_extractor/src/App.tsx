import { useState, useEffect, DragEvent, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import { open } from "@tauri-apps/plugin-dialog";
import { openUrl } from "@tauri-apps/plugin-opener";
import { useTranslation } from "react-i18next";
import { FileVideo, Download, Loader2, Settings, X, Square } from "lucide-react";
import "./App.css";

interface Track {
  index: number;
  codec_name: string;
  is_text_based?: boolean;
  tags?: {
    language?: string;
  };
}

interface RemoteConfig {
  latest_version?: string;
  min_version?: string;
  notice?: {
    active: boolean;
    title: string;
    content: string;
  };
  ad_config?: {
    active: boolean;
    image_url: string;
    html_url?: string;
    target_url: string;
    cf_tracker_url: string;
    ad_id?: string;
  };
}

const CONFIG_URL = "https://subfast-manager.web.app/latest_version.json";
const CURRENT_VERSION = "0.2.0";

function App() {
  const { t, i18n } = useTranslation();
  
  const [videoPath, setVideoPath] = useState("");
  const [tracks, setTracks] = useState<Track[]>([]);
  const [selectedTracks, setSelectedTracks] = useState<Set<number>>(new Set());
  
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const isCancelled = useRef(false);
  const [isDone, setIsDone] = useState(false);
  const [outputFormat, setOutputFormat] = useState("srt");
  const [progressMsg, setProgressMsg] = useState("");
  const [progressPercent, setProgressPercent] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  
  // OCR Options
  const [ocrLanguage, setOcrLanguage] = useState("한국어");
  
  // Save Location Config
  const [saveToSameFolder, setSaveToSameFolder] = useState(true);
  const [customSavePath, setCustomSavePath] = useState("");
  
  // Modals & Config
  const [showSettings, setShowSettings] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [lastResult, setLastResult] = useState({ success: 0, total: 0 });
  const [config, setConfig] = useState<RemoteConfig | null>(null);
  const [showNotice, setShowNotice] = useState(false);
  const [showLicenseModal, setShowLicenseModal] = useState(false);
  const [killSwitch, setKillSwitch] = useState(false);

  useEffect(() => {
    let unlisten: UnlistenFn | undefined;
    const setupListener = async () => {
      unlisten = await listen<{status: string, percentage: number, message: string}>("extract-progress", (event) => {
        // [완료] 진행률 리스너 - 중단 요청 시 이벤트 무시 로직 적용 (임의 수정 금지)
        if (isCancelled.current) return;
        const { percentage, message } = event.payload;
        setProgressPercent(percentage);
        if (message) setProgressMsg(message);
      });
    };
    setupListener();

    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  useEffect(() => {
    // Message listener for iframe clicks
    const handleMessage = async (event: MessageEvent) => {
      if (event.data && event.data.type === 'open_url' && event.data.url) {
        try {
          await openUrl(event.data.url);
        } catch (e) {
          console.error("URL Open Error:", e);
        }
      }
    };
    window.addEventListener('message', handleMessage);

    // Fetch remote config (캐시 방지를 위해 타임스탬프 추가)
    fetch(`${CONFIG_URL}?t=${Date.now()}`)
      .then(r => r.json())
      .then((data: RemoteConfig) => {
        setConfig(data);
        
        // Kill switch logic
        const minVer = parseFloat(data.min_version || "0.01");
        const curVer = parseFloat(CURRENT_VERSION);
        if (curVer < minVer) {
          setKillSwitch(true);
        }
        
        // Notice logic
        if (data.notice?.active) {
          setShowNotice(true);
        }
      })
      .catch(console.error);

    return () => window.removeEventListener('message', handleMessage);
  }, []);

  useEffect(() => {
    // 자동 언어 선택 로직
    const pgsTracks = Array.from(selectedTracks).filter(idx => {
      const tr = tracks.find(x => x.index === idx);
      return tr && !tr.is_text_based && tr.codec_name?.includes("pgs");
    });
    
    if (pgsTracks.length > 0) {
      const firstPgsTrack = tracks.find(x => x.index === pgsTracks[0]);
      const lang = firstPgsTrack?.tags?.language?.toLowerCase();
      if (lang === 'eng') {
        setOcrLanguage("영어");
      } else if (lang === 'kor') {
        setOcrLanguage("한국어");
      }
    }
  }, [selectedTracks, tracks]);

  const resetApp = () => {
    setVideoPath("");
    setTracks([]);
    setSelectedTracks(new Set());
    setIsDone(false);
    setProgressPercent(0);
    setProgressMsg("");
  };

  async function handleFile(path: string) {
    setVideoPath(path);
    setLoading(true);
    setIsDone(false);
    setTracks([]);
    setSelectedTracks(new Set());
    
    try {
      const result: string = await invoke("probe_video", { path });
      const parsed: Track[] = JSON.parse(result);
      setTracks(parsed);
      // Select only the first track by default
      if (parsed.length > 0) {
        setSelectedTracks(new Set([parsed[0].index]));
      }
    } catch (e: any) {
      console.error(e);
      alert(t('msg_error_occurred', { error: String(e) }));
    } finally {
      setLoading(false);
    }
  }

  async function selectVideo() {
    const selected = await open({
      multiple: false,
      filters: [{ name: "Video", extensions: ["mp4", "mkv", "avi", "mov", "webm"] }],
    });
    if (selected && typeof selected === "string") {
      handleFile(selected);
    }
  }

  // Handle Drag & Drop (Tauri injects physical path into File object)
  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };
  const onDragLeave = () => setDragActive(false);
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0] as any;
      if (file.path) {
        handleFile(file.path);
      }
    }
  };

  const toggleTrack = (index: number) => {
    const next = new Set(selectedTracks);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setSelectedTracks(next);
  };

  const selectAll = (select: boolean) => {
    if (select) setSelectedTracks(new Set(tracks.map(t => t.index)));
    else setSelectedTracks(new Set());
  };

  const selectTextOnly = () => {
    const textCodecs = ["subrip", "ass", "webvtt", "mov_text"];
    const textTracks = tracks.filter(t => textCodecs.includes(t.codec_name?.toLowerCase()));
    setSelectedTracks(new Set(textTracks.map(t => t.index)));
  };

  async function pickSaveDirectory() {
    const selected = await open({
      directory: true,
      multiple: false,
    });
    if (selected && typeof selected === "string") {
      setCustomSavePath(selected);
    }
  }

  async function startBatchExtraction() {
    if (!videoPath || selectedTracks.size === 0) {
      alert(t('msg_select_track'));
      return;
    }

    if (!saveToSameFolder && !customSavePath) {
      alert(t('msg_select_folder_first', { defaultValue: "Please select a destination folder first." }));
      return;
    }
    
    setExtracting(true);
    setStopping(false);
    isCancelled.current = false;
    setIsDone(false);
    setProgressPercent(0);
    let successCount = 0;
    const totalCount = selectedTracks.size;
    const selectedArray = Array.from(selectedTracks);
    
    for (let i = 0; i < selectedArray.length; i++) {
      if (isCancelled.current) break;
      const trackIdx = selectedArray[i];
      setProgressMsg(`${t('msg_extract_start', { count: totalCount })} (${i + 1}/${totalCount})`);
      
      const track = tracks.find(t => t.index === trackIdx);
      if (!track) continue;
      
      let ext = outputFormat; // Start with requested format
      
      // If it's an image track, we must use sup/sub regardless of requested format
      if (!track.is_text_based) {
        if (track.codec_name?.includes("pgs")) {
            ext = "srt"; // OCR process will output SRT
        } else {
            ext = track.codec_name?.includes("dvd") ? "sub" : "srt";
        }
      }

      const lang = track.tags?.language || 'und';
      const fileNameRaw = videoPath.split(/[\\/]/).pop() || "output";
      const fileNameNoExt = fileNameRaw.substring(0, fileNameRaw.lastIndexOf("."));
      const outName = `${fileNameNoExt}_t${trackIdx}_${lang}.${ext}`;

      let outputPath = "";
      if (saveToSameFolder) {
        outputPath = videoPath.substring(0, videoPath.lastIndexOf(".")) + `_t${trackIdx}_${lang}.${ext}`;
      } else {
        // Construct path for custom folder
        outputPath = customSavePath + (customSavePath.endsWith("\\") || customSavePath.endsWith("/") ? "" : "\\") + outName;
      }
      
      try {
        let invokeCmd = "extract_subtitle";
        let invokeArgs: any = { 
          videoPath: videoPath, 
          trackIndex: trackIdx, 
          outputPath: outputPath 
        };

        if (!track.is_text_based && track.codec_name?.includes("pgs")) {
          invokeCmd = "extract_pgs_subtitle";
          invokeArgs.language = ocrLanguage;
        }

        await invoke(invokeCmd, invokeArgs);
        successCount++;
      } catch (e: any) {
        if (e && typeof e === 'string' && e.includes("Cancelled")) {
           break;
        }
        console.error(`Failed track ${trackIdx}:`, e);
      }
    }
    
    if (isCancelled.current) {
        setProgressMsg(t('msg_extract_cancelled', { defaultValue: "사용자에 의해 추출이 중단되었습니다." }));
    } else {
        if (successCount === totalCount) {
             setProgressPercent(100);
             setProgressMsg(t('msg_extract_done_title', { defaultValue: "100% 추출 완료" }));
        } else if (successCount > 0) {
             setProgressPercent(100);
             setProgressMsg(`완료 (일부 실패: ${successCount}/${totalCount})`);
        } else {
             setProgressPercent(0);
             setProgressMsg("추출 실패 (로그를 확인해주세요)");
        }
    }
    
    setLastResult({ success: successCount, total: totalCount });
    setShowToast(true);
    setIsDone(true);
    setExtracting(false);
    setStopping(false);
    
    // Hide toast after 4 seconds
    setTimeout(() => {
      setShowToast(false);
    }, 4000);
  }

  const handleStopExtraction = async () => {
    isCancelled.current = true;
    setStopping(true);
    setProgressMsg(t('btn_waiting', { defaultValue: "⌛ 중단 대기 중" }));
    try {
      await invoke("stop_extraction");
    } catch (e) {
      console.error(e);
    }
  };

  const changeLang = (l: string) => {
    i18n.changeLanguage(l);
    localStorage.setItem('appLanguage', l);
  };

  // Rendering Kill Switch
  if (killSwitch) {
    return (
      <div className="modal-overlay force-centered">
        <div className="modal-content kill-switch">
          <h2>{t('update_required')}</h2>
          <p>{t('update_msg', { current: CURRENT_VERSION, latest: config?.latest_version })}</p>
          <button className="btn-primary" onClick={() => openUrl("https://subtitle.mainko.net/")}>
            {t('btn_download')}
          </button>
        </div>
      </div>
    );
  }

  const hasPgsSelected = Array.from(selectedTracks).some(idx => {
    const tr = tracks.find(x => x.index === idx);
    return tr && !tr.is_text_based && tr.codec_name?.includes("pgs");
  });

  return (
    <div 
      className={`container ${dragActive ? "drag-active" : ""}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {dragActive && (
        <div className="drag-overlay">
          <FileVideo size={64} className="spinning-slow" />
          <h2>{t('drag_drop_hint')}</h2>
        </div>
      )}

      <header className="app-header">
        <div className="header-left">
          <h1>{t('header_title')}</h1>
          <span className="version-badge">v{CURRENT_VERSION}</span>
        </div>
        <button className="btn-icon" onClick={() => setShowSettings(true)}>
          <Settings size={20} /> {t('btn_settings')}
        </button>
      </header>

      <main>
        <div className="action-bar">
          <button 
            onClick={selectVideo} 
            className="btn-primary" 
            disabled={loading || extracting}
          >
            {loading ? <Loader2 className="spinning" size={20} /> : <FileVideo size={20} />}
            {loading ? "..." : t('btn_select_file')}
          </button>
        </div>

        {videoPath && (
          <div className="tracks-container">
            <div className="tracks-header">
              <h3>{videoPath.split('\\').pop()?.split('/').pop()}</h3>
              <div className="track-controls">
                <button className="btn-sm" onClick={() => selectAll(true)}>{t('btn_select_all')}</button>
                <button className="btn-sm" onClick={() => selectAll(false)}>{t('btn_deselect_all')}</button>
                <button className="btn-sm" onClick={selectTextOnly}>{t('btn_select_text')}</button>
              </div>
            </div>

            {tracks.length === 0 && !loading ? (
              <p className="empty-text">No subtitle tracks found in this video.</p>
            ) : (
              <ul className="tracks-list">
                {tracks.map((track) => (
                  <li key={track.index} className="track-item" onClick={() => toggleTrack(track.index)}>
                    <label className="checkbox-container" onClick={(e) => e.preventDefault()}>
                      <input 
                        type="checkbox" 
                        checked={selectedTracks.has(track.index)}
                        readOnly
                      />
                      <span className="checkmark"></span>
                      <span className="track-info">
                        Track #{track.index} <span className="codec-badge">{track.codec_name}</span> - {track.tags?.language?.toUpperCase() || "UND"}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

      </main>

      {/* Footer Controls & Ad Banner */}
      <footer className="app-footer">
        {videoPath && tracks.length > 0 && (
          <div className="extract-bar">
            {extracting || isDone ? (
              <div className="progress-container">
                <div className="progress-labels">
                  <span className="progress-text">{progressMsg}</span>
                  <span className="progress-percent">{progressPercent}%</span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${progressPercent}%` }}></div>
                </div>
              </div>
            ) : (
              <div className="extract-options-row">
                <div className="format-selector-group">
                  <span className="save-label">{t('label_format')}</span>
                  <select 
                    className="select-format" 
                    value={outputFormat} 
                    onChange={(e) => setOutputFormat(e.target.value)}
                  >
                    <option value="srt">srt</option>
                    <option value="ass">ass</option>
                    <option value="vtt">webvtt</option>
                  </select>
                </div>
                
                {hasPgsSelected && (
                  <div className="format-selector-group ocr-group">
                    <span className="save-label" style={{ color: "#a855f7" }}>OCR 언어</span>
                    <select 
                      className="select-format" 
                      value={ocrLanguage} 
                      onChange={(e) => setOcrLanguage(e.target.value)}
                      style={{ borderColor: "#a855f7" }}
                    >
                      <option value="한국어">한국어 (Korean)</option>
                      <option value="영어">영어 (English)</option>
                    </select>
                  </div>
                )}

                <div className="save-options">
                  <div className="radio-group">
                    <label className="radio-item">
                      <input type="radio" checked={saveToSameFolder} onChange={() => setSaveToSameFolder(true)} />
                      <span>{t('radio_same_folder')}</span>
                    </label>
                    <label className="radio-item">
                      <input type="radio" checked={!saveToSameFolder} onChange={() => setSaveToSameFolder(false)} />
                      <span>{t('radio_custom_folder')}</span>
                    </label>
                  </div>
                  {!saveToSameFolder && (
                    <button className="btn-sm btn-folder" onClick={pickSaveDirectory}>
                      {customSavePath ? customSavePath.split(/[\\/]/).pop() : "..."}
                    </button>
                  )}
                </div>
              </div>
            )}
            
            <button 
              className={`btn-extract btn-primary action ${extracting ? 'btn-danger' : ''}`} 
              onClick={extracting ? handleStopExtraction : (isDone ? resetApp : startBatchExtraction)}
              disabled={(selectedTracks.size === 0 && !extracting && !isDone) || stopping}
              style={extracting ? { background: '#ef4444' } : {}}
            >
              {extracting ? (
                 stopping ? <><Loader2 size={20} className="spinning" /> {t('btn_waiting')}</> : <><Square size={20} /> {t('btn_stop')}</>
              ) : isDone ? (
                 <>🔄 {t('btn_reset', { defaultValue: '새로운 작업 시작 (초기화)' })}</>
              ) : (
                 <><Download size={20} /> {t('btn_extract')}</>
              )}
            </button>
          </div>
        )}

        <div className="ad-container">
          {/* [완료] 배너 클릭 이동 이슈 해결 - 투명 오버레이 방식 적용 (2026-04-22) 
              Tauri 보안 정책 및 Cross-Origin 문제를 우회하기 위해 오버레이 클릭 방식을 사용함. 임의 수정 금지. */}
          {config?.ad_config?.active ? (
            config.ad_config.html_url ? (
              <div style={{ position: 'relative', width: '100%', height: '100%' }}>
                <iframe 
                  src={config.ad_config.html_url} 
                  className="dynamic-banner"
                  frameBorder="0" 
                  scrolling="no"
                  title="Advertisement Banner"
                  sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-same-origin"
                  style={{ pointerEvents: 'none' }}
                />
                <div 
                  style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', cursor: 'pointer', zIndex: 10 }}
                  onClick={async () => {
                    const target = config.ad_config?.target_url || "https://flowstate-timer.netlify.app/";
                    const tracker = config.ad_config?.cf_tracker_url;
                    const trackUrl = tracker 
                      ? tracker + "/click?ad_id=" + (config.ad_config?.ad_id || "flowstate_timer_v1") + "&target=" + encodeURIComponent(target)
                      : target;
                    try {
                      await openUrl(trackUrl);
                    } catch (e) {
                      console.error("Overlay click error:", e);
                      await openUrl(target);
                    }
                  }}
                />
              </div>
            ) : config.ad_config.image_url ? (
              <div 
                style={{ cursor: 'pointer' }}
                onClick={async () => {
                  const target = config.ad_config?.target_url || "https://flowstate-timer.netlify.app/";
                  const tracker = config.ad_config?.cf_tracker_url;
                  const trackUrl = tracker 
                    ? tracker + "/click?ad_id=" + (config.ad_config?.ad_id || "flowstate_timer_v1") + "&target=" + encodeURIComponent(target)
                    : target;
                  try {
                    await openUrl(trackUrl);
                  } catch (e) {
                    console.error("Banner click error:", e);
                    await openUrl(target);
                  }
                }}
              >
                <img src={config.ad_config.image_url} alt="Advertisement" className="dynamic-banner" />
              </div>
            ) : (
              <iframe 
                src="/banner/index.html" 
                className="dynamic-banner"
                frameBorder="0" 
                scrolling="no"
                title="Fallback Advertisement"
              />
            )
          ) : (
             <iframe 
               src="/banner/index.html" 
               className="dynamic-banner"
               frameBorder="0" 
               scrolling="no"
               title="Fallback Advertisement"
               sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-same-origin"
             />
          )}
        </div>
      </footer>

      {/* Settings Modal */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('settings_title')}</h2>
              <button className="btn-close" onClick={() => setShowSettings(false)}><X size={20} /></button>
            </div>
            
            <div className="settings-group">
              <label>{t('label_language')}</label>
              <select value={i18n.language} onChange={(e) => changeLang(e.target.value)}>
                <option value="ko">한국어</option>
                <option value="en">English</option>
                <option value="ja">日本語</option>
                <option value="zh">中文</option>
                <option value="hi">हिन्दी</option>
              </select>
            </div>

            <button className="btn-link homepage-link" onClick={() => openUrl("https://subtitle.mainko.net")}>
              {t('btn_visit_home')}
            </button>

            <button className="btn-link license-link" onClick={() => setShowLicenseModal(true)}>
              {t('btn_license')}
            </button>
          </div>
        </div>
      )}

      {/* License Modal */}
      {showLicenseModal && (
        <div className="modal-overlay" onClick={() => setShowLicenseModal(false)}>
          <div className="modal-content license-modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{t('license_title')}</h2>
              <button className="btn-close" onClick={() => setShowLicenseModal(false)}><X size={20} /></button>
            </div>
            <div className="license-text-area">
              <h3>Tesseract OCR</h3>
              <pre>
                Apache License Version 2.0, January 2004
                http://www.apache.org/licenses/
                Copyright (c) Ray Smith
              </pre>
              <hr />
              <h3>FFmpeg</h3>
              <pre>
                Licensed under LGPL v2.1 or later.
                http://www.ffmpeg.org/
              </pre>
              <hr />
              <h3>Tauri</h3>
              <pre>
                MIT License / Apache License 2.0
                Copyright (c) Tauri Programme
              </pre>
              <hr />
              <h3>React</h3>
              <pre>
                MIT License
                Copyright (c) Meta Platforms, Inc. and affiliates.
              </pre>
            </div>
            <button className="btn-primary" style={{ width: '100%', marginTop: '20px' }} onClick={() => setShowLicenseModal(false)}>
              {t('license_close')}
            </button>
          </div>
        </div>
      )}

      {/* Notice Modal */}
      {showNotice && config?.notice && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h2>{t('notice_title')}</h2>
            </div>
            <h3 className="notice-heading">{config.notice.title}</h3>
            <p className="notice-body">{config.notice.content}</p>
            <button className="btn-primary" onClick={() => setShowNotice(false)}>OK</button>
          </div>
        </div>
      )}

      {/* Toast Message */}
      {showToast && (
        <div className="toast-container animation-slide-up">
           <div className={`toast-content ${isCancelled.current ? 'cancelled' : ''}`}>
             <p>
               {isCancelled.current 
                 ? t('msg_extract_cancelled', { defaultValue: "사용자에 의해 추출이 중단되었습니다." })
                 : t('msg_extract_done', { success: lastResult.success, total: lastResult.total })}
             </p>
           </div>
        </div>
      )}

    </div>
  );
}

export default App;
