import os
import json
import random
import asyncio
import math
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# ==========================================
# 1. DATABASE SETUP
# ==========================================
DB_FILE = "omega_titan_quantum.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{DB_FILE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
# 3. QUANTUM SIMULATION LOOP
# ==========================================
async def auto_simulation_loop():
    await asyncio.sleep(2)
    threat_types = [
        ("🚨 ตรวจพบขีปนาวุธข้ามทวีป ICBM", "ICBM_LAUNCH", "#ff0055"),
        ("⚠️ ฝูงโดรน Hypersonic รุกล้ำเขตน่านฟ้า", "DRONE_SWARM", "#ffaa00"),
        ("⚡ การโจมตี Quantum Cybernetics ต่อดาวเทียม", "SATELLITE_HACK", "#00e5ff"),
        ("🛸 วัตถุบินไม่ปรากฏนามเคลื่อนที่ความเร็ว 15 Mach", "UFO_TACTICAL", "#a855f7")
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
    sim_task = asyncio.create_task(auto_simulation_loop())
    yield
    sim_task.cancel()

app = FastAPI(title="PROJECT OMEGA OMNI TITAN", lifespan=lifespan)

# ==========================================
# 4. API ENDPOINTS
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
        "color": "#00ff88",
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
        "color": "#ff0055",
        "latitude": lat,
        "longitude": lng,
        "id": random.randint(1000, 9999),
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    await manager.broadcast(json.dumps(payload))
    return {"status": "triggered"}

# ==========================================
# 5. ULTRA CINEMATIC FRONTEND HTML/CSS/JS
# ==========================================
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PROJECT OMEGA TITAN | Quantum Tactical Defense Command</title>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Prompt:wght@300;400;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
    <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
    <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-color: #010206;
            --cyber-red: #ff0055;
            --cyber-blue: #00e5ff;
            --cyber-green: #00ff88;
            --cyber-gold: #ffaa00;
            --cyber-purple: #b026ff;
            --panel-bg: rgba(2, 8, 20, 0.85);
            --glow: 0 0 25px rgba(0, 229, 255, 0.5);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body { background-color: var(--bg-color); color: #fff; font-family: 'Share Tech Mono', 'Prompt', sans-serif; overflow: hidden; height: 100vh; width: 100vw; }

        /* Holographic Scanlines */
        body::before {
            content: ""; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.4) 50%),
                        radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.9) 100%);
            background-size: 100% 4px, 100% 100%; z-index: 999; pointer-events: none; opacity: 0.85;
        }

        /* Glassmorphism Panel */
        .glass-panel {
            background: var(--panel-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(0, 229, 255, 0.3); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8), var(--glow);
        }

        /* SPLASH SCREEN (หน้าปกระดับโลก) */
        #splash {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: radial-gradient(circle at center, #061026 0%, #010206 100%);
            z-index: 10000; display: flex; flex-direction: column; align-items: center; justify-content: center;
        }
        #particle-canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }

        .splash-card {
            position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center;
            text-align: center; max-width: 900px; padding: 50px 40px; border-radius: 20px;
            border: 1px solid rgba(0, 229, 255, 0.5); background: rgba(2, 6, 18, 0.88);
            box-shadow: 0 0 80px rgba(0, 229, 255, 0.25); clip-path: polygon(0 0, 95% 0, 100% 5%, 100% 100%, 5% 100%, 0 95%);
        }

        /* 3D Rotating HUD Rings */
        .hud-ring {
            position: absolute; border-radius: 50%; border: 1px dashed rgba(0, 229, 255, 0.3);
            pointer-events: none; animation: spin 25s linear infinite;
        }
        .hud-ring-1 { width: 380px; height: 380px; top: -50px; border-top-color: var(--cyber-red); border-right-color: var(--cyber-blue); }
        .hud-ring-2 { width: 520px; height: 520px; top: -120px; border-bottom-color: var(--cyber-purple); animation-duration: 45s; animation-direction: reverse; }
        @keyframes spin { 100% { transform: rotate(360deg); } }

        .clearance-tag {
            font-family: 'Orbitron'; font-size: 11px; letter-spacing: 6px; color: var(--cyber-blue);
            border: 1px solid var(--cyber-blue); padding: 6px 24px; border-radius: 20px; margin-bottom: 20px;
            background: rgba(0, 229, 255, 0.1); text-shadow: 0 0 12px var(--cyber-blue);
        }

        .main-title {
            font-family: 'Orbitron', sans-serif; font-size: 4.8rem; font-weight: 900;
            background: linear-gradient(180deg, #ffffff 10%, var(--cyber-blue) 50%, var(--cyber-purple) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-shadow: 0 0 45px rgba(0, 229, 255, 0.8); letter-spacing: 8px; margin-bottom: 10px;
        }

        /* Chief Architect Hologram Badge */
        .creator-badge {
            background: linear-gradient(135deg, rgba(255,0,85,0.2), rgba(0,229,255,0.2));
            border: 1px solid rgba(0, 229, 255, 0.6); border-left: 5px solid var(--cyber-red); border-right: 5px solid var(--cyber-blue);
            padding: 16px 50px; border-radius: 10px; margin: 25px 0; text-align: center; position: relative;
            box-shadow: 0 0 30px rgba(0, 229, 255, 0.2);
        }
        .creator-title { font-family: 'Orbitron'; font-size: 11px; color: var(--cyber-gold); letter-spacing: 4px; }
        .creator-name { font-family: 'Prompt'; font-size: 26px; font-weight: 700; color: #fff; text-shadow: 0 0 20px var(--cyber-blue); }

        /* Biometrics Scanner Button */
        .scan-launch-btn {
            background: transparent; border: 2px solid var(--cyber-red); color: var(--cyber-red);
            padding: 20px 60px; font-family: 'Orbitron', sans-serif; font-size: 1.3rem; font-weight: 800;
            cursor: pointer; transition: 0.4s; letter-spacing: 4px; border-radius: 8px;
            position: relative; overflow: hidden; box-shadow: 0 0 30px rgba(255, 0, 85, 0.4);
        }
        .scan-launch-btn:hover {
            background: var(--cyber-red); color: #000; box-shadow: 0 0 60px var(--cyber-red); transform: scale(1.05);
        }

        /* TOP COMMAND BAR */
        #top-bar {
            position: absolute; top: 0; left: 0; width: 100%; height: 42px;
            background: rgba(2, 6, 16, 0.95); border-bottom: 1px solid rgba(0, 229, 255, 0.4);
            z-index: 20; display: flex; align-items: center; justify-content: space-between; padding: 0 25px; font-family: 'Orbitron'; font-size: 12px;
        }
        #ticker-text { color: var(--cyber-red); font-weight: bold; font-family: 'Share Tech Mono'; letter-spacing: 1px; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

        #container { display: flex; width: 100vw; height: 100vh; position: relative; padding-top: 42px; }
        #map { flex: 1; height: 100%; background: #010206; }

        /* HUD Camera Controls */
        #camera-controls { position: absolute; top: 58px; left: 25px; z-index: 10; display: flex; gap: 10px; }
        .cam-btn {
            background: var(--panel-bg); border: 1px solid rgba(0,229,255,0.4); color: #ccc;
            padding: 10px 20px; font-size: 12px; cursor: pointer; font-family: 'Prompt'; transition: 0.3s; border-radius: 6px;
        }
        .cam-btn:hover, .cam-btn.active { background: var(--cyber-blue); color: #000; font-weight: bold; box-shadow: 0 0 20px var(--cyber-blue); }

        /* DEFCON Controls */
        #defcon-widget {
            position: absolute; top: 58px; right: 440px; z-index: 10; display: flex; gap: 6px; padding: 6px; border-radius: 8px;
        }
        .def-btn {
            padding: 8px 16px; font-family: 'Orbitron'; font-weight: 800; font-size: 11px; cursor: pointer;
            border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.6); color: #888; border-radius: 4px; transition: 0.3s;
        }
        .def-btn.active-1 { background: var(--cyber-red); color: #000; border-color: var(--cyber-red); box-shadow: 0 0 25px var(--cyber-red); }
        .def-btn.active-5 { background: var(--cyber-green); color: #000; border-color: var(--cyber-green); box-shadow: 0 0 25px var(--cyber-green); }

        /* SIDEBAR HUD PANEL */
        #sidebar {
            width: 420px; height: calc(100% - 42px); background: var(--panel-bg);
            display: flex; flex-direction: column; z-index: 10; border-left: 1px solid rgba(0,229,255,0.4);
        }
        .sidebar-title {
            padding: 14px 18px; color: var(--cyber-blue); font-family: 'Orbitron'; font-size: 12px;
            border-bottom: 1px solid rgba(0,229,255,0.2); display: flex; justify-content: space-between; align-items: center;
        }
        #feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 16px; }
        
        .card {
            background: rgba(255, 255, 255, 0.03); border-left: 4px solid var(--cyber-blue); padding: 14px; font-size: 12px;
            display: flex; flex-direction: column; gap: 8px; border-radius: 6px; border-top: 1px solid rgba(255,255,255,0.08);
        }
        .abm-btn {
            background: var(--cyber-red); color: #000; border: none; padding: 10px 14px; font-size: 11px;
            cursor: pointer; font-family: 'Orbitron'; font-weight: bold; margin-top: 6px; border-radius: 4px; transition: 0.3s;
        }
        .abm-btn:hover { background: #fff; box-shadow: 0 0 20px var(--cyber-red); }

        #terminal-box { background: rgba(0, 0, 0, 0.95); border-top: 1px solid rgba(0, 229, 255, 0.4); padding: 14px; display: flex; align-items: center; }
        #terminal-box span { color: var(--cyber-green); margin-right: 10px; font-weight: bold; font-size: 13px; }
        #cmd-prompt { background: transparent; border: none; color: var(--cyber-blue); width: 100%; font-family: 'Share Tech Mono'; font-size: 14px; outline: none; }
    </style>
</head>
<body>

    <!-- ULTRA SPLASH SCREEN COVER -->
    <div id="splash">
        <canvas id="particle-canvas"></canvas>
        <div class="hud-ring hud-ring-1"></div>
        <div class="hud-ring hud-ring-2"></div>
        <div class="splash-card glass-panel">
            <div class="clearance-tag">QUANTUM CLEARANCE: LEVEL 5 (CLASSIFIED OMNI)</div>
            <h1 class="main-title">PROJECT OMEGA</h1>
            <p style="letter-spacing:6px; color:#bbb; font-size:13px; margin-bottom:15px;">SUPREME 3D GLOBAL WAR ROOM & ABM MISSILE DEFENSE MATRIX</p>
            
            <div class="creator-badge">
                <div class="creator-title">CHIEF SYSTEM ARCHITECT</div>
                <div class="creator-name">👨‍💻 ผู้สร้าง ปกรณ์</div>
            </div>

            <button class="scan-launch-btn" onclick="authorizeSystem()">
                <span id="btn-text">INITIALIZE BIOMETRIC SCAN</span>
            </button>
        </div>
    </div>

    <!-- MAIN DASHBOARD UI -->
    <div id="top-bar">
        <span>PROJECT OMEGA TITAN v5.0 (3D GLOBE EDITION)</span>
        <span id="ticker-text">🚨 SYSTEM ONLINE: 3D SATELLITE RADAR ACTIVE | TELEGRAM ALERT CONNECTED</span>
        <span id="time-display">00:00:00 UTC</span>
    </div>

    <div id="container">
        <div id="camera-controls">
            <button class="cam-btn active" onclick="selectRegion('TH', 100.5, 13.7, 6.5, this)">🇹🇭 THAILAND COMMAND</button>
            <button class="cam-btn" onclick="selectRegion('GLOBAL', 100.0, 15.0, 2.2, this)">🌍 3D GLOBAL GLOBE</button>
            <button class="cam-btn" style="border-color:var(--cyber-red); color:var(--cyber-red);" onclick="triggerManualThreat()">⚡ SIMULATE THREAT</button>
        </div>

        <div id="defcon-widget" class="glass-panel">
            <button class="def-btn active-1" onclick="setDefcon(1, this)">DEFCON 1</button>
            <button class="def-btn" onclick="setDefcon(3, this)">DEFCON 3</button>
            <button class="def-btn active-5" onclick="setDefcon(5, this)">DEFCON 5</button>
        </div>

        <div id="map"></div>

        <div id="sidebar">
            <div class="sidebar-title">
                <span>TACTICAL QUANTUM ANALYTICS</span>
                <span style="font-size:11px; color:var(--cyber-green);">LIVE RADAR</span>
            </div>
            <div style="padding:15px; height:200px; border-bottom:1px solid rgba(255,255,255,0.1);">
                <canvas id="threatChart"></canvas>
            </div>
            <div class="sidebar-title">INCIDENT FEED & INTERCEPT CONTROL</div>
            <div id="feed"></div>
            <div id="terminal-box">
                <span>pakorn@omega-titan:~#</span>
                <input type="text" id="cmd-prompt" placeholder="Type /help or command..." autocomplete="off">
            </div>
        </div>
    </div>

    <script>
        let map, ws, audioCtx;
        let abmArcData = { 'type': 'FeatureCollection', 'features': [] };

        // Web Audio Synthesizer Engine
        function playSciFiSound(type) {
            try {
                if(!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
                osc.connect(gain); gain.connect(audioCtx.destination);
                
                if (type === 'scan') {
                    osc.type = 'sine'; osc.frequency.setValueAtTime(200, audioCtx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(1500, audioCtx.currentTime + 0.4);
                    gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
                    osc.start(); osc.stop(audioCtx.currentTime + 0.4);
                } else if (type === 'abm') {
                    osc.type = 'sawtooth'; osc.frequency.setValueAtTime(150, audioCtx.currentTime);
                    osc.frequency.exponentialRampToValueAtTime(2200, audioCtx.currentTime + 0.7);
                    gain.gain.setValueAtTime(0.35, audioCtx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.7);
                    osc.start(); osc.stop(audioCtx.currentTime + 0.7);
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

        function authorizeSystem() {
            playSciFiSound('scan');
            document.getElementById('btn-text').innerText = "BIOMETRICS CONFIRMED...";
            setTimeout(() => {
                document.getElementById('splash').style.display = 'none';
                speakAI("เข้าสู่ระบบยุทธการระดับโลก โปรเจกต์ โอเมก้า ไททัน โดยผู้สร้าง ปกรณ์ ระบบพร้อมทำงาน");
                init3DMap(); initChart(); initWebSocket();
                setInterval(updateClock, 1000);
            }, 800);
        }

        function init3DMap() {
            map = new maplibregl.Map({
                container: 'map',
                style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
                center: [100.5018, 13.7563],
                zoom: 2.5, pitch: 45, bearing: -10,
                projection: 'globe' // 3D Globe Projection!
            });

            map.on('load', () => {
                map.setProjection({ type: 'globe' });
                
                map.addSource('abm-source', { type: 'geojson', data: abmArcData });
                map.addLayer({
                    id: 'abm-layer', type: 'line', source: 'abm-source',
                    paint: { 'line-color': '#00e5ff', 'line-width': 4, 'line-blur': 1 }
                });
            });

            map.on('click', (e) => { launchABM(e.lngLat.lat, e.lngLat.lng); });
        }

        function initChart() {
            const ctx = document.getElementById('threatChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['15m', '12m', '9m', '6m', '3m', 'Now'],
                    datasets: [{
                        label: 'Quantum Threat Index',
                        data: [2, 5, 3, 9, 6, 12],
                        borderColor: '#00e5ff', backgroundColor: 'rgba(0, 229, 255, 0.15)',
                        borderWidth: 2, fill: true, tension: 0.4
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        function initWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws/telemetry`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if(data.title) {
                    appendFeedCard(data.color || '#ff0055', data.title, data.summary, data.latitude, data.longitude, data.timestamp);
                }
            };
        }

        function appendFeedCard(color, title, desc, lat=null, lng=null, time="NOW") {
            const feed = document.getElementById('feed');
            const card = document.createElement('div');
            card.className = 'card'; card.style.borderLeftColor = color;
            let btnHtml = (lat && lng) ? `<button class="abm-btn" onclick="launchABM(${lat}, ${lng})">🚀 LAUNCH ABM INTERCEPTOR</button>` : '';
            card.innerHTML = `<div style="display:flex; justify-content:space-between;"><b style="color:${color}">${title}</b><span style="color:#666;">${time}</span></div><span>${desc}</span>${btnHtml}`;
            feed.prepend(card);
        }

        async function launchABM(targetLat, targetLng) {
            playSciFiSound('abm');
            speakAI("ยิง จรวด สกัด กั้น");
            
            const baseLat = 12.6664, baseLng = 100.9007;
            const steps = 30;
            for (let i = 0; i <= steps; i++) {
                const t = i / steps;
                const curLng = baseLng + (targetLng - baseLng) * t;
                const curLat = baseLat + (targetLat - baseLat) * t;
                
                abmArcData.features = [{
                    'type': 'Feature',
                    'geometry': { 'type': 'LineString', 'coordinates': [[baseLng, baseLat], [curLng, curLat]] }
                }];
                if(map.getSource('abm-source')) map.getSource('abm-source').setData(abmArcData);
                await new Promise(r => setTimeout(r, 12));
            }
            
            setTimeout(() => {
                abmArcData.features = [];
                if(map.getSource('abm-source')) map.getSource('abm-source').setData(abmArcData);
                appendFeedCard('#00ff88', 'TARGET DESTROYED', `ยิงสกัดกั้นสำเร็จที่พิกัด ${targetLat.toFixed(2)}, ${targetLng.toFixed(2)}`);
            }, 300);

            try {
                await fetch('/api/v1/abm/launch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target_lat: targetLat, target_lng: targetLng })
                });
            } catch(e) {}
        }

        function selectRegion(region, lng, lat, zoom, btn) {
            document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            map.flyTo({ center: [lng, lat], zoom: zoom, speed: 1.2, pitch: zoom > 4 ? 60 : 30 });
        }

        function triggerManualThreat() {
            fetch('/api/v1/telemetry/trigger?region=TH', {method:'POST'});
        }

        function setDefcon(level, btn) {
            document.querySelectorAll('.def-btn').forEach(b => b.className = 'def-btn');
            if(level === 1) {
                btn.className = 'def-btn active-1';
                document.documentElement.style.setProperty('--cyber-red', '#ff0000');
                speakAI("แจ้งเตือน สภาวะวิกฤตระดับ เดฟคอน 1");
            } else {
                btn.className = 'def-btn active-5';
                speakAI("สภาวะปกติ เดฟคอน " + level);
            }
        }

        function updateClock() {
            const now = new Date();
            document.getElementById('time-display').innerText = now.toUTCString().split(' ')[4] + " UTC";
        }

        // Canvas Particle Starfield Animation
        const canvas = document.getElementById('particle-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        let particles = Array.from({length: 80}, () => ({
            x: Math.random() * canvas.width, y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 1.0, vy: (Math.random() - 0.5) * 1.0
        }));

        function drawParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'rgba(0, 229, 255, 0.6)';
            particles.forEach(p => {
                p.x += p.vx; p.y += p.vy;
                if(p.x < 0 || p.x > canvas.width) p.vx *= -1;
                if(p.y < 0 || p.y > canvas.height) p.vy *= -1;
                ctx.beginPath(); ctx.arc(p.x, p.y, 2, 0, Math.PI * 2); ctx.fill();
            });
            requestAnimationFrame(drawParticles);
        }
        drawParticles();

        document.getElementById('cmd-prompt').addEventListener('keypress', function(e) {
            if(e.key === 'Enter') {
                const cmd = this.value.trim();
                if(cmd === '/trigger') triggerManualThreat();
                else if(cmd === '/help') appendFeedCard('#00e5ff', 'SYSTEM COMMANDS', '/trigger - จำลองภัยคุกคาม | /help - คำแนะนำ');
                this.value = '';
            }
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return HTML_CONTENT

# ==========================================
# 6. EXECUTION POINT
# ==========================================
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)