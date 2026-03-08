# PipeWire Audio Configuration

This project provides automated installation and configuration of PipeWire with multiple audio profiles including spatial audio (HeSuVi 5.1).

## ⚠️ Device-Specific Presets

These audio profiles are **made for the ASUS Vivobook Go E1504FA** with its built-in speakers.

**The presets feature:**
- Bass cut-off at 65 Hz (suitable for small notebook speakers)
- EQ tuned to compensate for laptop speaker limitations
- Soft-limiter to prevent distortion on small drivers

## Overview

This project provides automated installation and configuration of PipeWire with multiple audio profiles.

### Available Profiles

1. **HeSuVi 5.1** (`sink-eq10-5.1.conf`)
   - 5.1 Surround-Sound processing (FL, FR, FC, LFE, SL, SR)
   - HeSuVi HRTF filter for spatial audio
   - Conversion to stereo output
   - 10-band EQ per channel

2. **Standard EQ** (`sink-eq10-wide.conf`)
   - 10-Band Graphic Equalizer
   - Stereo processing (FL, FR)
   - Optimized for standard stereo playback
   - Stereo widening (Widen effect)
   - Soft-Limiter protection against clipping

### Common Features

- **Real-Time (RT) Priority** for low audio latency
- **Automatic Soundcard Detection** and audio sink configuration
- **User-Level Installation** in `~/.config/pipewire/`
- **De-Esser** to reduce sibilance (S/Sh sounds)
- **Soft-Limiter** to prevent digital clipping

## Requirements

- PipeWire installed and active
- `wpctl` (Part of PipeWire)
- `sudo` or `doas` for group management
- Python 3.8+ (for GUI)
- Flask (for GUI)

### Optional (for RT Priority)
- Configuration in `/etc/security/limits.d/25-pw-rlimits.conf`
- Membership in the `pipewire` group

### Optional (for Production Deployment)
- Gunicorn (for production-grade server)

### Python Dependencies Installation

Install required Python packages:

```bash
pip install -r requirements.txt
```

Or install individually:

```bash
pip install Flask gunicorn
```

## Installation

### User-Level Installation (supported method)

```bash
chmod +x ./install
./install user
```

The script will:
- Create directories in `~/.config/pipewire/`
- Detect your current username
- Detect the soundcard and its sink ID automatically
- Adjust file paths (HeSuVi, EQ filters)
- Add you to the `pipewire` group (for RT priority)
- Create automatic backups if configurations already exist

#### Installation Flow

```
Check pipewire.conf exists?
├─ YES → Ask if override
│  ├─ YES → Install new pipewire.conf
│  └─ NO  → Keep existing
└─ NO  → Install pipewire.conf

Install filter configurations (always)
Install HeSuVi files (always)
Detect audio sink (wpctl)
Set target.object in configs
Add user to pipewire group
```

### Uninstallation

```bash
./install uninstall
```

The script will:
- Remove HeSuVi files
- Remove filter configurations (sink-eq10-5.1.conf, sink-eq10-wide.conf)
- **Ask if pipewire.conf should be removed**
  - YES → Delete pipewire.conf
  - NO → Keep pipewire.conf (preserves manual edits)
- Remove user from `pipewire` group

## Directory Structure

```
.
├── install                          # Installation script
├── gui.py                           # Web GUI server
├── gunicorn_config.py               # Gunicorn configuration
├── config.json                      # GUI configuration
├── README.md                        # This file
├── LICENSE                          # MIT License
├── pipewire.conf.d/
│   ├── pipewire.conf               # Main PipeWire configuration
│   ├── sink-eq10-5.1.conf          # HeSuVi 5.1 filter configuration
│   └── sink-eq10-wide.conf         # Standard EQ stereo configuration
├── hesuvi/
│   └── hesuvi.wav                  # HeSuVi HRTF Impulse Response
└── templates/
    └── eq.html                     # Web GUI interface
```

## Configurations

### HeSuVi 5.1 (`sink-eq10-5.1.conf`)

Specialized configuration for spatial audio:

- **Input**: 5.1 Surround-Sound (FL, FR, FC, LFE, SL, SR)
- **Processing**: HeSuVi HRTF filter with 10-band EQ per channel
- **Output**: Stereo (FL, FR) with spatial impression
- **Use Case**: Movies, TV series, immersive games

### Standard EQ (`sink-eq10-wide.conf`)

Graphic 10-band equalizer for everyday music:

