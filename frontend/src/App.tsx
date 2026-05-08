/** [COMPLETED: 2026-04-02] API Key 가시화 및 로깅 마스킹 제거 완료 (임의 수정 금지) */
/** [COMPLETED: 2026-04-22] 다국어 지원(i18n) 적용 완료 (임의 수정 금지) */
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
import ClickmonBanner from './components/ClickmonBanner';

// 백엔드 API를 통해 동적으로 광고 링크를 받아오도록 개선됨

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
const AdSidebar = ({ side, platform, bannerId }: { side: 'left' | 'right', platform: 'coupang' | 'clickmon', bannerId?: number }) => (
  <div className={`ad-sidebar ad-sidebar-${side}`} style={{ padding: '0', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
    <span className="ad-label" style={{ padding: '10px 0 0' }}>ADVERTISEMENT</span>
    <div style={{ flex: 1, width: '100%', display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
      {platform === 'coupang' ? (
        <CoupangDynamicBanner id={bannerId} width="160" height="600" template="carousel" />
      ) : (
        <ClickmonBanner width="160" height="600" />
      )}
    </div>
  </div>
);

// 모바일 전용 가로 광고 배너
const MobileAdBanner = ({ id, bannerId, platform = 'coupang' }: { id?: number, bannerId?: number, platform?: 'coupang' | 'clickmon' }) => (
  <div className="mobile-ad-container glass-morphism">
    <span className="ad-label" style={{ fontSize: '9px', marginBottom: '8px' }}>Advertisement</span>
    <div style={{ width: '100%', overflow: 'hidden', display: 'flex', justifyContent: 'center' }}>
      {platform === 'coupang' ? (
        <CoupangDynamicBanner id={bannerId || id} width="320" height="100" template="carousel" />
      ) : (
        <ClickmonBanner width="320" height="100" />
      )}
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
  const [adStatus, setAdStatus] = useState<'idle' | 'loading' | 'ready' | 'failed'>('idle');
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [adInfo, setAdInfo] = useState<{type: string, link: string, provider: string} | null>(null);
  const [adBlockDetected, setAdBlockDetected] = useState(false);
  const isDebug = new URLSearchParams(window.location.search).get('test') === '1';
  const [adActionType, setAdActionType] = useState<'sync' | 'download' | null>(null);
  const [tokenUsage, setTokenUsage] = useState<any>(null);
  const defaultBannerIds = [981842, 981849, 987286, 987287];
  const [coupangBannerIds, setCoupangBannerIds] = useState<number[]>(defaultBannerIds);
  // [완료] 쿠팡 배너 ID 랜덤 선택 로직 (임의 수정 금지)
  const getRandomBannerId = (ids: number[]) => ids[Math.floor(Math.random() * ids.length)];

  const [leftBannerId, setLeftBannerId] = useState<number>(() => {
    const firstId = getRandomBannerId(defaultBannerIds);
    return firstId;
  });
  const [rightBannerId, setRightBannerId] = useState<number>(() => {
    const firstId = getRandomBannerId(defaultBannerIds);
    // 왼쪽과 겹치면 다른 것 선택 (최소 2개 이상의 ID가 있다고 가정)
    if (defaultBannerIds.length > 1) {
      let secondId = getRandomBannerId(defaultBannerIds);
      while (secondId === firstId) {
        secondId = getRandomBannerId(defaultBannerIds);
      }
      return secondId;
    }
    return firstId;
  });
  const [mobileBannerId, setMobileBannerId] = useState<number>(() => getRandomBannerId(defaultBannerIds));

  // [완료] 플랫폼 랜덤 선택 로직 (쿠팡/클릭몬) (임의 수정 금지)
  const getRandomPlatform = () => Math.random() > 0.5 ? 'coupang' : 'clickmon';

  const [leftPlatform, setLeftPlatform] = useState<'coupang' | 'clickmon'>(getRandomPlatform);
  const [rightPlatform, setRightPlatform] = useState<'coupang' | 'clickmon'>(getRandomPlatform);
  const [mobilePlatform, setMobilePlatform] = useState<'coupang' | 'clickmon'>(getRandomPlatform);

  // 파이어베이스에서 광고 설정 가져오기 (배너 로테이션용)
  useEffect(() => {
    const fetchAdConfig = async () => {
      try {
        // 파이어베이스 호스팅에서 광고 설정 가져오기
        const CONFIG_URL = "https://subfast-manager.web.app/web_banners.json";
        const res = await axios.get(CONFIG_URL);
        if (res.data) {
          if (res.data.banner_ids && Array.isArray(res.data.banner_ids) && res.data.banner_ids.length > 0) {
            setCoupangBannerIds(res.data.banner_ids);
            // 서버 데이터 기반으로 각각 랜덤 선택 덮어쓰기 (좌우 중복 방지)
            const ids = res.data.banner_ids;
            const newLeft = getRandomBannerId(ids);
            setLeftBannerId(newLeft);
            
            if (ids.length > 1) {
              let newRight = getRandomBannerId(ids);
              while (newRight === newLeft) {
                newRight = getRandomBannerId(ids);
              }
              setRightBannerId(newRight);
            } else {
              setRightBannerId(newLeft);
            }
            
            setMobileBannerId(getRandomBannerId(ids));
            console.log("새로운 배너 ID들 로드됨 (중복 방지 적용)");
          }
          
          // 좌우 및 모바일 플랫폼 설정 로드 (서버 우선)
          if (res.data.left_platform) setLeftPlatform(res.data.left_platform);
          if (res.data.right_platform) setRightPlatform(res.data.right_platform);
          if (res.data.mobile_platform) setMobilePlatform(res.data.mobile_platform);
        }
      } catch (e) {
        console.warn("서버 커스텀 광고 설정을 찾을 수 없어, 기본 내장된 설정으로 작동합니다.");
      }
    };
    fetchAdConfig();
  }, []);

  // 광고 차단기 감지 로직 개선 (v0.16: 로컬 화이트리스트 우선 순위 부여)
  const checkAdBlocker = async (): Promise<boolean> => {
    // [테스트를 위해 로컬에서도 감지 허용]
    // if (!isProduction) return false;
    
    let localBlocked = false;
    let imagesBlocked = false;
    let fetchBlocked = false;

    // 1순위: 로컬 베이트 스크립트(/js/ads.js) 확인
    if ((window as any).canRunAds !== true) {
      localBlocked = true;
    }

    // 2순위: 이미지 로드 테스트 (하나라도 실패하면 차단으로 간주)
    const testImages = [
      'https://omg10.com/favicon.ico',
      'https://tab2.clickmon.co.kr/favicon.ico',
      'https://pagead2.googlesyndication.com/favicon.ico'
    ];
    
    try {
      const imgResults = await Promise.all(testImages.map(url => {
        return new Promise<boolean>((resolve) => {
          const img = new Image();
          img.onload = () => resolve(false);
          img.onerror = () => resolve(true);
          img.src = `${url}?t=${Date.now()}`;
          setTimeout(() => resolve(true), 2500); // 타임아웃 단축
        });
      }));
      if (imgResults.some(r => r === true)) imagesBlocked = true;
    } catch (e) {
      imagesBlocked = true;
    }

    // 3순위: 네트워크 도메인 차단 확인 (하나라도 실패하면 차단으로 간주)
    const adDomains = [
      'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js',
      'https://tab2.clickmon.co.kr/pop/wp_ad_pop_js.php'
    ];
    
    for (const domain of adDomains) {
      try {
        await fetch(domain, { method: 'HEAD', mode: 'no-cors', cache: 'no-store' });
      } catch (error) {
        fetchBlocked = true;
        break; 
      }
    }

    // [완료] 최종 결과 반영: 하나라도 감지되면 true (임의 수정 금지)
    const detected = localBlocked || imagesBlocked || fetchBlocked;

    setAdBlockDetected(detected);
    return detected;
  };

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

  // isProduction 상태가 true로 변경되면 광고 차단기 검사 실행
  useEffect(() => {
    if (isProduction) {
      checkAdBlocker();
    }
  }, [isProduction]);


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
      showToast(t('contactSuccess'), 'success');
      setShowContact(false);
    } catch (err) {
      showToast(t('contactFail'), 'error');
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
    setTokenUsage(null);
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

  const loadSamples = async () => {
    try {
      const [refRes, targetRes] = await Promise.all([
        fetch('/test_data/test_ref.srt'),
        fetch('/test_data/test_target.smi')
      ]);
      
      if (!refRes.ok || !targetRes.ok) throw new Error("Sample files not found");

      const refText = await refRes.text();
      const targetText = await targetRes.text();

      const refBlob = new Blob([refText], { type: 'text/plain' });
      const targetBlob = new Blob([targetText], { type: 'text/plain' });
      
      setRefFile(new File([refBlob], "Terminator_Ref.srt", { type: 'text/plain' }));
      setTargetFile(new File([targetBlob], "Terminator_Target.smi", { type: 'text/plain' }));
      showToast(t('sampleUploadedToast'));
    } catch (e) {
      console.error(e);
      showToast(t('sampleLoadFailToast'), 'error');
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
    if (!isDebug && (!refFile || !targetFile)) return;

    // [강력 보안] 실행 직전 광고 차단기 재검사
    const isBlocked = await checkAdBlocker();
    if (isBlocked) {
      showToast(lang === 'ko' ? '광고 차단기를 끄고 진행해주세요.' : 'Please disable ad blocker to proceed.', 'error');
      return;
    }


    if (isProduction) {
      setAdActionType('sync');
      setShowAdModal(true);
      setAdStatus('loading');

      // 광고 정보 미리 가져오기
      try {
        const adRes = await axios.get('/api/reward/link');
        if (adRes.data && adRes.data.status === 'success') {
          setAdInfo({
            type: adRes.data.type,
            link: adRes.data.link,
            provider: adRes.data.provider
          });
          setAdStatus('idle'); // 로딩 완료 후 버튼 즉시 활성화
        } else {
          throw new Error("Invalid Ad Config");
        }
      } catch (e) {
        console.error("광고 정보 로드 실패:", e);
        // 로드 실패 시에도 예비 광고를 띄우기 위해 버튼 활성화
        setAdStatus('idle');
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
      if (response.data.usage) setTokenUsage(response.data.usage);
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
    const originalName = targetFile?.name || 'subtitle.srt';
    const fileNameWithoutExt = originalName.substring(0, originalName.lastIndexOf('.')) || originalName;
    link.download = `[Synced]_${fileNameWithoutExt}.srt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    axios.post('/api/log-action', { message: t('downloadLog', { n: results.length }) }).catch(() => {});
  };

  const handleDownloadApp = async () => {
    // [강력 보안] 실행 직전 광고 차단기 재검사
    const isBlocked = await checkAdBlocker();
    if (isBlocked) {
      showToast(lang === 'ko' ? '광고 차단기를 끄고 진행해주세요.' : 'Please disable ad blocker to proceed.', 'error');
      return;
    }

    
    if (isProduction) {
      setAdActionType('download');
      setShowAdModal(true);
      setAdStatus('loading');
      
      try {
        const adRes = await axios.get('/api/reward/link');
        if (adRes.data && adRes.data.status === 'success') {
          setAdInfo({
            type: adRes.data.type,
            link: adRes.data.link,
            provider: adRes.data.provider
          });
          setAdStatus('idle');
        } else {
          setAdStatus('idle');
        }
      } catch (e) {
        setAdStatus('idle');
      }
      return;
    }
    
    executeActualDownload();
  };

  const executeActualDownload = () => {
    const downloadUrl = "https://www.dropbox.com/scl/fi/dzebaz75prvdj9q5sqkqr/v2.0.zip?rlkey=dmd2vgdd26itv7wu9pr3n7xd7&st=t5kzqlq3&dl=1";
    window.location.href = downloadUrl;
    axios.post('/api/log-action', { message: "[앱 다운로드 실행] 광고 확인 완료 후 다운로드 시작됨" }).catch(() => {});
  };

  return (
    <div className="container">

      {/* 1550px 이상일 때만 표시되는 사이드 광고 (CSS로 제어) */}
      <AdSidebar side="left" platform={leftPlatform} bannerId={leftBannerId} />
      <AdSidebar side="right" platform={rightPlatform} bannerId={rightBannerId} />

      {/* 모바일/태블릿용 상단 광고 */}
      <MobileAdBanner bannerId={mobileBannerId} platform={mobilePlatform} />

      <header>
        <div className="logo">
          <KoreanLangIcon size={32} color="#6366f1" />
          <h1>Subtitle Sync <span>Pro</span></h1>
        </div>
        <p>{t('appDesc')}</p>
        <div className="header-actions">
          <button 
            onClick={handleDownloadApp}
            className="download-app-btn"
            style={{ border: 'none', cursor: 'pointer' }}
          >
            <Download size={18} /> {t('downloadApp')}
          </button>
          <button className="log-btn help-btn" onClick={() => setShowGuide(true)}>{t('guideMenu')}</button>
          {import.meta.env.DEV && (
            <button 
              className="log-btn" 
              onClick={loadSamples}
              style={{ backgroundColor: '#4f46e5', color: 'white', border: 'none' }}
            >
              샘플 로드(DEV)
            </button>
          )}
        </div>
      </header>

      {adBlockDetected ? (
        <div className="adblock-warning-card glass-morphism animate-in">
          <XCircle size={48} color="#ef4444" />
          <h2>{lang === 'ko' ? '광고 차단기가 감지되었습니다' : 'Ad Blocker Detected'}</h2>
          <p>
            {lang === 'ko' 
              ? 'Subtitle Sync Pro는 광고 수익을 기반으로 운영되고 있습니다. 핵심 기능을 이용하시려면 광고 차단기(AdGuard, uBlock 등)를 해제해 주세요.' 
              : 'Subtitle Sync Pro relies on ad revenue. Please disable your ad blocker (AdGuard, uBlock, etc.) to use the core features.'}
          </p>
          <div className="warning-hint">
            {lang === 'ko' 
              ? '차단 해제 후 아래 버튼을 눌러 페이지를 새로고침(F5) 하시면 즉시 이용이 가능합니다.' 
              : 'Please refresh the page (F5) after disabling to gain access.'}
          </div>
          <button onClick={() => window.location.reload()} className="sync-btn refresh-btn">
            {lang === 'ko' ? '새로고침하여 다시 시도' : 'Refresh and Try Again'}
          </button>
        </div>
      ) : (
        /* [완료] 메인 기능 영역: 광고 차단 감지 시 경고 카드로 대체 (임의 수정 금지) */
        <>
          <div className="settings-bar glass-morphism" style={{ justifyContent: 'center' }}>
            <div className="setting-group flex-1" style={{ flexDirection: 'column', alignItems: 'center', gap: '5px', maxWidth: '860px', margin: '0 auto', width: '100%' }}>
              <div className="api-input-container" style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'center', gap: '15px', flexWrap: 'wrap' }}>
                <label style={{ whiteSpace: 'nowrap', fontSize: '0.95rem', fontWeight: 'bold' }}>{t('apiKeyLabel')} (제미나이 API)</label>
                <div className="api-input-group" style={{ flex: 'none' }}>
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
                {t('apiKeyNotice')} 
                <button 
                  onClick={() => setShowDisclaimer(true)} 
                  style={{ background: 'none', border: 'none', color: '#6366f1', textDecoration: 'underline', cursor: 'pointer', marginLeft: '5px', fontSize: '0.8rem' }}
                >
                  {t('footerDisclaimerBtn')}
                </button>
              </p>
            </div>
          </div>

          <main>
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
                <button className="sync-btn" onClick={handleSync} disabled={(!isDebug && (!refFile || !targetFile)) || syncing}>
                  {syncing ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <RefreshCcw className="spinning" /> <span>{syncProgress}%</span>
                    </div>
                  ) : t('syncStart')}
                </button>

                {results.length > 0 && !syncing && (
                  <button className="sync-btn" onClick={handleDownload} style={{ background: 'var(--accent)', boxShadow: '0 10px 25px rgba(16, 185, 129, 0.4)' }}>
                    <Download size={18} /> {t('downloadResult')}
                  </button>
                )}

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
              
              {/* 모바일/태블릿용 중간 광고 */}
              <MobileAdBanner platform={mobilePlatform} />
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
                      {tokenUsage && (
                        <span style={{ marginLeft: '12px', paddingLeft: '12px', borderLeft: '1px solid rgba(255,255,255,0.1)', color: '#10b981' }}>
                          Token: <strong>{tokenUsage.total_tokens.toLocaleString()}</strong>
                        </span>
                      )}
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

            {/* 모바일/태블릿용 하단 광고 */}
            <MobileAdBanner id={981842} platform={mobilePlatform} />
          </main>
        </>
      )}

      <footer style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', padding: '40px 0' }}>
        <p style={{ fontSize: '0.9rem', color: '#64748b' }}>&copy; 2026 Subtitle Sync Pro v0.16. All rights reserved.</p>
        <p style={{ fontSize: '0.75rem', color: '#475569', textAlign: 'center', maxWidth: '700px', margin: '0 20px' }}>
          ※ {t('footerDisclaimerTitle')}: {t('footerDisclaimer1')} 
          {t('footerDisclaimer2')}
        </p>
        <div style={{ display: 'flex', gap: '20px', marginTop: '10px' }}>
          <button className="contact-btn" onClick={() => setShowContact(true)}>{t('footerContactBtn')}</button>
          <button className="contact-btn" onClick={() => setShowPrivacy(true)} style={{ background: 'rgba(255,255,255,0.05)' }}>{t('privacyTitle')}</button>
        </div>
      </footer>

      {showAdModal && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in reward-ad-modal">
            <div className="ad-video-container">
              {adStatus === 'loading' ? (
                <div className="ad-loading-spinner">
                  <RefreshCcw className="spinning" size={48} color="#6366f1" />
                  <p style={{ marginTop: '15px' }}>{t('adTitleLoading')}</p>
                </div>
              ) : (
                <>
                  <img src="/ads/reward_preview.png" alt="Ad Preview" style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.4 }} />
                  <div className="ad-overlay-content">
                    <CheckCircle size={48} color="#10b981" />
                    <p style={{ marginTop: '10px', fontSize: '1.1rem', fontWeight: 'bold' }}>{t('adTitleReady')}</p>
                  </div>
                </>
              )}
            </div>
            <div className="ad-modal-body">
              <h2>{adInfo?.type === 'coupang' ? t('adCoupangTitle') : t('adWatchRequired')}</h2>
              <p style={{ color: '#94a3b8', marginTop: '12px' }}>
                {adInfo?.type === 'coupang' ? t('adCoupangDesc') : t('adDisclaimer')}
              </p>
              
              {adStatus === 'idle' && (
                <div style={{ marginTop: '24px' }}>
                  <button 
                    className="sync-btn" 
                    style={{ width: '100%', justifyContent: 'center', background: adInfo?.type === 'coupang' ? '#e11d48' : '#6366f1' }} 
                    onClick={async () => {
                      try {
                        if (!adInfo) return;
                        
                        // [광고 로테이션 적용]
                        let adTriggered = false;
                        const { type, link } = adInfo;
                        
                        if (type === 'clickmon') {
                          window.open('/ad-bridge.html?type=clickmon', '_blank', 'width=800,height=600');
                          adTriggered = true;
                        } else if (link) {
                          window.open(`/ad-bridge.html?target=${encodeURIComponent(link)}`, '_blank', 'width=800,height=600');
                          adTriggered = true;
                        }
                        
                        if (!adTriggered) {
                          showToast(t('adLoadFail'), 'error');
                          return;
                        }

                        // 사용자 인지를 위해 지연, 지연 중에 다시 한 번 광고 차단기를 검사하여 
                        // 새 탭이 차단당하는 동작(AdGuard 등)을 잡아냄
                        setTimeout(async () => {
                          try {
                            const isStillBlocked = await checkAdBlocker();
                            if (isStillBlocked) {
                              setShowAdModal(false);
                              showToast(lang === 'ko' ? '광고 차단기가 켜져있어 진행이 취소되었습니다.' : 'Ad Blocker prevented the process.', 'error');
                              return;
                            }

                            const res = await axios.post('/api/reward/verify');
                            if (res.data.status === 'success') {
                              setShowAdModal(false);
                              if (adActionType === 'sync') {
                                startSyncWithToken(res.data.token);
                              } else if (adActionType === 'download') {
                                executeActualDownload();
                              }
                            }
                          } catch (verifyErr) {
                            showToast(t('logFetchFailToast'), 'error');
                          }
                        }, 2500);
                      } catch (e) {
                        showToast(t('logFetchFailToast'), 'error');
                      }
                    }}
                  >
                    {adActionType === 'download' ? (lang === 'ko' ? '광고 확인 및 다운로드 시작' : 'Verify Ad & Start Download') : t('adCoupangTitle')}
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
            <div className="guide-header"><h2>{t('contactTitle')}</h2><button className="close-x" onClick={() => setShowContact(false)}>&times;</button></div>
            <form onSubmit={handleContactSubmit} className="contact-form" style={{ padding: '20px' }}>
              <input type="text" name="name" required placeholder={t('contactName')} style={{ width: '100%', marginBottom: '10px', padding: '10px' }} />
              <input type="email" name="email" required placeholder={t('contactEmail')} style={{ width: '100%', marginBottom: '10px', padding: '10px' }} />
              <textarea name="message" required rows={5} placeholder={t('contactMessage')} style={{ width: '100%', padding: '10px' }}></textarea>
              <button type="submit" style={{ width: '100%', padding: '12px', background: '#6366f1', color: 'white', border: 'none' }}>{t('contactSend')}</button>
            </form>
          </div>
        </div>
      )}

      {showGuide && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in">
            <div className="guide-header">
              <h2>{t('guideTitle')}</h2>
              <button className="close-x" onClick={() => setShowGuide(false)}>&times;</button>
            </div>

            <div className="guide-tabs">
              <button 
                className={`tab-btn ${guideTab === 'web' ? 'active' : ''}`} 
                onClick={() => setGuideTab('web')}
              >
                {t('tabWeb')}
              </button>
              <button 
                className={`tab-btn ${guideTab === 'ext' ? 'active' : ''}`} 
                onClick={() => setGuideTab('ext')}
              >
                {t('tabExt')}
              </button>
            </div>

            <div className="guide-content">
              {guideTab === 'web' ? (
                <div className="web-guide animate-in">
                  <section className="purpose-section">
                    <h3>{t('purposeTitle')}</h3>
                    <p>{t('purposeDesc')}</p>
                  </section>
                  <section className="steps-section">
                    <div className="step-item"><div className="step-num">1</div><p>{t('guideStep1')}</p></div>
                    <div className="step-item"><div className="step-num">2</div><p>{t('guideStep2')}</p></div>
                    <div className="step-item"><div className="step-num">3</div><p>{t('guideStep3')}</p></div>
                    <div className="step-item"><div className="step-num">4</div><p>{t('guideStep4')}</p></div>
                  </section>
                </div>
              ) : (
                <div className="extractor-guide animate-in">
                  <section className="purpose-section">
                    <h3>{t('extTitle')}</h3>
                    <p>{t('extDesc')}</p>
                  </section>
                  <section className="steps-section">
                    <div className="step-item"><div className="step-num">1</div><p>{t('extStep1')}</p></div>
                    <div className="step-item"><div className="step-num">2</div><p>{t('extStep2')}</p></div>
                  </section>
                </div>
              )}
            </div>
            <button className="guide-close-btn" onClick={() => setShowGuide(false)}>{t('closeGuide')}</button>
          </div>
        </div>
      )}
      {showPrivacy && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in" style={{ maxWidth: '600px' }}>
            <div className="guide-header">
              <h2>{t('privacyTitle')}</h2>
              <button className="close-x" onClick={() => setShowPrivacy(false)}>&times;</button>
            </div>
            <div className="guide-content" style={{ padding: '20px', fontSize: '0.9rem', lineHeight: '1.6', maxHeight: '600px', overflowY: 'auto' }}>
              <h3>{t('privacy1Title')}</h3>
              <p>{t('privacy1Desc')}</p>
              
              <h3>{t('privacy2Title')}</h3>
              <p>{t('privacy2Desc')}</p>
              
              <h3>{t('privacy3Title')}</h3>
              <p>{t('privacy3Desc')}</p>
              
              <h3>{t('privacy4Title')}</h3>
              <p>{t('privacy4Desc')}</p>
            </div>
            <button className="guide-close-btn" onClick={() => setShowPrivacy(false)}>{t('privacyConfirm')}</button>
          </div>
        </div>
      )}

      {showDisclaimer && (
        <div className="modal-overlay">
          <div className="guide-modal glass-morphism animate-in" style={{ maxWidth: '600px' }}>
            <div className="guide-header">
              <h2>{t('footerDisclaimerTitle')}</h2>
              <button className="close-x" onClick={() => setShowDisclaimer(false)}>&times;</button>
            </div>
            <div className="guide-content" style={{ padding: '20px', fontSize: '1rem', lineHeight: '1.8' }}>
              <p style={{ marginBottom: '15px' }}>
                {t('footerDisclaimer1')}
              </p>
              <p style={{ color: '#f87171', fontWeight: 'bold' }}>
                {t('footerDisclaimer3')}
              </p>
              <p style={{ marginTop: '15px', color: '#94a3b8', fontSize: '0.9rem' }}>
                {t('footerDisclaimer4')}
              </p>
            </div>
            <button className="guide-close-btn" onClick={() => setShowDisclaimer(false)}>{t('footerDisclaimerConfirm')}</button>
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
