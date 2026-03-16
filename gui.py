#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, session
from flask_babel import gettext
from babel_config import create_babel, get_languages, get_locale, SUPPORTED_LANGUAGES
from datetime import datetime
import subprocess
import re
import json
import os
import shutil
import time
import argparse

# Load config
config = json.loads(open('config.json', 'r').read())
site_config = config['site_config']

# Initialize Flask
app = Flask(__name__, template_folder='templates')
app.secret_key = 'pipewire-eq-secret-key'

# Initialize Babel with custom config
create_babel(app)

# Configuration
BACKUP_DIR = os.path.expanduser("~/.local/share/goldaudio/backups")
BACKUP_LOCK_FILE = os.path.expanduser("~/.local/share/goldaudio/backups/.backup_in_progress")
MAX_BACKUPS = 10

CONFIG_MAPPING = {
    "Pipewire Gold Standard Audio": "sink-eq10-wide.conf",
    "Pipewire Gold (5.1) Audio": "sink-eq10-5.1.conf"
}

# Helper functions
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
        
        # Round value to 1 decimal place for consistency
        value = round(float(value), 1)
        
        backup_created = False
        content_modified = False
        
        for band_name in band_names:
            old_pattern = f'(name = "{band_name}"[^}}]*?Gain = )([\\d.-]+)'
            current_match = re.search(old_pattern, content)
            
            if not current_match:
                continue
            
            current_value = round(float(current_match.group(2)), 1)
            
            # Only update if different
            if current_value == value:
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
        
        # Round value to 2 decimal places for consistency
        value = round(float(value), 2)
        
        backup_created = False
        content_modified = False
        
        for band_name in band_names:
            old_pattern = f'(name = "{band_name}"[^}}]*?Q = )([\\d.-]+)'
            current_match = re.search(old_pattern, content)
            
            if not current_match:
                continue
            
            current_value = round(float(current_match.group(2)), 2)
            
            # Only update if different
            if current_value == value:
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
    """Cleanly restart PipeWire service via socket trigger"""
    try:
        result = subprocess.run(
            ['systemctl', '--user', 'restart', 'pipewire.socket'],
            capture_output=True,
            timeout=5,
            check=False
        )
        time.sleep(2)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error restarting PipeWire: {e}")
        return False

# Context processor to inject variables into templates
@app.context_processor
def inject_languages():
    """Inject language info into all templates"""
    try:
        current_lang = session.get('language') or request.accept_languages.best_match(['en', 'de', 'tr']) or 'en'
    except:
        current_lang = 'en'
    
    return dict(
        supported_languages=SUPPORTED_LANGUAGES,
        current_language=current_lang
    )