**EQ Bands:**
1. High-Pass (65 Hz) - removes inaudible sub-bass
2. Sub-Bass Peak (80 Hz, +5dB) - kick punch
3. Foundation (200 Hz, +5dB) - bass body
4. Warmth (400 Hz, +3dB) - warmth and proximity
5. Anti-Boxy (600 Hz, -1.5dB) - reduces papery sound
6. Anti-Nasal (1000 Hz, -2dB) - reduces nasal tone
7. Midrange Clarity (1500 Hz, -2dB) - clarity and separation
8. Anti-Plastic (2000 Hz, -3dB) - natural, organic sound
9. Presence (4500 Hz, +1.5dB) - speech intelligibility
10. Brilliance (9000 Hz, +2dB) - detail and sparkle
11. Air (12000 Hz, +2dB) - silkiness and extension

**Additional Features:**

- **De-Esser** (6 kHz, -1.5dB) - reduces sibilance from S/Sh sounds
- **Soft-Limiter** (High-Shelf, 10 kHz, -1dB) - prevents digital clipping
- **Stereo widening** (0.35) - wider stereo impression
- **Final gain** (1.0 = unity gain) - no additional boost to prevent clipping
- **CPU Impact**: Low (11 EQ bands only)

**Signal Flow:**
```
Input → High-Pass → EQ Bands (1-11) → De-Esser → Final Gain → Soft-Limiter → Output
```

#### Gain Calculation

```
Factor = 10^(dB / 20)
+1dB  ≈ 1.12
+2dB  ≈ 1.26
+3dB  ≈ 1.41
+4dB  ≈ 1.58
+6dB  ≈ 2.00
```

## Web GUI

The project includes an interactive web-based EQ editor for real-time audio adjustments.

### Features

- **Real-time EQ adjustments** with instant preview
- **Dual sliders per band**: Gain (dB) and Q (bandwidth) control
- **Audio presets**: Music, Podcast, Bright, Warm, Custom
- **Visual feedback**: Live value displays and status messages
- **Automatic backups**: All changes are backed up to `~/.local/share/pipewire/backups/`
- **Modern UI**: Responsive design with Material Design icons

### Running the GUI

#### Development Mode (Flask built-in server)

```bash
python3 gui.py
```

**Pros:**
- Simple one-command startup
- Auto-reload on code changes
- Great for development and testing

**Cons:**
- Single-threaded (only one connection at a time)
- Not suitable for production
- Slower performance

Then open your browser and navigate to: **http://127.0.0.1:1338**

#### Production Mode (Gunicorn WSGI server)

```bash
python3 -B -m gunicorn --config gunicorn_config.py gui:app
```

**Pros:**
- Multi-worker support (concurrent connections)
- Better performance and stability
- Production-grade reliability
- Pre-fork worker model for robustness

**Cons:**
- Requires gunicorn installation: `pip install gunicorn`

Installation:
```bash
pip install gunicorn
```

Then navigate to: **http://127.0.0.1:1338**

### GUI Configuration

Edit `config.json` to customize GUI behavior:

```json
{
  "site_config": {
    "title": "PipeWire Gold Audio EQ Editor",
    "port": 5000,
    "host": "127.0.0.1"
  }
}
```

### Backup Management

All EQ changes are automatically backed up to:

```
~/.local/share/pipewire/backups/
```

- **Backup strategy**: Circular (oldest backup is overwritten when limit reached)
- **Max backups**: 10 per configuration file
- **Naming**: `sink-eq10-wide.conf.backup_YYYYMMDD_HHMMSS`

### Presets

Available presets for quick EQ switching:

- **🎵 Musik** - Boosted bass and presence for music listening
- **🎙️ Podcast** - Optimized for speech intelligibility
- **✨ Hell** - Bright, detailed sound for analytical listening
- **🔥 Warm** - Warm, smooth sound for casual listening

## Automatically Configured Values

The installation script automatically adjusts the following values:

```ini
target.object = "sink-name"      # Your audio sink
```

File paths are set to the user's installation directory:
```
~/.config/pipewire/hesuvi/hesuvi.wav
```

### Manual Soundcard Detection

If automatic detection doesn't work:

1. **Get sink ID:**
   ```bash
   wpctl status
   ```
   Look for "Speaker + Headphones" and note the ID (e.g. 75)

2. **Get sink name:**
   ```bash
   wpctl inspect <ID> | grep 'node.name' | awk '{print $4}' | tr -d '"'
   ```

3. **Manually edit configuration:**
   ```bash
   editor ~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf
   ```
   
   Find and update:
   ```ini
   target.object = "alsa_output.pci-0000_03_00.6.HiFi__hw_Generic_1__sink"
   ```

## Real-Time Priority

For optimal audio latency, PipeWire should run with Real-Time (RT) priority.

### Check Prerequisites

```bash
# Check RT limits
cat /etc/security/limits.d/25-pw-rlimits.conf

# Check RT status
ps -mo pid,tid,rtprio,comm -C pipewire
```

