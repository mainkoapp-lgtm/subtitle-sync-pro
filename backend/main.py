# [COMPLETED: 2026-04-11] 진행률 멈춤(Blocking) 해결 및 작업 취소(멈춤) 기능 구현 완료 (임의 수정 금지)
from fastapi import FastAPI, UploadFile, File, Form, Header, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from typing import List, Optional
import uvicorn
import os
import sys
from datetime import datetime

# 현재 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aligner import parse_srt, align_subtitles
from logger_config import logger, LOG_FILE_PATH
from dotenv import load_dotenv
import secrets # 보안 토큰 생성을 위한 라이브러리 추가
from datetime import timedelta

# .env 로드
load_dotenv()

# .env 로드
load_dotenv()

IS_PRODUCTION = os.getenv("IS_PRODUCTION", "false").lower() == "true"
MASTER_API_KEY = os.getenv("MASTER_API_KEY", "")

app = FastAPI(title="Subtitle Sync API")

api_router = APIRouter(prefix="/api")

from pydantic import BaseModel
class LogAction(BaseModel):
    message: str

@api_router.post("/log-action")
def log_action(data: LogAction):
    logger.info(f"[Frontend Action] {data.message}")
    return {"status": "success"}

# 토큰 관리 (API 접근 정책의 핵심)
# 구조: { "token_string": { "expire_at": datetime, "used": bool, "issued_at": datetime } }
reward_tokens = {}
tasks_progress = {}
tasks_cancelled = set()

def verify_job_token(token: Optional[str]) -> bool:
    """토큰의 유효성을 검증하고 소모합니다. (정책 검증기)"""
    if not IS_PRODUCTION:
        return True # 개발 모드에서는 무조건 통과
    
    if not token or token not in reward_tokens:
        return False
        
    token_data = reward_tokens[token]
    # 만료 여부 및 사용 여부 확인
    if token_data["used"] or datetime.now() > token_data["expire_at"]:
        return False
        
    # [사용 처리] 검증 직후 즉시 소모 (One-time Policy)
    token_data["used"] = True
    return True

@app.on_event("startup")
async def startup_event():
    logger.info("Subtitle Sync API Server Started")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@api_router.post("/sync")
async def sync_subtitles(
    ref_file: UploadFile = File(...),
    target_file: UploadFile = File(...),
    api_key: Optional[str] = Form(None),
    ai_model: str = Form("gemini-3.1-flash-lite-preview"),
    task_id: Optional[str] = Form(None),
    target_lang: str = Form("ko"),
    reward_token: Optional[str] = Form(None)
):
    # 1. [접근 정책 검증] 토큰이 없거나 유효하지 않으면 즉시 차단
    if not verify_job_token(reward_token):
        logger.warning(f"접근 거부: 유효하지 않은 토큰 (Token: {reward_token})")
        return {"status": "error", "message": "광고 시청 확인이 만료되었거나 유효하지 않습니다."}

    # 2. [API 키 터널링] 보안 노출 방지를 위해 서버 키 주입
    effective_api_key = api_key
    if IS_PRODUCTION:
        if not MASTER_API_KEY:
            logger.error("MASTER_API_KEY 미설정")
            return {"status": "error", "message": "서버 설정 오류"}
        effective_api_key = MASTER_API_KEY
        logger.info(f"보안 터널 통과: 마스터 키 주입 완료")

    logger.info(f"동기화 작업 시작: {ref_file.filename} (태스크: {task_id})")
    
    def set_progress(p: int):
        if task_id:
            tasks_progress[task_id] = p
            
    def check_cancel() -> bool:
        return task_id in tasks_cancelled
            
    def decode_content(content_bytes: bytes) -> str:
        # 시도할 인코딩 순서
        encodings = ['utf-8-sig', 'utf-8', 'cp949', 'utf-16', 'euc-kr']
        for enc in encodings:
            try:
                return content_bytes.decode(enc)
            except UnicodeDecodeError:
                continue
        return content_bytes.decode('utf-8', errors='ignore') # 최후의 수단

    ref_content = decode_content(await ref_file.read())
    target_content = decode_content(await target_file.read())
    
    from aligner import parse_subtitles
    from fastapi.concurrency import run_in_threadpool
    ref_blocks = parse_subtitles(ref_content, ref_file.filename)
    target_blocks = parse_subtitles(target_content, target_file.filename)
    
    try:
        result = await run_in_threadpool(
            align_subtitles,
            ref_subs=ref_blocks, 
            target_subs=target_blocks, 
            api_key=effective_api_key, 
            ai_model=ai_model, 
            progress_callback=set_progress,
            check_cancel=check_cancel,
            target_lang=target_lang
        )
    except Exception as e:
        if str(e) == "Cancelled":
            logger.info(f"작업 취소됨: {task_id}")
            return {"status": "cancelled", "message": "작업이 취소되었습니다."}
        
        # [수정] 에러 발생 시 로그에 상세 원인 기록 (사용자가 로그 보기 버튼으로 원인 파악 가능하게 함)
        logger.exception(f"싱크 처리 중 중대한 에러 발생 (태스크: {task_id}): {str(e)}")
        return {"status": "error", "message": f"싱크 중 오류 발생: {str(e)}"}

    
    if task_id and task_id in tasks_progress:
        del tasks_progress[task_id]
    if task_id and task_id in tasks_cancelled:
        tasks_cancelled.remove(task_id)
        
    return {
        "status": "success",
        "count": len(result),
        "data": result
    }

