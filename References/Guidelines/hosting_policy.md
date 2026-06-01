# ☁️ 글로벌 배포 및 무료 서버 정책 (2026년 기준)

본 문서는 전 세계 서비스를 위한 무료 호스팅 티어의 할당량 및 제한 사항을 공식적으로 정리한 문서입니다. (Rule 21 준수)

## 1. 프런트엔드 (UI & Static)

| 서비스 | 주요 무료 혜택 (무기한) | 제약 사항 및 특이점 |
| :--- | :--- | :--- |
| **Cloudflare Pages** 🏆 | - **메인 홈페이지 호스팅** (`subtitle.mainko.net`) | - **최종 선정**: 무제한 대역폭과 글로벌 속도 우위<br>- **관리 계정**: `misuni0313@gmail.com` |
| **Firebase Hosting** | - **프로그램 리소스 & 배너** | - **용도**: 자막 추출기 앱 전용 이미지/배너/내부 공지 관리<br>- **프로젝트**: `subfast-manager` |
| **Vercel** | - **미사용** | - 현재 프로젝트에서 호스팅 용도로 사용 안 함 |

## 2. 백엔드 및 엔진 (Python / API)

AI 자막 매칭 엔진(`aligner.py`)을 구동하기 위한 서버 정책입니다.

| 서비스 | 주요 무료 혜택 | 제약 사항 및 특이점 |
| :--- | :--- | :--- |
| **Render** 🏆 | - 서버 가동: 750시간/월<br>- HTTPS 자동 지원 | - **Cold Start 방지**: 핑 서비스(UptimeRobot 등)를 이용해 10~14분 주기로 호출하여 **24시간 무중단 가동** 유지 (꼼수 적용)<br>- 영구 무료 제공 (신용카드 불필요) |
| **Railway** | -Trial $5 크레딧 (최초 1회) | - **30일 기간 제한**: 체험 종료 후 Hobby 플랜($5/월) 전환 필수<br>- 신용카드 등록 필수 (Abuse 방지) |
| **Vercel Functions** | - 실행 횟수: 100만 회/월 | - **Time Limit**: 요청 1개당 실행 시간 제한(약 10~60초) 존재<br>- 긴 시간 소요되는 자막 매칭 작업 시 Timeout 위험 |

---

## 🛡️ 기술 보호 및 보안 정책 (Security First)
1. **Source Isolation**: 핵심 엔진 소스(`backend/`)는 GitHub Private Repo에 보관하며, 절대 Client-side로 배포하지 않는다.
2. **Secret Management**: 모든 API Key 및 AI 프롬프트는 서버의 'Environment Variables' 환경에만 등록하여 소스 코드 유출 시에도 동작하지 않도록 한다.
3. **API Tunneling**: 프런트엔드에서 백엔드 엔진을 호출할 때 도메인 마스킹을 적용하여 실제 서버 주소 노출을 최소화한다.

