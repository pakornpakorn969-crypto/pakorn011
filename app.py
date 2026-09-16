import json
import random
import asyncio
from typing import List
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# =====================================================================
# 🗄️ 1. DATABASE SETUP
# =====================================================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./omega.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="UNKNOWN")
    incident_type = Column(String, index=True)
    latitude = Column(Float)
    longitude = Column(Float)
    threat_level = Column(Float)
    wave_height = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================================
# ⚙️ 2. CONFIGURATION & CONSTANTS
# =====================================================================
LOCATIONS_BY_REGION = {
    "TH": [
        {"name": "กรุงเทพมหานคร / BANGKOK", "lat": 13.7563, "lng": 100.5018},
        {"name": "เชียงใหม่ / CHIANG MAI", "lat": 18.7883, "lng": 98.9853},
        {"name": "ภูเก็ต / PHUKET", "lat": 7.8804, "lng": 98.3923}
    ],
    "GLOBAL": [
        {"name": "ลอสแอนเจลิส / LOS ANGELES", "lat": 34.0522, "lng": -118.2437},
        {"name": "โตเกียว / TOKYO", "lat": 35.6762, "lng": 139.6503},
        {"name": "วงแหวนไฟ / RING OF FIRE", "lat": 12.5000, "lng": 140.0000}
    ]
}

THREAT_TYPES = [
    {"type": "ORBITAL", "title": "KINETIC ORBITAL STRIKE", "level": 10.0, "wave": 0},
    {"type": "NUCLEAR", "title": "THERMONUCLEAR DETONATION", "level": 9.9, "wave": 0},
    {"type": "ASTEROID", "title": "EXTINCTION ASTEROID IMPACT", "level": 10.0, "wave": 50.0},
    {"type": "TSUNAMI", "title": "MEGA TSUNAMI DISASTER", "level": 9.0, "wave": 25.0}
]

THREAT_CONFIG = {
    "ORBITAL": {"protocol": "OMEGA-ZERO", "color": "#00ffff", "radius": 60, "desc": "ลำแสงเลเซอร์ดาวเทียมเข้าปะทะเป้าหมาย"},
    "NUCLEAR": {"protocol": "EXTINCTION", "color": "#ff0000", "radius": 55, "desc": "ระเบิดเทอร์โมนิวเคลียร์ทำงาน กัมมันตรังสีแพร่กระจาย"},
    "ASTEROID": {"protocol": "EXTINCTION", "color": "#ff5500", "radius": 70, "desc": "อุกกาบาตยักษ์ทำลายล้างพื้นผิวโลก"},
    "TSUNAMI": {"protocol": "EXTINCTION", "color": "#0099ff", "radius": 45, "desc": "มหาคลื่นยักษ์ถล่มแนวชายฝั่ง"}
}

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
            try: await connection.send_text(message)
            except Exception: self.disconnect(connection)

manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="PROJECT OMEGA EXTREME", lifespan=lifespan)

class StrikeCoords(BaseModel):
    lat: float
    lng: float

