import urllib.request
import json

url = "http://127.0.0.1:8000/api/v1/telemetry/ingest"
data = {
    "title": "เพลิงไหม้ตึกสูง ย่านสยาม",
    "incident_type": "FIRE",
    "latitude": 13.7456,
    "longitude": 100.5342,
    "temperature": 85.5,
    "smoke": 90.0,
    "water_level": 0,
    "seismic": 0
}

payload = json.dumps(data).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req) as response:
        print("ส่งข้อมูลสำเร็จ:", response.read().decode())
except Exception as e:
    print("เกิดข้อผิดพลาดในการเชื่อมต่อ:", e)