from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3, os, requests
from datetime import datetime
import random

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'agrisense.db')
OPENWEATHER_API_KEY = "demo"
CITY = "Meknes,MA"

PLANTS = {
    "zone_1": {"name": "Tomates",  "emoji": "🍅", "water_need": "high",   "ph_min": 6.0, "ph_max": 6.8, "humidity_min": 60, "humidity_max": 80, "color": "#e74c3c"},
    "zone_2": {"name": "Blé",      "emoji": "🌾", "water_need": "medium", "ph_min": 6.0, "ph_max": 7.0, "humidity_min": 45, "humidity_max": 65, "color": "#f39c12"},
    "zone_3": {"name": "Oliviers", "emoji": "🫒", "water_need": "low",    "ph_min": 6.5, "ph_max": 8.0, "humidity_min": 30, "humidity_max": 50, "color": "#27ae60"},
    "zone_4": {"name": "Menthe",   "emoji": "🌿", "water_need": "high",   "ph_min": 6.0, "ph_max": 7.0, "humidity_min": 65, "humidity_max": 85, "color": "#1abc9c"},
    "zone_5": {"name": "Maïs",     "emoji": "🌽", "water_need": "medium", "ph_min": 5.8, "ph_max": 7.0, "humidity_min": 50, "humidity_max": 70, "color": "#f1c40f"},
    "zone_6": {"name": "Fraises",  "emoji": "🍓", "water_need": "high",   "ph_min": 5.5, "ph_max": 6.5, "humidity_min": 65, "humidity_max": 80, "color": "#e91e8c"},
}
WATER_QUANTITY = {"low": 5, "medium": 12, "high": 20}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        zone TEXT NOT NULL,
        humidity REAL, temperature REAL, ph REAL,
        nitrogen REAL, phosphorus REAL, potassium REAL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        zone TEXT, message TEXT, level TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        resolved INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()

def get_weather():
    try:
        if OPENWEATHER_API_KEY == "demo":
            return {"temp": round(random.uniform(18,32),1), "humidity": round(random.uniform(40,70),1),
                    "description": random.choice(["Ensoleillé","Partiellement nuageux","Clair"]),
                    "rain_prob": round(random.uniform(0,0.3),2), "wind_speed": round(random.uniform(5,20),1), "source": "simulation"}
        url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
        r = requests.get(url, timeout=5)
        d = r.json()
        return {"temp": d["main"]["temp"], "humidity": d["main"]["humidity"],
                "description": d["weather"][0]["description"],
                "rain_prob": d.get("rain",{}).get("1h",0)/10,
                "wind_speed": d["wind"]["speed"], "source": "openweathermap"}
    except:
        return {"temp": 25, "humidity": 55, "description": "Inconnu", "rain_prob": 0, "wind_speed": 10, "source": "fallback"}

def irrigation_decision(zone_id, sensor_data, weather):
    plant = PLANTS.get(zone_id, {})
    if not plant: return {"should_irrigate": False, "reason": "Zone inconnue", "quantity": 0, "reasons": []}
    hum = sensor_data.get("humidity", 50)
    ph  = sensor_data.get("ph", 6.5)
    rain_prob = weather.get("rain_prob", 0)
    temp = weather.get("temp", 25)
    reasons = []
    score = 0
    if hum < plant["humidity_min"]:
        score += 3; reasons.append(f"Humidite sol basse ({hum:.0f}% < {plant['humidity_min']}%)")
    elif hum > plant["humidity_max"]:
        score -= 2; reasons.append(f"Humidite sol suffisante ({hum:.0f}%)")
    else:
        reasons.append(f"Humidite sol optimale ({hum:.0f}%)")
    if rain_prob > 0.6: score -= 2; reasons.append(f"Pluie prevue ({rain_prob*100:.0f}%)")
    elif rain_prob > 0.3: score -= 1; reasons.append(f"Faible risque pluie ({rain_prob*100:.0f}%)")
    if temp > 30: score += 1; reasons.append(f"Temperature elevee ({temp}C)")
    ph_ok = plant["ph_min"] <= ph <= plant["ph_max"]
    reasons.append(f"pH {'optimal' if ph_ok else 'anormal'} ({ph:.1f})")
    base_qty = WATER_QUANTITY[plant["water_need"]]
    if temp > 30: base_qty = int(base_qty * 1.2)
    if rain_prob > 0.3: base_qty = int(base_qty * 0.7)
    return {"should_irrigate": score > 0, "score": score,
            "quantity": base_qty if score > 0 else 0, "reasons": reasons}

