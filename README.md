## Overview

This project provides automated installation and configuration of PipeWire with multiple audio profiles.

### Available Profiles

1. **HeSuVi 5.1** (`sink-eq10-5.1.conf`)
   - 5.1 Surround-Sound processing (FL, FR, FC, LFE, SL, SR)
   - HeSuVi HRTF filter for spatial audio
   - Conversion to stereo output

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

### Optional (for RT Priority)
- Configuration in `/etc/security/limits.d/25-pw-rlimits.conf`
- Membership in the `pipewire` group

## Installation

### User-Level Installation (supported method)

```bash
./install user
```

This creates the configuration in `~/.config/pipewire/` and:
- Automatically detects the current username
- Detects the soundcard and its sink ID
- Adjusts file paths (HeSuVi, EQ)
- Adds the user to the `pipewire` group (for RT priority)

### Uninstallation

```bash
./install uninstall
```

Removes all installed files from user configuration.

## Directory Structure

```
.
├── install                          # Installation script
├── README.md                        # This file
├── LICENSE                          # MIT License
├── pipewire.conf.d/
│   ├── pipewire.conf               # Main PipeWire configuration
│   ├── sink-eq10-5.1.conf          # HeSuVi 5.1 filter configuration
│   └── sink-eq10-wide.conf         # Standard EQ stereo configuration
└── hesuvi/
    └── hesuvi.wav                  # HeSuVi HRTF Impulse Response
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

## Automatically Configured Values

The installation script automatically adjusts the following values:

```ini
target.object = "Sink-Name"
```

File paths are set to the user's installation directory.

## Soundcard Detection

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

3. **Manually enter in configuration:**
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

### Add User to pipewire Group

```bash
sudo usermod -a -G pipewire $USER
```

**Important**: Log out and log back in for the change to take effect!

## Usage

After installation, new audio sinks will be created:

### Available Sinks

- **Pipewire Gold (5.1) Audio** - HeSuVi 5.1 for spatial audio
- **Pipewire Gold Standard Audio** - 10-Band EQ for standard stereo

Choose the sink based on use case:
- Movies/Gaming → HeSuVi 5.1
- Music/Daily use → Standard EQ

```bash
# Display all available sinks
wpctl status

# Inspect sink details
wpctl inspect <sink-id>```

## Troubleshooting

### Filter Not Loading

```bash
# Restart PipeWire
systemctl --user restart pipewire

# Check logs
journalctl --user -u pipewire -f

# Check filter chain status
wpctl inspect <sink-id>
```

### Audio Not Working

```bash
# Check available sinks
wpctl status

# Verify target.object is correct
grep "target.object" ~/.config/pipewire/pipewire.conf.d/sink-eq10-wide.conf

# Set default sink
wpctl set-default <sink-id>
```

### RT Priority Not Taking Effect

```bash
# Check user group membership
groups $USER

# Check limits
ulimit -r

# Restart PipeWire
systemctl --user restart pipewire
```

### Clipping/Distortion

```
If audio sounds distorted or clips:
1. Reduce EQ gains (especially bands 1-3)
2. Verify soft-limiter is enabled at 10 kHz, -1dB
3. Check playback volume in system settings
```

## Customizing EQ Settings

EQ bands can be adjusted in `sink-eq10-wide.conf`:

```ini
{ type = "builtin" name = "eq_band_1" label = "bq_peaking" 
  control = { Freq = 80.0 Q = 1.5 Gain = 5.0 } }
```

- **Freq**: Center frequency in Hz
- **Q**: Quality factor (higher = narrower bandwidth)
- **Gain**: Boost/Cut in dB (positive = boost, negative = cut)

### Soft-Limiter Adjustment

To increase limiter threshold:
```ini
{ type = "builtin" name = "soft_limiter" label = "bq_highshelf" 
  control = { Freq = 10000.0 Q = 0.7 Gain = -0.5 } }  # Less aggressive
```

## Known Limitations

- **User-level installation only**: System-wide installation can cause audio playback issues when switching the default device
- **No hardware compressor/limiter**: PipeWire filter-chain does not include native compressor or hard-limiter. Soft-limiter is approximated with high-shelf EQ.
- **Single target device**: Each configuration targets one audio sink. For multiple devices, create separate configurations.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
