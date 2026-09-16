import requests
import time
import random

API_URL = "http://127.0.0.1:8000/api/v1/telemetry/ingest"

# 🔑 กุญแจรักษาความปลอดภัย (ต้องตรงกับใน main.py)
API_KEY = "DEFENSE-SHIELD-X999"

HEADERS = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

# ภัยคุกคามระดับสูญพันธุ์ (Global Level)
INCIDENTS = [
    {"title": "สึนามิขนาดใหญ่ มหาสมุทรแปซิฟิก", "type": "TSUNAMI"},
    {"title": "ภูเขาไฟซูเปอร์โวลคาโนปะทุ", "type": "VOLCANO"},
    {"title": "ตรวจพบเชื้อไวรัสกลายพันธุ์ร้ายแรง", "type": "BIOHAZARD"},
    {"title": "การโจมตีทางไซเบอร์เจาะระบบฐานยิงนิวเคลียร์", "type": "CYBER_ATTACK"},
    {"title": "อุกกาบาตขนาดยักษ์เข้าใกล้ชั้นบรรยากาศ", "type": "ASTEROID"}
]

def generate_global_telemetry():
    incident = random.choice(INCIDENTS)
    
    # สุ่มพิกัดทั่วทุกมุมโลก (Lat: -60 ถึง 70, Lng: -180 ถึง 180)
    lat = random.uniform(-60.0, 70.0)
    lng = random.uniform(-180.0, 180.0)
    
    return {
        "title": incident["title"],
        "incident_type": incident["type"],
        "latitude": lat,
        "longitude": lng,
        "wave_height": random.uniform(10, 50) if incident["type"] == "TSUNAMI" else 0,
        "ash_cloud_radius": random.uniform(100, 1000) if incident["type"] == "VOLCANO" else 0,
        "infection_rate": random.uniform(50, 99) if incident["type"] == "BIOHAZARD" else 0,
        "threat_level": random.uniform(8, 10) if incident["type"] == "CYBER_ATTACK" else 0,
        "diameter_meters": random.uniform(50, 500) if incident["type"] == "ASTEROID" else 0
    }

if __name__ == "__main__":
    print("🛰️ [SYSTEM] INIT GLOBAL THREAT SIMULATOR...")
    print(f"🔒 [SECURITY] USING ENCRYPTED API KEY: {API_KEY}")
    print("ส่งข้อมูลภัยคุกคามทั่วโลกทุกๆ 5 วินาที (กด Ctrl+C เพื่อหยุด)\n")
    
    while True:
        try:
            data = generate_global_telemetry()
            
            # ส่ง Request พร้อมแนบ API KEY ใน Header
            response = requests.post(API_URL, json=data, headers=HEADERS)
            
            if response.status_code == 200:
                print(f"🟢 [AUTHORIZED & SENT] {data['title']} (พิกัด: {data['latitude']:.1f}, {data['longitude']:.1f})")
            elif response.status_code == 403:
                print(f"🔴 [ACCESS DENIED] โดนเซิร์ฟเวอร์เตะออก! กุญแจ API KEY ไม่ถูกต้อง")
            else:
                print(f"⚠️ [Error] โค้ดแปลกประหลาด: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("❌ ไม่สามารถเชื่อมต่อศูนย์บัญชาการได้")
        
        time.sleep(5) # ส่งทุก 5 วินาทีเพื่อให้กล้องมีเวลาบินข้ามทวีป
        