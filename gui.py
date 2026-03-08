#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify
import subprocess
import re
import json
import os
import shutil
from datetime import datetime
import time
import argparse

config = json.loads(open('config.json', 'r').read())
site_config = config['site_config']

app = Flask(__name__, template_folder='templates')
CONFIG_FILE = os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")

# Neuer Backup-Ordner & Limit
BACKUP_DIR = os.path.expanduser("~/.local/share/pipewire/backups")
MAX_BACKUPS = 10

def make_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    base = os.path.basename(CONFIG_FILE)
    # vorhandene Backups (älteste zuerst)
    files = [f for f in os.listdir(BACKUP_DIR) if f.startswith(base + ".backup_")]
    files_paths = [os.path.join(BACKUP_DIR, f) for f in files]
    files_sorted = sorted(files_paths, key=os.path.getmtime)
    if len(files_sorted) < MAX_BACKUPS:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{base}.backup_{timestamp}"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
    else:
        # Limit erreicht: ältestes überschreiben
        backup_path = files_sorted[0]
    shutil.copy2(CONFIG_FILE, backup_path)
    try:
        os.utime(backup_path, None)
    except Exception:
        pass
    return backup_path

def get_gains():
    """Liest die aktuellen EQ-Werte (Gain und Q) aus der Config-Datei"""
    if not os.path.exists(CONFIG_FILE):
        print(f"Fehler: Config-Datei nicht gefunden: {CONFIG_FILE}")
        return {}
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        gains = {}
        for i in range(1, 11):
            # Lese Gain
            gain_pattern = f'name = "eq_band_{i}"[^}}]*?Gain = ([\\d.-]+)'
            gain_match = re.search(gain_pattern, content)
            if gain_match:
                gains[f'band_{i}'] = float(gain_match.group(1))
                print(f"✓ Band {i} Gain: {gains[f'band_{i}']}")
            else:
                gains[f'band_{i}'] = 0.0
                print(f"✗ Band {i} Gain nicht gefunden (default: 0.0)")
            
            # Lese Q
            q_pattern = f'name = "eq_band_{i}"[^}}]*?Q = ([\\d.-]+)'
            q_match = re.search(q_pattern, content)
            if q_match:
                gains[f'band_{i}_q'] = float(q_match.group(1))
                print(f"✓ Band {i} Q: {gains[f'band_{i}_q']}")
            else:
                gains[f'band_{i}_q'] = 1.0
                print(f"✗ Band {i} Q nicht gefunden (default: 1.0)")
        
        return gains
    except Exception as e:
        print(f"Fehler beim Lesen der Gains: {e}")
        import traceback
        traceback.print_exc()
        return {}

