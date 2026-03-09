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

# Backup directory and limit
BACKUP_DIR = os.path.expanduser("~/.local/share/pipewire/backups")
MAX_BACKUPS = 10

# Mapping: node.description -> config file
CONFIG_MAPPING = {
    "Pipewire Gold Standard Audio": "sink-eq10-wide.conf",
    "Pipewire Gold (5.1) Audio": "sink-eq10-5.1.conf"
}

def get_active_config_file():
    """Determine active PipeWire config based on node.description"""
    try:
        wpctl_status = subprocess.run(
            "wpctl status | grep '*' | awk '{print $3}' | tr -d '.'",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if wpctl_status.returncode != 0:
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        sink_id_raw = wpctl_status.stdout.strip().split('\n')[0] if wpctl_status.stdout.strip() else None
        
        if not sink_id_raw:
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        wpctl_inspect = subprocess.run(
            f"wpctl inspect {sink_id_raw}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if wpctl_inspect.returncode != 0:
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        description_match = re.search(r'node\.description = "([^"]+)"', wpctl_inspect.stdout)
        
        if not description_match:
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
        
        node_description = description_match.group(1)
        
        if node_description in CONFIG_MAPPING:
            config_file = CONFIG_MAPPING[node_description]
            full_path = os.path.expanduser(f"~/.config/pipewire/pipewire.conf.d/{config_file}")
            return full_path
        else:
            return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")
    
    except Exception:
        return os.path.expanduser("~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf")

# Initialize CONFIG_FILE on startup
CONFIG_FILE = get_active_config_file()
LAST_CONFIG_CHECK = time.time()

def make_backup():
    """Create backup of current config file"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    base = os.path.basename(CONFIG_FILE)
    files = [f for f in os.listdir(BACKUP_DIR) if f.startswith(base + ".backup_")]
    files_paths = [os.path.join(BACKUP_DIR, f) for f in files]
    files_sorted = sorted(files_paths, key=os.path.getmtime)
    
    if len(files_sorted) < MAX_BACKUPS:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{base}.backup_{timestamp}"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
    else:
        backup_path = files_sorted[0]
    
    shutil.copy2(CONFIG_FILE, backup_path)
    try:
        os.utime(backup_path, None)
    except Exception:
        pass
    return backup_path

def get_gains():
    """Read current EQ values (Gain and Q) from config file"""
    global CONFIG_FILE
    CONFIG_FILE = get_active_config_file()
    
    if not os.path.exists(CONFIG_FILE):
        return {}
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        gains = {}
        is_5_1 = 'eq_band_1_L' in content
        
        for i in range(1, 11):
            band_name = f"eq_band_{i}_L" if is_5_1 else f"eq_band_{i}"
            
            # Read Gain
            gain_pattern = f'name = "{band_name}"[^}}]*?Gain = ([\\d.-]+)'
            gain_match = re.search(gain_pattern, content)
            gains[f'band_{i}'] = float(gain_match.group(1)) if gain_match else 0.0
            
            # Read Q
            q_pattern = f'name = "{band_name}"[^}}]*?Q = ([\\d.-]+)'
            q_match = re.search(q_pattern, content)
            gains[f'band_{i}_q'] = float(q_match.group(1)) if q_match else 1.0
        
        return gains
    except Exception:
        return {}

def update_gain(band, value, create_backup=True):
    """Update EQ Gain value in config file"""
    if not os.path.exists(CONFIG_FILE):
        raise Exception(f"Config file not found: {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        is_5_1 = 'eq_band_1_L' in content
        band_names = [f"{band}_L", f"{band}_R"] if is_5_1 else [band]
        
        backup_created = False
        content_modified = False
        
        for band_name in band_names:
            old_pattern = f'(name = "{band_name}"[^}}]*?Gain = )([\\d.-]+)'
            current_match = re.search(old_pattern, content)
            
            if not current_match:
                continue
            
            current_value = float(current_match.group(2))
            
            if abs(current_value - float(value)) < 1e-6:
                continue
            
            if not backup_created and create_backup:
                make_backup()
                backup_created = True
            
            content = re.sub(old_pattern, rf'\g<1>{value}', content)
            content_modified = True
        
        if content_modified:
            with open(CONFIG_FILE, 'w') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        raise

def update_q(band, value, create_backup=True):
    """Update EQ Q value in config file"""
    if not os.path.exists(CONFIG_FILE):
        raise Exception(f"Config file not found: {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            content = f.read()
        
        is_5_1 = 'eq_band_1_L' in content
        band_names = [f"{band}_L", f"{band}_R"] if is_5_1 else [band]
        
        backup_created = False
        content_modified = False
        
        for band_name in band_names:
            old_pattern = f'(name = "{band_name}"[^}}]*?Q = )([\\d.-]+)'
            current_match = re.search(old_pattern, content)
            
            if not current_match:
                continue
            
            current_value = float(current_match.group(2))
            
            if abs(current_value - float(value)) < 1e-6:
                continue
            
            if not backup_created and create_backup:
                make_backup()
                backup_created = True
            
            content = re.sub(old_pattern, rf'\g<1>{value}', content)
            content_modified = True
        
        if content_modified:
            with open(CONFIG_FILE, 'w') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        raise

def restart_pipewire():
    """Cleanly restart PipeWire service"""
    try:
        subprocess.run(['systemctl', '--user', 'stop', 'pipewire'], capture_output=True, timeout=5)
        time.sleep(1)
        
        result = subprocess.run(['systemctl', '--user', 'start', 'pipewire'], capture_output=True, timeout=10)
        time.sleep(2)
        
        return result.returncode == 0
    except Exception:
        return False

def cleanup_duplicate_sinks():
    """Remove duplicate audio sinks from PipeWire"""
    try:
        # Get all sinks
        wpctl_status = subprocess.run(
            "wpctl status",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        
        sinks = {}
        for line in wpctl_status.stdout.split('\n'):
            if 'Pipewire Gold' in line:
                # Extract sink ID and name
                parts = line.strip().split()
                if len(parts) >= 2:
                    sink_id = parts[0].strip('*.')
                    sink_name = ' '.join(parts[2:])
                    
                    if sink_name not in sinks:
                        sinks[sink_name] = []
                    sinks[sink_name].append(sink_id)
        
        # Remove duplicates (keep the first one)
        for sink_name, sink_ids in sinks.items():
            if len(sink_ids) > 1:
                for sink_id in sink_ids[1:]:
                    subprocess.run(
                        f"wpctl set-default {sink_ids[0]}",
                        shell=True,
                        capture_output=True,
                        timeout=5
                    )
                    subprocess.run(
                        f"pactl remove-sink-input {sink_id}",
                        shell=True,
                        capture_output=True,
                        timeout=5
                    )
    except Exception:
        pass

@app.route('/')
def index():
    try:
        gains = get_gains()
        return render_template('eq.html', gains=json.dumps(gains))
    except Exception as e:
        return f"Error: {e}", 500

@app.route('/api/gains', methods=['GET'])
def get_gains_api():
    """API endpoint to retrieve gains and Q values"""
    try:
        gains = get_gains()
        return jsonify(gains)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update():
    """API endpoint to update Gain and Q values"""
    try:
        data = request.json
        
        create_backup = data.pop('_backup', False)
        restart_pw = data.pop('_restart', False)
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data received'}), 400
        
        success_count = 0
        error_count = 0
        actual_changes = 0
        
        for key, value in data.items():
            try:
                # Determine parameter type
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
                    error_count += 1
                    continue

                # Normalize to config naming
                cfg_band = base if base.startswith('eq_') else ('eq_' + base if base.startswith('band_') else base)

                # Update config file
                changed = False
                if param == 'gain':
                    changed = update_gain(cfg_band, float(value), create_backup=create_backup)
                else:
                    changed = update_q(cfg_band, float(value), create_backup=create_backup)

                if changed:
                    actual_changes += 1
                
                success_count += 1

            except Exception:
                error_count += 1
        
        # Restart PipeWire only if _restart=true
        if actual_changes > 0 and restart_pw:
            restart_pipewire()
        
        return jsonify({
            'status': 'ok' if error_count == 0 else 'partial',
            'message': f'{actual_changes} changes applied' + (f', {error_count} errors' if error_count > 0 else ''),
            'success': success_count,
            'changes': actual_changes,
            'errors': error_count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/restart', methods=['POST'])
def restart():
    """API endpoint to restart PipeWire"""
    try:
        success = restart_pipewire()
        if success:
            return jsonify({'status': 'ok', 'message': 'PipeWire restarted'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to restart PipeWire'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/config-info', methods=['GET'])
def config_info():
    """API endpoint to check if config has changed"""
    try:
        global CONFIG_FILE, LAST_CONFIG_CHECK
        
        current_time = time.time()
        config_changed = False
        
        # Check if config changed (with caching - only every 1 second)
        if current_time - LAST_CONFIG_CHECK > 1:
            new_config = get_active_config_file()
            LAST_CONFIG_CHECK = current_time
            
            if new_config != CONFIG_FILE:
                CONFIG_FILE = new_config
                config_changed = True
        
        config_name = os.path.basename(CONFIG_FILE)
        
        return jsonify({
            'status': 'ok',
            'config_file': config_name,
            'changed': config_changed
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

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
        print(f"Config file: {CONFIG_FILE}")
        print(f"Server running on: http://127.0.0.1:1338")
        print("="*60 + "\n")
        
        app.run(debug=True, host='127.0.0.1', port=1338)