import re

with open('d:/Project Temporary/subtitle/subtitle_development/frontend/src/App.tsx', 'r', encoding='utf-8') as f:
    code = f.read()

# Add import
code = code.replace("import { Upload, CheckCircle, AlertCircle, RefreshCcw, Download, Copy, Languages, XCircle } from 'lucide-react';", "import { Upload, CheckCircle, AlertCircle, RefreshCcw, Download, Copy, Languages, XCircle } from 'lucide-react';\nimport { useTranslation, setLanguage, Language } from './i18n';")

# Add hook
code = code.replace("function App() {", "function App() {\n  const { t, lang } = useTranslation();")

# Inject language detection into the tracker
orig_tracker = '''      let country = 'Unknown';
      try {
        const res = await fetch('https://ipapi.co/json/');
        const data = await res.json();
        country = data.country_name || 'Unknown';
      } catch (e) {'''

new_tracker = '''      let country = 'Unknown';
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
        
      } catch (e) {
        const navLang = navigator.language.substring(0, 2);
        if (['ko', 'ja', 'zh', 'hi'].includes(navLang)) {
          setLanguage(navLang as Language);
        }'''
code = code.replace(orig_tracker, new_tracker)

# Replace all texts
replacements = [
    ("<p>참조 자막에 맞춰 번역 자막의 싱크를 자동으로 교정합니다.</p>", "<p>{t('appDesc')}</p>"),
    ("실시간 로그 확인", "{t('logCheck')}"),
    ("AI 엔진:", "{t('aiEngine')}"),
    ("API Key:", "{t('apiKeyLabel')}"),
    ("placeholder=\"API 키를 입력하세요\"", "placeholder={t('apiKeyPlaceholder')}"),
    (">설정 저장<", ">{t('saveSettings')}<"),
    ("<h3>참조 자막 (Synced)</h3>", "<h3>{t('refSubTitle')}</h3>"),
    ("<p>원본 영어 자막 등 싱크가 맞는 파일</p>", "<p>{t('refSubDesc')}</p>"),
    ("alert('.srt 또는 .smi 파일만 가능합니다.');", "alert(t('onlySrtSmi'));"),
    ("alert('.srt 또는 .smi 형식의 자막 파일만 업로드할 수 있습니다.');", "alert(t('onlySrtSmiAlert'));"),
    ("<h3>대상 자막 (Unsynced)</h3>", "<h3>{t('targetSubTitle')}</h3>"),
    ("<p>싱크를 맞출 번역 자막 파일</p>", "<p>{t('targetSubDesc')}</p>"),
    ("`⚠️ 서로 다른 자막일 수 있습니다 (유사도 ${(similarity * 100).toFixed(0)}%)`", "t('mismatchWarning', { n: (similarity * 100).toFixed(0) })"),
    ("자동 싱크 맞추기", "{t('syncStart')}"),
    ("멈춤", "{t('syncStop')}"),
    ("초기화", "{t('syncReset')}"),
    ("시스템 로그 (최근 200줄)", "{t('sysLogs')}"),
    ("로그 복사", "{t('logCopy')}"),
    ("닫기", "{t('logClose')}"),
    ("동기화 결과 (총 {results.length}개)", "{t('syncResultTitle', { n: results.length })}"),
    ("원형 매칭:", "{t('originMatched')}"),
    ("AI 번역 보완:", "{t('aiTranslated')}"),
    ("실패:", "{t('failedCount')}"),
    ("결과 다운로드", "{t('downloadResult')}"),
    ("유사도: {(res.score * 100).toFixed(1)}%", "{t('similarity')} {(res.score * 100).toFixed(1)}%"),
    ("매칭 실패 (시간 정보만 복제됨)", "{t('matchFailed')}"),
    ("외 {results.length - displayLimit}개의 문장이 더 있습니다.", "{t('moreResults', { n: results.length - displayLimit })}"),
    ("전체 결과 보기 ({results.length}개)", "{t('showAll', { n: results.length })}"),
    ("`사용자 설정 저장됨 (모델: ${aiModel}, API Key: ${maskedKey})`", "t('settingsSavedLog', { model: aiModel, key: maskedKey })"),
    ("'설정이 안전하게 저장되었습니다.'", "t('settingsSavedToast')"),
    ("'사용자가 실시간 로그 확인을 요청함'", "t('logRequestLog')"),
    ("'로그를 불러올 수 없습니다.'", "t('logFetchFailToast')"),
    ("`파일 드롭됨: ${file.name} (${type === 'ref' ? '참조용' : '대상용'})`", "t('fileDropLog', { filename: file.name, type: type === 'ref' ? t('refType') : t('targetType') })"),
    ("'모든 데이터와 로그가 초기화되었습니다.'", "t('resetLog')"),
    ("'데이터는 초기화되었으나 로그 초기화에 실패했습니다.'", "t('resetFailToast')"),
    ("'작업이 취소되었습니다.'", "t('taskCancelledToast')"),
    ("'매칭률이 매우 낮습니다(30% 미만). 영화가 일치하는지 다시 확인해 주세요.'", "t('lowMatchToast')"),
    ("`[경고] 낮은 매칭률 발생: ${(rate * 100).toFixed(1)}%`", "t('lowMatchLog', { n: (rate * 100).toFixed(1) })"),
    ("`동기화 완료! (${(rate * 100).toFixed(1)}% 매칭 성공)`", "t('syncCompleteToast', { n: (rate * 100).toFixed(1) })"),
    ("'싱크 작업에 실패했습니다.'", "t('syncFailToast')"),
    ("`사용자가 결과 자막(${results.length}개 블록)을 다운로드함`", "t('downloadLog', { n: results.length })")
]