# =====================================================================
# 🌐 3. ADVANCED DASHBOARD INTERFACE WITH EPIC SPLASH SCREEN
# =====================================================================
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="th">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PROJECT OMEGA | Command Matrix</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=Prompt:wght@300;400;600&family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet" />
        <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
        <style>
            :root { --bg: #03070d; --cyber-red: #ff003c; --cyber-blue: #00e5ff; --panel-bg: rgba(4, 10, 20, 0.94); }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { background-color: var(--bg); color: #fff; font-family: 'Share Tech Mono', 'Prompt', sans-serif; overflow: hidden; height: 100vh; width: 100vw; cursor: crosshair; }
            
            /* CRT Scanline Effect */
            body::before { content: " "; display: block; position: absolute; top: 0; left: 0; bottom: 0; right: 0; background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%); z-index: 9999; background-size: 100% 4px; pointer-events: none; }
            .shake { animation: shakeAnim 0.15s infinite; }
            @keyframes shakeAnim { 0% { transform: translate(2px, 2px); } 50% { transform: translate(-2px, -1px); } 100% { transform: translate(1px, -2px); } }

            /* =========================================================
               🔥 EPIC SPLASH SCREEN DESIGN & CREATOR BADGE
               ========================================================= */
            #splash { 
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; 
                background: radial-gradient(circle at center, #0a192f 0%, #03070d 100%); 
                z-index: 10000; display: flex; flex-direction: column; align-items: center; justify-content: center; 
                backdrop-filter: blur(15px); overflow: hidden;
            }
            
            /* Background Hologram Grid */
            #splash::after {
                content: ""; position: absolute; width: 200%; height: 200%;
                background-image: linear-gradient(rgba(0, 229, 255, 0.05) 1px, transparent 1px),
                                  linear-gradient(90deg, rgba(0, 229, 255, 0.05) 1px, transparent 1px);
                background-size: 40px 40px; transform: perspective(500px) rotateX(60deg);
                animation: gridMove 20s linear infinite; pointer-events: none; z-index: 1;
            }
            @keyframes gridMove { 0% { transform: perspective(500px) rotateX(60deg) translateY(0); } 100% { transform: perspective(500px) rotateX(60deg) translateY(40px); } }

            .splash-content { z-index: 2; display: flex; flex-direction: column; align-items: center; text-align: center; max-width: 800px; padding: 20px; }

            .system-tag { 
                font-family: 'Orbitron'; font-size: 12px; letter-spacing: 6px; color: var(--cyber-blue); 
                border: 1px solid var(--cyber-blue); padding: 4px 14px; border-radius: 20px; margin-bottom: 20px;
                box-shadow: 0 0 15px rgba(0, 229, 255, 0.3); animation: pulseGlow 2s infinite alternate;
            }
            @keyframes pulseGlow { 0% { box-shadow: 0 0 5px rgba(0,229,255,0.2); } 100% { box-shadow: 0 0 20px rgba(0,229,255,0.8); } }

            .main-title { 
                font-family: 'Orbitron', sans-serif; font-size: 4.5rem; font-weight: 900; 
                background: linear-gradient(180deg, #ffffff 0%, var(--cyber-blue) 60%, var(--cyber-red) 100%);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                text-shadow: 0 0 40px rgba(0, 229, 255, 0.5); letter-spacing: 4px; margin-bottom: 5px;
            }

            .sub-title { font-size: 14px; color: #888; letter-spacing: 4px; margin-bottom: 30px; }

            /* 🪪 CREATOR BADGE / แถบใส่ชื่อคนสร้าง */
            .creator-card {
                background: rgba(8, 16, 28, 0.85); border: 1px solid rgba(0, 229, 255, 0.5);
                border-left: 5px solid var(--cyber-red); border-right: 5px solid var(--cyber-blue);
                padding: 12px 28px; border-radius: 6px; margin-bottom: 35px;
                box-shadow: 0 0 25px rgba(0, 0, 0, 0.8); display: flex; flex-direction: column; gap: 4px;
                backdrop-filter: blur(10px); transition: 0.3s;
            }
            .creator-card:hover { border-color: var(--cyber-blue); box-shadow: 0 0 20px rgba(0, 229, 255, 0.4); }
            .creator-label { font-size: 10px; color: #aaa; font-family: 'Orbitron'; letter-spacing: 2px; }
            .creator-name { font-size: 18px; font-weight: 700; color: #fff; font-family: 'Prompt'; text-shadow: 0 0 10px var(--cyber-blue); }

            /* Launch Button */
            .launch-btn { 
                background: transparent; border: 2px solid var(--cyber-red); color: var(--cyber-red); 
                padding: 16px 50px; font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 700;
                cursor: pointer; transition: 0.3s; position: relative; overflow: hidden; letter-spacing: 2px;
                box-shadow: 0 0 15px rgba(255, 0, 60, 0.3);
            }
            .launch-btn:hover { 
                background: var(--cyber-red); color: #000; box-shadow: 0 0 35px var(--cyber-red); 
                transform: scale(1.05);
            }
<span class="creator-name">👨‍💻 [ ผู้สร้าง ปกรณ์ / YOUR NAME ]</span>

            /* Dashboard Layout CSS */
            #top-ticker { position: absolute; top: 0; left: 0; width: 100%; height: 30px; background: rgba(255, 0, 60, 0.25); border-bottom: 1px solid var(--cyber-red); z-index: 20; display: flex; align-items: center; overflow: hidden; font-size: 12px; font-family: 'Orbitron', sans-serif; }
            #ticker-content { white-space: nowrap; animation: ticker 20s linear infinite; color: #ff3366; font-weight: bold; }
            @keyframes ticker { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
            
            #container { display: flex; width: 100vw; height: 100vh; position: relative; padding-top: 30px; }
            #map { flex: 1; height: 100%; background: #03070d; }
            
            #defcon-badge { position: absolute; top: 45px; right: 380px; z-index: 10; background: rgba(255, 0, 0, 0.2); border: 2px solid var(--cyber-red); padding: 8px 18px; border-radius: 4px; font-family: 'Orbitron'; text-align: center; }
            .defcon-title { font-size: 10px; color: #aaa; }
            .defcon-level { font-size: 24px; font-weight: 900; color: #00ff66; text-shadow: 0 0 10px #00ff66; }
            
            #camera-controls { position: absolute; top: 45px; left: 20px; z-index: 10; display: flex; gap: 8px; }
            .cam-btn { background: var(--panel-bg); border: 1px solid rgba(0, 229, 255, 0.4); color: #ccc; padding: 8px 16px; font-size: 11px; cursor: pointer; font-family: 'Prompt', sans-serif; transition: 0.3s; }
            .cam-btn:hover, .cam-btn.active { background: var(--cyber-blue); color: #000; box-shadow: 0 0 10px var(--cyber-blue); }
            
            #sidebar { width: 360px; height: calc(100% - 30px); background: var(--panel-bg); border-left: 1px solid var(--cyber-blue); display: flex; flex-direction: column; z-index: 10; }
            #sidebar-header { padding: 15px; color:var(--cyber-blue); font-family:'Orbitron'; border-bottom:1px solid #333; }
            #feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding: 15px; }
            #terminal-box { background: #000; border-top: 1px solid var(--cyber-blue); padding: 12px; display: flex; align-items: center; }
            #terminal-box span { color: #00ff66; margin-right: 8px; font-weight: bold; font-size: 13px; }
            #cmd-prompt { background: transparent; border: none; color: #00e5ff; width: 100%; font-family: 'Share Tech Mono', monospace; font-size: 13px; outline: none; }
            .card { background: rgba(255, 255, 255, 0.03); border-left: 4px solid var(--cyber-blue); padding: 10px; font-size: 11px; }
            
            .ripple-container { position: relative; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; }
            .dot-marker { width: 14px; height: 14px; border-radius: 50%; background: var(--cyber-red); position: absolute; z-index: 2; box-shadow: 0 0 15px var(--cyber-red); }
            .ripple-ring { position: absolute; width: 40px; height: 40px; border-radius: 50%; border: 2px solid var(--cyber-red); animation: rippleEffect 1.5s infinite ease-out; opacity: 0; }
            @keyframes rippleEffect { 0% { transform: scale(0.1); opacity: 1; } 100% { transform: scale(3.0); opacity: 0; } }
            
            #emp-flash { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: white; z-index: 99999; opacity: 0; pointer-events: none; transition: opacity 0.4s ease-out; }
            .target-tooltip { background: rgba(0,0,0,0.9); color: #00e5ff; padding: 4px 8px; border: 1px solid #00e5ff; font-size: 10px; font-family: 'Orbitron'; position: absolute; pointer-events: none; display: none; z-index: 999; }
        </style>
    </head>
    <body>
        <!-- 🔥 EPIC SPLASH SCREEN OVERLAY -->
        <div id="splash">
            <div class="splash-content">
                <div class="system-tag">SECURITY CLEARANCE: LEVEL 5 (CLASSIFIED)</div>
                <h1 class="main-title">PROJECT OMEGA</h1>
                <p class="sub-title">GLOBAL DISASTER MONITORING & COMMAND MATRIX</p>
                
                <!-- 🪪 แถบใส่ชื่อคนสร้าง / CREATOR BADGE -->
                <div class="creator-card">
                    <span class="creator-label">SYSTEM ARCHITECT / DEVELOPER</span>
                    <span class="creator-name">👨‍💻 [ ผู้สร้าง ปกรณ์ ]</span>
                </div>

                <button class="launch-btn" onclick="authorizeSystem()">ENGAGE DEFCON 5</button>
            </div>
        </div>

        <div id="emp-flash"></div>
        <div class="target-tooltip" id="crosshair">TARGET LOCK</div>
        <div id="top-ticker"><div id="ticker-content">🚨 OMEGA SYSTEM STANDBY: AWAITING COMMAND PROTOCOLS...</div></div>
        
        <div id="container">
            <div id="camera-controls">
                <button class="cam-btn active" onclick="selectRegion('TH', 100.5, 13.7, 5.5, this)">🇹🇭 THAILAND</button>
                <button class="cam-btn" onclick="selectRegion('GLOBAL', 100.0, 15.0, 1.8, this)">🌍 GLOBAL</button>
            </div>
            
            <div id="defcon-badge">
                <div class="defcon-title">SYSTEM STATUS</div>
                <div id="defcon-val" class="defcon-level">DEFCON 5</div>
            </div>
            
            <div id="map"></div>
            
            <div id="sidebar">
                <div id="sidebar-header">CRITICAL INCIDENT LOGS</div>
                <div id="feed"></div>
                <div id="terminal-box">
                    <span>root@omega:~#</span>
                    <input type="text" id="cmd-prompt" placeholder="Command (/help)..." autocomplete="off">
                </div>
            </div>
        </div>

        <script>
            let map, ws, currentDefcon = 5;
            let geoData = { 'type': 'FeatureCollection', 'features': [] };
            let laserData = { 'type': 'FeatureCollection', 'features': [] };

            function playAlarmSound(frequency = 1046.5) {
                try {
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    const osc = audioCtx.createOscillator();
                    const gain = audioCtx.createGain();
                    osc.type = 'sawtooth';
                    osc.frequency.setValueAtTime(frequency, audioCtx.currentTime); 
                    osc.frequency.exponentialRampToValueAtTime(frequency / 2, audioCtx.currentTime + 0.4); 
                    gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4);
                    osc.connect(gain); gain.connect(audioCtx.destination);
                    osc.start(); osc.stop(audioCtx.currentTime + 0.4);
                } catch(e) {}
            }

            function speakAI(text) {
                if(!('speechSynthesis' in window)) return;
                window.speechSynthesis.cancel();
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = 1.0; utterance.lang = 'th-TH';
                window.speechSynthesis.speak(utterance);
            }

            function setDefcon(level) {
                currentDefcon = level;
                const badge = document.getElementById('defcon-val');
                badge.innerText = `DEFCON ${level}`;
                
                if(level === 1) {
                    badge.style.color = '#ff003c'; badge.style.textShadow = '0 0 15px #ff003c';
                    document.body.classList.add('shake');
                    speakAI("เตือนภัยระดับสูงสุด เดฟคอน 1 เข้าสู่ภาวะสงครามและภัยพิบัติล้างเผ่าพันธุ์");
                } else {
                    badge.style.color = '#00ff66'; badge.style.textShadow = '0 0 10px #00ff66';
                    document.body.classList.remove('shake');
                }
            }

            function authorizeSystem() {
                document.getElementById('splash').style.display = 'none';
                speakAI("เข้าสู่ระบบควบคุมโอเมก้าขั้นสูงสุด พร้อมรับคำสั่งยุทธการ");
                initMap(); initWebSocket();
            }

            async function selectRegion(region, lng, lat, zoom, btnElem) {
                document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
                if(btnElem) btnElem.classList.add('active');
                map.flyTo({ center: [lng, lat], zoom: zoom, speed: 1.4 });
                await fetch(`/api/v1/telemetry/trigger?region=${region}`, { method: 'POST' });
            }

            function fireOrbitalLaser(targetLng, targetLat) {
                const satLng = targetLng + 15.0;
                const satLat = targetLat + 25.0;
                
                laserData.features.push({
                    'type': 'Feature',
                    'geometry': { 'type': 'LineString', 'coordinates': [[satLng, satLat], [targetLng, targetLat]] }
                });
                if(map.getSource('laser-source')) map.getSource('laser-source').setData(laserData);
                
                playAlarmSound(1800);
                setTimeout(() => {
                    laserData.features = [];
                    if(map.getSource('laser-source')) map.getSource('laser-source').setData(laserData);
                }, 800);
            }

            document.getElementById('cmd-prompt').addEventListener('keypress', async function (e) {
                if (e.key === 'Enter') {
                    const cmd = this.value.trim().toLowerCase();
                    this.value = ''; 
                    
                    if (cmd === '/defcon1' || cmd.includes('วิกฤต')) {
                        setDefcon(1);
                        for(let i=0; i<3; i++) await fetch('/api/v1/telemetry/trigger?region=GLOBAL', { method: 'POST' });
                    } else if (cmd === '/orbital' || cmd.includes('เลเซอร์')) {
                        speakAI("เปิดใช้งานอาวุธเลเซอร์วงโคจร ยิงใส่พิกัดยุทธศาสตร์");
                        fireOrbitalLaser(100.5018, 13.7563);
                        await fetch('/api/v1/telemetry/strike', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ lat: 13.7563, lng: 100.5018 })
                        });
                    } else if (cmd === '/shield' || cmd.includes('เกราะ')) {
                        setDefcon(5);
                        speakAI("เปิดเกราะป้องกัน ล้างภัยพิบัติทั้งหมด");
                        const flash = document.getElementById('emp-flash');
                        flash.style.opacity = '1';
                        setTimeout(() => {
                            geoData.features = [];
                            if (map.getSource('impact-zones')) map.getSource('impact-zones').setData(geoData);
                            document.querySelectorAll('.ripple-container').forEach(m => m.remove());
                            flash.style.opacity = '0';
                        }, 400);
                    } else if (cmd === '/help') {
                        appendFeedCard('#00e5ff', 'EXTINCTION COMMANDS', '<b>/defcon1</b> : ยกระดับวิกฤตสูงสุด<br><b>/orbital</b> : ยิงเลเซอร์ดาวเทียม<br><b>/shield</b> : ล้างภัยพิบัติ');
                    } else {
                        fetch(`/api/v1/telemetry/trigger?region=GLOBAL`, { method: 'POST' });
                    }
                }
            });

            function appendFeedCard(color, title, bodyHTML) {
                const feed = document.getElementById('feed');
                const card = document.createElement('div');
                card.className = 'card'; card.style.borderLeftColor = color;
                card.innerHTML = `<div style="color:${color}; font-weight:bold;">${title}</div><div style="font-family:'Prompt'; margin-top:4px;">${bodyHTML}</div>`;
                feed.insertBefore(card, feed.firstChild);
            }

            function initMap() {
                map = new maplibregl.Map({
                    container: 'map', style: 'https://tiles.openfreemap.org/styles/dark',
                    center: [100.5, 13.7], zoom: 5.5, pitch: 45
                });
                
                map.on('load', () => {
                    map.addSource('impact-zones', { type: 'geojson', data: geoData });
                    map.addLayer({
                        'id': 'impact-circles', 'type': 'circle', 'source': 'impact-zones',
                        'paint': { 'circle-radius': ['get', 'radius'], 'circle-color': ['get', 'color'], 'circle-opacity': 0.5 }
                    });
                    
                    map.addSource('laser-source', { type: 'geojson', data: laserData });
                    map.addLayer({
                        'id': 'laser-lines', 'type': 'line', 'source': 'laser-source',
                        'paint': { 'line-color': '#00ffff', 'line-width': 4, 'line-blur': 2 }
                    });
                });

                const tooltip = document.getElementById('crosshair');
                map.on('mousemove', (e) => {
                    tooltip.style.display = 'block';
                    tooltip.style.left = e.point.x + 15 + 'px';
                    tooltip.style.top = e.point.y + 15 + 'px';
                    tooltip.innerText = `TARGET: ${e.lngLat.lat.toFixed(4)} N, ${e.lngLat.lng.toFixed(4)} E`;
                });
                map.on('mouseout', () => { tooltip.style.display = 'none'; });
                
                map.on('click', async (e) => {
                    fireOrbitalLaser(e.lngLat.lng, e.lngLat.lat);
                    await fetch('/api/v1/telemetry/strike', {
                        method: 'POST', headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ lat: e.lngLat.lat, lng: e.lngLat.lng })
                    });
                });
            }

            function initWebSocket() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws/telemetry`);
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    playAlarmSound(1200);
                    speakAI("เตือนภัย " + data.summary);

                    document.getElementById('ticker-content').innerText = `🚨 CRITICAL THREAT: ${data.title} [LEVEL ${data.threat_level}]`;
                    
                    const el = document.createElement('div');
                    el.className = 'ripple-container';
                    el.innerHTML = `<div class="dot-marker" style="background:${data.color}"></div><div class="ripple-ring" style="border-color:${data.color}"></div>`;
                    new maplibregl.Marker(el).setLngLat([data.longitude, data.latitude]).addTo(map);

                    geoData.features.push({
                        'type': 'Feature', 'properties': { 'radius': data.radius, 'color': data.color },
                        'geometry': { 'type': 'Point', 'coordinates': [data.longitude, data.latitude] }
                    });
                    if (map.getSource('impact-zones')) map.getSource('impact-zones').setData(geoData);

                    appendFeedCard(data.color, data.title, `LEVEL: ${data.threat_level} | ${data.protocol}`);
                };
                ws.onclose = () => setTimeout(initWebSocket, 3000);
            }
        </script>
    </body>
    </html>
    """

# =====================================================================
# 🚀 4. REST API ENDPOINTS
# =====================================================================
@app.post("/api/v1/telemetry/strike")
async def strike_target(coords: StrikeCoords, db: Session = Depends(get_db)):
    threat = random.choice(THREAT_TYPES)
    new_incident = Incident(
        title=f"STRIKE: {threat['type']}", incident_type=threat["type"],
        latitude=coords.lat, longitude=coords.lng, threat_level=threat["level"], wave_height=threat["wave"]
    )
    db.add(new_incident); db.commit(); db.refresh(new_incident)

    cfg = THREAT_CONFIG.get(new_incident.incident_type, {"protocol": "EXTINCTION", "color": "#ff003c", "radius": 50, "desc": "ภัยพิบัติรุนแรงปะทะ"})
    payload = {
        "id": new_incident.id, "title": new_incident.title, "incident_type": new_incident.incident_type,
        "latitude": new_incident.latitude, "longitude": new_incident.longitude, "threat_level": new_incident.threat_level,
        "protocol": cfg["protocol"], "radius": cfg["radius"], "color": cfg["color"], "summary": cfg['desc']
    }
    await manager.broadcast(json.dumps(payload))
    return {"status": "success", "data": payload}

@app.post("/api/v1/telemetry/trigger")
async def trigger_event(region: str = "TH", db: Session = Depends(get_db)):
    reg_key = region.upper() if region.upper() in LOCATIONS_BY_REGION else "TH"
    loc = random.choice(LOCATIONS_BY_REGION[reg_key])
    threat = random.choice(THREAT_TYPES)

    new_incident = Incident(
        title=f"{threat['title']} - {loc['name']}", incident_type=threat["type"],
        latitude=loc["lat"] + random.uniform(-0.1, 0.1), longitude=loc["lng"] + random.uniform(-0.1, 0.1),
        threat_level=threat["level"]
    )
    db.add(new_incident); db.commit(); db.refresh(new_incident)

    cfg = THREAT_CONFIG.get(new_incident.incident_type, {"protocol": "EXTINCTION", "color": "#ff003c", "radius": 45, "desc": "ภัยพิบัติเข้าปะทะ"})
    payload = {
        "id": new_incident.id, "title": new_incident.title, "incident_type": new_incident.incident_type,
        "latitude": new_incident.latitude, "longitude": new_incident.longitude, "threat_level": new_incident.threat_level,
        "protocol": cfg["protocol"], "radius": cfg["radius"], "color": cfg["color"], "summary": cfg['desc']
    }
    await manager.broadcast(json.dumps(payload))
    return {"status": "success"}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)