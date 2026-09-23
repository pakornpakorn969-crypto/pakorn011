import os
import json
import random
import asyncio
import hashlib
import uuid
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Form, Cookie, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

# ==========================================
# 1. DATABASE SETUP (SQLite)
# ==========================================
DB_FILE = "omega_titan_quantum.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{DB_FILE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="operator")  # "admin" หรือ "operator"

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="UNKNOWN THREAT")
    incident_type = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    severity = Column(String, default="CRITICAL")
    created_at = Column(DateTime, default=datetime.utcnow)

class ABMLaunchRequest(BaseModel):
    target_lat: float
    target_lng: float
    incident_id: Optional[int] = None

# In-Memory Active Sessions Store
ACTIVE_SESSIONS = {}  # session_token -> {"username": str, "role": str}

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed_default_users():
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(username="pakorn").first():
            db.add(User(username="pakorn", password_hash=hash_password("admin123"), role="admin"))
        if not db.query(User).filter_by(username="operator").first():
            db.add(User(username="operator", password_hash=hash_password("user123"), role="operator"))
        db.commit()
    finally:
        db.close()

# ==========================================
# 2. WEBSOCKET BROADCAST MANAGER
# ==========================================
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ==========================================
# 3. REAL-TIME THREAT SIMULATION LOOP
# ==========================================
async def auto_simulation_loop():
    await asyncio.sleep(2)
    threat_types = [
        ("🚨 ตรวจพบขีปนาวุธข้ามทวีป ICBM", "ICBM_LAUNCH", "#dc2626"),
        ("⚠️ ฝูงโดรน Hypersonic รุกล้ำเขตน่านฟ้า", "DRONE_SWARM", "#d97706"),
        ("⚡ การโจมตี Quantum Cybernetics ต่อดาวเทียม", "SATELLITE_HACK", "#0284c7"),
        ("🛸 วัตถุบินไม่ปรากฏนามเคลื่อนที่ความเร็ว 15 Mach", "UFO_TACTICAL", "#7c3aed")
    ]
    while True:
        try:
            db = SessionLocal()
            threat = random.choice(threat_types)
            lat = random.uniform(-40.0, 55.0)
            lng = random.uniform(-100.0, 140.0)
            
            new_incident = Incident(
                title=threat[0],
                incident_type=threat[1],
                latitude=lat,
                longitude=lng,
                severity="DEFCON " + str(random.randint(1, 2))
            )
            db.add(new_incident)
            db.commit()
            db.refresh(new_incident)

            payload = {
                "id": new_incident.id, 
                "title": new_incident.title, 
                "latitude": new_incident.latitude, 
                "longitude": new_incident.longitude, 
                "color": threat[2], 
                "summary": f"พิกัด {lat:.4f}, {lng:.4f} | ภัยคุกคามระดับ {new_incident.severity}",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            await manager.broadcast(json.dumps(payload))
            db.close()
        except Exception:
            pass
        await asyncio.sleep(random.randint(5, 9))

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_default_users()
    sim_task = asyncio.create_task(auto_simulation_loop())
    yield
    sim_task.cancel()

app = FastAPI(title="PROJECT OMEGA OMNI TITAN", lifespan=lifespan)

# Helper function to check session
def get_current_user(session_token: Optional[str]):
    if session_token and session_token in ACTIVE_SESSIONS:
        return ACTIVE_SESSIONS[session_token]
    return None

# ==========================================
# 4. AUTHENTICATION & FORGOT PASSWORD ENDPOINTS (LIGHT THEME)
# ==========================================
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LOGIN | PROJECT OMEGA TITAN</title>
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Orbitron:wght@500;700;900&display=swap" rel="stylesheet">
    <style>
        :root { 
            --bg-light: #f1f5f9; 
            --primary-blue: #2563eb; 
            --cyber-red: #dc2626; 
            --cyber-green: #059669; 
            --text-dark: #0f172a;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-light); color: var(--text-dark);
            font-family: 'Chakra Petch', sans-serif;
            display: flex; justify-content: center; align-items: center; min-height: 100vh;
            background-image: 
                radial-gradient(circle at 50% 20%, rgba(37, 99, 235, 0.08) 0%, transparent 60%),
                radial-gradient(circle at 50% 80%, rgba(2, 132, 199, 0.06) 0%, transparent 70%);
        }
        .login-card {
            background: #ffffff; border: 1px solid #cbd5e1;
            border-radius: 20px; padding: 42px; width: 420px; 
            box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
            text-align: center; position: relative; overflow: hidden;
        }
        .login-card::before {
            content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 4px;
            background: linear-gradient(90deg, transparent, var(--primary-blue), #0284c7, transparent);
            animation: scan 3.5s infinite;
        }
        @keyframes scan { 0% { left: -100%; } 100% { left: 100%; } }
        .system-badge {
            font-family: 'Orbitron'; font-size: 10px; color: var(--primary-blue); letter-spacing: 3px;
            border: 1px solid rgba(37, 99, 235, 0.3); padding: 5px 14px; border-radius: 20px; display: inline-block; margin-bottom: 14px;
            background: rgba(37, 99, 235, 0.06); font-weight: 700;
        }
        h2 { font-family: 'Orbitron'; color: var(--text-dark); margin-bottom: 6px; letter-spacing: 2px; font-size: 1.8rem; }
        p { font-size: 13px; color: var(--text-muted); margin-bottom: 25px; }
        .form-group { text-align: left; margin-bottom: 20px; }
        label { font-size: 11px; font-family: 'Orbitron'; color: var(--primary-blue); display: block; margin-bottom: 6px; letter-spacing: 1px; font-weight: 700; }
        input {
            width: 100%; padding: 13px; background: #f8fafc;
            border: 1px solid #cbd5e1; border-radius: 8px; color: var(--text-dark); font-size: 14px; outline: none; transition: 0.3s;
        }
        input:focus { border-color: var(--primary-blue); box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15); background: #fff; }
        .btn-submit {
            width: 100%; padding: 13px; background: var(--primary-blue); color: #fff;
            border: none; border-radius: 8px; font-family: 'Orbitron'; font-weight: 700; cursor: pointer; margin-top: 10px; transition: 0.3s; font-size: 14px;
        }
        .btn-submit:hover { background: #1d4ed8; box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3); transform: translateY(-1px); }
        .links-group { display: flex; justify-content: center; margin-top: 22px; font-size: 13px; }
        .links-group a { color: var(--primary-blue); text-decoration: none; transition: 0.3s; font-weight: 600; }
        .links-group a:hover { color: #1e40af; text-decoration: underline; }
        .msg-box { font-size: 13px; padding: 11px; border-radius: 8px; margin-bottom: 18px; text-align: left; }
        .error-msg { background: #fef2f2; border: 1px solid #fca5a5; color: var(--cyber-red); }
        .success-msg { background: #ecfdf5; border: 1px solid #6ee7b7; color: var(--cyber-green); }
        .creator-tag { margin-top: 25px; font-size: 11px; color: var(--text-muted); border-top: 1px solid #e2e8f0; padding-top: 14px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="system-badge">PROJECT OMEGA OMNI TITAN</div>
        <h2>🔒 SYSTEM LOGIN</h2>
        <p>กรุณาลงชื่อเข้าใช้งานศูนย์บัญชาการยุทธการ</p>
        {MESSAGE_PLACEHOLDER}
        <form action="/login" method="post">
            <div class="form-group">
                <label>USERNAME / ชื่อผู้ใช้</label>
                <input type="text" name="username" required placeholder="เช่น pakorn หรือ operator">
            </div>
            <div class="form-group">
                <label>PASSWORD / รหัสผ่าน</label>
                <input type="password" name="password" required placeholder="กรอกรหัสผ่าน">
            </div>
            <button type="submit" class="btn-submit">LOGIN SYSTEM</button>
        </form>
        <div class="links-group">
            <a href="/forgot-password">🔑 ลืมรหัสผ่าน? (RESET PASSWORD)</a>
        </div>
        <div class="creator-tag">SYSTEM DESIGNED BY ARCHITECT: <b>ผู้สร้าง ปกรณ์</b></div>
    </div>
</body>
</html>
"""

FORGOT_PASSWORD_HTML = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FORGOT PASSWORD | PROJECT OMEGA TITAN</title>
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Orbitron:wght@500;700;900&display=swap" rel="stylesheet">
    <style>
        :root { 
            --bg-light: #f1f5f9; 
            --primary-amber: #d97706; 
            --cyber-red: #dc2626; 
            --text-dark: #0f172a;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-light); color: var(--text-dark);
            font-family: 'Chakra Petch', sans-serif;
            display: flex; justify-content: center; align-items: center; min-height: 100vh;
            background-image: radial-gradient(circle at 50% 50%, rgba(217, 119, 6, 0.08) 0%, transparent 70%);
        }
        .reset-card {
            background: #ffffff; border: 1px solid var(--primary-amber);
            border-radius: 20px; padding: 40px; width: 420px; 
            box-shadow: 0 20px 40px rgba(217, 119, 6, 0.12);
            text-align: center;
        }
        h2 { font-family: 'Orbitron'; color: var(--primary-amber); margin-bottom: 6px; font-size: 1.6rem; }
        p { font-size: 13px; color: var(--text-muted); margin-bottom: 25px; }
        .form-group { text-align: left; margin-bottom: 18px; }
        label { font-size: 11px; font-family: 'Orbitron'; color: var(--primary-amber); display: block; margin-bottom: 6px; font-weight: 700; }
        input {
            width: 100%; padding: 13px; background: #f8fafc;
            border: 1px solid #cbd5e1; border-radius: 8px; color: var(--text-dark); font-size: 14px; outline: none; transition: 0.3s;
        }
        input:focus { border-color: var(--primary-amber); box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.15); background: #fff; }
        .btn-submit {
            width: 100%; padding: 13px; background: var(--primary-amber); color: #fff;
            border: none; border-radius: 8px; font-family: 'Orbitron'; font-weight: 700; cursor: pointer; margin-top: 10px; transition: 0.3s; font-size: 14px;
        }
        .btn-submit:hover { background: #b45309; box-shadow: 0 10px 20px rgba(217, 119, 6, 0.3); }
        .back-link { display: inline-block; margin-top: 22px; color: var(--text-muted); text-decoration: none; font-size: 13px; transition: 0.3s; font-weight: 600; }
        .back-link:hover { color: var(--text-dark); text-decoration: underline; }
        .error-msg { background: #fef2f2; border: 1px solid #fca5a5; color: var(--cyber-red); padding: 11px; border-radius: 8px; font-size: 13px; margin-bottom: 18px; text-align: left; }
    </style>
</head>
<body>
    <div class="reset-card">
        <h2>🔑 RESET PASSWORD</h2>
        <p>ระบบตั้งรหัสผ่านใหม่ประจำบัญชีผู้ใช้งาน</p>
        {ERROR_PLACEHOLDER}
        <form action="/forgot-password" method="post">
            <div class="form-group">
                <label>USERNAME / ชื่อผู้ใช้ที่ต้องการรีเซ็ต</label>
                <input type="text" name="username" required placeholder="กรอกชื่อผู้ใช้ เช่น pakorn">
            </div>
            <div class="form-group">
                <label>NEW PASSWORD / รหัสผ่านใหม่</label>
                <input type="password" name="new_password" required placeholder="กำหนดรหัสผ่านใหม่">
            </div>
            <div class="form-group">
                <label>CONFIRM NEW PASSWORD / ยืนยันรหัสผ่านใหม่</label>
                <input type="password" name="confirm_password" required placeholder="กรอกรหัสผ่านใหม่อีกครั้ง">
            </div>
            <button type="submit" class="btn-submit">UPDATE PASSWORD</button>
        </form>
        <a href="/login" class="back-link">🔙 กลับไปยังหน้าเข้าสู่ระบบ (Back to Login)</a>
    </div>
</body>
</html>
"""

@app.get("/login", response_class=HTMLResponse)
async def login_page(error: Optional[str] = None, success: Optional[str] = None):
    msg_html = ""
    if error:
        msg_html = f'<div class="msg-box error-msg">⚠️ {error}</div>'
    elif success:
        msg_html = f'<div class="msg-box success-msg">✅ {success}</div>'
    return LOGIN_HTML.replace("{MESSAGE_PLACEHOLDER}", msg_html)

@app.post("/login")
async def process_login(response: Response, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user or user.password_hash != hash_password(password):
            return RedirectResponse(url="/login?error=ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", status_code=303)
        
        session_token = str(uuid.uuid4())
        ACTIVE_SESSIONS[session_token] = {"username": user.username, "role": user.role}
        
        redirect_url = "/admin" if user.role == "admin" else "/"
        res = RedirectResponse(url=redirect_url, status_code=303)
        res.set_cookie(key="session_token", value=session_token, httponly=True)
        return res
    finally:
        db.close()

@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(error: Optional[str] = None):
    err_html = f'<div class="error-msg">⚠️ {error}</div>' if error else ""
    return FORGOT_PASSWORD_HTML.replace("{ERROR_PLACEHOLDER}", err_html)

@app.post("/forgot-password")
async def process_forgot_password(username: str = Form(...), new_password: str = Form(...), confirm_password: str = Form(...)):
    if new_password != confirm_password:
        return RedirectResponse(url="/forgot-password?error=รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกัน", status_code=303)
    
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            return RedirectResponse(url="/forgot-password?error=ไม่พบชื่อผู้ใช้นี้ในระบบ", status_code=303)
        
        user.password_hash = hash_password(new_password)
        db.commit()
        return RedirectResponse(url="/login?success=เปลี่ยนรหัสผ่านสำเร็จแล้ว! กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่", status_code=303)
    finally:
        db.close()

@app.get("/logout")
async def logout(session_token: Optional[str] = Cookie(None)):
    if session_token in ACTIVE_SESSIONS:
        del ACTIVE_SESSIONS[session_token]
    res = RedirectResponse(url="/login", status_code=303)
    res.delete_cookie("session_token")
    return res

# ==========================================
# 5. API ENDPOINTS & ANALYTICS
# ==========================================
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/v1/abm/launch")
async def api_launch_abm(req: ABMLaunchRequest):
    payload = {
        "title": "🛡️ QUANTUM ABM INTERCEPTOR DEPLOYED",
        "summary": f"ปล่อยขีปนาวุธสกัดกั้นจากฐานปกรณ์ พิกัดเป้าหมาย {req.target_lat:.4f}, {req.target_lng:.4f}",
        "color": "#059669",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    await manager.broadcast(json.dumps(payload))
    return {"status": "intercepted", "target": {"lat": req.target_lat, "lng": req.target_lng}}

@app.post("/api/v1/telemetry/trigger")
async def api_trigger_manual(region: str = Query("TH")):
    lat = 13.7563 + random.uniform(-2.0, 2.0) if region == "TH" else random.uniform(-50, 50)
    lng = 100.5018 + random.uniform(-2.0, 2.0) if region == "TH" else random.uniform(-120, 120)
    payload = {
        "title": "🚨 ALERT: EMERGENCY THREAT SIMULATION",
        "summary": f"เปิดระบบจำลองสภาวะสงครามฉุกเฉิน พิกัด {lat:.4f}, {lng:.4f}",
        "color": "#dc2626",
        "latitude": lat,
        "longitude": lng,
        "id": random.randint(1000, 9999),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    await manager.broadcast(json.dumps(payload))
    return {"status": "triggered"}

@app.get("/api/v1/analytics/stats")
async def get_analytics_stats():
    db = SessionLocal()
    try:
        total = db.query(func.count(Incident.id)).scalar() or 0
        type_counts = db.query(Incident.incident_type, func.count(Incident.id)).group_by(Incident.incident_type).all()
        by_type = {t: c for t, c in type_counts}

        severity_counts = db.query(Incident.severity, func.count(Incident.id)).group_by(Incident.severity).all()
        by_severity = {s: c for s, c in severity_counts}

        recent = db.query(Incident).order_by(Incident.created_at.desc()).limit(10).all()
        timeline = [{
            "id": inc.id,
            "title": inc.title,
            "type": inc.incident_type,
            "severity": inc.severity,
            "lat": inc.latitude,
            "lng": inc.longitude,
            "time": inc.created_at.strftime("%H:%M:%S") if inc.created_at else "N/A"
        } for inc in reversed(recent)]

        return {
            "total_incidents": total,
            "by_type": by_type,
            "by_severity": by_severity,
            "timeline": timeline,
            "active_ws_connections": len(manager.active_connections)
        }
    finally:
        db.close()

# ==========================================
# 6. ADMIN BACKOFFICE DASHBOARD (LIGHT THEME)
# ==========================================
ADMIN_HTML_CONTENT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROJECT OMEGA TITAN | BACKEND COMMAND ANALYTICS</title>
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Orbitron:wght@500;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-light: #f8fafc; 
            --card-bg: #ffffff;
            --primary-blue: #2563eb; 
            --cyber-red: #dc2626;
            --cyber-green: #059669; 
            --cyber-purple: #7c3aed; 
            --cyber-amber: #d97706;
            --text-dark: #0f172a;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-light); color: var(--text-dark);
            font-family: 'Chakra Petch', 'JetBrains Mono', sans-serif;
            min-height: 100vh; padding: 24px;
        }
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding-bottom: 20px; border-bottom: 2px solid #e2e8f0; margin-bottom: 25px;
        }
        .title-group h1 { font-family: 'Orbitron'; color: var(--primary-blue); font-size: 1.8rem; letter-spacing: 1px; }
        .title-group p { font-size: 0.95rem; color: var(--text-muted); margin-top: 4px; }
        .btn-group { display: flex; gap: 10px; }
        .nav-btn {
            background: #ffffff; border: 1px solid var(--primary-blue); color: var(--primary-blue);
            padding: 10px 18px; border-radius: 8px; font-family: 'Orbitron'; font-size: 12px; font-weight: 700;
            cursor: pointer; text-decoration: none; transition: all 0.25s ease; shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .nav-btn:hover { background: var(--primary-blue); color: #fff; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3); }
        .logout-btn { border-color: var(--cyber-red); color: var(--cyber-red); }
        .logout-btn:hover { background: var(--cyber-red); color: #fff; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3); }
        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 25px; }
        .metric-card {
            background: var(--card-bg); border: 1px solid #e2e8f0;
            border-left: 5px solid var(--primary-blue); border-radius: 12px; padding: 20px;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
        }
        .metric-title { font-size: 11px; color: var(--text-muted); font-family: 'Orbitron'; letter-spacing: 1px; font-weight: 700; }
        .metric-value { font-size: 2.2rem; font-weight: 800; color: var(--text-dark); margin-top: 6px; font-family: 'Orbitron'; }
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .chart-card {
            background: var(--card-bg); border: 1px solid #e2e8f0;
            border-radius: 12px; padding: 22px; height: 360px; display: flex; flex-direction: column;
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
        }
        .chart-card h3 { font-family: 'Orbitron'; font-size: 15px; color: var(--primary-blue); margin-bottom: 16px; border-bottom: 1px solid #f1f5f9; padding-bottom: 10px; }
        .chart-container { flex: 1; position: relative; }
        .table-card { background: var(--card-bg); border: 1px solid #e2e8f0; border-radius: 12px; padding: 22px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04); }
        .table-card h3 { font-family: 'Orbitron'; color: var(--cyber-amber); font-size: 15px; margin-bottom: 16px; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }
        th { background: #f1f5f9; color: var(--primary-blue); padding: 12px; font-family: 'Orbitron'; font-size: 12px; }
        td { padding: 12px; border-bottom: 1px solid #f1f5f9; font-family: 'JetBrains Mono', sans-serif; color: var(--text-dark); }
    </style>
</head>
<body>
    <header>
        <div class="title-group">
            <h1>⚙️ OMEGA BACKEND ANALYTICS CONTROL</h1>
            <p>แผงวิเคราะห์และประมวลผลสถิติจำลองภัยคุกคามหลังบ้าน (Logged in as: {USERNAME})</p>
        </div>
        <div class="btn-group">
            <a href="/" class="nav-btn">🔙 MAIN WAR ROOM</a>
            <a href="/logout" class="nav-btn logout-btn">🚪 LOGOUT</a>
        </div>
    </header>
    <div class="metrics-grid">
        <div class="metric-card" style="border-left-color: var(--primary-blue);">
            <div class="metric-title">TOTAL INCIDENTS RECORDED</div>
            <div class="metric-value" id="val-total">0</div>
        </div>
        <div class="metric-card" style="border-left-color: var(--cyber-red);">
            <div class="metric-title">CRITICAL DEFCON 1 THREATS</div>
            <div class="metric-value" id="val-def1" style="color: var(--cyber-red);">0</div>
        </div>
        <div class="metric-card" style="border-left-color: var(--cyber-green);">
            <div class="metric-title">ACTIVE WS CONNECTIONS</div>
            <div class="metric-value" id="val-ws" style="color: var(--cyber-green);">0</div>
        </div>
        <div class="metric-card" style="border-left-color: var(--cyber-purple);">
            <div class="metric-title">DATABASE STATUS</div>
            <div class="metric-value" style="color: var(--cyber-purple); font-size: 1.4rem; margin-top:10px;">SQLITE ONLINE</div>
        </div>
    </div>
    <div class="charts-grid">
        <div class="chart-card">
            <h3>📊 THREAT DISTRIBUTION BY TYPE</h3>
            <div class="chart-container"><canvas id="typeDoughnutChart"></canvas></div>
        </div>
        <div class="chart-card">
            <h3>📈 INCIDENTS BY SEVERITY LEVEL</h3>
            <div class="chart-container"><canvas id="severityBarChart"></canvas></div>
        </div>
    </div>
    <div class="table-card">
        <h3>📋 RECENT DB INCIDENT LOGS</h3>
        <table>
            <thead>
                <tr><th>ID</th><th>TIME</th><th>THREAT TITLE</th><th>TYPE</th><th>SEVERITY</th><th>COORDINATES</th></tr>
            </thead>
            <tbody id="logs-tbody"><tr><td colspan="6" style="text-align:center;">กำลังโหลดข้อมูล...</td></tr></tbody>
        </table>
    </div>
    <script>
        Chart.defaults.devicePixelRatio = window.devicePixelRatio || 2;
        let doughnutChart, barChart;
        function initAdminCharts() {
            doughnutChart = new Chart(document.getElementById('typeDoughnutChart'), {
                type: 'doughnut',
                data: { labels: ['ICBM Launch', 'Drone Swarm', 'Satellite Hack', 'UFO Tactical'], datasets: [{ data: [0,0,0,0], backgroundColor: ['#dc2626', '#d97706', '#0284c7', '#7c3aed'], borderColor: '#ffffff', borderWidth: 2 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: '#0f172a', font: { family: 'Chakra Petch' } } } } }
            });
            barChart = new Chart(document.getElementById('severityBarChart'), {
                type: 'bar',
                data: { labels: ['DEFCON 1', 'DEFCON 2', 'DEFCON 3', 'DEFCON 5'], datasets: [{ label: 'จำนวน', data: [0,0,0,0], backgroundColor: ['#dc2626', '#d97706', '#0284c7', '#059669'], borderRadius: 6 }] },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { color: '#64748b' }, grid: { color: '#e2e8f0' } }, x: { ticks: { color: '#64748b' }, grid: { display: false } } }, plugins: { legend: { display: false } } }
            });
        }
        async function fetchBackendStats() {
            try {
                const res = await fetch('/api/v1/analytics/stats');
                const data = await res.json();
                document.getElementById('val-total').innerText = data.total_incidents;
                document.getElementById('val-def1').innerText = data.by_severity['DEFCON 1'] || 0;
                document.getElementById('val-ws').innerText = data.active_ws_connections;
                doughnutChart.data.datasets[0].data = [data.by_type['ICBM_LAUNCH']||0, data.by_type['DRONE_SWARM']||0, data.by_type['SATELLITE_HACK']||0, data.by_type['UFO_TACTICAL']||0];
                doughnutChart.update();
                barChart.data.datasets[0].data = [data.by_severity['DEFCON 1']||0, data.by_severity['DEFCON 2']||0, data.by_severity['DEFCON 3']||0, data.by_severity['DEFCON 5']||0];
                barChart.update();
                const tbody = document.getElementById('logs-tbody');
                tbody.innerHTML = '';
                data.timeline.forEach(item => {
                    tbody.innerHTML += `<tr><td>#${item.id}</td><td>${item.time}</td><td style="color:#0f172a; font-weight:600;">${item.title}</td><td>${item.type}</td><td style="color:${item.severity.includes('1')?'var(--cyber-red)':'var(--cyber-amber)'}; font-weight:bold;">${item.severity}</td><td>${item.lat.toFixed(2)}, ${item.lng.toFixed(2)}</td></tr>`;
                });
            } catch(e) {}
        }
        window.onload = () => { initAdminCharts(); fetchBackendStats(); setInterval(fetchBackendStats, 3000); };
    </script>
</body>
</html>
"""

# ==========================================
# 7. FRONTEND MAIN WAR ROOM UI (LIGHT THEME)
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROJECT OMEGA TITAN | Quantum Tactical Defense Command</title>
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Orbitron:wght@500;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
    <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #f8fafc; 
            --cyber-red: #dc2626; 
            --primary-blue: #2563eb;
            --cyber-green: #059669; 
            --cyber-amber: #d97706; 
            --cyber-purple: #7c3aed;
            --panel-bg: rgba(255, 255, 255, 0.94); 
            --panel-border: rgba(203, 213, 225, 0.8);
            --text-dark: #0f172a;
            --text-muted: #64748b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body { 
            background-color: var(--bg-color); color: var(--text-dark); 
            font-family: 'Chakra Petch', 'JetBrains Mono', sans-serif; 
            overflow: hidden; height: 100vh; width: 100vw; 
        }
        .glass-panel { background: var(--panel-bg); backdrop-filter: blur(16px); border: 1px solid var(--panel-border); box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }
        
        /* COVER / SPLASH SCREEN DESIGN (LIGHT THEME) */
        #splash {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: radial-gradient(circle at center, #ffffff 0%, #e2e8f0 100%);
            z-index: 10000; display: flex; flex-direction: column; align-items: center; justify-content: center;
        }
        #particle-canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }
        .splash-card {
            position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center;
            text-align: center; max-width: 900px; width: 90%; padding: 50px 40px; border-radius: 24px;
            border: 1px solid rgba(37, 99, 235, 0.3); background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 20px 50px rgba(37, 99, 235, 0.12);
        }
        .clearance-tag {
            font-family: 'Orbitron'; font-size: 11px; letter-spacing: 5px; color: var(--primary-blue);
            border: 1px solid var(--primary-blue); padding: 6px 24px; border-radius: 20px; margin-bottom: 20px;
            background: rgba(37, 99, 235, 0.06); font-weight: 700;
        }
        .main-title {
            font-family: 'Orbitron', sans-serif; font-size: 4.2rem; font-weight: 900;
            background: linear-gradient(180deg, #1e3a8a 0%, var(--primary-blue) 60%, var(--cyber-purple) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 10px;
        }
        .creator-badge {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), rgba(124, 58, 237, 0.06));
            border: 1px solid rgba(37, 99, 235, 0.3); border-left: 6px solid var(--primary-blue); border-right: 6px solid var(--cyber-purple);
            padding: 18px 50px; border-radius: 12px; margin: 25px 0; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }
        .creator-title { font-family: 'Orbitron'; font-size: 11px; color: var(--cyber-amber); letter-spacing: 4px; font-weight: 700; }
        .creator-name { font-family: 'Chakra Petch'; font-size: 28px; font-weight: 700; color: var(--text-dark); }
        .scan-launch-btn {
            background: var(--primary-blue); border: none; color: #fff;
            padding: 18px 55px; font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 700;
            cursor: pointer; transition: 0.3s ease; border-radius: 12px; box-shadow: 0 10px 25px rgba(37, 99, 235, 0.3);
        }
        .scan-launch-btn:hover { background: #1d4ed8; transform: scale(1.04); box-shadow: 0 15px 35px rgba(37, 99, 235, 0.45); }
        
        #top-bar {
            position: absolute; top: 0; left: 0; width: 100%; height: 44px;
            background: #ffffff; border-bottom: 1px solid #cbd5e1;
            z-index: 20; display: flex; align-items: center; justify-content: space-between; padding: 0 25px; font-family: 'Orbitron'; font-size: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        #container { display: flex; width: 100vw; height: 100vh; position: relative; padding-top: 44px; }
        #map { flex: 1; height: 100%; background: #f1f5f9; }
        #camera-controls { position: absolute; top: 60px; left: 25px; z-index: 10; display: flex; gap: 10px; }
        .cam-btn {
            background: #ffffff; border: 1px solid #cbd5e1; color: var(--text-dark);
            padding: 10px 20px; font-size: 13px; cursor: pointer; border-radius: 8px; font-weight: 600;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05); transition: 0.2s;
        }
        .cam-btn.active { background: var(--primary-blue); color: #fff; border-color: var(--primary-blue); font-weight: 700; }
        #sidebar {
            width: 420px; height: calc(100% - 44px); background: var(--panel-bg);
            display: flex; flex-direction: column; z-index: 10; border-left: 1px solid #cbd5e1;
            box-shadow: -5px 0 20px rgba(0,0,0,0.03);
        }
        .sidebar-title { padding: 14px 18px; color: var(--primary-blue); font-family: 'Orbitron'; font-size: 12px; font-weight: 700; border-bottom: 1px solid #e2e8f0; background: #f8fafc; }
        #feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 16px; }
        .card { background: #ffffff; border-left: 4px solid var(--primary-blue); padding: 14px; font-size: 13px; border-radius: 8px; border: 1px solid #e2e8f0; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }
        .abm-btn { background: var(--cyber-red); color: #fff; border: none; padding: 10px 14px; font-size: 11px; cursor: pointer; font-family: 'Orbitron'; font-weight: 700; margin-top: 8px; border-radius: 6px; transition: 0.2s; width: 100%; }
        .abm-btn:hover { background: #b91c1c; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.3); }
        #terminal-box { background: #0f172a; border-top: 1px solid #334155; padding: 14px; display: flex; align-items: center; }
        #terminal-box span { color: #38bdf8; margin-right: 10px; font-weight: bold; font-size: 13px; font-family: 'JetBrains Mono'; }
        #cmd-prompt { background: transparent; border: none; color: #fff; width: 100%; font-family: 'JetBrains Mono'; font-size: 14px; outline: none; }
    </style>
</head>
<body>
    <!-- COVER PAGE UI -->
    <div id="splash">
        <canvas id="particle-canvas"></canvas>
        <div class="splash-card glass-panel">
            <div class="clearance-tag">QUANTUM CLEARANCE: LEVEL 5 (CLASSIFIED OMNI)</div>
            <h1 class="main-title">PROJECT OMEGA</h1>
            <p style="letter-spacing:6px; color:#475569; font-size:13px; margin-bottom:15px; font-family:'Orbitron'; font-weight:700;">SUPREME 3D GLOBAL WAR ROOM & ABM DEFENSE MATRIX</p>
            <div class="creator-badge">
                <div class="creator-title">CHIEF SYSTEM ARCHITECT</div>
                <div class="creator-name">👨‍💻 ผู้สร้าง ปกรณ์</div>
            </div>
            <button class="scan-launch-btn" onclick="authorizeSystem()"><span id="btn-text">INITIALIZE BIOMETRIC SCAN</span></button>
        </div>
    </div>
    <div id="top-bar">
        <span>PROJECT OMEGA TITAN v6.0 (USER: {USERNAME})</span>
        <span style="color:var(--cyber-red); font-weight:bold;">🚨 SYSTEM ONLINE: 3D SATELLITE RADAR ACTIVE</span>
        <div style="display:flex; gap:12px; align-items:center;">
            <a href="/admin" style="color:var(--primary-blue); text-decoration:none; font-size:11px; border:1px solid var(--primary-blue); padding:4px 10px; border-radius:6px; font-weight:bold; background:#eff6ff;">📊 ADMIN</a>
            <a href="/logout" style="color:var(--cyber-red); text-decoration:none; font-size:11px; border:1px solid var(--cyber-red); padding:4px 10px; border-radius:6px; font-weight:bold; background:#fef2f2;">🚪 LOGOUT</a>
            <span id="time-display" style="color:var(--text-muted);">00:00:00 UTC</span>
        </div>
    </div>
    <div id="container">
        <div id="camera-controls">
            <button class="cam-btn active" onclick="selectRegion('TH', 100.5, 13.7, 6.5, this)">🇹🇭 THAILAND COMMAND</button>
            <button class="cam-btn" onclick="selectRegion('GLOBAL', 100.0, 15.0, 2.2, this)">🌍 3D GLOBAL GLOBE</button>
            <button class="cam-btn" style="border-color:var(--cyber-red); color:var(--cyber-red);" onclick="triggerManualThreat()">⚡ SIMULATE THREAT</button>
        </div>
        <div id="map"></div>
        <div id="sidebar">
            <div class="sidebar-title">LIVE DATABASE ANALYTICS</div>
            <div style="padding:15px; height:200px; border-bottom:1px solid #e2e8f0; background:#fff;"><canvas id="threatChart"></canvas></div>
            <div class="sidebar-title">INCIDENT FEED & INTERCEPT CONTROL</div>
            <div id="feed"></div>
            <div id="terminal-box">
                <span>pakorn@omega-titan:~#</span>
                <input type="text" id="cmd-prompt" placeholder="Type /help or command..." autocomplete="off">
            </div>
        </div>
    </div>
    <script>
        Chart.defaults.devicePixelRatio = window.devicePixelRatio || 2;
        let map, ws, mainChart;
        let abmArcData = { 'type': 'FeatureCollection', 'features': [] };

        function speakAI(text) {
            if(!('speechSynthesis' in window)) return;
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0; utterance.lang = 'th-TH';
            window.speechSynthesis.speak(utterance);
        }

        function authorizeSystem() {
            document.getElementById('btn-text').innerText = "BIOMETRICS CONFIRMED...";
            setTimeout(() => {
                document.getElementById('splash').style.display = 'none';
                speakAI("เข้าสู่ระบบยุทธการระดับโลก โปรเจกต์ โอเมก้า ไททัน โดยผู้สร้าง ปกรณ์ ระบบพร้อมทำงาน");
                init3DMap(); initChart(); initWebSocket();
                setInterval(() => { document.getElementById('time-display').innerText = new Date().toUTCString().split(' ')[4] + " UTC"; }, 1000);
            }, 700);
        }

        function init3DMap() {
            map = new maplibregl.Map({
                container: 'map',
                style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json', // LIGHT MAP STYLE
                center: [100.5018, 13.7563], zoom: 2.5, pitch: 45, bearing: -10, projection: 'globe'
            });
            map.on('load', () => {
                map.setProjection({ type: 'globe' });
                map.addSource('abm-source', { type: 'geojson', data: abmArcData });
                map.addLayer({ id: 'abm-layer', type: 'line', source: 'abm-source', paint: { 'line-color': '#2563eb', 'line-width': 4 } });
            });
            map.on('click', (e) => { launchABM(e.lngLat.lat, e.lngLat.lng); });
        }

        function initChart() {
            mainChart = new Chart(document.getElementById('threatChart').getContext('2d'), {
                type: 'bar',
                data: { labels: ['ICBM', 'DRONE', 'SATELLITE', 'UFO'], datasets: [{ data: [0, 0, 0, 0], backgroundColor: ['#dc2626', '#d97706', '#0284c7', '#7c3aed'], borderRadius: 4 }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { color: '#64748b' }, grid: { color: '#f1f5f9' } }, x: { ticks: { color: '#64748b' }, grid: { display: false } } } }
            });
            setInterval(async () => {
                try {
                    const res = await fetch('/api/v1/analytics/stats');
                    const data = await res.json();
                    mainChart.data.datasets[0].data = [data.by_type['ICBM_LAUNCH']||0, data.by_type['DRONE_SWARM']||0, data.by_type['SATELLITE_HACK']||0, data.by_type['UFO_TACTICAL']||0];
                    mainChart.update();
                } catch(e) {}
            }, 3000);
        }

        function initWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws/telemetry`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if(data.title) appendFeedCard(data.color || '#dc2626', data.title, data.summary, data.latitude, data.longitude, data.timestamp);
            };
        }

        function appendFeedCard(color, title, desc, lat=null, lng=null, time="NOW") {
            const feed = document.getElementById('feed');
            const card = document.createElement('div');
            card.className = 'card'; card.style.borderLeftColor = color;
            let btnHtml = (lat && lng) ? `<button class="abm-btn" onclick="launchABM(${lat}, ${lng})">🚀 LAUNCH ABM INTERCEPTOR</button>` : '';
            card.innerHTML = `<div style="display:flex; justify-content:space-between;"><b style="color:${color}">${title}</b><span style="color:#64748b;">${time}</span></div><span style="color:#334155;">${desc}</span>${btnHtml}`;
            feed.prepend(card);
        }

        async function launchABM(targetLat, targetLng) {
            speakAI("ยิง จรวด สกัด กั้น");
            const baseLat = 12.6664, baseLng = 100.9007;
            for (let i = 0; i <= 25; i++) {
                const t = i / 25;
                abmArcData.features = [{ 'type': 'Feature', 'geometry': { 'type': 'LineString', 'coordinates': [[baseLng, baseLat], [baseLng + (targetLng - baseLng) * t, baseLat + (targetLat - baseLat) * t]] } }];
                if(map.getSource('abm-source')) map.getSource('abm-source').setData(abmArcData);
                await new Promise(r => setTimeout(r, 12));
            }
            setTimeout(() => {
                abmArcData.features = [];
                if(map.getSource('abm-source')) map.getSource('abm-source').setData(abmArcData);
                appendFeedCard('#059669', 'TARGET DESTROYED', `ยิงสกัดกั้นสำเร็จที่พิกัด ${targetLat.toFixed(2)}, ${targetLng.toFixed(2)}`);
            }, 300);
            try { fetch('/api/v1/abm/launch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ target_lat: targetLat, target_lng: targetLng }) }); } catch(e) {}
        }

        function selectRegion(region, lng, lat, zoom, btn) {
            document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            map.flyTo({ center: [lng, lat], zoom: zoom, speed: 1.2 });
        }

        function triggerManualThreat() { fetch('/api/v1/telemetry/trigger?region=TH', {method:'POST'}); }

        const canvas = document.getElementById('particle-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        let particles = Array.from({length: 70}, () => ({ x: Math.random()*canvas.width, y: Math.random()*canvas.height, vx: (Math.random()-0.5), vy: (Math.random()-0.5) }));
        function drawParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.fillStyle = 'rgba(37, 99, 235, 0.25)';
            particles.forEach(p => { p.x += p.vx; p.y += p.vy; ctx.beginPath(); ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2); ctx.fill(); });
            requestAnimationFrame(drawParticles);
        }
        drawParticles();
    </script>
</body>
</html>
"""

# ==========================================
# 8. PROTECTED ROUTE HANDLERS
# ==========================================
@app.get("/", response_class=HTMLResponse)
async def get_dashboard(session_token: Optional[str] = Cookie(None)):
    user = get_current_user(session_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return HTML_CONTENT.replace("{USERNAME}", user["username"].upper())

@app.get("/admin", response_class=HTMLResponse)
async def get_admin_dashboard(session_token: Optional[str] = Cookie(None)):
    user = get_current_user(session_token)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] != "admin":
        return RedirectResponse(url="/login?error=ไม่มีสิทธิ์เข้าถึงหน้าแอดมิน (เฉพาะบัญชี admin)", status_code=303)
    return ADMIN_HTML_CONTENT.replace("{USERNAME}", user["username"].upper())

# ==========================================
# 9. EXECUTION POINT
# ==========================================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)