@api_router.get("/progress/{task_id}")
def get_progress(task_id: str):
    return {"progress": tasks_progress.get(task_id, 0)}

@api_router.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    tasks_cancelled.add(task_id)
    return {"status": "cancelled"}

@api_router.get("/config")
def get_config():
    """프런트엔드에 현재 서버 운영 모드를 반환합니다."""
    return {
        "isProduction": IS_PRODUCTION,
        "apiBaseUrl": os.getenv("API_BASE_URL", "http://localhost:8000")
    }

@api_router.post("/reward/verify")
async def verify_reward(ad_payload: Optional[dict] = None):
    """
    광고 완료 검증 및 작업 티켓 발행
    - ad_payload: 추후 광고 플랫폼의 SSV Signature를 검증하는 용도로 확장됩니다.
    """
    # 1. [미래 구현 예정] 여기에 SSV 검증 로직이 들어갑니다.
    # if not validate_adsense_ssv(ad_payload): raise HTTPException(...)
    
    # 2. 작업 티켓 발행
    new_token = secrets.token_urlsafe(32)
    reward_tokens[new_token] = {
        "expire_at": datetime.now() + timedelta(minutes=5),
        "used": False,
        "issued_at": datetime.now()
    }
    
    # 가비지 컬렉션 (만료 토큰 정리)
    now = datetime.now()
    expired = [tk for tk, d in reward_tokens.items() if now > d["expire_at"]]
    for tk in expired: del reward_tokens[tk]
    
    logger.info(f"신규 작업 티켓 발행 (정책 승인): {new_token[:8]}...")
    return {"status": "success", "token": new_token}

@api_router.get("/logs")
def get_logs():
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            return PlainTextResponse("".join(lines[-400:])) # 더 긴 로그 확인 가능하게 상향
    return PlainTextResponse("No logs found.")

@api_router.post("/clear-logs")
async def clear_logs():
    if os.path.exists(LOG_FILE_PATH):
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - INFO - 로그 초기화됨 (새로고침)\n")
    return {"status": "success"}

import json

TRAFFIC_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traffic_logs.json")

@api_router.post("/traffic")
async def log_traffic(data: dict):
    """방문자 유입 로그를 저장합니다."""
    # 필수 필드 추출
    log_entry = {
        "id": data.get("id", int(datetime.now().timestamp() * 1000)),
        "visitorId": data.get("visitorId", "unknown"),
        "source": data.get("source", "direct"),
        "referrer": data.get("referrer", "direct"),
        "country": data.get("country", "Unknown"),
        "device": data.get("device", "PC"),
        "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "timestamp": data.get("timestamp", int(datetime.now().timestamp() * 1000))
    }
    
    try:
        logs = []
        if os.path.exists(TRAFFIC_LOG_FILE):
            with open(TRAFFIC_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        
        logs.insert(0, log_entry)
        # 최신 5000건만 유지 (성능 및 용량 제한 고려)
        logs = logs[:5000]
        
        with open(TRAFFIC_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
            
        logger.info(f"방문자 로그 저장됨: {log_entry['source']} ({log_entry['country']})")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"방문자 로그 저장 실패: {str(e)}")
        return {"status": "error", "message": str(e)}

from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class ContactForm(BaseModel):
    name: str
    email: str
    type: str # 협찬/제휴 or 일반 문의
    message: str

@api_router.post("/contact")
async def send_contact_email(form: ContactForm):
    """프론트엔드에 이메일 주소를 노출하지 않고 백엔드에서만 처리를 담당하는 보안 발송기"""
    logger.info(f"--- 신규 접수 ({form.type}) --- 발신자 명: {form.name} ({form.email})")
    
    target_email = "mainkoapp@gmail.com"
    # 메일 제목 및 본문 첫 줄 포맷팅 (사용자 요청 사항 반영)
    email_type = "광고협찬" if "협찬" in form.type else "일반문의"
    subject = f"[자막 싱크] {email_type} - {form.name}님"
    body = f"[자막 싱크] {email_type}\n\n보낸사람: {form.name} ({form.email})\n\n내용:\n{form.message}"
    
    msg = MIMEMultipart()
    msg['From'] = target_email
    msg['To'] = target_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # 보안: .env 등에서 구글 앱 비밀번호를 로드하여 사용
    smtp_pwd = os.environ.get("SMTP_APP_PASSWORD", "") 
    
    if not smtp_pwd:
        logger.warning(f"[SMTP 패스워드 미설정] 로컬 로그에만 문의를 기록합니다: {body}")
        # 프론트 오류가 나지 않도록 일단 성공으로 처리
        return {"status": "success", "note": "Log Only (No PWD)"}
        
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(target_email, smtp_pwd)
        server.send_message(msg)
        server.quit()
        logger.info("보안 문의 이메일 발송 완료.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"이메일 발송 실패: {str(e)}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Mail server error")

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "subfast-master-key-default-2026") # 보안: .env에서 로드

@api_router.get("/admin/traffic")
async def get_traffic_logs(x_admin_key: Optional[str] = Header(None)):
    """관리자용 방문자 통계를 반환합니다 (비밀 키 검증)."""
    if x_admin_key != ADMIN_SECRET_KEY:
        logger.warning(f"승인되지 않은 관리자 API 접근 시도 차단됨 (Key: {x_admin_key})")
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Unauthorized access")
        
    if os.path.exists(TRAFFIC_LOG_FILE):
        with open(TRAFFIC_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