## 💡 최종 배포 확정 전략 (Verified)
- **Frontend**: **Cloudflare Pages / Firebase Hosting** ([https://subtitle.mainko.net](https://subtitle.mainko.net))
- **Backend/Engine**: **Render** (`subtitle-sync-api` 서비스)
- **Trackers**: **Cloudflare Workers** (`ad-tracker` - 광고 클릭 로그)
- **Data/Program Resources**: **Firebase** (`subfast-manager` - 배너 및 업데이트 파일)
- **Extractor App**: **Tauri (Main)** / **Python (Legacy/Backup)**
- **Ad Platform**: **Monetag** / **Coupang Partners** (계정 보유 및 전략 수립 완료)

*최종 확인 일자: 2026-06-02*

---

### 2026-04-22: [서버/호스팅] 전체 인프라 운영 현황 전수 확인 및 업데이트
- **문제점**: 이전 정보에서 Vercel 사용 여부 및 서비스별 역할 분담(홈페이지 vs 프로그램 리소스)이 불분명했음. API 직접 호출을 통해 실제 운영 상태를 재검증함.
- **수정 과정 및 핵심 코드**: 
   - **Vercel**: 미사용 확인 (서비스 목록에서 비활성화 처리)
   - **Cloudflare/Firebase**: 홈페이지(`subtitle.mainko.net`) 호스팅 및 광고 트래커 워커 담당 확인. (관리 계정: `mainkoapp`, `misuni0313`)
  - **Render**: 파이썬 백엔드 API 서버(`subtitle-sync-api`) 구동 확인. (계정: `misuni0313`)
  - **Firebase**: 자막 추출기 프로그램 전용 리소스 및 배너 호스팅(`subfast-manager`) 담당 확인. (계정: `misuni0313`)
- **결과**: [성공] (실제 서버 인스턴스 정보와 일치함 확인)

### 2026-04-22: [배너/배포] SubFast Manager 배너 서버(Firebase) 최종 배포
- **내용**: `img/flowstatetimer/index.html` 소스를 서버(`subfast-manager.web.app`)에 반영함.
- **수정 과정**: `FIREBASE_TOKEN`을 사용하여 `firebase deploy` 명령을 성공적으로 수행함.
- **결과**: [성공] (배포 완료: https://subfast-manager.web.app)

### 2026-04-22: [플랫폼/전략] 자막 추출기 메인 개발 플랫폼 전환
- **내용**: 자막 추출기(Extractor)의 메인 플랫폼을 Python에서 **Tauri(Rust/React)**로 전격 교체함.
- **수정 과정**: 
  - `.agent/rules/extractor_platform.md` 신규 규칙 생성.
  - 기존 파이썬 버전은 삭제하지 않고 `Legacy/Backup` 용도로 보존 결정.
  - 인프라 규칙에서 Vercel 정보를 삭제하고 Cloudflare 중심으로 현행화함.
- **결과**: [성공] (지침서 및 에이전트 규칙 반영 완료)

### 2026-05-10: [인프라/확장성] 대규모 동시 접속(100명 이상) 대응을 위한 백엔드 아키텍처 상담
- **문제점**: 현재 Render 프리 티어 서버와 JSON 기반 로그 시스템으로는 수백 명의 동시 접속을 처리하기에 자원(RAM/CPU)이 부족하고 데이터 유실(휘발성 저장소) 위험이 매우 높음.
- **수정 과정 및 핵심 내용**:
  - **AI 쿼터**: 사용자 개별 API 키를 사용하게 함으로써 AI 할당량 문제는 해결됨을 확인.
  - **서버 부하**: 수백 명의 동시 파싱 및 비교 연산을 위해 최소 **Starter(2GB RAM)** 이상 또는 **Pro(4GB+)** 플랜 권장.
  - **데이터 관리**: 휘발성인 JSON 시스템을 즉시 **PostgreSQL(DB)**로 교체하여 동시 쓰기 안정성 및 영구 저장소 확보 필수.
  - **비동기 처리**: 서버 블로킹 방지를 위해 **Celery + Redis** 등 작업 큐(Task Queue) 도입 필요성 강조.
- **결과**: [성공] (인프라 확장 전략 수립 완료 및 지침서 기록)

### 2026-05-11: [SEO] 네이버 사이트 소유 확인 및 메타 디스크립션 추가
- **문제점**: 네이버 서치어드바이저 사이트 등록을 위한 소유 확인 태그 부재 및 검색 엔진 최적화(SEO)를 위한 메타 설명(Description) 부족.
- **수정 과정 및 핵심 코드**: 
  - `frontend/index.html`: 
    - `<meta name="naver-site-verification" content="519c7082a42b092e9cffeeed570322821c548231" />` 추가.
    - `<meta name="description" content="Subtitle Sync Pro는 영상과 맞지 않는 자막 싱크를 인공지능(AI) 기술로 완벽하게 해결합니다. 자막 밀림 현상, 싱크가 맞지 않는 자막 파일을 업로드만 하세요. 한국어, 영어 등 다국어 자막 싱크 맞추기를 가장 빠르고 정확하게 지원합니다. 지금 바로 무료로 자막 싱크를 복구해보세요." />` 추가 (자막 싱크 맞추기, 자막 밀림 등 핵심 키워드 포함, 455자 이하 준수).
  - GitHub `master` 브랜치 푸시를 통한 자동 배포 완료.
- **결과**: [성공]

---

### 2026-06-02: [배포] 새 홈페이지(SubMaster 랜딩 페이지 v2) 서버 교체 배포 & 초경량 문의 텔레그램 연동 및 Render 서버 정리
- **대상 파일**: [frontend/src/App.tsx](file:///D:/Project%20Temporary/subtitle/subtitle_development/frontend/src/App.tsx), [server/cf_contact_worker/](file:///D:/Project%20Temporary/subtitle/subtitle_development/server/cf_contact_worker/) (index.js, wrangler.toml)
- **원인 및 문제점**: 기존 Subtitle Sync Pro 단순 UI에서 SubMaster 풀 랜딩 페이지로 교체 요청 및 "문의 / 협찬" 모달 메일 수신 요구 발생.
- **수정 요약**: 
  1. **텔레그램 백엔드 중계 서버 배포**: Cloudflare Workers(`subtitle-contact-api`)를 배포하여 클라이언트에서 텔레그램 Bot API로 직접 요청 시 발생하는 CORS 및 보안 토큰 노출 문제를 원천 해결.
  2. **자격 증명 서버 격리**: 텔레그램 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`를 Cloudflare Worker Secret으로 안전하게 등록 및 격리하여 클라이언트 단에 절대 노출되지 않도록 조치.
  3. **axios baseURL 충돌 방지**: 프런트엔드(`App.tsx`) 상단의 axios 전역 baseURL과의 충돌을 방지하기 위해 `fetch` API를 사용하여 Worker URL로만 안전하게 데이터를 전송하도록 구현.
  4. **환경 변수 유실 및 보안 위험 제거**: `frontend/.env` 파일에서 민감 정보인 `VITE_TELEGRAM_*`을 완전히 제거하여 Git 및 빌드 결과물 유출 위협을 영구 차단.
  5. **불필요한 구버전 서버 정리**: 더 이상 사용하지 않는 Render 백엔드 서버용 설정 파일인 `render_service.json`을 `backup/` 디렉토리로 안전하게 격리하고 프로젝트 루트에서 삭제.
  6. **배포**: Git `master` 브랜치에 코드를 Push하여 Cloudflare Pages로 연동된 실서비스에 자동 빌드 및 배포 완료.
- **최종 아키텍처**: `홈페이지 문의 작성 → Cloudflare Worker(자격증명 Secret 격리) → 텔레그램 Bot API → 텔레그램 실시간 수신`
- **결과**: [성공] (실제 홈페이지 문의 모달을 통한 텔레그램 실시간 수신 확인 완료)

### 2026-06-02: [보안] Cloudflare Worker CORS 도메인 제한 + 자체 도메인(contact-api.mainko.net) 연결
- **대상 파일**: [server/cf_contact_worker/index.js](file:///D:/Project%20Temporary/subtitle/subtitle_development/server/cf_contact_worker/index.js), [frontend/src/App.tsx](file:///D:/Project%20Temporary/subtitle/subtitle_development/frontend/src/App.tsx)
- **원인 및 문제점**: 
  1. Worker CORS가 `*`(전체 허용)으로 설정되어 타 사이트에서 Worker URL을 도용하여 스팸 발송이 가능한 취약점 존재.
  2. Worker URL(`subtitle-contact-api.misuni0313.workers.dev`)에 계정명(`misuni0313`)이 공개적으로 노출되는 개인정보 문제.
- **수정 요약**: 
  1. **CORS 도메인 제한**: `ALLOWED_ORIGINS` 배열을 정의하여 `https://subtitle.mainko.net`, 로컬 개발 환경(`localhost:5173/4173`)만 허용. 허용되지 않은 Origin의 preflight(OPTIONS) 및 본 요청(POST) 모두 **403 Forbidden**으로 차단.
  2. **자체 도메인 연결**: Cloudflare `mainko.net` Zone에 CNAME 레코드 `contact-api → subtitle-contact-api.misuni0313.workers.dev` (Proxied) 등록. `App.tsx`의 fetch URL을 `https://contact-api.mainko.net`으로 교체하여 계정명 완전 은닉.
- **최종 인프라**: `subtitle.mainko.net → https://contact-api.mainko.net (CNAME, Proxied) → subtitle-contact-api Worker → 텔레그램`
- **결과**: [테스트 필요] (https://subtitle.mainko.net 문의 모달 → 텔레그램 수신 재확인 필요)

---

## 🚀 배포 및 텔레그램 연동 가이드 (차후 배포 작업 참고용)

### 1. 프런트엔드 배포 (Cloudflare Pages)
- **배포 방식**: GitHub `master` 브랜치에 코드 Push 시 Cloudflare Pages에서 자동으로 감지하여 빌드 및 배포를 수행합니다.
- **배포 프로세스**:
  1. 로컬에서 수정 및 테스트 완료.
  2. `git add .` -> `git commit -m "commit message"` -> `git push origin master` 수행.
  3. Cloudflare Pages 대시보드에서 빌드 진행 상황 확인 (통상 1~3분 소요).
  4. 도메인(`https://subtitle.mainko.net`) 접속 후 업데이트 반영 사항 확인.

### 2. 백엔드 중계 서버 배포 (Cloudflare Workers)
- **위치**: `D:\Project Temporary\subtitle\subtitle_development\server\cf_contact_worker\`
- **배포 준비 및 명령어**:
  - `wrangler` CLI를 이용해 Cloudflare Workers 서버에 배포합니다.
  - 배포 명령어: `npx wrangler deploy`
- **텔레그램 Secret Key 관리 (보안 필수)**:
  - 텔레그램 자격 증명(토큰, ID)은 절대 프런트엔드 코드나 `.env`에 평문으로 적어서는 안 됩니다.
  - Worker Secret을 통해 서버 상에 격리되어야 합니다.
  - **Secret 등록 명령어**:
    ```bash
    npx wrangler secret put TELEGRAM_BOT_TOKEN
    # (프롬프트 입력창에 텔레그램 봇 토큰 입력)
    
    npx wrangler secret put TELEGRAM_CHAT_ID
    # (프롬프트 입력창에 텔레그램 채팅방/채널 ID 입력)
    ```
  - 등록된 Secret은 Worker 코드 내에서 전역 바인딩되어 `env.TELEGRAM_BOT_TOKEN`, `env.TELEGRAM_CHAT_ID`로 안전하게 호출됩니다.

### 3. 불필요한 백엔드 서버 정리 (Render 은퇴)
- **정리 대상**: 이전 자막 매칭용 파이썬 백엔드 서버 (`subtitle-sync-api`)
- **수행 사항**:
  - 로컬 코드 레벨 정리: `render_service.json` 설정 파일을 `backup/` 디렉토리로 이동 및 루트에서 안전하게 삭제 완료.
  - **차후 인프라 권장 정리 작업 (사용자 직접 수행 필요)**:
    1. Render 대시보드(`https://dashboard.render.com`)에 접속하여 `subtitle-sync-api` 서비스를 **Suspend**(중지) 또는 **Delete**(삭제) 처리합니다.
    2. UptimeRobot 등 외부 모니터링 핑 서비스에 등록된 구 백엔드 서버(Render URL) 모니터링 항목을 **Pause** 또는 **Delete** 처리하여 불필요한 호출과 메일 알림을 영구 중단합니다.

---

### 2026-05-22: [인프라/역할조정] 백엔드 및 프런트엔드 서버 역할 축소 및 데스크톱 앱 일원화 배포
- **문제점**: 무제한적인 웹 API 요청으로 인한 Render 프리 티어 한도 초과 및 서버 과부하를 예방하고, 효율적인 자원 배치를 위해 웹과 데스크톱의 인프라 역할을 명확히 재정의해야 함.
- **수정 과정 및 핵심 내용**:
  - **백엔드(Render)**: `/sync` 엔진 연동을 제거하고 경량 자막 유틸 API (`backend/main.py`)로 역할을 축소하여 750시간/월 무료 티어 내 안정적 운영 보장.
  - **프런트엔드(Cloudflare Pages)**: 브라우저 자막 싱크 웹앱에서 데스크톱 자막 솔루션 **SubMaster**의 공식 홈페이지/랜딩 페이지로 전격 리브랜딩 및 전환 배포 완료.
  - **배포 방식**: Cloudflare Pages의 자동 빌드/배포 환경 유지, Dropbox 직링크를 통한 데스크톱(v0.2.6) 다운로드 배포 체계 연동.
- **결과**: [성공]

### 2026-06-02: [계정/정보정정] Cloudflare 메인 공식 계정 및 R2 소유 계정 정정
- **대상 파일**: [hosting_policy.md](file:///D:/Project%20Temporary/subtitle/subtitle_development/References/Guidelines/hosting_policy.md) (섹션: `Cloudflare Pages 관리 계정`), [.env](file:///D:/Project%20Temporary/subtitle/subtitle_development/.env)
- **원인 및 문제점**: Cloudflare 메인 계정을 깃허브 계정인 `mainkoapp@gmail.com`으로 잘못 오인하여 지침서 및 설정 주석에 잘못 반영되어 있었음. 실제 관리 대장 확인을 통해 `misuni0313@gmail.com`이 메인 Cloudflare 실서비스 운영 및 R2 계정임을 교차 검증함.
- **수정 요약**: `hosting_policy.md` 가이드라인 문서와 `.env` 설정 내 이메일 설명 주석의 Cloudflare 계정 역할을 `misuni0313@gmail.com`이 메인 실서비스 및 R2 소유 계정이 되도록 모두 정상 정정 완료함.
- **결과**: [성공]

### 2026-06-02: [배포/자동화] 영구 고정 GitHub Releases 배포 체계 연동 및 홈페이지 다운로드 링크 교체
- **대상 파일**: [App.tsx](file:///D:/Project%20Temporary/subtitle/subtitle_development/frontend/src/App.tsx) (함수: `downloadApp`)
- **원인 및 문제점**: 드롭박스(Dropbox)를 통한 수동 업데이트는 매 버전 업로드 시 다운로드 링크가 깨지거나 매번 홈페이지 코드를 고친 후 재배포해야 하는 극심한 번거로움이 존재함. 또한 Firebase Storage는 무료 1GB 일일 트래픽 초과 시 먹통이 되는 한계가 있음.
- **수정 요약**: 
  1. **무제한 대역폭 배포망 확보**: 깃허브 공식 정책 상 Releases 다운로드 트래픽은 100% 무제한 무료이고 초과 요금이 청구되지 않음을 공식 홈페이지를 통해 교차 검증 및 확정.
  2. **GitHub Releases 릴리스 생성 및 에셋 업로드**: `mainkoapp-lgtm/subtitle-sync-pro` 공식 레포에 `v0.2.6` 릴리스를 생성하고 191MB의 `SubMaster.zip` 빌드 아웃풋을 무사히 업로드 완료.
  3. **영구 최신버전 고정 연동**: `App.tsx` 내의 수동 Dropbox 링크를 영구 최신 버전을 다운로드하게 고정되는 `https://github.com/mainkoapp-lgtm/subtitle-sync-pro/releases/latest/download/SubMaster.zip` 주소로 완벽히 리다이렉트 교체.
- **결과**: [성공]
