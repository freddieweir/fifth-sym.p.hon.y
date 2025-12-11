# Overseerr Audio Notifications

Audio notification system for Overseerr media requests using ElevenLabs voice synthesis.

## 📋 Overview

This integration connects Overseerr's webhook notifications to the Fifth Symphony audio monitoring system, providing real-time voice announcements for media requests, approvals, and availability notifications.

```
┌─────────────┐      HTTP POST      ┌──────────────────┐
│  Overseerr  ├─────────────────────►│ Webhook Listener │
│             │  (Webhook/API)       │  (FastAPI:8765)  │
└─────────────┘                      └────────┬─────────┘
                                              │
                                              │ Extract event data
                                              │ Format notification
                                              ▼
                                     ┌────────────────────┐
                                     │   Write .txt file  │
                                     │  (with -main/-vm)  │
                                     └────────┬───────────┘
                                              │
                                              │ File written
                                              ▼
                                     ┌────────────────────┐
                                     │  Audio Monitor Dir │
                                     │ communications/    │
                                     │      audio/        │
                                     └────────┬───────────┘
                                              │
                                              │ Watchdog detects
                                              │ Auto-generate speech
                                              │ Auto-play audio
                                              ▼
                                     ┌────────────────────┐
                                     │   Audio Monitor    │
                                     │  Service (launchd) │
                                     └────────────────────┘
```

## 🚀 Quick Start

### 1. Start the Webhook Listener

```bash
cd ~/git/internal/repos/fifth-symphony
./scripts/launchers/start-overseerr-webhook.sh
```

The webhook listener will start on port 8765 and display:
```
Starting Overseerr webhook listener...
Endpoint: http://0.0.0.0:8765/webhook/overseerr
Test endpoint: http://0.0.0.0:8765/webhook/test
Health check: http://0.0.0.0:8765/health
```

### 2. Configure Overseerr

1. Log into Overseerr admin panel
2. Navigate to **Settings → Notifications → Webhook**
3. Click **Add Webhook**
4. Configure webhook:

   **Webhook URL:**
   ```
   http://<your-machine-ip>:8765/webhook/overseerr
   ```

   **JSON Payload:**
   ```json
   {
     "notification_type": "{{notification_type}}",
     "event": "{{event}}",
     "subject": "{{subject}}",
     "message": "{{message}}",
     "image": "{{image}}",
     "requestedBy_username": "{{requestedBy_username}}",
     "requestedBy_email": "{{requestedBy_email}}",
     "requestedBy_avatar": "{{requestedBy_avatar}}",
     "media": "{{media}}",
     "request": "{{request}}",
     "extra": "{{extra}}"
   }
   ```

5. Select notification types:
   - ✅ Media Requested
   - ✅ Media Approved
   - ✅ Media Auto-Approved
   - ✅ Media Available
   - ✅ Media Declined
   - ✅ Media Failed

6. **Test webhook** using the "Send Test Notification" button

### 3. Verify Audio Monitor is Running

The audio monitor service should already be running on your main machine at:
```
~/git/internal/repos/ai-bedo/audio_monitor/
```

Check status:
```bash
# Check if audio monitor is running
pgrep -f audio_monitor

# Or check launchd service
launchctl list | grep audio
```

## 🎯 Supported Notification Types

| Event Type | Description | Audio Notification Example |
|------------|-------------|---------------------------|
| `MEDIA_PENDING` | New request submitted | "username requested The Matrix nineteen ninety-nine" |
| `MEDIA_APPROVED` | Request approved | "The Matrix nineteen ninety-nine approved for download" |
| `MEDIA_AUTO_APPROVED` | Auto-approved | "The Matrix nineteen ninety-nine automatically approved" |
| `MEDIA_AVAILABLE` | Media ready | "The Matrix nineteen ninety-nine is now available in Plex" |
| `MEDIA_DECLINED` | Request declined | "The Matrix nineteen ninety-nine request declined" |
| `MEDIA_FAILED` | Download failed | "Download failed for The Matrix nineteen ninety-nine. Check Sonarr or Radarr" |

## 🔧 Configuration

