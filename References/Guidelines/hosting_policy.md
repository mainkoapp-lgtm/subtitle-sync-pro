# ☁️ 글로벌 배포 및 무료 서버 정책 (2026년 기준)

본 문서는 전 세계 서비스를 위한 무료 호스팅 티어의 할당량 및 제한 사항을 공식적으로 정리한 문서입니다. (Rule 21 준수)

## 1. 프런트엔드 (UI & Static)

| 서비스 | 주요 무료 혜택 (무기한) | 제약 사항 및 특이점 |
| :--- | :--- | :--- |
| **Cloudflare Pages** 🏆 | - 대역폭/요청: **무제한**<br>- 글로벌 CDN 기본 탑재 | - **최종 선정**: 가장 강력한 무료 티어 제공<br>- 도메인: `*.pages.dev` |
| **Vercel** | - 대역폭: 100GB/월 | - 비상업적 용도 한정<br>- 할당량 초과 시 서비스 중단 위험 |
| **Firebase** | - 대역폭: 10GB/월 | - 구글 인프라 기반 안정성 |

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

## 💡 최종 배포 확정 전략
- **Frontend**: **Cloudflare Pages** ([https://subtitle-sync-pro.pages.dev/](https://subtitle-sync-pro.pages.dev/))
- **Backend/Engine**: **Render** (핵심 파이썬 로직 격리 배포)
- **Keep-alive**: 외부 모니터링 서비스로 Render 서버 상시 기상 유지 (무료 무한 가동)
- **Data/Notice**: **Firebase** (공지사항 JSON 관리)

*최종 확인 일자: 2026-04-18*

---

### 2026-04-18: [환경 설정] 실 배포 호스팅 정보 업데이트
- **내용**: 프런트엔드 호스팅 서비스를 Vercel에서 Cloudflare Pages로 변경하고 실제 운영 URL을 지침서에 반영함.
- **주소**: [https://subtitle-sync-pro.pages.dev/](https://subtitle-sync-pro.pages.dev/)
- **결과**: [성공] (사용자 확인 완료)
