import requests
import json
import os

# API 설정
# API 설정 (보안을 위해 .env 환경 변수에서 가져오거나 수동 입력 필요)
API_KEY = os.environ.get("CF_GLOBAL_KEY_MAINKOAPP", "YOUR_API_KEY")
EMAIL = os.environ.get("CF_EMAIL_MAINKOAPP", "mainkoapp@gmail.com")
DOMAIN = "mainko.net"
SUBDOMAIN = "subtitle"
TARGET = "subtitle-sync-pro.pages.dev"

headers = {
    "X-Auth-Email": EMAIL,
    "X-Auth-Key": API_KEY,
    "Content-Type": "application/json"
}

def setup_dns():
    try:
        # 1. Zone ID 조회
        print(f"[*] {DOMAIN}의 Zone ID를 조회 중...")
        res = requests.get("https://api.cloudflare.com/client/v4/zones", headers=headers, params={"name": DOMAIN})
        zones = res.json().get("result", [])
        
        if not zones:
            print(f"[!] {DOMAIN} 도메인을 찾을 수 없습니다. 계정 권한이나 도메인명을 확인해주세요.")
            return

        zone_id = zones[0]["id"]
        print(f"[+] Zone ID 확인 완료: {zone_id}")

        # 2. 기존 레코드 확인 (중복 방지)
        print(f"[*] 기존 {SUBDOMAIN}.{DOMAIN} 레코드를 확인 중...")
        res = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers, params={"name": f"{SUBDOMAIN}.{DOMAIN}"})
        records = res.json().get("result", [])

        if records:
            print(f"[!] 이미 {SUBDOMAIN}.{DOMAIN} 레코드가 존재합니다. (ID: {records[0]['id']})")
            print("[*] 기존 레코드를 업데이트합니다...")
            record_id = records[0]["id"]
            action_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
            method = requests.put
        else:
            print(f"[*] 새로운 CNAME 레코드를 생성합니다...")
            action_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            method = requests.post

        # 3. CNAME 레코드 생성/수정
        payload = {
            "type": "CNAME",
            "name": SUBDOMAIN,
            "content": TARGET,
            "proxied": True,
            "ttl": 1 # Auto
        }

        res = method(action_url, headers=headers, data=json.dumps(payload))
        result = res.json()

        if result.get("success"):
            print(f"\n[★] 성공! {SUBDOMAIN}.{DOMAIN} 주소가 {TARGET}으로 연결되었습니다.")
            print("[*] 이제 1~5분 이내에 주소 접속이 가능해집니다.")
        else:
            print(f"[!] 실패: {result.get('errors')}")

    except Exception as e:
        print(f"[!] 오류 발생: {str(e)}")

if __name__ == "__main__":
    setup_dns()
