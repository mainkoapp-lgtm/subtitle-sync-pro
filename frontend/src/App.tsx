/** [COMPLETED: 2026-04-02] API Key 가시화 및 로깅 마스킹 제거 완료 (임의 수정 금지) */
import { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, CheckCircle, AlertCircle, RefreshCcw, Download, Copy, XCircle } from 'lucide-react';

const KoreanLangIcon = ({ size, color }: { size: number, color: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <text x="3" y="15" fontSize="14" fontWeight="bold" stroke="none" fill={color} fontFamily="sans-serif">가</text>
    <path d="m22 22-5-10-5 10"/>
    <path d="M14 18h6"/>
  </svg>
);
import { useTranslation, setLanguage, Language } from './i18n';
import './App.css';
import CoupangDynamicBanner from './components/CoupangDynamicBanner';

// 백엔드 API 주소 설정 (Render)
axios.defaults.baseURL = import.meta.env.VITE_API_URL || '';

interface TrafficLog {
  id: number;
  visitorId: string;
  source: string;
  referrer: string;
  country: string;
  device: string;
  date: string;
  timestamp: number;
}

interface SubtitleBlock {
  index: number;
  start: string;
  end: string;
  text: string;
}

interface SyncResult {
  matched: boolean;
  ref_index: number;
  target_index: number | null;
  ref: SubtitleBlock;
  target: SubtitleBlock | null;
  score: number;
  new_start: string;
  new_end: string;
  translated?: boolean;
}

// 광고 사이드바 컴포넌트 (App 외부로 이동하여 리렌더링 시 언마운트 방지)
const AdSidebar = ({ side }: { side: 'left' | 'right' }) => (
  <div className={`ad-sidebar ad-sidebar-${side}`} style={{ padding: '0', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
    <span className="ad-label" style={{ padding: '10px 0 0' }}>ADVERTISEMENT</span>
    <div style={{ flex: 1, width: '100%', display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
      <CoupangDynamicBanner id={side === 'left' ? 981842 : 981849} width="160" height="600" template="carousel" />
    </div>
  </div>
);

function App() {
  const { t, lang } = useTranslation();
  const [refFile, setRefFile] = useState<File | null>(null);
  const [targetFile, setTargetFile] = useState<File | null>(null);
  const [isRefDragging, setIsRefDragging] = useState(false);
  const [isTargetDragging, setIsTargetDragging] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(0);
  const [results, setResults] = useState<SyncResult[]>([]);
  const [apiKey, setApiKey] = useState<string>(localStorage.getItem('gemini_api_key') || '');
  const [aiModel] = useState<string>('gemini-3.1-flash-lite-preview');
  const [logs, setLogs] = useState<string>('');
  const [showLogs, setShowLogs] = useState(false);
  const [toast, setToast] = useState<{message: string, type: 'success' | 'error'} | null>(null);
  const [displayLimit, setDisplayLimit] = useState(100);
  const [fileMismatchWarning, setFileMismatchWarning] = useState<string | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);
  const [guideTab, setGuideTab] = useState<'web' | 'ext'>('web');
  const [showContact, setShowContact] = useState(false);
  const [isProduction, setIsProduction] = useState(false);
  const [showAdModal, setShowAdModal] = useState(false);
  const [adCountdown, setAdCountdown] = useState(5);
  const [adStatus, setAdStatus] = useState<'idle' | 'loading' | 'ready' | 'failed'>('idle');
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(false);

  // 서버 설정 가져오기 (운영 모드 확인)
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await axios.get('/api/config');
        setIsProduction(res.data.isProduction);
      } catch (e) {
        console.error("서버 설정을 불러오는데 실패했습니다.", e);
      }
    };
    fetchConfig();
  }, []);

  const handleContactSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const data = {
      name: formData.get('name'),
      email: formData.get('email'),
      type: formData.get('type'), // 협찬 or 문의
      message: formData.get('message'),
    };
    try {
      await axios.post('/api/contact', data);
      showToast('문의가 성공적으로 전송되었습니다.', 'success');
      setShowContact(false);
    } catch (err) {
      showToast('전송 실패. 잠시 후 다시 시도해주세요.', 'error');
    }
  };

  // [수집] 방문자 유입 정보 추적 (기존 Homepage Manager 솔루션 로직 본 앱 이식)
  useEffect(() => {
    if (sessionStorage.getItem('tracked_visit')) return;

    const trackVisit = async () => {
      let visitorId = localStorage.getItem('visitor_id');
      if (!visitorId) {
        visitorId = Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
        localStorage.setItem('visitor_id', visitorId);
      }

      const referrer = document.referrer;
      const ua = navigator.userAgent.toLowerCase();
      let source = 'direct';
      
      if (referrer.includes('naver.com')) source = 'naver';
      else if (referrer.includes('google.com')) source = 'google';
      else if (referrer.includes('instagram.com')) source = 'instagram';
      else if (ua.includes('kakaotalk')) source = 'kakao';
      else if (referrer) source = 'referral';

      let country = 'Unknown';
      try {
        const res = await fetch('https://ipapi.co/json/');
        const data = await res.json();
        country = data.country_name || 'Unknown';
        
        const countryCode = data.country_code || '';
        let detectedLang: Language = 'en';
        if (countryCode === 'KR') detectedLang = 'ko';
        else if (countryCode === 'JP') detectedLang = 'ja';
        else if (['CN', 'TW', 'HK'].includes(countryCode)) detectedLang = 'zh';
        else if (countryCode === 'IN') detectedLang = 'hi';
        
        if (detectedLang === 'en') {
          const navLang = navigator.language.substring(0, 2);
          if (['ko', 'ja', 'zh', 'hi'].includes(navLang)) {
            detectedLang = navLang as Language;
          }
        }
        setLanguage(detectedLang);
        if (!localStorage.getItem('has_seen_guide')) {
          setShowGuide(true);
          localStorage.setItem('has_seen_guide', 'true');
        }
        
      } catch (e) {
        const navLang = navigator.language.substring(0, 2);
        if (['ko', 'ja', 'zh', 'hi'].includes(navLang)) {
          setLanguage(navLang as Language);
        }
        console.error('IP Geolocation failed');
      }

      const logData = {
        visitorId,
        source,
        referrer: referrer || 'direct',
        country,
        device: /Mobi|Android/i.test(navigator.userAgent) ? 'Mobile' : 'PC',
        date: new Date().toLocaleDateString(),
        timestamp: Date.now()
      };

      try {
        await axios.post('/api/traffic', logData);
        sessionStorage.setItem('tracked_visit', 'true');
      } catch (e) {
        console.error('Failed to save traffic log');
      }
    };

    trackVisit();
  }, []);

  // 실시간 파일명 정합성 체크
  useEffect(() => {
    if (refFile && targetFile) {
      const name1 = refFile.name.toLowerCase().replace('.srt', '');
      const name2 = targetFile.name.toLowerCase().replace('.srt', '');
      
      // 영화 파일명에서 흔히 쓰이는 기술적 단어들은 제외 (순수 제목 비교를 위해)
      const stopWords = ['1080p', '2160p', '4k', 'uhd', 'bluray', 'bdrip', 'brrip', 'x264', 'x265', 'hevc', 'h264', 'hdr', '10bit', 'dts', 'aac', 'ma', 'rarbg', 'fmx', 'psa', 'yify', 'yts'];
      
      const filterKeywords = (name: string) => 
        name.split(/[\s\.\-\(\)\[\]]+/)
            .filter(k => k.length >= 2 && !stopWords.includes(k));

      const keywords1 = filterKeywords(name1);
      const keywords2 = filterKeywords(name2);
      
      if (keywords1.length === 0 || keywords2.length === 0) return;

      const common = keywords1.filter(k => keywords2.includes(k));
      const similarity = common.length / Math.max(keywords1.length, keywords2.length);

      if (similarity < 0.5) {
        setFileMismatchWarning(t('mismatchWarning', { n: (similarity * 100).toFixed(0) }));
        axios.post('/api/log-action', { 
          message: `[파일명 부정합 경고 표시] 유사도: ${(similarity * 100).toFixed(1)}%` 
        }).catch(() => {});
      } else {
        setFileMismatchWarning(null);
      }
    } else {
      setFileMismatchWarning(null);
    }
  }, [refFile, targetFile]);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    // 앱 시작/새로고침 시 서버 로그 {t('syncReset')} 요청 (테스트를 위해 잠시 비활성화)
    // axios.post('/api/clear-logs').catch(e => console.error("로그 {t('syncReset')} {t('failedCount')}", e));
  }, []);

  const handleSaveSettings = () => {
    localStorage.setItem('gemini_api_key', apiKey);
    localStorage.setItem('gemini_model', aiModel);
    
    // 서버 로그에 기록 요청 (보안상 API 키는 제외)
    axios.post('/api/log-action', { 
      message: t('settingsSavedLog', { model: aiModel })
    }).catch(e => console.error("로깅 실패", e));

    showToast(t('settingsSavedToast'));
  };

  const fetchLogs = async () => {
    try {
      axios.post('/api/log-action', { message: t('logRequestLog') }).catch(() => {});
      const response = await axios.get('/api/logs');
      setLogs(response.data);
      setShowLogs(true);
    } catch (error) {
      console.error('Failed to fetch logs', error);
      showToast(t('logFetchFailToast'), 'error');
    }
  };

  const handleReset = async () => {
    setRefFile(null);
    setTargetFile(null);
    setResults([]);
    setFileMismatchWarning(null);
    try {
      // 서버 로그도 함께 초기화
      await axios.post('/api/clear-logs');
      showToast(t('resetLog'));
    } catch (e) {
      console.error("초기화 중 오류:", e);
      showToast(t('resetFailToast'), 'error');
    }
  };

  const onDragOver = (e: React.DragEvent, type: 'ref' | 'target') => {
// ... existing onDragOver ...
    e.preventDefault();
    if (type === 'ref') setIsRefDragging(true);
    else setIsTargetDragging(true);
  };

  const onDragLeave = (type: 'ref' | 'target') => {
    if (type === 'ref') setIsRefDragging(false);
    else setIsTargetDragging(false);
  };

  const onDrop = (e: React.DragEvent, type: 'ref' | 'target') => {
    e.preventDefault();
    if (type === 'ref') setIsRefDragging(false);
    else setIsTargetDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file && (file.name.endsWith('.srt') || file.name.endsWith('.smi'))) {
      if (type === 'ref') setRefFile(file);
      else setTargetFile(file);
      axios.post('/api/log-action', { message: t('fileDropLog', { filename: file.name, type: type === 'ref' ? t('refType') : t('targetType') }) }).catch(() => {});
    } else if (file) {
      alert(t('onlySrtSmiAlert'));
    }
  };

  const handleSync = async () => {
    if (!refFile || !targetFile) return;

    if (isProduction) {
      // 배포 모드: 실제 광고 게이트웨이 작동 (Monetag 전면 광고 우선)
      setShowAdModal(true);
      setAdStatus('loading');
      setAdCountdown(5); 

      // Monetag 전면 광고 함수 확인 (Zone ID: 232159)
      const monetagShowAd = (window as any).show_232159;

      if (monetagShowAd) {
        setAdStatus('ready');
        try {
          // Monetag 보상형 인터스티셜 실행
          await monetagShowAd();
          
          // 광고 시청 완료 후 서버에 토큰 요청
          const res = await axios.post('/api/reward/verify');
          if (res.data.status === 'success') {
            setShowAdModal(false);
            startSyncWithToken(res.data.token);
          }
        } catch (e) {
          console.error("Monetag 광고 실행 중 오류:", e);
          setAdStatus('idle'); // 오류 시 쿠팡 브릿지로 대체
        }
      } else {
        // Monetag 로드 실패(AdBlock 등) 시 쿠팡 파트너스 브릿지 활성화
        setAdStatus('idle'); 
        const timer = setInterval(() => {
          setAdCountdown(prev => {
            if (prev <= 1) {
              clearInterval(timer);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
      return;
    }

    // 개발 모드: 즉시 시작
    startSyncWithToken();
  };

  const startSyncWithToken = async (token?: string) => {
    setSyncing(true);
    // ... 기존 startSyncWithToken 로직 동일 ...
    setSyncProgress(0);
    const taskId = 'task_' + Math.random().toString(36).substr(2, 9);
    setCurrentTaskId(taskId);
    
    const formData = new FormData();
    formData.append('ref_file', refFile!);
    formData.append('target_file', targetFile!);
    if (apiKey) formData.append('api_key', apiKey);
    formData.append('ai_model', aiModel);
    formData.append('task_id', taskId);
    formData.append('target_lang', lang);
    if (token) formData.append('reward_token', token);

    const intervalId = setInterval(async () => {
      try {
        const res = await axios.get(`/api/progress/${taskId}`);
        if (res.data && typeof res.data.progress === 'number') {
           setSyncProgress(res.data.progress);
        }
      } catch (e) {}
    }, 1000);

    try {
      const response = await axios.post('/api/sync', formData);
      if (response.data.status === 'error') {
        showToast(response.data.message || '서버 오류가 발생했습니다.', 'error');
        return;
      }
      if (response.data.status === 'cancelled') {
        showToast(t('taskCancelledToast'), 'error');
        return;
      }
      setResults(response.data.data);
      const matchCount = response.data.data.filter((r: any) => r.matched).length;
      const rate = matchCount / response.data.data.length;
      showToast(t('syncCompleteToast', { n: (rate * 100).toFixed(1) }));
    } catch (error) {
      showToast(t('syncFailToast'), 'error');
    } finally {
      clearInterval(intervalId);
      setSyncing(false);
      setSyncProgress(0);
      setCurrentTaskId(null);
    }
  };

  const handleStop = async () => {
    if (!currentTaskId) return;
    try {
      await axios.post(`/api/cancel/${currentTaskId}`);
      showToast(t('taskCancelledToast'), 'error');
    } catch (e) {
      console.error("중단 요청 실패:", e);
    } finally {
      setSyncing(false);
      setCurrentTaskId(null);
    }
  };

  // ... (다른 핸들러들)
  const handleDownload = () => {
    if (results.length === 0) return;
    
    let content = "";
    results.forEach((res, i) => {
      content += `${i + 1}\n`;
      content += `${res.new_start} --> ${res.new_end}\n`;
      content += `${res.matched ? (res.target?.text || res.ref.text) : res.ref.text}\n\n`;
    });

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `[Synced]_${targetFile?.name || 'subtitle.srt'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    axios.post('/api/log-action', { message: t('downloadLog', { n: results.length }) }).catch(() => {});
  };

  return (
    <div className="container">
      {/* 1400px 이상일 때만 표시되는 사이드 광고 */}
      <AdSidebar side="left" />
      <AdSidebar side="right" />

      <header>
        <div className="logo">
          <KoreanLangIcon size={32} color="#6366f1" />
          <h1>Subtitle Sync <span>Pro</span></h1>
        </div>
        <p>{t('appDesc')}</p>
        <div className="header-actions">
          <select value={lang} onChange={(e) => setLanguage(e.target.value as Language)} className="lang-select" style={{ marginRight: '10px', padding: '6px 12px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.1)', color: 'white', border: '1px solid rgba(255,255,255,0.2)' }}>
            <option value="ko" style={{color: 'black'}}>한국어</option>
            <option value="en" style={{color: 'black'}}>English</option>
            <option value="ja" style={{color: 'black'}}>日本語</option>
            <option value="zh" style={{color: 'black'}}>中文</option>
            <option value="hi" style={{color: 'black'}}>हिन्दी</option>
          </select>
          <button className="log-btn help-btn" onClick={() => setShowGuide(true)}>{t('guideMenu')}</button>
        </div>
      </header>

      <div className="settings-bar glass-morphism" style={{ justifyContent: 'center' }}>
        <div className="setting-group flex-1" style={{ flexDirection: 'column', alignItems: 'center', gap: '5px', maxWidth: '860px', margin: '0 auto', width: '100%' }}>
          <div style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'center', gap: '15px' }}>
            <label style={{ whiteSpace: 'nowrap', fontSize: '0.95rem', fontWeight: 'bold' }}>{t('apiKeyLabel')} (제미나이 API)</label>
            <div className="api-input-group" style={{ flex: 'none', width: '380px' }}>
              <input 
                type="text" 
                placeholder={t('apiKeyPlaceholder')} 
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <button className="save-btn" onClick={handleSaveSettings}>{t('saveSettings')}</button>
            </div>
          </div>
          <p style={{ margin: '8px 0 0', fontSize: '0.85rem', color: '#94a3b8', textAlign: 'center' }}>
            * (안내) 입력하신 API 키는 서버에 저장/수집되지 않습니다. 
            <button 
              onClick={() => setShowDisclaimer(true)} 
              style={{ background: 'none', border: 'none', color: '#6366f1', textDecoration: 'underline', cursor: 'pointer', marginLeft: '5px', fontSize: '0.8rem' }}
            >
              [면책조항 보기]
            </button>
          </p>
        </div>
      </div>

      <main>
        {/* ... 메인 업로드 및 결과 섹션 기존과 동일 ... */}
        <section className="upload-section">
          <div className="upload-grid">
            <div 
              className={`upload-card glass-morphism ${refFile ? 'active' : ''} ${isRefDragging ? 'dragging' : ''}`}
              onDragOver={(e) => onDragOver(e, 'ref')}
              onDragLeave={() => onDragLeave('ref')}
              onDrop={(e) => onDrop(e, 'ref')}
            >
              <Upload className="icon" />
              <h3>{t('refSubTitle')}</h3>
              <p>{t('refSubDesc')}</p>
              <input type="file" accept=".srt,.smi" onChange={(e) => setRefFile(e.target.files?.[0] || null)} />
              {refFile && <span className="filename">{refFile.name}</span>}
            </div>

            <div 
              className={`upload-card glass-morphism ${targetFile ? 'active' : ''} ${isTargetDragging ? 'dragging' : ''}`}
              onDragOver={(e) => onDragOver(e, 'target')}
              onDragLeave={() => onDragLeave('target')}
              onDrop={(e) => onDrop(e, 'target')}
            >
              <Upload className="icon" />
              <h3>{t('targetSubTitle')}</h3>
              <p>{t('targetSubDesc')}</p>
              <input type="file" accept=".srt,.smi" onChange={(e) => setTargetFile(e.target.files?.[0] || null)} />
              {targetFile && <span className="filename">{targetFile.name}</span>}
            </div>
          </div>

          {fileMismatchWarning && (
            <div className="mismatch-warning-banner">
              <AlertCircle size={20} />
              <span>{fileMismatchWarning}</span>
            </div>
          )}

          <div className="action-group">
            <button className="sync-btn" onClick={handleSync} disabled={!refFile || !targetFile || syncing}>
              {syncing ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <RefreshCcw className="spinning" /> <span>{syncProgress}%</span>
                </div>
              ) : t('syncStart')}
            </button>
            {syncing ? (
              <button className="reset-btn stop-btn" onClick={handleStop} style={{ backgroundColor: '#ef4444', color: 'white', borderColor: '#ef4444' }}>
                <XCircle size={18} /> {t('syncStop')}
              </button>
            ) : (refFile || targetFile || results.length > 0) ? (
              <button className="reset-btn" onClick={handleReset}>
                <RefreshCcw size={18} /> {t('syncReset')}
              </button>
            ) : null}
          </div>
        </section>

        {showLogs && (
          <section className="logs-view glass-morphism">
            <div className="logs-header">
              <h3>{t('sysLogs')}</h3>
              <div className="logs-actions">
                <button className="copy-btn" onClick={() => {
                  navigator.clipboard.writeText(logs);
                  showToast(t('logCopiedToast'));
                }}><Copy size={14} /> {t('logCopy')}</button>
                <button className="close-btn" onClick={() => setShowLogs(false)}>{t('logClose')}</button>
              </div>
            </div>
            <pre className="logs-content">{logs}</pre>
          </section>
        )}

        {results.length > 0 && (
          <section className="results-section glass-morphism">
            <div className="results-header">
              <h2>{t('syncResultTitle', { n: results.length })}</h2>
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <span style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
                  {t('originMatched')} <strong>{results.filter(r => r.matched && !r.translated).length}</strong> | {t('aiTranslated')} <strong style={{ color: '#818cf8' }}>{results.filter(r => r.translated).length}</strong> | {t('failedCount')} <strong style={{ color: '#ef4444' }}>{results.filter(r => !r.matched).length}</strong>
                </span>
                <button className="download-btn" onClick={handleDownload}><Download size={18} /> {t('downloadResult')}</button>
              </div>
            </div>
            <div className="results-list">
              {results.slice(0, displayLimit).map((res, i) => (
                <div key={i} className={`result-item ${res.matched ? 'matched' : 'failed'}`}>
                  <div className="res-idx">{res.ref.index}</div>
                  <div className="res-content">
                    <div className="res-meta">
                      <span className="res-time">{res.new_start} → {res.new_end}</span>
                      {res.matched && <span className="res-score">{t('similarity')} {(res.score * 100).toFixed(1)}%</span>}
                    </div>
                    <div className="res-texts">
                      <div className="ref-text">{res.ref.text}</div>
                      <div className="target-text">
                        {res.matched ? res.target?.text : <span className="error">{t('matchFailed')}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="res-status">
                    {res.matched ? <CheckCircle color="#10b981" /> : <AlertCircle color="#ef4444" />}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 쿠팡 가로 배너 삭제됨 (사이드로 이동) */}
      </main>

      <footer style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '40px 0' }}>
        <p style={{ fontSize: '0.9rem', color: '#64748b' }}>&copy; 2026 Subtitle Sync Pro v0.11. All rights reserved.</p>
        <p style={{ fontSize: '0.75rem', color: '#475569', textAlign: 'center', maxWidth: '700px', margin: '0 20px' }}>
          ※ 면책 조항: 본 서비스는 사용자가 업로드한 자막 파일을 서버에 무단 저장·배포하지 않는 단순 동기화 도구입니다. 
          불법적인 사용 및 공유에 대한 책임은 사용자에게 있습니다.
        </p>
        <div style={{ display: 'flex', gap: '20px', marginTop: '10px' }}>
          <button className="contact-btn" onClick={() => setShowContact(true)}>광고/협찬 및 문의하기</button>
          <button className="contact-btn" onClick={() => setShowPrivacy(true)} style={{ background: 'rgba(255,255,255,0.05)' }}>개인정보처리방침</button>
        </div>
      </footer>

      {showAdModal && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in reward-ad-modal">
            <div className="ad-video-container">
              <img src="/ads/reward_preview.png" alt="Ad Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              {adStatus !== 'failed' && adCountdown > 0 && (
                <div className="ad-timer-overlay">{adCountdown}s</div>
              )}
            </div>
            <div className="ad-modal-body">
              <h2>{t(adStatus === 'ready' ? 'adTitleReady' : adStatus === 'loading' ? 'adTitleLoading' : adStatus === 'failed' ? 'adTitleComplete' : 'adWatchRequired')}</h2>
              <p style={{ color: '#94a3b8', marginTop: '12px' }}>{t('adCoupangDesc')}</p>
              
              {adStatus === 'idle' && (
                <div style={{ marginTop: '24px' }}>
                  <button 
                    className="sync-btn" 
                    style={{ width: '100%', justifyContent: 'center', background: '#e11d48' }} 
                    onClick={async () => {
                      // Monetag 실패 시의 수동 브릿지 (쿠팡 파트너스 등)
                      window.open('https://link.coupang.com/a/bl6V3C', '_blank'); 
                      try {
                        const res = await axios.post('/api/reward/verify');
                        if (res.data.status === 'success') {
                          setShowAdModal(false);
                          startSyncWithToken(res.data.token);
                        }
                      } catch (e) {
                        showToast(t('logFetchFailToast'), 'error');
                      }
                    }}
                  >
                    {t('adCoupangTitle')}
                  </button>
                  <p className="coupang-disclaimer" style={{ margin: '15px auto 0' }}>{t('adDisclaimer')}</p>
                </div>
              )}

              {adStatus === 'failed' && (
                <button className="sync-btn" style={{ width: '100%', justifyContent: 'center', marginTop: '20px' }} onClick={() => setShowAdModal(false)}>
                  {t('adStartNext')}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {showContact && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in" style={{ maxWidth: '500px' }}>
            <div className="guide-header"><h2>광고/협찬 문의</h2><button className="close-x" onClick={() => setShowContact(false)}>&times;</button></div>
            <form onSubmit={handleContactSubmit} className="contact-form" style={{ padding: '20px' }}>
              <input type="text" name="name" required placeholder="이름" style={{ width: '100%', marginBottom: '10px', padding: '10px' }} />
              <input type="email" name="email" required placeholder="이메일" style={{ width: '100%', marginBottom: '10px', padding: '10px' }} />
              <textarea name="message" required rows={5} placeholder="내용" style={{ width: '100%', padding: '10px' }}></textarea>
              <button type="submit" style={{ width: '100%', padding: '12px', background: '#6366f1', color: 'white', border: 'none' }}>보내기</button>
            </form>
          </div>
        </div>
      )}

      {showGuide && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in">
            <div className="guide-header"><h2>{t('guideTitle')}</h2><button className="close-x" onClick={() => setShowGuide(false)}>&times;</button></div>
            <div className="guide-content">
              <section className="steps-section">
                <div className="step-item"><div className="step-num">1</div><p>{t('guideStep1')}</p></div>
                <div className="step-item"><div className="step-num">2</div><p>{t('guideStep2')}</p></div>
              </section>
            </div>
            <button className="guide-close-btn" onClick={() => setShowGuide(false)}>{t('closeGuide')}</button>
          </div>
        </div>
      )}
      {showPrivacy && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in" style={{ maxWidth: '600px' }}>
            <div className="guide-header">
              <h2>개인정보처리방침</h2>
              <button className="close-x" onClick={() => setShowPrivacy(false)}>&times;</button>
            </div>
            <div className="guide-content" style={{ padding: '20px', fontSize: '0.9rem', lineHeight: '1.6', maxHeight: '600px', overflowY: 'auto' }}>
              <h3>1. 수집하는 개인정보</h3>
              <p>본 서비스는 별도의 회원가입 없이 이용 가능하며, 사용자의 이름, 연락처 등을 수기 입력하는 문의하기 기능을 제외하고는 어떠한 민감 개인정보도 수집하지 않습니다.</p>
              
              <h3>2. 광고 및 쿠키 사용</h3>
              <p>본 사이트는 구글 애드센스(Google AdSense)를 통해 광고를 게재합니다. 구글은 사용자의 관심사에 맞는 광고를 제공하기 위해 쿠키를 사용하여 데이터를 수집할 수 있습니다.</p>
              
              <h3>3. 파일 보안</h3>
              <p>사용자가 업로드하는 자막 파일은 싱크 작업을 위해 일시적으로 서버에서 처리될 뿐, DB 등에 저장되거나 제3자에게 공유되지 않습니다. 작업 완료 후 즉시 파기됩니다.</p>
              
              <h3>4. 문의처</h3>
              <p>기타 문의사항은 '광고/협찬 및 문의하기' 폼을 통해 접수해주시기 바랍니다.</p>
            </div>
            <button className="guide-close-btn" onClick={() => setShowPrivacy(false)}>확인</button>
          </div>
        </div>
      )}

      {showDisclaimer && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in" style={{ maxWidth: '600px' }}>
            <div className="guide-header">
              <h2>면책 조항 (Disclaimer)</h2>
              <button className="close-x" onClick={() => setShowDisclaimer(false)}>&times;</button>
            </div>
            <div className="guide-content" style={{ padding: '20px', fontSize: '1rem', lineHeight: '1.8' }}>
              <p style={{ marginBottom: '15px' }}>
                본 서비스는 사용자가 업로드한 자막 파일을 서버에 무단 저장·배포하지 않는 <strong>단순 동기화 도구(Utility)</strong>입니다.
              </p>
              <p style={{ color: '#f87171', fontWeight: 'bold' }}>
                저작권이 있는 자막 파일 원본의 불법 사용 및 공유로 인해 발생하는 모든 법적 책임은 전적으로 사용자 본인에게 있음을 알려드립니다.
              </p>
              <p style={{ marginTop: '15px', color: '#94a3b8', fontSize: '0.9rem' }}>
                사용자는 본 서비스를 이용함으로써 위 사항에 동의하는 것으로 간주됩니다.
              </p>
            </div>
            <button className="guide-close-btn" onClick={() => setShowDisclaimer(false)}>확인 및 동의</button>
          </div>
        </div>
      )}
      
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.type === 'success' ? <CheckCircle size={18} /> : <XCircle size={18} />}
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
}

export default App;
