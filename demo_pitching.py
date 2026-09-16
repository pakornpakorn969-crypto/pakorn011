import requests
import time
import random

API_URL = "http://127.0.0.1:8000/api/v1/telemetry/trigger"

if __name__ == "__main__":
    print("🎬 [PROJECT OMEGA] MULTI-REGION ALERT STREAM ACTIVATED")
    print("📍 รองรับการยิงสุ่มสัญญาณเตือนภัย: [TH] ประเทศไทย | [ASIA] เอเชีย | [GLOBAL] ทั่วโลก")
    print("กด Enter เพื่อเริ่มรันการเตือนภัยต่อเนื่อง...")
    input()
    
    regions = ["TH", "TH", "ASIA", "GLOBAL"]
    count = 1
    
    try:
        while True:
            reg = random.choice(regions)
            resp = requests.post(f"{API_URL}?region={reg}")
            
            if resp.status_code == 200:
                json_resp = resp.json()
                
                # ป้องกัน KeyError โดยการเช็กว่ามีคำว่า data ส่งกลับมาหรือไม่
                if "data" in json_resp:
                    data = json_resp["data"]
                    print(f"[{count}] 🚀 [{reg}] DEPLOYED: {data['title']} (Level: {data['threat_level']})")
                else:
                    print(f"[{count}] 🚀 [{reg}] DEPLOYED (ตรวจสอบพิกัดบนหน้า Dashboard)")
            else:
                print(f"❌ Error {resp.status_code}")
                
            count += 1
            time.sleep(random.uniform(3.5, 5.0))
            
    except KeyboardInterrupt:
        print("\n⏹️ สั่งหยุดการทำงานแล้ว")