# ☁️ 글로벌 배포 및 무료 서버 정책 (2026년 기준)

본 문서는 전 세계 서비스를 위한 무료 호스팅 티어의 할당량 및 제한 사항을 공식적으로 정리한 문서입니다. (Rule 21 준수)

## 1. 프런트엔드 (UI & Static)

| 서비스 | 주요 무료 혜택 (무기한) | 제약 사항 및 특이점 |
| :--- | :--- | :--- |
| **Cloudflare Pages** 🏆 | - **메인 홈페이지 호스팅** (`subtitle.mainko.net`) | - **최종 선정**: 무제한 대역폭과 글로벌 속도 우위<br>- **관리 계정**: `mainkoapp@gmail.com` |
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

### 2026-05-22: [인프라/역할조정] 백엔드 및 프런트엔드 서버 역할 축소 및 데스크톱 앱 일원화 배포
- **문제점**: 무제한적인 웹 API 요청으로 인한 Render 프리 티어 한도 초과 및 서버 과부하를 예방하고, 효율적인 자원 배치를 위해 웹과 데스크톱의 인프라 역할을 명확히 재정의해야 함.
- **수정 과정 및 핵심 내용**:
  - **백엔드(Render)**: `/sync` 엔진 연동을 제거하고 경량 자막 유틸 API (`backend/main.py`)로 역할을 축소하여 750시간/월 무료 티어 내 안정적 운영 보장.
  - **프런트엔드(Cloudflare Pages)**: 브라우저 자막 싱크 웹앱에서 데스크톱 자막 솔루션 **SubMaster**의 공식 홈페이지/랜딩 페이지로 전격 리브랜딩 및 전환 배포 완료.
  - **배포 방식**: Cloudflare Pages의 자동 빌드/배포 환경 유지, Dropbox 직링크를 통한 데스크톱(v0.2.6) 다운로드 배포 체계 연동.
- **결과**: [성공]