def check_alerts(zone_id, sd):
    plant = PLANTS.get(zone_id, {})
    conn = get_db(); c = conn.cursor()
    hum = sd.get("humidity",50); ph = sd.get("ph",6.5); temp = sd.get("temperature",22)
    if hum < plant.get("humidity_min",40) - 15:
        c.execute("INSERT INTO alerts (zone,message,level) VALUES (?,?,?)",
                  (zone_id, f"{plant['name']}: Humidite critique ({hum:.0f}%)!", "critical"))
    elif hum < plant.get("humidity_min",40):
        c.execute("INSERT INTO alerts (zone,message,level) VALUES (?,?,?)",
                  (zone_id, f"{plant['name']}: Humidite basse ({hum:.0f}%)", "warning"))
    if ph < plant.get("ph_min",6.0)-0.5 or ph > plant.get("ph_max",7.5)+0.5:
        c.execute("INSERT INTO alerts (zone,message,level) VALUES (?,?,?)",
                  (zone_id, f"{plant['name']}: pH anormal ({ph:.1f})", "warning"))
    if temp > 38:
        c.execute("INSERT INTO alerts (zone,message,level) VALUES (?,?,?)",
                  (zone_id, f"{plant['name']}: Temperature critique ({temp}C)!", "critical"))
    conn.commit(); conn.close()

@app.route('/')
def index(): return render_template('index.html', plants=PLANTS)

@app.route('/api/sensors', methods=['POST'])
def receive_sensor_data():
    data = request.get_json()
    if not data: return jsonify({"error": "No data"}), 400
    conn = get_db(); c = conn.cursor()
    c.execute('''INSERT INTO sensor_data (device_id,zone,humidity,temperature,ph,nitrogen,phosphorus,potassium,timestamp)
        VALUES (?,?,?,?,?,?,?,?,?)''',
        (data.get('device_id'), data.get('zone'), data.get('humidity'), data.get('temperature'),
         data.get('ph'), data.get('nitrogen'), data.get('phosphorus'), data.get('potassium'),
         data.get('timestamp', datetime.now().isoformat())))
    conn.commit(); conn.close()
    check_alerts(data.get('zone'), data)
    return jsonify({"status": "ok"}), 201

@app.route('/api/data', methods=['GET'])
def get_all_data():
    zone = request.args.get('zone'); limit = int(request.args.get('limit', 50))
    conn = get_db(); c = conn.cursor()
    if zone: c.execute('SELECT * FROM sensor_data WHERE zone=? ORDER BY timestamp DESC LIMIT ?', (zone, limit))
    else: c.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify(rows)

@app.route('/api/zones/status', methods=['GET'])
def zones_status():
    weather = get_weather(); conn = get_db(); c = conn.cursor(); result = {}
    for zone_id, plant in PLANTS.items():
        c.execute('SELECT * FROM sensor_data WHERE zone=? ORDER BY timestamp DESC LIMIT 1', (zone_id,))
        row = c.fetchone()
        if row:
            sd = dict(row); decision = irrigation_decision(zone_id, sd, weather)
            status = "critical" if sd.get("humidity",50) < plant["humidity_min"]-15 else \
                     "warning"  if sd.get("humidity",50) < plant["humidity_min"] else "good"
            result[zone_id] = {"plant": plant, "latest_data": sd, "irrigation": decision, "status": status}
        else:
            result[zone_id] = {"plant": plant, "latest_data": None, "irrigation": {"should_irrigate": False, "quantity": 0}, "status": "no_data"}
    conn.close()
    return jsonify({"zones": result, "weather": weather})

@app.route('/api/zone/<zone_id>', methods=['GET'])
def zone_detail(zone_id):
    weather = get_weather(); conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM sensor_data WHERE zone=? ORDER BY timestamp DESC LIMIT 24', (zone_id,))
    history = [dict(r) for r in c.fetchall()]; conn.close()
    plant = PLANTS.get(zone_id, {})
    decision = irrigation_decision(zone_id, history[0] if history else {}, weather)
    return jsonify({"zone_id": zone_id, "plant": plant, "history": history, "irrigation": decision, "weather": weather})

@app.route('/api/weather', methods=['GET'])
def weather_route(): return jsonify(get_weather())

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT * FROM alerts WHERE resolved=0 ORDER BY timestamp DESC LIMIT 20')
    alerts = [dict(r) for r in c.fetchall()]; conn.close()
    return jsonify(alerts)

@app.route('/api/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    conn = get_db(); conn.execute('UPDATE alerts SET resolved=1 WHERE id=?', (alert_id,)); conn.commit(); conn.close()
    return jsonify({"status": "resolved"})

@app.route('/api/plants', methods=['GET'])
def get_plants(): return jsonify(PLANTS)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db(); c = conn.cursor()
    c.execute('SELECT COUNT(*) as total FROM sensor_data'); total = c.fetchone()['total']
    c.execute('SELECT COUNT(*) as alerts FROM alerts WHERE resolved=0'); alerts = c.fetchone()['alerts']
    c.execute('SELECT zone, AVG(humidity) as h, AVG(temperature) as t FROM sensor_data GROUP BY zone')
    avgs = {r['zone']: {"avg_humidity": round(r['h'],1), "avg_temp": round(r['t'],1)} for r in c.fetchall()}
    conn.close()
    return jsonify({"total_readings": total, "active_alerts": alerts, "zone_averages": avgs})

if __name__ == '__main__':
    init_db()
    print("AgriSense demarre sur http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
