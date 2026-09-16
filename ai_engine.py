class AIEngine:
    @staticmethod
    def analyze_threat(incident_type: str, threat_level: float, wave_height: float = 0.0):
        """
        AI Decision Matrix for PROJECT OMEGA (Bilingual Support: TH / EN)
        """
        protocol = "STANDARD"
        protocol_th = "สภาวะมาตรฐาน"
        radius = threat_level * 5.0
        color = "#00e5ff"  # Cyber Blue

        if threat_level >= 8.5:
            protocol = "EXTINCTION"
            protocol_th = "ระดับสูญพันธุ์"
            radius = threat_level * 15.0
            color = "#ff003c"  # Cyber Red
        elif threat_level >= 6.0:
            protocol = "HIGH_ALERT"
            protocol_th = "เฝ้าระวังสูงสุด"
            radius = threat_level * 10.0
            color = "#ff6600"  # Cyber Orange

        analysis_summary = (
            f"AI MATRIX: Threat level {threat_level:.1f} ({incident_type}). "
            f"Protocol [{protocol}] engaged. Calculated impact radius: {radius:.1f} km.\n"
            f"วิเคราะห์ AI: ระดับภัยคุกคาม {threat_level:.1f} ({incident_type}) "
            f"เริ่มโปรโตคอล [{protocol_th}] รัศมีผลกระทบ: {radius:.1f} กม."
        )

        return {
            "protocol": protocol,
            "protocol_th": protocol_th,
            "radius": radius,
            "color": color,
            "summary": analysis_summary
        }