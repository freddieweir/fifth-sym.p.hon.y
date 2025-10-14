# iTerm2 Remote Access via iPad

## Goal
Access iTerm2 terminal tabs from iPad Mini using Shellfish with hardware authentication only (YubiKey NFC + 1Password).

## Research Items

### iTerm2 Python API
- **URL**: https://iterm2.com/python-api/
- **Purpose**: Programmatic control of iTerm2 sessions, windows, and tabs
- **Architecture**: WebSocket-based (Google protobuf + websockets library)
- **Security Model**: Unix domain socket with cookie authentication
- **Enable**: Prefs > General > Magic > Enable Python API server
- **Limitation**: LOCAL ONLY - Unix domain socket, not network-accessible
- **Integration Points**:
  - Session management (attach to existing tabs)
  - Window/tab enumeration
  - Input/output streaming
  - Profile management
- **Reality Check**: API is for local scripting, NOT designed for remote access

### Shellfish App
- **URL**: https://secureshellfish.app/
- **Platform**: iOS/iPadOS
- **Authentication**:
  - ✅ YubiKey NFC support (ecdsa-sk keys)
  - ✅ Time-based authenticators
  - ❌ NO 1Password SSH agent (desktop only)
- **Features**:
  - Native terminal using system components
  - Multi-touch input mapping
  - Cloud server management
  - Files app integration
  - Offline directory caching
  - Widgets and Picture-in-Picture
- **Limitation**: Manual SSH key import required (no SSH agent on iOS)

### Authentication Strategy

**Requirements**:
- Passwordless authentication ONLY
- YubiKey NFC (physical presence required)
- NO password fallback
- Default deny without hardware token

**Reality-Based Flow**:
1. Generate ecdsa-sk SSH key on Mac tied to YubiKey
2. Import public key to Shellfish on iPad
3. iPad connects via Shellfish SSH
4. SSH server challenges for YubiKey signature
5. User taps NFC YubiKey on iPad
6. Connection established to tmux/screen session

**Corrections**:
- ❌ 1Password SSH agent NOT available on iOS (desktop only)
- ✅ YubiKey NFC with ecdsa-sk keys IS supported
- ⚠️ Must manually import SSH keys to Shellfish (no agent)

### Technical Approach (Recommended)

#### Primary: SSH + tmux Session Sharing with YubiKey Auth

**Architecture**:
```
iPad (Shellfish) → SSH (YubiKey NFC) → Mac (sshd) → tmux attach
```

**Why This Approach**:
- ✅ YubiKey NFC works with Shellfish (ecdsa-sk keys)
- ✅ Standard tools, battle-tested security
- ✅ Persistent sessions survive disconnects
- ✅ Can attach to SAME session as iTerm2 tab
- ✅ No custom bridge development required

**Implementation**:
1. Generate YubiKey-backed SSH key: `ssh-keygen -t ecdsa-sk`
2. Configure sshd for key-only auth (disable passwords)
3. Run tmux in iTerm2 tab
4. Connect from iPad: `ssh user@mac`, then `tmux attach`

**Alternative Considered (Rejected)**:
- **iTerm2 API Bridge**: API uses Unix domain socket (local only), would require complex SSH forwarding and custom bridge - not worth the effort when tmux provides same functionality

#### Enhancement: mosh for Mobile Resilience

**Add mosh layer** for better mobile experience:
- Handles network changes (WiFi ↔ cellular)
- Persistent connections during interruptions
- Lower latency on poor connections

**Requires**:
- Install mosh on Mac: `brew install mosh`
- Check if Shellfish supports mosh client (research needed)

## Implementation Tasks

### Phase 1: YubiKey SSH Key Setup
- [ ] Generate ecdsa-sk key pair on Mac: `ssh-keygen -t ecdsa-sk -f ~/.ssh/id_yubikey`
- [ ] Test key locally: `ssh -i ~/.ssh/id_yubikey localhost`
- [ ] Export public key for Shellfish import
- [ ] Document key generation process for additional YubiKeys

### Phase 2: SSH Server Hardening
- [ ] Backup current sshd_config
- [ ] Configure /etc/ssh/sshd_config:
  - `PasswordAuthentication no`
  - `PubkeyAuthentication yes`
  - `ChallengeResponseAuthentication no`
  - `UsePAM no` (or configure PAM for YubiKey only)
- [ ] Restart sshd and test local connections
- [ ] Set up fail2ban for brute force protection
- [ ] Add connection rate limiting

### Phase 3: tmux Session Management
- [ ] Install/verify tmux: `brew install tmux`
- [ ] Create persistent tmux config (~/.tmux.conf)
- [ ] Set up auto-start tmux sessions in iTerm2
- [ ] Test attaching to same session from multiple terminals
- [ ] Document session naming conventions

### Phase 4: Shellfish Configuration
- [ ] Install Shellfish on iPad Mini
- [ ] Import SSH public key to Shellfish
- [ ] Configure server connection (hostname, port, user)
- [ ] Test YubiKey NFC authentication
- [ ] Set up connection shortcuts/widgets

### Phase 5: mosh Enhancement (Optional)
- [ ] Install mosh: `brew install mosh`
- [ ] Open UDP ports 60000-61000 in firewall
- [ ] Test mosh connection from laptop first
- [ ] Research Shellfish mosh client support
- [ ] Evaluate latency/resilience improvements

## Security Considerations

1. **No Password Fallback**: Remove all password authentication methods
2. **Hardware Binding**: YubiKey presence required for access
3. **Session Isolation**: Each iPad connection isolated to specific tabs
4. **Audit Logging**: Track all remote access attempts
5. **Network Restriction**: Consider limiting to specific IP ranges/VPN
6. **Timeout Policy**: Aggressive session timeout if YubiKey removed

## Research Findings Summary

### Questions Answered
- ❌ **Shellfish + 1Password SSH agent**: NOT supported (desktop only)
- ❌ **iTerm2 API remote access**: NOT designed for remote (Unix socket only)
- ✅ **YubiKey NFC support**: CONFIRMED (ecdsa-sk keys)
- ✅ **Solution**: SSH + tmux provides same functionality as API bridge

### Open Questions
- Does Shellfish support mosh protocol?
- What's the latency over SSH vs mosh from iPad?
- Best tmux config for mobile usage?
- Should we use separate ecdsa-sk keys per device (iPad, iPhone)?
- How to handle multiple YubiKeys (backup keys)?

## Related Projects

- **fifth-symphony/modules/claude_monitor.py** - Already uses iTerm2 AppleScript integration
- **Authentication systems** - YubiKey FIDO2 implementations in other repos
- **1Password CLI** - Existing integration patterns

## Next Steps

1. Research iTerm2 Python API capabilities for remote access
2. Test Shellfish YubiKey NFC authentication
3. Confirm 1Password SSH agent compatibility
4. Design authentication-first architecture
5. Prototype basic SSH + tmux approach as MVP
