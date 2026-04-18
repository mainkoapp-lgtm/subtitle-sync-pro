import { useEffect, useRef, memo } from 'react';

interface CoupangDynamicBannerProps {
  id?: number;
  width?: string;
  height?: string;
  template?: string;
}

/**
 * CoupangDynamicBanner - 쿠팡 파트너스 다이나믹 배너 컴포넌트
 * [승인 최적화] 공정위 대가성 문구가 기본 포함되어 있습니다.
 */
const CoupangDynamicBannerBase = ({ 
  id = 981842, 
  width = "680", 
  height = "140", 
  template = "carousel" 
}: CoupangDynamicBannerProps) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 1. 스크립트 로드 확인 및 주입
    const scriptId = 'coupang-partners-g-js';
    let script = document.getElementById(scriptId) as HTMLScriptElement;

    const initBanner = () => {
      if (window.PartnersCoupang && containerRef.current) {
        // 기존 배너 내용 삭제 (중복 생성 방지)
        containerRef.current.innerHTML = '';
        
        new window.PartnersCoupang.G({
          id,
          template,
          trackingCode: "AF6107121",
          width,
          height,
          container: containerRef.current,
          tsource: ""
        });
      }
    };

    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://ads-partners.coupang.com/g.js';
      script.async = true;
      script.addEventListener('load', initBanner);
      document.head.appendChild(script);
    } else {
      // 스크립트가 이미 있다면 즉시 초기화 시도
      if (window.PartnersCoupang) {
        initBanner();
      } else {
        script.addEventListener('load', initBanner);
      }
    }

    return () => {
      if (script) {
        script.removeEventListener('load', initBanner);
      }
    };
  }, [id, width, height, template]);

  return (
    <div className="coupang-banner-wrapper" style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      margin: '20px 0',
      width: '100%' 
    }}>
      {/* 배너 컨테이너 */}
      <div 
        ref={containerRef} 
        style={{ 
          width: `${width}px`, 
          height: `${height}px`, 
          backgroundColor: 'rgba(255,255,255,0.05)',
          borderRadius: '8px',
          overflow: 'hidden'
        }}
      >
        {/* 쿠팡 스크립트가 이곳에 배너를 렌더링합니다 */}
      </div>

      {/* [중요] 공정위 대가성 문구 (심사 필수 요건) */}
      <div style={{
        marginTop: '8px',
        fontSize: '11px',
        color: '#94a3b8',
        textAlign: 'center',
        opacity: 0.8
      }}>
        이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.
      </div>
    </div>
  );
};

const CoupangDynamicBanner = memo(CoupangDynamicBannerBase);

// Global Window 인터페이스 확장
declare global {
  interface Window {
    PartnersCoupang: any;
  }
}

export default CoupangDynamicBanner;
