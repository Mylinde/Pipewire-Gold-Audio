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

# Neuer Backup-Ordner & Limit
BACKUP_DIR = os.path.expanduser("~/.local/share/pipewire/backups")
MAX_BACKUPS = 10

# Mapping: node.description -> config file
CONFIG_MAPPING = {
    "Pipewire Gold Standard Audio": "sink-eq10-wide.conf",
    "Pipewire Gold (5.1) Audio": "sink-eq10-5.1.conf"
}

def get_active_config_file():
    """Ermittelt die aktuell in PipeWire geladene .config basierend auf node.description"""
    try:
        # Hole den aktuellen Standard-Sink mit wpctl status
        wpctl_status = subprocess.run(
            "wpctl status | grep '*' | awk '{print $3}' | tr -d '.'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if wpctl_status.returncode != 0:
            print("⚠ wpctl status Fehler, verwende Fallback: sink-eq10-wide.conf")
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        sink_id_raw = wpctl_status.stdout.strip().split('\n')[0] if wpctl_status.stdout.strip() else None
        
        if not sink_id_raw:
            print("⚠ Kein aktiver Sink gefunden, verwende Fallback: sink-eq10-wide.conf")
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        # Hole node.description für diesen Sink
        wpctl_inspect = subprocess.run(
            f"wpctl inspect {sink_id_raw}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if wpctl_inspect.returncode != 0:
            print(f"⚠ wpctl inspect {sink_id_raw} fehlgeschlagen, verwende Fallback")
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        # Extrahiere node.description
        description_match = re.search(r'node\.description = "([^"]+)"', wpctl_inspect.stdout)
        
        if not description_match:
            print("⚠ node.description nicht gefunden, verwende Fallback")
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        node_description = description_match.group(1)
        print(f"✓ Erkannte node.description: '{node_description}'")
        
        # Mappe auf config file
        if node_description in CONFIG_MAPPING:
            config_file = CONFIG_MAPPING[node_description]
            full_path = os.path.expanduser(f"~/.config/pipewire/pipewire.conf.d/{config_file}")
            print(f"✓ Verwende Config: {config_file}")
            return full_path
        else:
            print(f"⚠ node.description '{node_description}' nicht im Mapping, verwende Fallback")
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
    
    except Exception as e:
        print(f"✗ Fehler beim Ermitteln der Config: {e}")
        import traceback
        traceback.print_exc()
        return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")

# Initialisiere CONFIG_FILE beim Start
CONFIG_FILE = get_active_config_file()

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
    # Aktualisiere CONFIG_FILE bei jedem Aufruf
    global CONFIG_FILE
    CONFIG_FILE = get_active_config_file()
    
    if not os.path.exists(CONFIG_FILE):
        print(f"Fehler: Config-Datei nicht gefunden: {CONFIG_FILE}")
        return {}
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        gains = {}
        
        # Erkenne ob Stereo (ohne _L/_R) oder 5.1 (mit _L/_R)
        is_5_1 = 'eq_band_1_L' in content
        
        for i in range(1, 11):
            if is_5_1:
                # 5.1 Config: Lese nur den linken Kanal (_L)
                band_name = f"eq_band_{i}_L"
            else:
                # Stereo Config: Standard naming
                band_name = f"eq_band_{i}"
            
            # Lese Gain
            gain_pattern = f'name = "{band_name}"[^}}]*?Gain = ([\\d.-]+)'
            gain_match = re.search(gain_pattern, content)
            if gain_match:
                gains[f'band_{i}'] = float(gain_match.group(1))
                print(f"✓ {band_name} Gain: {gains[f'band_{i}']}")
            else:
                gains[f'band_{i}'] = 0.0
                print(f"✗ {band_name} Gain nicht gefunden (default: 0.0)")
            
            # Lese Q
            q_pattern = f'name = "{band_name}"[^}}]*?Q = ([\\d.-]+)'
            q_match = re.search(q_pattern, content)
            if q_match:
                gains[f'band_{i}_q'] = float(q_match.group(1))
                print(f"✓ {band_name} Q: {gains[f'band_{i}_q']}")
            else:
                gains[f'band_{i}_q'] = 1.0
                print(f"✗ {band_name} Q nicht gefunden (default: 1.0)")
        
        return gains
    except Exception as e:
        print(f"Fehler beim Lesen der Gains: {e}")
        import traceback
        traceback.print_exc()
        return {}

def update_gain(band, value, create_backup=True):
    """Aktualisiert einen EQ-Wert (Gain) in der Config-Datei"""
    if not os.path.exists(CONFIG_FILE):
        raise Exception(f"Config-Datei nicht gefunden: {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        print(f"\nVerarbeite: {band} Gain = {value}")
        
        # Erkenne ob Stereo oder 5.1
        is_5_1 = 'eq_band_1_L' in content
        
        # Bestimme die zu ändernden Band-Namen
        if is_5_1:
            band_names = [f"{band}_L", f"{band}_R"]
        else:
            band_names = [band]
        
        backup_created = False
        content_modified = False
        
        for band_name in band_names:
            # Pattern für Gain
            old_pattern = f'(name = "{band_name}"[^}}]*?Gain = )([\\d.-]+)'
            current_match = re.search(old_pattern, content)
            
            if not current_match:
                print(f"  ⚠ Gain-Pattern für {band_name} nicht gefunden")
                continue
            
            current_value = float(current_match.group(2))
            
            # Wenn Wert gleich: überspringen
            if abs(current_value - float(value)) < 1e-6:
                print(f"  ℹ {band_name} Gain ist bereits {current_value}")
                continue
            
            # Backup NUR beim ersten Mal
            if not backup_created and create_backup:
                backup_file = make_backup()
                print(f"✓ Backup erstellt: {backup_file}")
                backup_created = True
            else:
                print(f"ℹ Kein Backup (Auto-Save)")
            
            # Ersetze Gain
            content = re.sub(old_pattern, rf'\g<1>{value}', content)
            print(f"  ✓ {band_name} Gain aktualisiert: {current_value} → {value}")
            content_modified = True
        
        if content_modified:
            # Schreibe neue Config
            with open(CONFIG_FILE, 'w') as f:
                f.write(content)
            print(f"  ✓ Datei gespeichert")
            return True
        else:
            print(f"  ℹ Keine Änderungen vorgenommen")
            return False
        
    except Exception as e:
        print(f"  ✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        raise

def update_q(band, value, create_backup=True):
    """Aktualisiert den Q-Wert in der Config-Datei"""
    if not os.path.exists(CONFIG_FILE):
        raise Exception(f"Config-Datei nicht gefunden: {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        print(f"\nVerarbeite: {band} Q = {value}")
        
        # Erkenne ob Stereo oder 5.1
        is_5_1 = 'eq_band_1_L' in content
        
        # Bestimme die zu ändernden Band-Namen
        if is_5_1:
            band_names = [f"{band}_L", f"{band}_R"]
        else:
            band_names = [band]
        
        backup_created = False
        content_modified = False
        
        for band_name in band_names:
            # Pattern für Q
            old_pattern = f'(name = "{band_name}"[^}}]*?Q = )([\\d.-]+)'
            current_match = re.search(old_pattern, content)
            
            if not current_match:
                print(f"  ⚠ Q-Pattern für {band_name} nicht gefunden")
                continue
            
            current_value = float(current_match.group(2))
            
            # Wenn Wert gleich: überspringen
            if abs(current_value - float(value)) < 1e-6:
                print(f"  ℹ {band_name} Q ist bereits {current_value}")
                continue
            
            # Backup NUR beim ersten Mal
            if not backup_created and create_backup:
                backup_file = make_backup()
                print(f"✓ Backup erstellt: {backup_file}")
                backup_created = True
            else:
                print(f"ℹ Kein Backup (Auto-Save)")
            
            # Ersetze Q
            content = re.sub(old_pattern, rf'\g<1>{value}', content)
            print(f"  ✓ {band_name} Q aktualisiert: {current_value} → {value}")
            content_modified = True
        
        if content_modified:
            # Schreibe neue Config
            with open(CONFIG_FILE, 'w') as f:
                f.write(content)
            print(f"  ✓ Datei gespeichert")
            return True
        else:
            print(f"  ℹ Keine Änderungen vorgenommen")
            return False
        
    except Exception as e:
        print(f"  ✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        raise

def restart_pipewire():
    """Startet PipeWire sauber neu"""
    try:
        print("\nStarte PipeWire neu...")
        
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
        print(f"\nSende Gains an Frontend: {gains}")
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
        print(f"\n/api/gains gibt zurück: {gains}")
        return jsonify(gains)
    except Exception as e:
        print(f"✗ Fehler in /api/gains: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update():
    """API-Endpoint zum Aktualisieren von Gain und Q"""
    try:
        data = request.json
        
        # Neuer Parameter: create_backup Flag
        create_backup = data.pop('_backup', False)
        restart_pw = data.pop('_restart', False)
        
        print(f"\n{'='*60}")
        print(f"UPDATE-REQUEST erhalten (Backup: {create_backup}, Restart: {restart_pw})")
        print(f"{'='*60}")
        print(f"Daten: {data}")
        
        if not data:
            return jsonify({'status': 'error', 'message': 'Keine Daten erhalten'}), 400
        
        success_count = 0
        error_count = 0
        actual_changes = 0
        
        # Speichere alle Änderungen
        for key, value in data.items():
            try:
                # Bestimme Basis-Band-Key
                if key.endswith('_gain'):
                    base = key[:-5]
                    param = 'gain'
                elif key.endswith('_q'):
                    base = key[:-2]
                    param = 'q'
                elif re.match(r'^band_\d+$', key):
                    base = key
                    param = 'gain'
                else:
                    print(f"⚠ Unbekannter Parameter: {key}")
                    error_count += 1
                    continue

                # Normalisiere auf Config-Namen
                if base.startswith('eq_'):
                    cfg_band = base
                elif base.startswith('band_'):
                    cfg_band = 'eq_' + base
                else:
                    cfg_band = base

                # Aufruf der Aktualisierer mit create_backup Flag
                changed = False
                if param == 'gain':
                    changed = update_gain(cfg_band, float(value), create_backup=create_backup)
                else:
                    changed = update_q(cfg_band, float(value), create_backup=create_backup)

                if changed:
                    actual_changes += 1
                
                success_count += 1

            except Exception as e:
                print(f"✗ Fehler bei {key}: {e}")
                error_count += 1
        
        print(f"\nErgebnis: {success_count} verarbeitet, {actual_changes} echte Änderungen, {error_count} Fehler")
        
        # Restart PipeWire NUR wenn _restart=true
        if actual_changes > 0 and restart_pw:
            print("Starte PipeWire neu...")
            restart_pipewire()
        elif actual_changes > 0:
            print("ℹ Änderungen gespeichert, aber PipeWire wird NICHT neu gestartet")
        else:
            print("ℹ Keine echten Änderungen")
        
        return jsonify({
            'status': 'ok' if error_count == 0 else 'partial',
            'message': f'{actual_changes} Änderungen angewendet' + (f', {error_count} Fehler' if error_count > 0 else ''),
            'success': success_count,
            'changes': actual_changes,
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
        print("PipeWire EQ Editor Server")
        print("="*60)
        print(f"Config-Datei: {CONFIG_FILE}")
        print(f"✓ Existiert: {os.path.exists(CONFIG_FILE)}")
        print(f"Aktuelle Gains und Q-Werte:")
        gains = get_gains()
        for key, value in sorted(gains.items()):
            print(f"   {key}: {value}")
        print("="*60)
        print("Server läuft auf: http://127.0.0.1:1338")
        print("="*60 + "\n")
        
        app.run(debug=True, host='127.0.0.1', port=1338)