# API Routes
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
    # Create lock file to prevent other operations during update
    lock_created = False
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        with open(BACKUP_LOCK_FILE, 'w') as f:
            f.write('')
        lock_created = True
        print(f"[UPDATE] Lock file created: {BACKUP_LOCK_FILE}")
    except Exception as e:
        print(f"[UPDATE] FAILED to create lock file: {e}")
    
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

            except Exception as ex:
                error_count += 1
        
        print(f"[UPDATE] Changes: {actual_changes}, Restart requested: {restart_pw}")
        # Restart PipeWire if _restart=true and changes were made
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
        print(f"[UPDATE] Exception: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        # Remove lock file when done
        if lock_created:
            try:
                os.remove(BACKUP_LOCK_FILE)
                print(f"[UPDATE] Lock file removed")
            except Exception as e:
                print(f"[UPDATE] FAILED to remove lock file: {e}")

@app.route('/api/backup-status', methods=['GET'])
def backup_status():
    """API endpoint to check if backup is in progress"""
    try:
        is_backup_in_progress = os.path.exists(BACKUP_LOCK_FILE)
        return jsonify({
            'status': 'ok',
            'backupInProgress': is_backup_in_progress
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/restart', methods=['POST'])
def restart():
    """API endpoint to restart PipeWire"""
    try:
        # Check if backup is in progress
        if os.path.exists(BACKUP_LOCK_FILE):
            return jsonify({
                'status': 'error',
                'message': 'Backup in progress. Cannot restart during backup.'
            }), 409
        
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

@app.route('/api/backups', methods=['GET'])
def list_backups():
    """API endpoint to list available backups"""
    try:
        global CONFIG_FILE
        
        if not os.path.exists(BACKUP_DIR):
            return jsonify({'status': 'ok', 'backups': []})
        
        base = os.path.basename(CONFIG_FILE)
        files = [f for f in os.listdir(BACKUP_DIR) if f.startswith(base + ".backup_")]
        files_paths = [os.path.join(BACKUP_DIR, f) for f in files]
        
        backups = []
        for filepath in files_paths:
            stat = os.stat(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            backups.append({
                'filename': os.path.basename(filepath),
                'path': filepath,
                'timestamp': mtime.strftime("%d.%m.%Y %H:%M:%S"),
                'size': stat.st_size
            })
        
        # Sort by modification time, newest first
        backups.sort(key=lambda x: x['path'], reverse=True)
        
        return jsonify({
            'status': 'ok',
            'backups': backups
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/restore-backup', methods=['POST'])
def restore_backup():
    """API endpoint to restore a backup"""
    # Create lock file to prevent service from being stopped during restore
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        open(BACKUP_LOCK_FILE, 'a').close()
    except Exception:
        pass
    
    try:
        global CONFIG_FILE
        data = request.json
        backup_filename = data.get('filename')
        
        if not backup_filename:
            return jsonify({'status': 'error', 'message': 'No backup specified'}), 400
        
        backup_path = os.path.join(BACKUP_DIR, backup_filename)
        
        # Security check: ensure backup is in BACKUP_DIR
        if not os.path.abspath(backup_path).startswith(os.path.abspath(BACKUP_DIR)):
            return jsonify({'status': 'error', 'message': 'Invalid backup path'}), 400
        
        if not os.path.exists(backup_path):
            return jsonify({'status': 'error', 'message': 'Backup file not found'}), 404
        
        # Create backup of current config before restoring
        make_backup()
        
        # Restore the backup
        shutil.copy2(backup_path, CONFIG_FILE)
        
        # Restart PipeWire
        restart_pipewire()
        
        return jsonify({
            'status': 'ok',
            'message': 'Backup restored successfully'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        # Remove lock file when done
        try:
            os.remove(BACKUP_LOCK_FILE)
        except Exception:
            pass

@app.route('/api/translations', methods=['GET'])
def get_translations():
    """Get all translations for current language"""
    translations = {
        # Band Labels
        'Bass Boost': gettext('Bass Boost'),
        'Foundation': gettext('Foundation'),
        'Warmth': gettext('Warmth'),
        'Anti-Boxy': gettext('Anti-Boxy'),
        'Anti-Nasal': gettext('Anti-Nasal'),
        'Midrange': gettext('Midrange'),
        'Anti-Plastic': gettext('Anti-Plastic'),
        'Presence': gettext('Presence'),
        'Brilliance': gettext('Brilliance'),
        'Air': gettext('Air'),
        
        # Special Filters
        'High-Pass Filter': gettext('High-Pass Filter'),
        'De-Esser': gettext('De-Esser'),
        'Final Gain': gettext('Final Gain'),
        'Soft Limiter': gettext('Soft Limiter'),
        'Frequency (Hz)': gettext('Frequency (Hz)'),
        'Gain (dB)': gettext('Gain (dB)'),
        'Gain (Factor)': gettext('Gain (Factor)'),
        'Q (Sharpness)': gettext('Q (Sharpness)'),
        'Q (Width)': gettext('Q (Width)'),
        'Q (Response)': gettext('Q (Response)'),
        'Removes low-frequency rumble and noise below the cutoff frequency.': gettext('Removes low-frequency rumble and noise below the cutoff frequency.'),
        'Reduces sibilance and harsh high-frequency sounds in vocals and speech.': gettext('Reduces sibilance and harsh high-frequency sounds in vocals and speech.'),
        'Tip: Keep below 1.2 to avoid clipping.': gettext('Tip: Keep below 1.2 to avoid clipping.'),
        'Protects from digital clipping at high frequencies.': gettext('Protects from digital clipping at high frequencies.'),
        
        # Status Messages
        'Configuration loaded successfully': gettext('Configuration loaded successfully'),
        'Error loading configuration': gettext('Error loading configuration'),
        'Adjusting value (will save on release)': gettext('Adjusting value (will save on release)'),
        'Saving changes...': gettext('Saving changes...'),
        'Changes applied': gettext('Changes applied'),
        'Saving changes and restarting PipeWire...': gettext('Saving changes and restarting PipeWire...'),
        'Reset all values to default (0 dB)?': gettext('Reset all values to default (0 dB)?'),
        'Resetting all values...': gettext('Resetting all values...'),
        'All values reset to default': gettext('All values reset to default'),
        'Preset loaded': gettext('Preset loaded'),
        'Restart PipeWire? (audio will be interrupted for ~2 seconds)': gettext('Restart PipeWire? (audio will be interrupted for ~2 seconds)'),
        'PipeWire restarted': gettext('PipeWire restarted'),
        'Restarting PipeWire...': gettext('Restarting PipeWire...'),
        'No changes to save': gettext('No changes to save'),
        'Backup in progress. Please wait before making changes.': gettext('Backup in progress. Please wait before making changes.'),
        'Changes applied, PipeWire restarted': gettext('Changes applied, PipeWire restarted'),
        'Error': gettext('Error'),
        
        # Backup/Undo Translations
        'Undo': gettext('Undo'),
        'Restore Backup': gettext('Restore Backup'),
        'Restore': gettext('Restore'),
        'No backups available': gettext('No backups available'),
        'Error loading backups': gettext('Error loading backups'),
        'Restore this backup? Current configuration will be backed up.': gettext('Restore this backup? Current configuration will be backed up.'),
        'Backup restored successfully': gettext('Backup restored successfully'),
        'Error restoring backup': gettext('Error restoring backup'),
        'Configuration reloaded': gettext('Configuration reloaded'),
        'Restoring backup...': gettext('Restoring backup...'),
    }
    
    return jsonify(translations)

# Error handlers
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
    parser.add_argument("-b", "--host", default="127.0.0.1",
                        help="Host address (default: %(default)s)")

    arguments = parser.parse_args()

    if "GUNICORN_ARGV" in dict(os.environ):
        run_with_gunicorn = True
        os.environ.pop("GUNICORN_ARGV")
        port = int(os.getenv("PORT", site_config["port"]))
        host = os.getenv("HOST", "127.0.0.1")
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