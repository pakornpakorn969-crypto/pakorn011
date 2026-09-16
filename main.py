import json
import math
import random
import urllib.parse
import urllib.request
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
import uvicorn

# =====================================================================
# ⚙️ TELEGRAM CONFIGURATION
# =====================================================================
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ใส่ HTTP API Token จาก @BotFather
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"  # ใส่ Chat ID จาก @userinfobot


def send_telegram_alert(
    title: str, threat_type: str, lat: float, lng: float, desc: str = ""
):
  if (
      TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE"
      or not TELEGRAM_BOT_TOKEN
      or not TELEGRAM_CHAT_ID
  ):
    return

  msg = (
      f"🚨 <b>[PROJECT OMEGA ALERT]</b>\n"
      f"<b>เหตุการณ์:</b> {title}\n"
      f"<b>ประเภท:</b> {threat_type}\n"
      f"<b>พิกัด:</b> {lat:.4f}, {lng:.4f}\n"
      f"<b>รายละเอียด:</b> {desc}\n"
      f"<b>เวลา:</b> {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
  )

  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = urllib.parse.urlencode({
      "chat_id": TELEGRAM_CHAT_ID,
      "text": msg,
      "parse_mode": "HTML",
  }).encode("utf-8")

  try:
    req = urllib.request.Request(url, data=payload)
    urllib.request.urlopen(req, timeout=3)
  except Exception as e:
    print(f"⚠️ Telegram Alert Failed: {e}")


# =====================================================================
# 🗄️ 1. DATABASE & ORM MODELS
# =====================================================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./omega_supreme.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Incident(Base):
  __tablename__ = "incidents"
  id = Column(Integer, primary_key=True, index=True)
  title = Column(String, default="UNKNOWN INCIDENT")
  incident_type = Column(String, index=True)
  latitude = Column(Float)
  longitude = Column(Float)
  threat_level = Column(Float)
  radius = Column(Float, default=50.0)
  status = Column(String, default="ACTIVE")
  created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SystemState(Base):
  __tablename__ = "system_state"
  id = Column(Integer, primary_key=True, default=1)
  defcon_level = Column(Integer, default=5)
  shield_hp = Column(Float, default=100.0)


def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()


# =====================================================================
# 🔑 2. CLEARANCE AUTHENTICATION & SECURITY
# =====================================================================
api_key_header = APIKeyHeader(name="X-Clearance-Token", auto_error=False)

USER_ROLES = {
    "token-admin-omega": {"name": "General Pakorn", "role": "ADMIN", "level": 5},
    "token-commander-01": {"name": "Cmdr. Alex", "role": "COMMANDER", "level": 3},
    "token-operator-99": {"name": "Op. John", "role": "OPERATOR", "level": 1},
}


def verify_clearance(required_level: int):

  def dependency(token: str = Security(api_key_header)):
    if not token:
      return {"name": "Anonymous Operator", "role": "OPERATOR", "level": 1}
    user = USER_ROLES.get(token)
    if not user:
      raise HTTPException(
          status_code=401, detail="ACCESS DENIED: Invalid Clearance Token"
      )
    if user["level"] < required_level:
      raise HTTPException(
          status_code=403,
          detail="PERMISSION DENIED: Insufficient Clearance Level",
      )
    return user

  return dependency