### Webhook Listener Settings

Edit `config/overseerr-notifier.yaml`:

```yaml
overseerr:
  webhook_url: "http://localhost:8765/webhook/overseerr"
  port: 8765
  host: "0.0.0.0"
  enabled_events:
    - MEDIA_PENDING
    - MEDIA_APPROVED
    - MEDIA_AVAILABLE
    # ... etc

audio:
  output_dir: "/Users/fweir/git/ai-bedo/communications/audio"
  voice_source: "main"  # or "vm"

notification_templates:
  MEDIA_PENDING: "{user} requested {media_title}"
  MEDIA_APPROVED: "{media_title} approved for download"
  # ... customize as needed
```

### Customizing Notification Text

You can customize the notification templates in two ways:

**1. Edit config file** (`config/overseerr-notifier.yaml`):
```yaml
notification_templates:
  MEDIA_AVAILABLE: "New media ready: {media_title}"
```

**2. Edit module directly** (`modules/overseerr_webhook.py`):
```python
NOTIFICATION_TEMPLATES = {
    "MEDIA_AVAILABLE": "{media_title} is ready to watch",
    # ... customize as needed
}
```

## 🧪 Testing

### Test the webhook listener directly:

```bash
# Test endpoint
curl -X POST http://localhost:8765/webhook/test

# Check health
curl http://localhost:8765/health

# Simulate Overseerr webhook
curl -X POST http://localhost:8765/webhook/overseerr \
  -H "Content-Type: application/json" \
  -d '{
    "notification_type": "MEDIA_PENDING",
    "event": "New Request",
    "subject": "The Matrix (1999)",
    "message": "A computer hacker learns about the true nature of his reality.",
    "requestedBy_username": "testuser"
  }'
```

### Expected workflow:

1. **Webhook received** → Logged in webhook listener console
2. **Text file written** → `$ALBEDO_ROOT/communications/audio/YYYYMMDD-HHMMSS-overseerr-media-pending-main.txt`
3. **Audio monitor detects** → Watchdog picks up new file
4. **Speech generated** → ElevenLabs synthesizes voice
5. **Audio plays** → Automatic playback with Secretary voice

### Check audio files:

```bash
# List recent audio notifications
ls -lt ~/git/internal/repos/ai-bedo/communications/audio/ | head -10

# View a notification text
cat ~/git/internal/repos/ai-bedo/communications/audio/20251103-*.txt
```

## 🛠️ Troubleshooting

### Webhook not receiving events

**Check webhook listener is running:**
```bash
curl http://localhost:8765/health
```

