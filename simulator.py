#!/usr/bin/env python3
"""
AgriSense - Simulateur de capteurs IoT
Simule 6 zones avec des données réalistes pour Meknès
"""
import requests, random, time, json
from datetime import datetime

API_URL = "http://localhost:5000/api/sensors"

ZONES_CONFIG = {
    "zone_1": {"name": "Tomates",  "hum": (55, 82), "temp": (18, 34), "ph": (5.8, 7.0), "n": (80,150), "p": (40,80), "k": (100,200)},
    "zone_2": {"name": "Ble",      "hum": (40, 68), "temp": (15, 30), "ph": (5.9, 7.2), "n": (60,120), "p": (30,60), "k": (80,160)},
    "zone_3": {"name": "Oliviers", "hum": (25, 55), "temp": (20, 38), "ph": (6.3, 8.2), "n": (40,90),  "p": (20,50), "k": (60,120)},
    "zone_4": {"name": "Menthe",   "hum": (60, 88), "temp": (16, 28), "ph": (5.8, 7.2), "n": (70,140), "p": (35,70), "k": (90,180)},
    "zone_5": {"name": "Mais",     "hum": (45, 72), "temp": (18, 35), "ph": (5.6, 7.2), "n": (90,160), "p": (45,85), "k": (110,210)},
    "zone_6": {"name": "Fraises",  "hum": (60, 82), "temp": (15, 26), "ph": (5.3, 6.7), "n": (50,100), "p": (25,55), "k": (70,140)},
}

def generate_data(zone_id, config):
    hum  = round(random.uniform(*config["hum"]), 1)
    # Introduire parfois des valeurs basses pour déclencher des alertes
    if random.random() < 0.15:
        hum = round(random.uniform(config["hum"][0] - 20, config["hum"][0] - 5), 1)
        hum = max(5, hum)
    return {
        "device_id": f"sensor_{zone_id}",
        "zone": zone_id,
        "humidity":    hum,
        "temperature": round(random.uniform(*config["temp"]), 1),
        "ph":          round(random.uniform(*config["ph"]), 2),
        "nitrogen":    round(random.uniform(*config["n"]), 1),
        "phosphorus":  round(random.uniform(*config["p"]), 1),
        "potassium":   round(random.uniform(*config["k"]), 1),
        "timestamp":   datetime.now().isoformat()
    }

def send_data(data):
    try:
        r = requests.post(API_URL, json=data, timeout=5)
        if r.status_code == 201:
            print(f"  [OK] {data['zone']} ({ZONES_CONFIG[data['zone']]['name']}) - "
                  f"Hum:{data['humidity']}% Temp:{data['temperature']}C pH:{data['ph']}")
        else:
            print(f"  [ERREUR] {data['zone']}: {r.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"  [ERREUR] Impossible de joindre {API_URL} - Flask est-il démarré ?")

def run_once():
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Envoi données pour 6 zones...")
    for zone_id, config in ZONES_CONFIG.items():
        data = generate_data(zone_id, config)
        send_data(data)
        time.sleep(0.2)

def run_continuous(interval=10):
    print("=== AgriSense Simulateur ===")
    print(f"Envoi toutes les {interval} secondes. Ctrl+C pour arrêter.\n")
    try:
        while True:
            run_once()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nSimulateur arrêté.")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        run_once()
    else:
        interval = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        run_continuous(interval)