# =====================================================================
# ⚙️ 3. CONFIGURATION & WEBSOCKET MANAGER
# =====================================================================
LOCATIONS = {
    "TH": [
        {"name": "กรุงเทพมหานคร / BANGKOK", "lat": 13.7563, "lng": 100.5018},
        {"name": "เชียงใหม่ / CHIANG MAI", "lat": 18.7883, "lng": 98.9853},
        {"name": "ภูเก็ต / PHUKET", "lat": 7.8804, "lng": 98.3923},
        {
            "name": "สัตหีบ (ฐานทัพเรือ) / SATTAHIP ABM",
            "lat": 12.6664,
            "lng": 100.9007,
        },
    ],
    "GLOBAL": [
        {
            "name": "ลอสแอนเจลิส / LOS ANGELES",
            "lat": 34.0522,
            "lng": -118.2437,
        },
        {"name": "โตเกียว / TOKYO", "lat": 35.6762, "lng": 139.6503},
        {"name": "ลอนดอน / LONDON", "lat": 51.5074, "lng": -0.1278},
        {
            "name": "วงแหวนไฟ PACIFIC RING OF FIRE",
            "lat": 12.5000,
            "lng": 140.0000,
        },
    ],
}

THREAT_TYPES = [
    {
        "type": "ORBITAL",
        "title": "KINETIC ORBITAL STRIKE",
        "level": 10.0,
        "color": "#00ffff",
        "radius": 65,
        "desc": "ลำแสงเลเซอร์ดาวเทียมยิงถล่มเป้าหมาย",
    },
    {
        "type": "NUCLEAR",
        "title": "THERMONUCLEAR DETONATION",
        "level": 9.9,
        "color": "#ff003c",
        "radius": 60,
        "desc": "ขีปนาวุธนิวเคลียร์หัวรบทรงพลัง",
    },
    {
        "type": "ASTEROID",
        "title": "EXTINCTION ASTEROID IMPACT",
        "level": 10.0,
        "color": "#ff5500",
        "radius": 75,
        "desc": "อุกกาบาตขนาดใหญ่ตกลงสู่พื้นโลก",
    },
    {
        "type": "TSUNAMI",
        "title": "MEGA TSUNAMI DISASTER",
        "level": 8.8,
        "color": "#0099ff",
        "radius": 45,
        "desc": "มหาคลื่นยักษ์ความเร็วสูงถล่มชายฝั่ง",
    },
    {
        "type": "CYBER",
        "title": "GLOBAL GRID BLACKOUT",
        "level": 7.5,
        "color": "#ff00ff",
        "radius": 35,
        "desc": "การโจมตีทางไซเบอร์ตัดไฟระบบโครงสร้าง",
    },
]


class ConnectionManager:

  def __init__(self):
    self.active_connections: Dict[str, WebSocket] = {}

  async def connect(self, websocket: WebSocket, client_id: str):
    await websocket.accept()
    self.active_connections[client_id] = websocket

  def disconnect(self, client_id: str):
    if client_id in self.active_connections:
      del self.active_connections[client_id]

  async def broadcast(self, message: str, exclude_id: Optional[str] = None):
    for cid, connection in list(self.active_connections.items()):
      if cid != exclude_id:
        try:
          await connection.send_text(message)
        except Exception:
          self.disconnect(cid)


manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
  Base.metadata.create_all(bind=engine)
  db = SessionLocal()
  if not db.query(SystemState).first():
    db.add(SystemState(id=1, defcon_level=5, shield_hp=100.0))
    db.commit()
  db.close()
  yield


