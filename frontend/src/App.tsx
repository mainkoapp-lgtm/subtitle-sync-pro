// [최신 상태] App v0.2.6 | Engine v0.7.6 | 마지막 동기화: 2026-06-02 06:27:00
// 마지막 동기화: 2026-06-02
import { useState, useEffect } from 'react';
import axios from 'axios';
import { useTranslation } from './i18n';
import './App.css';
import CoupangDynamicBanner from './components/CoupangDynamicBanner';
import ClickmonBanner from './components/ClickmonBanner';

axios.defaults.baseURL = import.meta.env.VITE_API_URL || '';

const AdSidebar = ({ side, platform, bannerId }: { side: 'left' | 'right', platform: 'coupang' | 'clickmon', bannerId?: number }) => (
  <div className={`ad-sidebar ad-sidebar-${side}`}>
    <span className="ad-label">ADVERTISEMENT</span>
    <div style={{ flex: 1, width: '100%', display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
      {platform === 'coupang' ? (
        <CoupangDynamicBanner id={bannerId} width="160" height="600" template="carousel" />
      ) : (
        <ClickmonBanner width="160" height="600" />
      )}
    </div>
  </div>
);

function App() {
  const { t } = useTranslation();
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState<{message: string, type: 'success' | 'error'} | null>(null);
  const [heroImg, setHeroImg] = useState('/images/heroes/hero_4.png');
  
  useEffect(() => {
    // 1~4 사이의 랜덤 숫자를 생성하여 이미지 선택
    const randomNum = Math.floor(Math.random() * 4) + 1;
    setHeroImg(`/images/heroes/hero_${randomNum}.png`);
  }, []);
  
  // 문의하기 모달 상태
  const [showContact, setShowContact] = useState(false);
  const [contactForm, setContactForm] = useState({ name: '', email: '', type: '일반 문의', message: '' });
  const [sending, setSending] = useState(false);

  const defaultBannerIds = [981842, 981849, 987286, 987287];
  const [leftPlatform] = useState<'coupang' | 'clickmon'>(() => Math.random() > 0.5 ? 'coupang' : 'clickmon');
  const [rightPlatform] = useState<'coupang' | 'clickmon'>(() => Math.random() > 0.5 ? 'coupang' : 'clickmon');

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const downloadApp = () => {
    window.open('https://www.dropbox.com/scl/fi/0ivftkpsg4nul9zjj1hvs/v0.2.2.zip?rlkey=mrv3eqipsphm336df0vlt6czx&st=m44313b4&dl=1');
  };

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactForm.name || !contactForm.email || !contactForm.message) {
      showToast(t('contactFail'), 'error'); // i18n 문구로 대체
      return;
    }
    setSending(true);
    try {
      // Cloudflare Workers 이메일 발송 API 연동
      await axios.post('https://subtitle-contact-api.misuni0313.workers.dev', {
        name: contactForm.name,
        email: contactForm.email,
        type: contactForm.type,
        message: contactForm.message
      });

      showToast(t('contactSuccess'));
      setShowContact(false);
      setContactForm({ name: '', email: '', type: t('contactTypeGeneral'), message: '' });
    } catch (e) {
      console.error("Mail Send Error:", e);
      showToast(t('contactFail'), 'error');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="container">
      <div className="hero-background-overlay"></div>
      
      <AdSidebar side="left" platform={leftPlatform} bannerId={defaultBannerIds[0]} />
      <AdSidebar side="right" platform={rightPlatform} bannerId={defaultBannerIds[1]} />

      <section className="hero-section">
        <div className="hero-content animate-in">
          <div className="badge">Global No.1 Subtitle Solution</div>
          <h1>The Next Generation of <br/><span>Subtitle Editing</span></h1>
          <p className="hero-subtitle" dangerouslySetInnerHTML={{ __html: t('heroSubtitle') }}></p>
          
          <div className="cta-group">
            <button className="main-download-btn" onClick={downloadApp}>
              <div className="btn-text">
                <span className="small">Download for Windows</span>
                <span className="large">SubMaster v0.2.6</span>
              </div>
            </button>
            <div className="os-support">Windows 10/11 Support | Virus-Free</div>
          </div>
        </div>
        
        <div className="hero-image-container animate-in-delay">
          <img src={heroImg} alt="App Preview" className="hero-img" />
          <div className="img-glow"></div>
        </div>
      </section>

      <section className="features-grid">
        <div className="feature-card glass-morphism">
          <h3>{t('extStep1')}</h3>
          <p>수동 작업은 이제 그만. AI가 두 자막을 대조하여 밀리초 단위로 정확하게 싱크를 맞춥니다.</p>
        </div>
        <div className="feature-card glass-morphism">
          <h3>{t('extStep2')}</h3>
          <p>문맥을 파악하는 Gemini 3.1 Flash-Lite 기반 번역으로 누락된 내용을 완벽하게 채워줍니다.</p>
        </div>
        <div className="feature-card glass-morphism">
          <h3>PGS / OCR Extraction</h3>
          <p>블루레이 PGS 자막부터 이미지 형태의 자막까지, 손실 없이 깨끗한 SRT 파일로 추출해냅니다.</p>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <span>SubMaster</span>
          </div>
          <div className="footer-links">
            <button className="contact-link-btn" onClick={() => setShowContact(true)}>{t('navContact')}</button>
          </div>
        </div>
        <div className="copyright">&copy; 2026 SubMaster Pro v0.2.6. Created with Passion.</div>
      </footer>

      {/* 문의하기 모달 */}
      {showContact && (
        <div className="modal-overlay" onClick={() => setShowContact(false)}>
          <div className="modal-content glass-morphism animate-in" onClick={e => e.stopPropagation()}>
            <h2>{t('contactTitle')}</h2>
            <form onSubmit={handleContactSubmit} className="contact-form">
              <div className="form-group">
                <label>{t('contactName')}</label>
                <input 
                  type="text" 
                  value={contactForm.name} 
                  onChange={e => setContactForm({...contactForm, name: e.target.value})}
                  placeholder={t('contactPlaceholderName')}
                />
              </div>
              <div className="form-group">
                <label>{t('contactEmail')}</label>
                <input 
                  type="email" 
                  value={contactForm.email} 
                  onChange={e => setContactForm({...contactForm, email: e.target.value})}
                  placeholder={t('contactPlaceholderEmail')}
                />
              </div>
              <div className="form-group">
                <label>{t('contactType')}</label>
                <select 
                  value={contactForm.type} 
                  onChange={e => setContactForm({...contactForm, type: e.target.value})}
                >
                  <option value={t('contactTypeGeneral')}>{t('contactTypeGeneral')}</option>
                  <option value={t('contactTypeUsage')}>{t('contactTypeUsage')}</option>
                  <option value={t('contactTypePartner')}>{t('contactTypePartner')}</option>
                </select>
              </div>
              <div className="form-group">
                <label>{t('contactMessage')}</label>
                <textarea 
                  rows={5}
                  value={contactForm.message} 
                  onChange={e => setContactForm({...contactForm, message: e.target.value})}
                  placeholder={t('contactPlaceholderMessage')}
                />
              </div>
              <div className="form-actions">
                <button type="button" className="cancel-btn" onClick={() => setShowContact(false)}>{t('contactCancel')}</button>
                <button type="submit" className="submit-btn" disabled={sending}>
                  {sending ? t('contactSending') : t('contactSend')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

export default App;

