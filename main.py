import os
import json
import random
import asyncio
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
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
        ("⚡ การโจมตี Quantum Cybernetics ต่อดาวเทียม", "SATELLITE_HACK", "#00f3ff"),
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
# 4. API ENDPOINTS & ANALYTICS
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
        "color": "#00ff9d",
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
# 5. ADMIN BACKOFFICE DASHBOARD PAGE (/admin)
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
            --bg-dark: #060913;
            --card-bg: rgba(13, 20, 38, 0.85);
            --cyber-cyan: #00f3ff;
            --cyber-pink: #ff0055;
            --cyber-green: #00ff9d;
            --cyber-purple: #a855f7;
            --cyber-gold: #ffc800;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-dark); color: #f1f5f9;
            font-family: 'Chakra Petch', 'JetBrains Mono', sans-serif;
            min-height: 100vh; padding: 24px;
            -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
        }

        header {
            display: flex; justify-content: space-between; align-items: center;
            padding-bottom: 20px; border-bottom: 1px solid rgba(0, 243, 255, 0.25);
            margin-bottom: 25px;
        }

        .title-group h1 { font-family: 'Orbitron'; color: var(--cyber-cyan); font-size: 1.8rem; letter-spacing: 2px; text-shadow: 0 0 15px rgba(0,243,255,0.4); }
        .title-group p { font-size: 0.95rem; color: #94a3b8; margin-top: 4px; }
        
        .nav-btn {
            background: rgba(0, 243, 255, 0.08); border: 1px solid var(--cyber-cyan); color: var(--cyber-cyan);
            padding: 10px 22px; border-radius: 6px; font-family: 'Orbitron'; font-size: 13px; font-weight: 700;
            cursor: pointer; text-decoration: none; transition: all 0.25s ease;
        }
        .nav-btn:hover { background: var(--cyber-cyan); color: #000; box-shadow: 0 0 20px var(--cyber-cyan); }

        .metrics-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px; margin-bottom: 25px;
        }

        .metric-card {
            background: var(--card-bg); border: 1px solid rgba(255, 255, 255, 0.12);
            border-left: 4px solid var(--cyber-cyan); border-radius: 10px; padding: 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5); backdrop-filter: blur(12px);
        }
        .metric-title { font-size: 12px; color: #94a3b8; font-family: 'Orbitron'; letter-spacing: 1px; }
        .metric-value { font-size: 2.2rem; font-weight: 700; color: #fff; margin-top: 6px; font-family: 'Orbitron'; }

        .charts-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
            gap: 20px; margin-bottom: 25px;
        }

        .chart-card {
            background: var(--card-bg); border: 1px solid rgba(0, 243, 255, 0.2);
            border-radius: 12px; padding: 22px; height: 360px; display: flex; flex-direction: column;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6); backdrop-filter: blur(12px);
        }
        .chart-card h3 {
            font-family: 'Orbitron'; font-size: 15px; color: var(--cyber-cyan); letter-spacing: 1px;
            margin-bottom: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px;
        }
        .chart-container { flex: 1; position: relative; }

        .table-card {
            background: var(--card-bg); border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 12px; padding: 22px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); backdrop-filter: blur(12px);
        }
        .table-card h3 { font-family: 'Orbitron'; color: var(--cyber-gold); font-size: 15px; margin-bottom: 16px; letter-spacing: 1px; }

        table { width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }
        th { background: rgba(0, 243, 255, 0.12); color: var(--cyber-cyan); padding: 12px; font-family: 'Orbitron'; font-size: 12px; }
        td { padding: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-family: 'JetBrains Mono', sans-serif; }
        tr:hover { background: rgba(0, 243, 255, 0.04); }
    </style>