app = FastAPI(
    title="PROJECT OMEGA SUPREME WAR ROOM & MOBILE API",
    version="2.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# 📱 4. MOBILE & REST API ENDPOINTS
# =====================================================================
class MobileStrikeRequest(BaseModel):
  lat: float
  lng: float
  threat_type: str


class DefconUpdate(BaseModel):
  level: int


class AbmLaunch(BaseModel):
  target_lat: float
  target_lng: float
  incident_id: Optional[int] = None


@app.get("/api/v1/mobile/status")
async def get_mobile_status(db: Session = Depends(get_db)):
  state = db.query(SystemState).first()
  active_incidents = (
      db.query(Incident).filter(Incident.status == "ACTIVE").count()
  )
  return {
      "status": "ONLINE",
      "defcon": state.defcon_level if state else 5,
      "shield_hp": state.shield_hp if state else 100.0,
      "active_threats": active_incidents,
      "timestamp": datetime.now(timezone.utc).isoformat(),
  }


@app.get("/api/v1/mobile/incidents")
async def get_incidents_list(db: Session = Depends(get_db)):
  incidents = db.query(Incident).order_by(Incident.id.desc()).limit(10).all()
  return {"incidents": incidents}


@app.post("/api/v1/mobile/strike")
async def trigger_mobile_strike(
    data: MobileStrikeRequest, db: Session = Depends(get_db)
):
  new_inc = Incident(
      title=f"MOBILE COMMAND: {data.threat_type}",
      incident_type=data.threat_type,
      latitude=data.lat,
      longitude=data.lng,
      threat_level=9.5,
  )
  db.add(new_inc)
  db.commit()

  payload = {
      "id": new_inc.id,
      "title": new_inc.title,
      "incident_type": new_inc.incident_type,
      "latitude": new_inc.latitude,
      "longitude": new_inc.longitude,
      "threat_level": new_inc.threat_level,
      "radius": 50,
      "color": "#ff003c",
      "summary": "คำสั่งโจมตีทางยุทธการจากแอปพลิเคชันมือถือ",
  }
  await manager.broadcast(json.dumps(payload))

  # 📲 ส่งแจ้งเตือนไปยัง Telegram
  send_telegram_alert(
      title=new_inc.title,
      threat_type=data.threat_type,
      lat=data.lat,
      lng=data.lng,
      desc="คำสั่งโจมตีทางยุทธการจาก Mobile App",
  )

  return {"status": "STRIKE_EXECUTED", "incident_id": new_inc.id}


@app.post("/api/v1/abm/launch")
async def launch_abm_interceptor(
    data: AbmLaunch,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_clearance(3)),
):
  if data.incident_id:
    inc = db.query(Incident).filter(Incident.id == data.incident_id).first()
    if inc:
      inc.status = "INTERCEPTED"
      db.commit()

  payload = {
      "type": "ABM_INTERCEPT",
      "lat": data.target_lat,
      "lng": data.target_lng,
      "status": "INTERCEPTED",
      "message": f"ABM Interception by {user['name']}",
  }
  await manager.broadcast(json.dumps(payload))

  return {"status": "success", "data": payload}


@app.post("/api/v1/system/defcon")
async def update_defcon(
    data: DefconUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(verify_clearance(5)),
):
  state = db.query(SystemState).filter(SystemState.id == 1).first()
  if state:
    state.defcon_level = data.level
    db.commit()
  await manager.broadcast(
      json.dumps({"type": "DEFCON_CHANGE", "level": data.level})
  )
  return {
      "status": "success",
      "defcon": data.level,
      "authorized_by": user["name"],
  }


@app.post("/api/v1/telemetry/trigger")
async def trigger_event(
    region: str = Query("TH"), db: Session = Depends(get_db)
):
  reg_key = region.upper() if region.upper() in LOCATIONS else "TH"
  loc = random.choice(LOCATIONS[reg_key])
  threat = random.choice(THREAT_TYPES)

  new_incident = Incident(
      title=f"{threat['title']} - {loc['name']}",
      incident_type=threat["type"],
      latitude=loc["lat"] + random.uniform(-0.05, 0.05),
      longitude=loc["lng"] + random.uniform(-0.05, 0.05),
      threat_level=threat["level"],
      radius=threat["radius"],
  )
  db.add(new_incident)
  db.commit()
  db.refresh(new_incident)

  payload = {
      "id": new_incident.id,
      "title": new_incident.title,
      "incident_type": new_incident.incident_type,
      "latitude": new_incident.latitude,
      "longitude": new_incident.longitude,
      "threat_level": new_incident.threat_level,
      "radius": threat["radius"],
      "color": threat["color"],
      "summary": threat["desc"],
  }
  await manager.broadcast(json.dumps(payload))

  # 📲 ส่งแจ้งเตือนไปยัง Telegram
  send_telegram_alert(
      title=new_incident.title,
      threat_type=threat["type"],
      lat=new_incident.latitude,
      lng=new_incident.longitude,
      desc=threat["desc"],
  )

  return {"status": "success"}