The installation script automatically adds you to the `pipewire` group. After login, RT priority should be enabled.

**Important**: Log out and log back in for group changes to take effect!

## Usage

After installation and restart, new audio sinks will be created automatically.

### Available Sinks

- **Pipewire Gold (5.1) Audio** - HeSuVi 5.1 for spatial audio
- **Pipewire Gold Standard Audio** - 10-Band EQ for standard stereo

### Commands

```bash
# List all available sinks
wpctl status

# Set default sink
wpctl set-default <sink-id>

# Inspect sink details (see active filters)
wpctl inspect <sink-id>

# Restart PipeWire after configuration changes
systemctl --user restart pipewire

# View logs
journalctl --user -u pipewire -f
```

## Troubleshooting

### Audio Not Working

```bash
# Check available sinks
wpctl status

# Verify sink is active
wpctl inspect <sink-id>

# Set the sink as default
wpctl set-default <sink-id>

# Restart PipeWire
systemctl --user restart pipewire
```

### Filter Not Loading

```bash
# Restart PipeWire (required after config changes)
systemctl --user restart pipewire

# Check logs for errors
journalctl --user -u pipewire -f

# Verify target.object is correct
grep "target.object" ~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf

# Check sink name manually
wpctl inspect <sink-id> | grep 'node.name'
```

### Audio Crackles/Pops

This indicates CPU overload. Solutions:
1. Disable HeSuVi 5.1 (high CPU cost)
2. Increase quantum size in pipewire.conf:
   ```ini
   default.clock.quantum = 2048
   ```
3. Check CPU usage:
   ```bash
   top -p $(pgrep pipewire)
   ```

### RT Priority Not Taking Effect

```bash
# Check user group membership
groups $USER

# Expected output should include: pipewire

# Check limits
ulimit -r

# Should show: unlimited

# Restart PipeWire
systemctl --user restart pipewire

# Verify RT priority
ps -mo pid,tid,rtprio,comm -C pipewire
```

### Clipping/Distortion

If audio sounds distorted or clips:
1. Reduce EQ gains (especially bands 1-3)
2. Verify soft-limiter is enabled at 10 kHz, -1dB
3. Check playback volume in system settings
4. Reduce overall gain if needed

### GUI Won't Start

**Flask dev server issues:**
```bash
# Make sure Flask is installed
pip install flask

# Run with verbose output
python3 -u gui.py
```

**Gunicorn issues:**
```bash
# Check for permission errors
python3 -B -m gunicorn --config gunicorn_config.py gui:app

# If pkg_resources error occurs, use Flask dev server instead
python3 gui.py
```

## Customizing EQ Settings

EQ bands can be adjusted in `sink-eq10-wide.conf` or through the web GUI:

```ini
{ type = "builtin" name = "eq_band_1" label = "bq_peaking" 
  control = { Freq = 80.0 Q = 1.5 Gain = 5.0 } }
```

- **Freq**: Center frequency in Hz
- **Q**: Quality factor (higher = narrower bandwidth, more precise)
- **Gain**: Boost/Cut in dB (positive = boost, negative = cut)

### Via Web GUI

1. Start the GUI: `python3 gui.py` or `python3 -B -m gunicorn --config gunicorn_config.py gui:app`
2. Open **http://127.0.0.1:1338** in your browser
3. Adjust sliders for Gain and Q values
4. Click "Änderungen speichern" to apply changes
5. Changes are automatically backed up and PipeWire is restarted

### Manual Editing

Edit `~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf` directly and restart PipeWire:

```bash
systemctl --user restart pipewire
```

### Soft-Limiter Adjustment

To make limiter less aggressive:
```ini
{ type = "builtin" name = "soft_limiter" label = "bq_highshelf" 
  control = { Freq = 10000.0 Q = 0.7 Gain = -0.5 } }
```

To make limiter more aggressive:
```ini
{ type = "builtin" name = "soft_limiter" label = "bq_highshelf" 
  control = { Freq = 10000.0 Q = 0.7 Gain = -2.0 } }
```

After any changes:
```bash
systemctl --user restart pipewire
```

## Known Limitations

- **User-level installation only**: System-wide installation can cause audio playback issues when switching the default device
- **No hardware compressor**: PipeWire filter-chain does not include native compressor. Use soft-limiter or reduce EQ gains instead.
- **Single target device**: Each configuration targets one audio sink. For multiple devices, manually create separate configurations.
- **HeSuVi 5.1 CPU intensive**: Convolver + 20 EQ bands require significant CPU. Use Standard EQ for lower-end systems.
- **GUI requires restart**: EQ parameter changes via GUI trigger automatic PipeWire restart (~2 seconds of audio loss)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
