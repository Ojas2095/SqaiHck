import requests
import time

def test_api():
    print("Testing API endpoints...")
    base_url = "http://localhost:8080/api"
    
    # 1. Dashboard
    res = requests.get(f"{base_url}/dashboard")
    print("GET /dashboard:", res.status_code, "âœ…" if res.status_code == 200 else "âŒ")
    
    # 2. EHR processing
    ehr_payload = {
        "patient_id": "PAT-TEST-1",
        "voice_text": "Patient has severe headache and mild fever for 2 days. History of Ashwagandha use.",
        "language": "en"
    }
    res = requests.post(f"{base_url}/ehr", json=ehr_payload)
    print("POST /ehr:", res.status_code, "âœ…" if res.status_code == 200 else "âŒ")
    
    # 3. Treatment plan
    tx_payload = {
        "patient_id": "PAT-TEST-1"
    }
    res = requests.post(f"{base_url}/treatment", json=tx_payload)
    print("POST /treatment:", res.status_code, "âœ…" if res.status_code == 200 else "âŒ")
    if res.status_code == 200:
        data = res.json()
        print("  Treatment ID:", data.get("treatment_id"))
        
        # 4. Feedback
        fb_payload = {
            "treatment_id": data.get("treatment_id"),
            "approved": True,
            "score": 1.0
        }
        res = requests.post(f"{base_url}/feedback", json=fb_payload)
        print("POST /feedback:", res.status_code, "âœ…" if res.status_code == 200 else "âŒ")

if __name__ == "__main__":
    try:
        test_api()
    except Exception as e:
        print(f"Test script failed: {e}")


