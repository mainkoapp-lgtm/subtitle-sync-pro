# ☁️ 글로벌 배포 및 무료 서버 정책 (2026년 기준)

본 문서는 전 세계 서비스를 위한 무료 호스팅 티어의 할당량 및 제한 사항을 공식적으로 정리한 문서입니다. (Rule 21 준수)

## 1. 프런트엔드 (UI & Static)

| 서비스 | 주요 무료 혜택 (무기한) | 제약 사항 및 특이점 |
| :--- | :--- | :--- |
| **Cloudflare Pages** 🏆 | - **메인 홈페이지 호스팅** (`mainko.net`) | - **최종 선정**: 무제한 대역폭과 글로벌 속도 우위<br>- **관리 계정**: `mainkoapp@gmail.com` |
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
- **Frontend**: **Cloudflare Pages** ([https://mainko.net](https://mainko.net))
- **Backend/Engine**: **Render** (`subtitle-sync-api` 서비스)
- **Trackers**: **Cloudflare Workers** (`ad-tracker` - 광고 클릭 로그)
- **Data/Program Resources**: **Firebase** (`subfast-manager` - 배너 및 업데이트 파일)
- **Extractor App**: **Tauri (Main)** / **Python (Legacy/Backup)**
- **Ad Platform**: **Monetag** / **Coupang Partners** (계정 보유 및 전략 수립 완료)

*최종 확인 일자: 2026-04-18*

---

### 2026-04-22: [서버/호스팅] 전체 인프라 운영 현황 전수 확인 및 업데이트
- **문제점**: 이전 정보에서 Vercel 사용 여부 및 서비스별 역할 분담(홈페이지 vs 프로그램 리소스)이 불분명했음. API 직접 호출을 통해 실제 운영 상태를 재검증함.
- **수정 과정 및 핵심 코드**: 
  - **Vercel**: 미사용 확인 (서비스 목록에서 비활성화 처리)
  - **Cloudflare**: 홈페이지(`mainko.net`) 호스팅 및 광고 트래커 워커 담당 확인. (관리 계정: `mainkoapp`, `misuni0313`)
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