</head>
<body>

    <header>
        <div class="title-group">
            <h1>⚙️ OMEGA BACKEND ANALYTICS CONTROL</h1>
            <p>แผงวิเคราะห์และประมวลผลสถิติจำลองภัยคุกคามหลังบ้าน (Real-time Database Telemetry)</p>
        </div>
        <a href="/" class="nav-btn">🔙 MAIN WAR ROOM</a>
    </header>

    <div class="metrics-grid">
        <div class="metric-card" style="border-left-color: var(--cyber-cyan);">
            <div class="metric-title">TOTAL INCIDENTS RECORDED</div>
            <div class="metric-value" id="val-total">0</div>
        </div>
        <div class="metric-card" style="border-left-color: var(--cyber-pink);">
            <div class="metric-title">CRITICAL DEFCON 1 THREATS</div>
            <div class="metric-value" id="val-def1" style="color: var(--cyber-pink);">0</div>
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
            <h3>📊 THREAT DISTRIBUTION BY TYPE (ประเภทภัยคุกคาม)</h3>
            <div class="chart-container">
                <canvas id="typeDoughnutChart"></canvas>
            </div>
        </div>
        <div class="chart-card">
            <h3>📈 INCIDENTS BY SEVERITY LEVEL (ระดับความรุนแรง)</h3>
            <div class="chart-container">
                <canvas id="severityBarChart"></canvas>
            </div>
        </div>
    </div>

    <div class="table-card">
        <h3>📋 RECENT DB INCIDENT LOGS (รายการล่าสุดในฐานข้อมูล)</h3>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>TIME</th>
                    <th>THREAT TITLE</th>
                    <th>TYPE</th>
                    <th>SEVERITY</th>
                    <th>COORDINATES</th>
                </tr>
            </thead>
            <tbody id="logs-tbody">
                <tr><td colspan="6" style="text-align:center; color:#666;">กำลังโหลดข้อมูล...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        Chart.defaults.devicePixelRatio = window.devicePixelRatio || 2;
        let doughnutChart, barChart;

        function initAdminCharts() {
            const ctxDoughnut = document.getElementById('typeDoughnutChart').getContext('2d');
            doughnutChart = new Chart(ctxDoughnut, {
                type: 'doughnut',
                data: {
                    labels: ['ICBM Launch', 'Drone Swarm', 'Satellite Hack', 'UFO Tactical'],
                    datasets: [{
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#ff0055', '#ffc800', '#00f3ff', '#a855f7'],
                        borderColor: '#060913', borderWidth: 2
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: 'right', labels: { color: '#e2e8f0', font: { family: 'Chakra Petch', size: 13 } } } }
                }
            });

            const ctxBar = document.getElementById('severityBarChart').getContext('2d');
            barChart = new Chart(ctxBar, {
                type: 'bar',
                data: {
                    labels: ['DEFCON 1', 'DEFCON 2', 'DEFCON 3', 'DEFCON 5'],
                    datasets: [{
                        label: 'จำนวนเหตุการณ์',
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#ff0055', '#ffc800', '#00f3ff', '#00ff9d'],
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.06)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono' } } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { family: 'Orbitron' } } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        async function fetchBackendStats() {
            try {
                const res = await fetch('/api/v1/analytics/stats');
                const data = await res.json();

                document.getElementById('val-total').innerText = data.total_incidents;
                document.getElementById('val-def1').innerText = data.by_severity['DEFCON 1'] || 0;
                document.getElementById('val-ws').innerText = data.active_ws_connections;

                doughnutChart.data.datasets[0].data = [
                    data.by_type['ICBM_LAUNCH'] || 0,
                    data.by_type['DRONE_SWARM'] || 0,
                    data.by_type['SATELLITE_HACK'] || 0,
                    data.by_type['UFO_TACTICAL'] || 0
                ];
                doughnutChart.update();

                barChart.data.datasets[0].data = [
                    data.by_severity['DEFCON 1'] || 0,
                    data.by_severity['DEFCON 2'] || 0,
                    data.by_severity['DEFCON 3'] || 0,
                    data.by_severity['DEFCON 5'] || 0
                ];
                barChart.update();

                const tbody = document.getElementById('logs-tbody');
                tbody.innerHTML = '';
                data.timeline.forEach(item => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>#${item.id}</td>
                        <td>${item.time}</td>
                        <td style="color:#fff; font-weight:600;">${item.title}</td>
                        <td><span style="background:rgba(0,243,255,0.12); color:var(--cyber-cyan); border:1px solid rgba(0,243,255,0.3); padding:3px 10px; border-radius:4px; font-size:11px;">${item.type}</span></td>
                        <td style="color:${item.severity.includes('1') ? 'var(--cyber-pink)': 'var(--cyber-gold)'}; font-weight:bold;">${item.severity}</td>
                        <td>${item.lat.toFixed(2)}, ${item.lng.toFixed(2)}</td>
                    `;
                    tbody.appendChild(tr);
                });

            } catch(e) {}
        }

        window.onload = () => {
            initAdminCharts();
            fetchBackendStats();
            setInterval(fetchBackendStats, 3000);
        };
    </script>
</body>
</html>
"""

# ==========================================
# 6. FRONTEND MAIN DASHBOARD HTML/CSS/JS (ULTRA-CRISP DESIGN)
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
            --bg-color: #030611;
            --cyber-pink: #ff0055;
            --cyber-cyan: #00f3ff;
            --cyber-green: #00ff9d;
            --cyber-gold: #ffc800;
            --cyber-purple: #b026ff;
            --panel-bg: rgba(8, 14, 28, 0.88);
            --panel-border: rgba(0, 243, 255, 0.35);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        
        body { 
            background-color: var(--bg-color); color: #f8fafc; 
            font-family: 'Chakra Petch', 'JetBrains Mono', sans-serif; 
            overflow: hidden; height: 100vh; width: 100vw; 
            -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
            text-rendering: optimizeLegibility;
        }

        /* Glass Panel Ultra Crisp */
        .glass-panel {
            background: var(--panel-bg); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--panel-border); box-shadow: 0 12px 40px rgba(0, 0, 0, 0.7);
        }

        /* SPLASH SCREEN */
        #splash {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: radial-gradient(circle at center, #0b152e 0%, #02040a 100%);
            z-index: 10000; display: flex; flex-direction: column; align-items: center; justify-content: center;
        }
        #particle-canvas { position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; }

        .splash-card {
            position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center;
            text-align: center; max-width: 880px; padding: 50px 45px; border-radius: 20px;
            border: 1px solid rgba(0, 243, 255, 0.5); background: rgba(6, 12, 26, 0.92);
            box-shadow: 0 0 60px rgba(0, 243, 255, 0.2);
        }

        .clearance-tag {
            font-family: 'Orbitron'; font-size: 11px; letter-spacing: 5px; color: var(--cyber-cyan);
            border: 1px solid var(--cyber-cyan); padding: 6px 24px; border-radius: 20px; margin-bottom: 20px;
            background: rgba(0, 243, 255, 0.12); text-shadow: 0 0 10px var(--cyber-cyan);
        }

        .main-title {
            font-family: 'Orbitron', sans-serif; font-size: 4.5rem; font-weight: 900;
            background: linear-gradient(180deg, #ffffff 20%, var(--cyber-cyan) 60%, var(--cyber-purple) 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            letter-spacing: 8px; margin-bottom: 10px;
        }

        .creator-badge {
            background: linear-gradient(135deg, rgba(255,0,85,0.18), rgba(0,243,255,0.18));
            border: 1px solid rgba(0, 243, 255, 0.5); border-left: 5px solid var(--cyber-pink); border-right: 5px solid var(--cyber-cyan);
            padding: 16px 50px; border-radius: 10px; margin: 25px 0; text-align: center;
        }
        .creator-title { font-family: 'Orbitron'; font-size: 11px; color: var(--cyber-gold); letter-spacing: 4px; }
        .creator-name { font-family: 'Chakra Petch'; font-size: 26px; font-weight: 700; color: #fff; text-shadow: 0 0 15px var(--cyber-cyan); }

        .scan-launch-btn {
            background: rgba(255, 0, 85, 0.1); border: 2px solid var(--cyber-pink); color: var(--cyber-pink);
            padding: 18px 55px; font-family: 'Orbitron', sans-serif; font-size: 1.2rem; font-weight: 700;
            cursor: pointer; transition: 0.3s ease; letter-spacing: 3px; border-radius: 8px;
            box-shadow: 0 0 25px rgba(255, 0, 85, 0.3);
        }
        .scan-launch-btn:hover {
            background: var(--cyber-pink); color: #000; box-shadow: 0 0 50px var(--cyber-pink); transform: scale(1.03);
        }

        /* TOP COMMAND BAR */
        #top-bar {
            position: absolute; top: 0; left: 0; width: 100%; height: 44px;
            background: rgba(4, 8, 18, 0.96); border-bottom: 1px solid rgba(0, 243, 255, 0.3);
            z-index: 20; display: flex; align-items: center; justify-content: space-between; padding: 0 25px; font-family: 'Orbitron'; font-size: 12px;
        }
        #ticker-text { color: var(--cyber-pink); font-weight: bold; font-family: 'JetBrains Mono'; letter-spacing: 1px; }

        #container { display: flex; width: 100vw; height: 100vh; position: relative; padding-top: 44px; }
        #map { flex: 1; height: 100%; background: #030611; }

        #camera-controls { position: absolute; top: 60px; left: 25px; z-index: 10; display: flex; gap: 10px; }
        .cam-btn {
            background: var(--panel-bg); border: 1px solid rgba(0,243,255,0.4); color: #e2e8f0;
            padding: 10px 20px; font-size: 13px; cursor: pointer; font-family: 'Chakra Petch'; transition: 0.25s; border-radius: 6px; font-weight: 600;
        }
        .cam-btn:hover, .cam-btn.active { background: var(--cyber-cyan); color: #000; font-weight: 700; box-shadow: 0 0 20px var(--cyber-cyan); }

        #defcon-widget {
            position: absolute; top: 60px; right: 445px; z-index: 10; display: flex; gap: 8px; padding: 6px; border-radius: 8px;
        }
        .def-btn {
            padding: 8px 16px; font-family: 'Orbitron'; font-weight: 700; font-size: 11px; cursor: pointer;
            border: 1px solid rgba(255,255,255,0.2); background: rgba(0,0,0,0.7); color: #aaa; border-radius: 4px; transition: 0.25s;
        }
        .def-btn.active-1 { background: var(--cyber-pink); color: #000; border-color: var(--cyber-pink); box-shadow: 0 0 20px var(--cyber-pink); }
        .def-btn.active-5 { background: var(--cyber-green); color: #000; border-color: var(--cyber-green); box-shadow: 0 0 20px var(--cyber-green); }

        /* SIDEBAR */
        #sidebar {
            width: 420px; height: calc(100% - 44px); background: var(--panel-bg);
            display: flex; flex-direction: column; z-index: 10; border-left: 1px solid rgba(0,243,255,0.35);
        }
        .sidebar-title {
            padding: 14px 18px; color: var(--cyber-cyan); font-family: 'Orbitron'; font-size: 12px; font-weight: 700;
            border-bottom: 1px solid rgba(0,243,255,0.2); display: flex; justify-content: space-between; align-items: center;
        }
        #feed { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 16px; }
        
        .card {
            background: rgba(255, 255, 255, 0.04); border-left: 4px solid var(--cyber-cyan); padding: 14px; font-size: 13px;
            display: flex; flex-direction: column; gap: 8px; border-radius: 6px; border-top: 1px solid rgba(255,255,255,0.08);
            font-family: 'Chakra Petch', sans-serif;
        }
        .abm-btn {
            background: var(--cyber-pink); color: #000; border: none; padding: 10px 14px; font-size: 11px;
            cursor: pointer; font-family: 'Orbitron'; font-weight: 700; margin-top: 6px; border-radius: 4px; transition: 0.25s;
        }
        .abm-btn:hover { background: #fff; box-shadow: 0 0 20px var(--cyber-pink); }

        #terminal-box { background: rgba(2, 5, 12, 0.98); border-top: 1px solid rgba(0, 243, 255, 0.35); padding: 14px; display: flex; align-items: center; }
        #terminal-box span { color: var(--cyber-green); margin-right: 10px; font-weight: bold; font-size: 13px; font-family: 'JetBrains Mono'; }
        #cmd-prompt { background: transparent; border: none; color: var(--cyber-cyan); width: 100%; font-family: 'JetBrains Mono'; font-size: 14px; outline: none; }
    </style>
</head>
<body>

    <div id="splash">
        <canvas id="particle-canvas"></canvas>
        <div class="splash-card glass-panel">
            <div class="clearance-tag">QUANTUM CLEARANCE: LEVEL 5 (CLASSIFIED OMNI)</div>
            <h1 class="main-title">PROJECT OMEGA</h1>
            <p style="letter-spacing:5px; color:#cbd5e1; font-size:13px; margin-bottom:15px; font-family:'Orbitron';">SUPREME 3D GLOBAL WAR ROOM & ABM DEFENSE MATRIX</p>
            
            <div class="creator-badge">
                <div class="creator-title">CHIEF SYSTEM ARCHITECT</div>
                <div class="creator-name">👨‍💻 ผู้สร้าง ปกรณ์</div>
            </div>

            <button class="scan-launch-btn" onclick="authorizeSystem()">
                <span id="btn-text">INITIALIZE BIOMETRIC SCAN</span>
            </button>
        </div>
    </div>

    <div id="top-bar">
        <span>PROJECT OMEGA TITAN v5.0 (3D GLOBE EDITION)</span>
        <span id="ticker-text">🚨 SYSTEM ONLINE: 3D SATELLITE RADAR ACTIVE</span>
        <div style="display:flex; gap:15px; align-items:center;">
            <a href="/admin" style="color:var(--cyber-cyan); text-decoration:none; font-size:11px; border:1px solid var(--cyber-cyan); padding:4px 12px; border-radius:4px; font-weight:bold;">📊 ADMIN BACKOFFICE</a>
            <span id="time-display">00:00:00 UTC</span>
        </div>
    </div>

    <div id="container">
        <div id="camera-controls">
            <button class="cam-btn active" onclick="selectRegion('TH', 100.5, 13.7, 6.5, this)">🇹🇭 THAILAND COMMAND</button>
            <button class="cam-btn" onclick="selectRegion('GLOBAL', 100.0, 15.0, 2.2, this)">🌍 3D GLOBAL GLOBE</button>
            <button class="cam-btn" style="border-color:var(--cyber-pink); color:var(--cyber-pink);" onclick="triggerManualThreat()">⚡ SIMULATE THREAT</button>
        </div>

        <div id="defcon-widget" class="glass-panel">
            <button class="def-btn active-1" onclick="setDefcon(1, this)">DEFCON 1</button>
            <button class="def-btn" onclick="setDefcon(3, this)">DEFCON 3</button>
            <button class="def-btn active-5" onclick="setDefcon(5, this)">DEFCON 5</button>
        </div>

        <div id="map"></div>

        <div id="sidebar">
            <div class="sidebar-title">
                <span>LIVE DATABASE ANALYTICS</span>
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
        Chart.defaults.devicePixelRatio = window.devicePixelRatio || 2;
        let map, ws, audioCtx, mainChart;
        let abmArcData = { 'type': 'FeatureCollection', 'features': [] };

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
            }, 700);
        }

        function init3DMap() {
            map = new maplibregl.Map({
                container: 'map',
                style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
                center: [100.5018, 13.7563],
                zoom: 2.5, pitch: 45, bearing: -10,
                projection: 'globe'
            });

            map.on('load', () => {
                map.setProjection({ type: 'globe' });
                map.addSource('abm-source', { type: 'geojson', data: abmArcData });
                map.addLayer({
                    id: 'abm-layer', type: 'line', source: 'abm-source',
                    paint: { 'line-color': '#00f3ff', 'line-width': 4, 'line-blur': 0 }
                });
            });

            map.on('click', (e) => { launchABM(e.lngLat.lat, e.lngLat.lng); });
        }

        function initChart() {
            const ctx = document.getElementById('threatChart').getContext('2d');
            mainChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['ICBM', 'DRONE', 'SATELLITE', 'UFO'],
                    datasets: [{
                        label: 'ภัยคุกคามในระบบ',
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#ff0055', '#ffc800', '#00f3ff', '#a855f7'],
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.06)' }, ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono' } } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { family: 'Orbitron' } } }
                    }
                }
            });
            updateMainChartData();
            setInterval(updateMainChartData, 4000);
        }

        async function updateMainChartData() {
            try {
                const res = await fetch('/api/v1/analytics/stats');
                const data = await res.json();
                mainChart.data.datasets[0].data = [
                    data.by_type['ICBM_LAUNCH'] || 0,
                    data.by_type['DRONE_SWARM'] || 0,
                    data.by_type['SATELLITE_HACK'] || 0,
                    data.by_type['UFO_TACTICAL'] || 0
                ];
                mainChart.update();
            } catch(e) {}
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
            card.innerHTML = `<div style="display:flex; justify-content:space-between;"><b style="color:${color}">${title}</b><span style="color:#888;">${time}</span></div><span>${desc}</span>${btnHtml}`;
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
                appendFeedCard('#00ff9d', 'TARGET DESTROYED', `ยิงสกัดกั้นสำเร็จที่พิกัด ${targetLat.toFixed(2)}, ${targetLng.toFixed(2)}`);
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
                document.documentElement.style.setProperty('--cyber-pink', '#ff0000');
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

        const canvas = document.getElementById('particle-canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        let particles = Array.from({length: 80}, () => ({
            x: Math.random() * canvas.width, y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 1.0, vy: (Math.random() - 0.5) * 1.0
        }));

        function drawParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'rgba(0, 243, 255, 0.6)';
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
                else if(cmd === '/help') appendFeedCard('#00f3ff', 'SYSTEM COMMANDS', '/trigger - จำลองภัยคุกคาม | /help - คำแนะนำ');
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
# 7. EXECUTION POINT
# ==========================================

if __name__ == "__main__":
uvicorn.run(app, host="127.0.0.1", port=8001)