**Check Overseerr webhook configuration:**
- Verify URL is correct (use your machine's IP, not localhost if Overseerr is in Docker)
- Test webhook in Overseerr settings
- Check Overseerr logs for webhook errors

**Check firewall:**
```bash
# Allow port 8765 if needed
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/python3
```

### No audio playing

**Check audio monitor is running:**
```bash
pgrep -f audio_monitor
```

**Check audio files are being created:**
```bash
ls -lt ~/git/internal/repos/ai-bedo/communications/audio/ | head -5
```

**Check audio monitor logs:**
```bash
tail -f ~/git/internal/repos/ai-bedo/audio_monitor/logs/audio_monitor.log
```

**Verify ElevenLabs API key:**
```bash
# Check 1Password has the API key
op item get "ElevenLabs API Key" --vault Development
```

### Wrong voice playing

The voice is selected based on filename suffix:
- `-main.txt` → Secretary voice (Albedo V2)
- `-vm.txt` → Seer voice (Albedo V1)

Webhook listener defaults to `-main` since Overseerr runs on main machine.

### Webhook listener crashes

**Check logs:**
```bash
# Run in foreground to see errors
cd ~/git/internal/repos/fifth-symphony
uv run python -m modules.overseerr_webhook
```

**Common issues:**
- Port 8765 already in use → Change port in config
- Audio directory not writable → Check permissions
- Dependencies missing → Run `uv sync`

## 📊 Monitoring

### View webhook listener logs:

```bash
# If running in background
tail -f /tmp/overseerr-webhook.log

# If running in tmux/screen
tmux attach -t overseerr-webhook
```

### Health check endpoint:

```bash
curl http://localhost:8765/health | jq
```

Response:
```json
{
  "status": "healthy",
  "audio_output_dir": "/Users/fweir/git/ai-bedo/communications/audio",
  "audio_dir_exists": true,
  "audio_dir_writable": true
}
```

## 🔄 Running as a Service

### Option A: tmux/screen (simple)

```bash
# Start in tmux
tmux new-session -d -s overseerr-webhook \
  '~/git/internal/repos/fifth-symphony/scripts/launchers/start-overseerr-webhook.sh'

# Attach to view logs
tmux attach -t overseerr-webhook

# Detach: Ctrl+B, D
```

### Option B: launchd (automatic)

Create `~/Library/LaunchAgents/com.fifth-symphony.overseerr-webhook.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fifth-symphony.overseerr-webhook</string>

    <key>ProgramArguments</key>
    <array>
        <string>~/git/internal/repos/fifth-symphony/scripts/launchers/start-overseerr-webhook.sh</string>
    </array>

    <key>WorkingDirectory</key>
    <string>~/git/internal/repos/fifth-symphony</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/tmp/overseerr-webhook.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/overseerr-webhook.error.log</string>
</dict>
</plist>
```

Load service:
```bash
launchctl load ~/Library/LaunchAgents/com.fifth-symphony.overseerr-webhook.plist
launchctl start com.fifth-symphony.overseerr-webhook
```

## 🎛️ Advanced Configuration

### Change port:

Edit `modules/overseerr_webhook.py`:
```python
port = 8765  # Change to desired port
```

Or set via environment variable:
```bash
WEBHOOK_PORT=9000 ./scripts/launchers/start-overseerr-webhook.sh
```

### Add custom event types:

Edit `modules/overseerr_webhook.py`:
```python
NOTIFICATION_TEMPLATES = {
    # ... existing templates
    "CUSTOM_EVENT": "Custom notification for {media_title}",
}

EVENT_TYPE_ALIASES = {
    # ... existing aliases
    "custom.event": "CUSTOM_EVENT",
}
```

### Filter specific media types:

Edit `modules/overseerr_webhook.py` in `handle_overseerr_webhook()`:
```python
# Extract media type from payload
media_type = payload.get("media", {}).get("media_type", "")

# Filter movies only
if media_type != "movie":
    logger.info(f"Ignoring non-movie request: {media_type}")
    return JSONResponse({"status": "ignored", "reason": "media_type_filter"})
```

## 📚 Related Documentation

- **Audio Monitor Service**: `~/git/internal/repos/ai-bedo/audio_monitor/README.md`
- **AudioTTS Module**: `modules/audio_tts.py`
- **Fifth Symphony Main Docs**: `README.md`
- **Overseerr Webhook Docs**: https://docs.overseerr.dev/using-overseerr/notifications/webhooks

## 🐛 Known Issues

1. **Docker networking**: If Overseerr runs in Docker, use host machine IP in webhook URL, not `localhost`
2. **Firewall**: macOS firewall may block incoming webhooks on first run (approve in System Settings)
3. **Year formatting**: Years are spoken as "nineteen ninety-nine" not "1999" (ElevenLabs behavior)

## 🔮 Future Enhancements

- [ ] Support for Jellyseerr (Overseerr fork)
- [ ] Configurable voice selection per event type
- [ ] Rate limiting for rapid-fire notifications
- [ ] Notification grouping (batch multiple requests)
- [ ] Web dashboard for notification history
- [ ] Integration with other media management tools (Sonarr, Radarr)

## 💡 Tips

- Use **Media Auto-Approved** notifications to know when automated downloads start
- **Media Available** is the most important notification (media is ready to watch)
- **Media Failed** helps catch download issues early
- Customize templates to match your preference (formal vs. casual)
- Test with the `/webhook/test` endpoint before configuring Overseerr

---

**Version**: 1.0.0
**Last Updated**: 2025-11-03
**Maintained By**: Fifth Symphony Project
