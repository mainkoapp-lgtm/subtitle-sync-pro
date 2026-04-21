import { memo } from 'react';

interface ClickmonBannerProps {
  width?: string;
  height?: string;
}

/**
 * ClickmonBanner - 클릭몬 배너 컴포넌트
 * document.writeln 방식의 광고를 React에서 안전하게 로드하기 위해 iframe을 사용합니다.
 */
const ClickmonBannerBase = ({ 
  width = "160", 
  height = "600" 
}: ClickmonBannerProps) => {
  
  // 클릭몬 160x600 고유 스크립트 코드 (2026-04-22 발급)
  const adScript = `
    (function(cl,i,c,k,m,o,n)
    {m=c;o=cl.referrer;m+='&mon_rf='+encodeURIComponent(o);m+='&mon_direct_url='+encodeURIComponent(k);
    n='<' + 'i' + 't' + ' type="text/javascript" src="'+m+'"></'+'i' + 't' +'>';cl.writeln(n);
    })(document,'script','https://tab2.clickmon.co.kr/pop/wp_ad_160_js.php?PopAd=CM_M_1003067%7C%5E%7CCM_A_1156063%7C%5E%7CAdver_M=2&mon_di=','PASSBACK_INPUT');
  `;

  const srcDoc = `
    <!DOCTYPE html>
    <html>
      <head>
        <style>body { margin: 0; padding: 0; overflow: hidden; display: flex; justify-content: center; }</style>
      </head>
      <body>
        <script type="text/javascript">${adScript}</script>
      </body>
    </html>
  `;

  return (
    <div className="clickmon-banner-wrapper" style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      margin: '20px 0',
      width: '100%' 
    }}>
      <iframe
        title="Clickmon Ad"
        srcDoc={srcDoc}
        width={width}
        height={height}
        style={{ border: 'none', overflow: 'hidden' }}
        scrolling="no"
      />
      <div style={{
        marginTop: '8px',
        fontSize: '11px',
        color: '#94a3b8',
        textAlign: 'center',
        opacity: 0.8
      }}>
        ADVERTISEMENT
      </div>
    </div>
  );
};

const ClickmonBanner = memo(ClickmonBannerBase);

export default ClickmonBanner;