def update_gain(band, value):
    """Aktualisiert einen EQ-Wert (Gain) in der Config-Datei"""
    if not os.path.exists(CONFIG_FILE):
        raise Exception(f"Config-Datei nicht gefunden: {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        print(f"\n📝 Verarbeite: {band} Gain = {value}")
        
        # Prüfe aktuellen Wert zuerst, damit kein unnötiges Backup entsteht
        old_pattern = f'(name = "{band}"[^}}]*?Gain = )([\\d.-]+)'
        current_match = re.search(old_pattern, content)
        if current_match:
            current_value = float(current_match.group(2))
            if abs(current_value - float(value)) < 1e-6:
                print(f"  ✓ Gain ist bereits {current_value} — keine Änderung nötig")
                return True
        else:
            raise Exception(f"Gain-Pattern für {band} nicht gefunden")
        
        # Erstelle Backup
        backup_file = make_backup()
        print(f"✓ Backup erstellt: {backup_file}")
        
        # Ersetze Gain
        new_content = re.sub(old_pattern, rf'\g<1>{value}', content)
        if new_content == content:
            raise Exception(f"Substitution für {band} fehlgeschlagen")
        
        print(f"  ✓ Gain aktualisiert")
        
        # Schreibe neue Config
        with open(CONFIG_FILE, 'w') as f:
            f.write(new_content)
        print(f"  ✓ Datei gespeichert")
        
        return True
        
    except Exception as e:
        print(f"  ✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        raise

def update_q(band, value):
    """Aktualisiert den Q-Wert in der Config-Datei"""
    if not os.path.exists(CONFIG_FILE):
        raise Exception(f"Config-Datei nicht gefunden: {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        print(f"\n📝 Verarbeite: {band} Q = {value}")
        
        # Pattern für Q - prüfe aktuellen Wert zuerst
        old_pattern = f'(name = "{band}"[^}}]*?Q = )([\\d.-]+)'
        current_match = re.search(old_pattern, content)
        if current_match:
            current_value = float(current_match.group(2))
            if abs(current_value - float(value)) < 1e-6:
                print(f"  ✓ Q ist bereits {current_value} — keine Änderung nötig")
                return True
        else:
            print(f"  ✗ Q-Pattern für {band} nicht gefunden!")
            for line in content.split('\n'):
                if band in line:
                    print(f"  Zeile: {line}")
            raise Exception(f"Q-Pattern für {band} nicht gefunden")
        
        # Erstelle Backup
        backup_file = make_backup()
        print(f"✓ Backup erstellt: {backup_file}")
        
        # Ersetze Q
        new_content = re.sub(old_pattern, rf'\g<1>{value}', content)
        if new_content == content:
            raise Exception(f"Q-Substitution für {band} fehlgeschlagen")
        
        print(f"  ✓ Q aktualisiert")
        
        # Schreibe neue Config
        with open(CONFIG_FILE, 'w') as f:
            f.write(new_content)
        print(f"  ✓ Datei gespeichert")
        
        return True
        
    except Exception as e:
        print(f"  ✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        raise

def restart_pipewire():
    """Startet PipeWire sauber neu"""
    try:
        print("\n🔄 Starte PipeWire neu...")
        
        # Stoppe
        subprocess.run(['systemctl', '--user', 'stop', 'pipewire'], capture_output=True, timeout=5)
        print("  ✓ PipeWire gestoppt")
        
        time.sleep(1)
        
        # Starte
        result = subprocess.run(['systemctl', '--user', 'start', 'pipewire'], capture_output=True, timeout=10)
        time.sleep(2)
        
        if result.returncode == 0:
            print("✓ PipeWire neu gestartet")
            return True
        else:
            print(f"✗ Fehler: {result.stderr.decode()}")
            return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        raise

@app.route('/')
def index():
    try:
        gains = get_gains()
        print(f"\n📊 Sende Gains an Frontend: {gains}")
        return render_template('eq.html', gains=json.dumps(gains))
    except Exception as e:
        print(f"✗ Fehler in index(): {e}")
        import traceback
        traceback.print_exc()
        return f"Fehler: {e}", 500

@app.route('/api/gains', methods=['GET'])
def get_gains_api():
    """API-Endpoint zum Abrufen der Gains und Q-Werte"""
    try:
        gains = get_gains()
        print(f"\n📊 /api/gains gibt zurück: {gains}")
        return jsonify(gains)
    except Exception as e:
        print(f"✗ Fehler in /api/gains: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update():
    """API-Endpoint zum Aktualisieren von Gain und Q"""
    try:
        data = request.json
        print(f"\n{'='*60}")
        print(f"📝 UPDATE-REQUEST erhalten")
        print(f"{'='*60}")
        print(f"Daten: {data}")
        
        if not data:
            return jsonify({'status': 'error', 'message': 'Keine Daten erhalten'}), 400
        
        success_count = 0
        error_count = 0
        
        # Speichere alle Änderungen
        for key, value in data.items():
            try:
                # Bestimme Basis-Band-Key (z.B. "band_10" oder "eq_band_10")
                if key.endswith('_gain'):
                    base = key[:-5]  # entferne "_gain"
                    param = 'gain'
                elif key.endswith('_q'):
                    base = key[:-2]  # entferne "_q"
                    param = 'q'
                elif re.match(r'^band_\d+$', key):
                    base = key
                    param = 'gain'
                else:
                    print(f"⚠ Unbekannter Parameter: {key}")
                    error_count += 1
                    continue

                # Normalisiere auf Config-Namen: "eq_band_10"
                if base.startswith('eq_'):
                    cfg_band = base
                elif base.startswith('band_'):
                    cfg_band = 'eq_' + base
                else:
                    cfg_band = base  # fallback

                # Aufruf der Aktualisierer
                if param == 'gain':
                    update_gain(cfg_band, float(value))
                else:
                    update_q(cfg_band, float(value))

                success_count += 1

            except Exception as e:
                print(f"✗ Fehler bei {key}: {e}")
                error_count += 1
        
        print(f"\n📊 Ergebnis: {success_count} erfolgreich, {error_count} Fehler")
        
        # Restart PipeWire nach ALLEN Änderungen
        if success_count > 0:
            restart_pipewire()
        
        return jsonify({
            'status': 'ok' if error_count == 0 else 'partial',
            'message': f'{success_count} Änderungen gespeichert' + (f', {error_count} Fehler' if error_count > 0 else ''),
            'success': success_count,
            'errors': error_count
        })
    except Exception as e:
        print(f"✗ Fehler in /api/update: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/restart', methods=['POST'])
def restart():
    """API-Endpoint zum Neustart von PipeWire"""
    try:
        restart_pipewire()
        return jsonify({'status': 'ok', 'message': 'PipeWire neu gestartet'})
    except Exception as e:
        print(f"✗ Fehler in /api/restart: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Nicht gefunden'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"✗ Internal Server Error: {error}")
    import traceback
    traceback.print_exc()
    return jsonify({'error': 'Interner Fehler'}), 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the server")
    parser.add_argument("-p", "--port", type=int, default=site_config["port"],
                        help="Port number (default: %(default)d)")
    parser.add_argument("-b", "--host", default="0.0.0.0",
                        help="Host address (default: %(default)s)")

    arguments = parser.parse_args()

    if "GUNICORN_ARGV" in dict(os.environ):
        run_with_gunicorn = True
        os.environ.pop("GUNICORN_ARGV")
        port = int(os.getenv("PORT", site_config["port"]))
        host = os.getenv("HOST", "0.0.0.0")
    else:
        run_with_gunicorn = False

    if run_with_gunicorn:
        print("Running with Gunicorn...")
        print(f"Host: {host}")
        print(f"Port: {port}")

        from gunicorn.app.wsgiapp import WSGIApplication
        options = {
            'bind': f'{host}:{port}',
            'workers': 2,
            'reload': False,
        }

        WSGIApplication(app).run(**options)
    else:
        print("="*60)
        print("🎵 PipeWire EQ Editor Server")
        print("="*60)
        print(f"📁 Config-Datei: {CONFIG_FILE}")
        print(f"✓ Existiert: {os.path.exists(CONFIG_FILE)}")
        print(f"📊 Aktuelle Gains und Q-Werte:")
        gains = get_gains()
        for key, value in sorted(gains.items()):
            print(f"   {key}: {value}")
        print("="*60)
        print("🌐 Server läuft auf: http://127.0.0.1:1338")
        print("="*60 + "\n")
        
        app.run(debug=True, host='127.0.0.1', port=1338)