@app.websocket("/ws/telemetry")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(
        default_factory=lambda: str(uuid.uuid4())[:8]
    ),
):
  await manager.connect(websocket, client_id)
  try:
    while True:
      raw_msg = await websocket.receive_text()
      data = json.loads(raw_msg)
      if data.get("type") == "CURSOR":
        await manager.broadcast(json.dumps(data), exclude_id=client_id)
  except WebSocketDisconnect:
    manager.disconnect(client_id)


# =====================================================================
# 🌐 5. WEB WAR ROOM UI (HIGH-DEFINITION VECTOR & GLASSMORPHISM)
# =====================================================================
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
  return """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PROJECT OMEGA | Supreme Ultra-HD War Room</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Prompt:wght@300;400;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
        <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {
                --bg: #020408; 
                --cyber-red: #ff003c; 
                --cyber-blue: #00e5ff;
                --cyber-green: #00ff66; 
                --cyber-gold: #ffaa00; 
                --panel-bg: rgba(3, 8, 18, 0.75);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
            body { background-color: var(--bg); color: #fff; font-family: 'Share Tech Mono', 'Prompt', sans-serif; overflow: hidden; height: 100vh; width: 100vw; }
            
            /* CRT Scanline บางลงเพื่อความชัด HD */
            body::before {
                content: " "; display: block; position: absolute; top: 0; left: 0; bottom: 0; right: 0;
                background: linear-gradient(rgba(18, 16, 16, 0) 60%, rgba(0, 0, 0, 0.25) 50%);
                z-index: 9999; background-size: 100% 2px; pointer-events: none; opacity: 0.5;
            }

            /* Glassmorphism และ Neon Glow สำหรับกล่องควบคุม */
            .cam-btn, #hud-stats, #defcon-badge, #shield-container, #sidebar, .card {
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                box-shadow: 0 8px 32px 0 rgba(0, 229, 255, 0.15);
                border: 1px solid rgba(0, 229, 255, 0.3) !important;
            }

            #splash { 
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; 
                background: radial-gradient(circle at center, #0a192f 0%, #020408 100%); 
                z-index: 10000; display: flex; flex-direction: column; align-items: center; justify-content: center; 
            }
            .splash-content { display: flex; flex-direction: column; align-items: center; text-align: center; max-width: 800px; padding: 20px; z-index: 2; }
            .system-tag { 
                font-family: 'Orbitron'; font-size: 11px; letter-spacing: 6px; color: var(--cyber-blue); 
                border: 1px solid var(--cyber-blue); padding: 5px 16px; border-radius: 20px; margin-bottom: 20px;
                box-shadow: 0 0 15px rgba(0, 229, 255, 0.3);
            }
            .main-title { 
                font-family: 'Orbitron', sans-serif; font-size: 4rem; font-weight: 900; 
                background: linear-gradient(180deg, #ffffff 0%, var(--cyber-blue) 60%, var(--cyber-red) 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                text-shadow: 0 0 40px rgba(0, 229, 255, 0.5); letter-spacing: 4px;
            }
            .creator-card {
                background: rgba(8, 16, 28, 0.85); border: 1px solid rgba(0, 229, 255, 0.5);
                border-left: 5px solid var(--cyber-red); border-right: 5px solid var(--cyber-blue);
                padding: 12px 30px; border-radius: 6px; margin: 25px 0; text-align: center;
            }
            .launch-btn { 
                background: transparent; border: 2px solid var(--cyber-red); color: var(--cyber-red); 
                padding: 16px 50px; font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 700;
                cursor: pointer; transition: 0.3s; letter-spacing: 2px; box-shadow: 0 0 15px rgba(255, 0, 60, 0.3);
            }
            .launch-btn:hover { background: var(--cyber-red); color: #000; box-shadow: 0 0 35px var(--cyber-red); transform: scale(1.05); }

            #top-ticker { 
                position: absolute; top: 0; left: 0; width: 100%; height: 32px; 
                background: rgba(255, 0, 60, 0.15); border-bottom: 1px solid var(--cyber-red); 
                z-index: 20; display: flex; align-items: center; overflow: hidden; font-size: 12px; font-family: 'Orbitron'; 
            }
            #ticker-content { white-space: nowrap; animation: ticker 25s linear infinite; color: var(--cyber-red); font-weight: bold; }
            @keyframes ticker { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }

            #container { display: flex; width: 100vw; height: 100vh; position: relative; padding-top: 32px; }
            #map { flex: 1; height: 100%; background: #020408; }

            #camera-controls { position: absolute; top: 48px; left: 20px; z-index: 10; display: flex; gap: 8px; flex-wrap: wrap; }
            .cam-btn { 
                background: var(--panel-bg); color: #ccc; 
                padding: 8px 16px; font-size: 11px; cursor: pointer; font-family: 'Prompt'; transition: 0.3s; border-radius: 4px;
            }
            .cam-btn:hover, .cam-btn.active { background: var(--cyber-blue); color: #000; font-weight: bold; box-shadow: 0 0 15px var(--cyber-blue); }
            
            #voice-btn {
                background: var(--panel-bg); border: 1px solid var(--cyber-red); color: var(--cyber-red);
                padding: 8px 16px; font-size: 11px; cursor: pointer; font-family: 'Orbitron'; transition: 0.3s; display: flex; align-items: center; gap: 6px; border-radius: 4px;
            }
            #voice-btn.listening { background: var(--cyber-red); color: #000; animation: pulseGlow 1s infinite alternate; }

            #hud-stats {
                position: absolute; bottom: 20px; left: 20px; z-index: 10;
                background: var(--panel-bg); padding: 12px 20px; display: flex; gap: 20px; border-radius: 6px; font-family: 'Orbitron';
            }
            .hud-item { display: flex; flex-direction: column; }
            .hud-label { font-size: 9px; color: #888; }
            .hud-val { font-size: 15px; font-weight: bold; color: var(--cyber-blue); }

            #defcon-badge { 
                position: absolute; top: 48px; right: 410px; z-index: 10; 
                background: rgba(0, 255, 102, 0.1); border: 2px solid var(--cyber-green); 
                padding: 8px 18px; border-radius: 6px; font-family: 'Orbitron'; text-align: center;
            }
            .defcon-title { font-size: 9px; color: #aaa; }
            .defcon-level { font-size: 22px; font-weight: 900; color: var(--cyber-green); }

            #shield-container {
                position: absolute; top: 48px; right: 540px; z-index: 10;
                background: var(--panel-bg); padding: 8px 15px; border-radius: 6px; font-family: 'Orbitron'; width: 170px;
            }
            .shield-bar-bg { width: 100%; height: 8px; background: #112; border-radius: 4px; overflow: hidden; margin-top: 4px; }
            .shield-bar-fill { width: 100%; height: 100%; background: var(--cyber-blue); transition: width 0.4s; }

            #sidebar { 
                width: 390px; height: calc(100% - 32px); background: var(--panel-bg); 
                display: flex; flex-direction: column; z-index: 10; 
            }
            #sidebar-header { 
                padding: 12px 15px; color: var(--cyber-blue); font-family: 'Orbitron'; border-bottom: 1px solid rgba(0,229,255,0.2); 
                display: flex; justify-content: space-between; align-items: center; font-size: 13px;
            }
            #analytics-panel { padding: 10px 15px; border-bottom: 1px solid rgba(255,255,255,0.08); height: 160px; }
            #feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding: 12px; }
            .card { 
                background: rgba(255, 255, 255, 0.03); border-left: 4px solid var(--cyber-blue) !important; padding: 10px; font-size: 11px;
                display: flex; flex-direction: column; gap: 4px; border-radius: 4px;
            }
            .abm-btn { background: var(--cyber-red); color: #000; border: none; padding: 6px 10px; font-size: 10px; cursor: pointer; font-family: 'Orbitron'; font-weight: bold; margin-top: 4px; border-radius: 3px; }
            .abm-btn:hover { background: #fff; box-shadow: 0 0 12px var(--cyber-red); }

            #terminal-box { background: rgba(0, 0, 0, 0.8); border-top: 1px solid rgba(0, 229, 255, 0.3); padding: 10px; display: flex; align-items: center; }
            #terminal-box span { color: var(--cyber-green); margin-right: 8px; font-weight: bold; font-size: 12px; }
            #cmd-prompt { background: transparent; border: none; color: var(--cyber-blue); width: 100%; font-family: 'Share Tech Mono'; font-size: 12px; outline: none; }
        </style>
    </head>
    <body>
        <div id="splash">
            <div class="splash-content">
                <div class="system-tag">WAR ROOM CLEARANCE: LEVEL 5 (CLASSIFIED)</div>
                <h1 class="main-title">PROJECT OMEGA</h1>
                <p style="letter-spacing:4px; color:#888; font-size:12px;">SUPREME MULTI-USER DEFENSE & MOBILE API INTERFACE</p>
                <div class="creator-card">
                    <span style="font-size:10px; color:#aaa; font-family:'Orbitron';">CHIEF SYSTEM ARCHITECT</span><br>
                    <span style="font-size:18px; font-weight:700; color:#fff; font-family:'Prompt';">👨‍💻 ผู้สร้าง ปกรณ์</span>
                </div>
                <button class="launch-btn" onclick="authorizeSystem()">ENGAGE SUPREME WAR ROOM</button>
            </div>
        </div>

        <div id="top-ticker">
            <div id="ticker-content">🚨 OMEGA SUPREME MATRIX ONLINE: LIVE ABM MISSILE NETWORK & TELEGRAM ALERT SYSTEM ACTIVE...</div>
        </div>
        
        <div id="container">
            <div id="camera-controls">
                <button class="cam-btn active" onclick="selectRegion('TH', 100.5, 13.7, 5.8, this)">🇹🇭 THAILAND</button>
                <button class="cam-btn" onclick="selectRegion('GLOBAL', 100.0, 15.0, 1.8, this)">🌍 GLOBAL</button>
                <button id="voice-btn" onclick="toggleVoiceControl()">🎤 VOICE COMMAND</button>
            </div>

            <div id="shield-container">
                <div style="display:flex; justify-content:space-between; font-size:9px; color:var(--cyber-blue);">
                    <span>GRID SHIELD HP</span><span id="shield-val">100%</span>
                </div>
                <div class="shield-bar-bg"><div class="shield-bar-fill" id="shield-bar"></div></div>
            </div>

            <div id="hud-stats">
                <div class="hud-item"><span class="hud-label">OPERATORS</span><span class="hud-val" id="hud-op-count">1 ONLINE</span></div>
                <div class="hud-item"><span class="hud-label">TELEGRAM ALERT</span><span class="hud-val" style="color:var(--cyber-green);">ACTIVE</span></div>
                <div class="hud-item"><span class="hud-label">ABM MISSILES</span><span class="hud-val" style="color:var(--cyber-gold);">READY</span></div>
            </div>
            
            <div id="defcon-badge">
                <div class="defcon-title">SYSTEM STATUS</div>
                <div id="defcon-val" class="defcon-level">DEFCON 5</div>
            </div>
            
            <div id="map"></div>
            
            <div id="sidebar">
                <div id="sidebar-header">
                    <span>LIVE WAR ROOM ANALYTICS</span>
                    <span style="font-size:9px; color:#888;" id="role-badge">COMMANDER</span>
                </div>
                <div id="analytics-panel">
                    <canvas id="threatChart"></canvas>
                </div>
                <div id="sidebar-header" style="border-top:1px solid rgba(0,229,255,0.2);">INCIDENT FEED & ABM LAUNCH</div>
                <div id="feed"></div>
                <div id="terminal-box">
                    <span>root@omega:~#</span>
                    <input type="text" id="cmd-prompt" placeholder="Command (/help)..." autocomplete="off">
                </div>
            </div>
        </div>

        <script>
            let map, ws, clientId = "OP-" + Math.floor(1000 + Math.random() * 9000);
            let shieldHP = 100.0;
            let chartInstance = null;
            let isVoiceListening = false, recognition = null;
            let abmArcData = { 'type': 'FeatureCollection', 'features': [] };

            function playAudioEffect(type) {
                try {
                    const ctx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = ctx.createOscillator(); const gain = ctx.createGain();
                    osc.connect(gain); gain.connect(ctx.destination);
                    if (type === 'abm') {
                        osc.type = 'sawtooth'; osc.frequency.setValueAtTime(400, ctx.currentTime);
                        osc.frequency.exponentialRampToValueAtTime(1600, ctx.currentTime + 0.4);
                        gain.gain.setValueAtTime(0.2, ctx.currentTime); gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);
                        osc.start(); osc.stop(ctx.currentTime + 0.4);
                    }
                } catch(e) {}
            }

            function speakAI(text) {
                if(!('speechSynthesis' in window)) return;
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.0; utterance.lang = 'th-TH';
                window.speechSynthesis.speak(utterance);
            }

            function appendFeedCard(color, title, desc, lat=null, lng=null, id=null) {
                const feed = document.getElementById('feed');
                const card = document.createElement('div');
                card.className = 'card'; card.style.borderLeftColor = color;
                
                let btnHtml = (lat && lng) ? `<button class="abm-btn" onclick="launchABM(${lat}, ${lng}, ${id})">🚀 LAUNCH ABM INTERCEPTOR</button>` : '';
                card.innerHTML = `<b style="color:${color}">${title}</b><span>${desc}</span>${btnHtml}`;
                feed.prepend(card);
            }

            function authorizeSystem() {
                document.getElementById('splash').style.display = 'none';
                speakAI("เข้าสู่ห้องปฏิบัติการยุทธการสูงสุด ระบบสกัดกั้นและแจ้งเตือนโทรเลขพร้อมทำงาน");
                initMap(); initChart(); initWebSocket();
            }

            function initMap() {
                // อัปเดตเปลี่ยน Map Style เป็น CartoDB Dark Matter Vector เพื่อความชัดสูงระดับ HD
                map = new maplibregl.Map({
                    container: 'map',
                    style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
                    center: [100.5018, 13.7563],
                    zoom: 5.8,
                    pitch: 50,
                    bearing: 10,
                    pixelRatio: window.devicePixelRatio || 1
                });

                map.on('load', () => {
                    try {
                        map.setFog({
                            'range': [0.8, 8],
                            'color': '#020408',
                            'horizon-blend': 0.2
                        });
                    } catch(e){}

                    map.addSource('abm-source', { type: 'geojson', data: abmArcData });
                    map.addLayer({
                        id: 'abm-layer', type: 'line', source: 'abm-source',
                        paint: { 
                            'line-color': '#00ffff', 
                            'line-width': 3,
                            'line-blur': 1
                        }
                    });
                });

                map.on('click', (e) => {
                    launchABM(e.lngLat.lat, e.lngLat.lng);
                });
            }

            function initChart() {
                const ctx = document.getElementById('threatChart').getContext('2d');
                chartInstance = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['10m', '8m', '6m', '4m', '2m', 'Now'],
                        datasets: [{
                            label: 'Threat Intensity',
                            data: [2, 4, 3, 7, 5, 9],
                            borderColor: '#00e5ff', backgroundColor: 'rgba(0, 229, 255, 0.1)',
                            borderWidth: 2, fill: true, tension: 0.4
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false }
                });
            }

            function initWebSocket() {
                const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${location.host}/ws/telemetry?client_id=${clientId}`);
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if(data.title) {
                        appendFeedCard(data.color || '#ff003c', data.title, data.summary || 'แจ้งเตือนภัยคุกคาม', data.latitude, data.longitude, data.id);
                    }
                };
            }

            async function launchABM(targetLat, targetLng, incidentId = null) {
                playAudioEffect('abm');
                speakAI("ยิงจรวด เอ บี เอ็ม สกัดกั้นเป้าหมาย");
                
                const baseLat = 12.6664, baseLng = 100.9007;
                const steps = 20;
                for (let i = 0; i <= steps; i++) {
                    const t = i / steps;
                    const curLng = baseLng + (targetLng - baseLng) * t;
                    const curLat = baseLat + (targetLat - baseLat) * t;
                    
                    abmArcData.features = [{
                        'type': 'Feature',
                        'geometry': { 'type': 'LineString', 'coordinates': [[baseLng, baseLat], [curLng, curLat]] }
                    }];
                    if(map.getSource('abm-source')) map.getSource('abm-source').setData(abmArcData);
                    await new Promise(r => setTimeout(r, 20));
                }
                
                setTimeout(() => {
                    abmArcData.features = [];
                    if(map.getSource('abm-source')) map.getSource('abm-source').setData(abmArcData);
                    appendFeedCard('#00ff66', 'ABM INTERCEPTED', `สกัดกั้นเป้าหมายพิกัด ${targetLat.toFixed(2)}, ${targetLng.toFixed(2)} สำเร็จ`);
                }, 500);

                try {
                    await fetch('/api/v1/abm/launch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ target_lat: targetLat, target_lng: targetLng, incident_id: incidentId })
                    });
                } catch(e) {}
            }

            function selectRegion(region, lng, lat, zoom, btn) {
                document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                map.flyTo({ center: [lng, lat], zoom: zoom, speed: 1.2 });
            }

            function toggleVoiceControl() {
                if(!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                    alert('เบราว์เซอร์ไม่รองรับ Speech Recognition');
                    return;
                }
                const btn = document.getElementById('voice-btn');
                if(isVoiceListening) {
                    if(recognition) recognition.stop();
                    isVoiceListening = false;
                    btn.classList.remove('listening');
                    btn.innerText = '🎤 VOICE COMMAND';
                } else {
                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                    recognition = new SpeechRecognition();
                    recognition.lang = 'th-TH'; recognition.continuous = true;
                    recognition.onresult = (e) => {
                        const txt = e.results[e.results.length - 1][0].transcript.trim();
                        appendFeedCard('#ff00ff', 'VOICE COMMAND', `รับคำสั่งเสียง: "${txt}"`);
                        if(txt.includes('สกัดกั้น') || txt.includes('ยิง')) launchABM(13.7563, 100.5018);
                    };
                    recognition.start();
                    isVoiceListening = true;
                    btn.classList.add('listening');
                    btn.innerText = '🎙️ LISTENING...';
                }
            }

            document.getElementById('cmd-prompt').addEventListener('keypress', function(e) {
                if(e.key === 'Enter') {
                    const cmd = this.value.trim();
                    if(cmd === '/trigger') fetch('/api/v1/telemetry/trigger?region=TH', {method:'POST'});
                    else if(cmd === '/help') appendFeedCard('#00e5ff', 'COMMANDS', '/trigger - จำลองเหตุการณ์ | /help - ความช่วยเหลือ');
                    this.value = '';
                }
            });
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
  uvicorn.run(app, host="127.0.0.1", port=8000)