for old, new_s in replacements:
    code = code.replace(old, new_s)

# Fix the results counts
code = code.replace(
    "원형 매칭: <strong>{results.filter(r => r.matched && !r.translated).length}</strong>개 <span style={{margin: '0 4px'}}>|</span>",
    "{t('originMatched')} <strong>{results.filter(r => r.matched && !r.translated).length}</strong> <span style={{margin: '0 4px'}}>|</span>"
)
code = code.replace(
    "{t('aiTranslated')} <strong style={{ color: '#818cf8' }}>{results.filter(r => r.translated).length}</strong>개 <span style={{margin: '0 4px'}}>|</span>",
    "{t('aiTranslated')} <strong style={{ color: '#818cf8' }}>{results.filter(r => r.translated).length}</strong> <span style={{margin: '0 4px'}}>|</span>"
)
code = code.replace(
    "{t('failedCount')} <strong style={{ color: '#ef4444' }}>{results.filter(r => !r.matched).length}</strong>개",
    "{t('failedCount')} <strong style={{ color: '#ef4444' }}>{results.filter(r => !r.matched).length}</strong>"
)

# Add Language Selector visually in Header
header_old = '''        <div className="header-actions">
          <button className="log-btn" onClick={fetchLogs}>{t('logCheck')}</button>
        </div>'''
header_new = '''        <div className="header-actions">
          <select value={lang} onChange={(e) => setLanguage(e.target.value as Language)} className="lang-select" style={{ marginRight: '10px', padding: '6px 12px', borderRadius: '8px', background: 'rgba(255, 255, 255, 0.1)', color: 'white', border: '1px solid rgba(255,255,255,0.2)' }}>
            <option value="ko" style={{color: 'black'}}>한국어</option>
            <option value="en" style={{color: 'black'}}>English</option>
            <option value="ja" style={{color: 'black'}}>日本語</option>
            <option value="zh" style={{color: 'black'}}>中文</option>
            <option value="hi" style={{color: 'black'}}>हिन्दी</option>
          </select>
          <button className="log-btn" onClick={fetchLogs}>{t('logCheck')}</button>
        </div>'''
code = code.replace(header_old, header_new)

with open('d:/Project Temporary/subtitle/subtitle_development/frontend/src/App.tsx', 'w', encoding='utf-8') as f:
    f.write(code)

print('Rewrite complete')
