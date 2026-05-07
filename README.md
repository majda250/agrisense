# AgriSense - Plateforme IoT Agricole

## Installation & Lancement (Ubuntu)

### 1. Installer les dépendances
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
cd ~/agrisense
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Lancer le backend Flask
```bash
source venv/bin/activate
python3 app.py
```
→ Ouvrir http://localhost:5000

### 3. Lancer le simulateur (autre terminal)
```bash
source venv/bin/activate
python3 simulator.py 10   # Envoie données toutes les 10 secondes
```

## API REST
| Méthode | Route | Description |
|---------|-------|-------------|
| POST | /api/sensors | Envoyer données capteurs |
| GET  | /api/data | Lire toutes les données |
| GET  | /api/zones/status | État de toutes les zones |
| GET  | /api/zone/<id> | Détail d'une zone |
| GET  | /api/weather | Météo Meknès |
| GET  | /api/alerts | Alertes actives |
| POST | /api/alerts/<id>/resolve | Résoudre une alerte |
| GET  | /api/stats | Statistiques générales |
