# 1Password Secure Prompt Storage Setup

**Zero-hardcoded prompts**: All orchestrator prompts stored securely in 1Password and injected at runtime.

## 🔒 Security Benefits

1. **No plaintext prompts** in source code or config files
2. **Centralized management** - update prompts without code changes
3. **Audit trail** - 1Password logs all access
4. **Biometric unlock** - Touch ID/YubiKey for prompt access
5. **Encrypted storage** - Military-grade AES-256 encryption
6. **Easy rotation** - Update prompts instantly across all sessions

## 📋 Setup Steps

### 1. Create 1Password Items

Create **Secure Notes** in your Development vault:

#### Item 1: Permission Request Prompts
```
Name: Fifth Symphony Prompts - Permission Requests
Type: Secure Note
Vault: Development

Notes (paste this JSON):
{
  "file_deletion": "Permission requested: Delete {path}. This is a {risk_level} risk operation. The file contains {file_type} data. Approve deletion?",

  "git_push_force": "CRITICAL: Force push to {branch} on {remote}. This will rewrite history and may cause data loss. Are you absolutely sure?",

  "system_modification": "{agent} requests permission to modify system files in {directory}. Risk level: {risk_level}. This could affect system stability. Approve?",

  "network_operation": "Network operation requested: {action} to {destination}. This will expose data over the network. Risk level: {risk_level}. Proceed?",

  "generic": "{agent} requests permission: {action}. Risk level: {risk_level}. Approve?"
}
```

#### Item 2: Risk Warning Prompts
```
Name: Fifth Symphony Prompts - Risk Warnings
Type: Secure Note
Vault: Development

Notes (paste this JSON):
{
  "critical": "⚠️ CRITICAL RISK: {action}. This operation is EXTREMELY dangerous and could cause irreversible damage. Think carefully before approving.",

  "high": "⚠️ HIGH RISK: {action}. This operation could cause significant problems if not executed correctly. Review carefully.",

  "medium": "⚠️ MEDIUM RISK: {action}. This operation will make changes to your system. Ensure you understand the implications.",

  "low": "ℹ️ LOW RISK: {action}. This is a safe operation with minimal impact."
}
```

#### Item 3: Approval Response Prompts
```
Name: Fifth Symphony Prompts - Approval Responses
Type: Secure Note
Vault: Development

Notes (paste this JSON):
{
  "approved": "✅ Request approved. Proceeding with: {action}",

  "denied": "❌ Request denied. {agent} has been stopped.",

  "auto_approved": "✅ Auto-approved via rule: {rule_name}. Executing: {action}",

  "auto_denied": "❌ Auto-denied via rule: {rule_name}. Blocked: {action}",

  "custom_response": "📝 Custom response: {custom_message}"
}
```

#### Item 4: Error Handling Prompts
```
Name: Fifth Symphony Prompts - Error Handling
Type: Secure Note
Vault: Development

Notes (paste this JSON):
{
  "permission_timeout": "⏱️ Permission request timed out after {timeout} seconds. Request automatically denied for safety.",

  "ipc_error": "🔌 Communication error with Claude Code. Unable to process request: {error_message}",

  "voice_synthesis_failed": "🔇 Voice synthesis unavailable: {error_message}. Continuing with visual-only mode.",

  "1password_error": "🔐 Failed to retrieve prompts from 1Password: {error_message}. Using fallback prompts."
}
```

#### Item 5: System Status Prompts
```
Name: Fifth Symphony Prompts - System Status
Type: Secure Note
Vault: Development

Notes (paste this JSON):
{
  "orchestrator_started": "🎵 Fifth Symphony Orchestrator started. Permission system active. Voice feedback: {voice_status}",

  "orchestrator_stopped": "🎵 Fifth Symphony Orchestrator stopped. All sessions closed.",

  "session_established": "🔗 New session established: {session_id}. Agent: {agent_name}",

  "session_closed": "🔗 Session closed: {session_id}. Duration: {duration}",

  "auto_rule_created": "📋 New auto-approval rule created: {rule_description}",

  "health_check": "✅ System healthy. Active sessions: {session_count}. Auto-rules: {rule_count}. Uptime: {uptime}"
}
```

### 2. Verify 1Password CLI Access

```bash
# Test 1Password CLI access
op signin

# Test prompt retrieval
op item get "Fifth Symphony Prompts - Permission Requests" --vault Development --format json

# Should return JSON with your prompts
```

### 3. Configure Orchestrator

Update `config/orchestrator.yaml`:

```yaml
onepassword:
  vault: "Development"
  prompt_items:
    permission_request: "Fifth Symphony Prompts - Permission Requests"
    risk_warning: "Fifth Symphony Prompts - Risk Warnings"
    approval_response: "Fifth Symphony Prompts - Approval Responses"
    error_handling: "Fifth Symphony Prompts - Error Handling"
    system_status: "Fifth Symphony Prompts - System Status"

  # Cache prompts in memory for performance (cleared on restart)
  enable_cache: true

  # Fallback behavior if 1Password unavailable
  fallback_to_generic: true
```

### 4. Test Prompt Retrieval

```python
# Test in Python
from modules.orchestrator.prompt_manager import PromptManager
import asyncio

async def test():
    config = {
        "onepassword_vault": "Development"
    }

    manager = PromptManager(config)

    # Test permission request prompt
    prompt = await manager.get_prompt(
        "permission_request",
        "file_deletion",
        path="/etc/passwd",
        risk_level="CRITICAL",
        file_type="system credentials"
    )

    print(prompt)
    # Should output: "Permission requested: Delete /etc/passwd. This is a
    # CRITICAL risk operation. The file contains system credentials data.
    # Approve deletion?"

asyncio.run(test())
```

## 🎯 Usage in Orchestrator

```python
# In orchestrator.py
from modules.orchestrator.prompt_manager import PromptManager

async def handle_permission_request(request):
    # Get prompt from 1Password
    prompt = await prompt_manager.get_prompt(
        "permission_request",
        "generic",
        agent=request.agent,
        action=request.action,
        risk_level=request.risk_level.value.upper()
    )

    # Speak via ElevenLabs MCP
    await mcp_client.speak(prompt)

    # Show in TUI
    await tui.display_permission_request(prompt, request.risk_level)

    # Wait for user input
    response = await tui.get_user_response()

    # Get approval response prompt
    response_prompt = await prompt_manager.get_prompt(
        "approval_response",
        "approved" if response.approved else "denied",
        action=request.action,
        agent=request.agent
    )

    await mcp_client.speak(response_prompt)
```

## 🔄 Updating Prompts

**No code changes required!** Just update the 1Password secure note:

1. Open 1Password
2. Find the prompt item (e.g., "Fifth Symphony Prompts - Permission Requests")
3. Edit the JSON in the notes field
4. Save changes
5. Next orchestrator request will use updated prompts (cached prompts cleared on restart)

## 🎨 Prompt Customization

### Variable Substitution

Prompts support Python `.format()` style variables:

```json
{
  "my_prompt": "User {username} wants to {action} on {resource}. Risk: {risk_level}"
}
```

Usage:
```python
prompt = await manager.get_prompt(
    "category",
    "my_prompt",
    username="alice",
    action="delete",
    resource="/important/file",
    risk_level="HIGH"
)
```

### Voice-Optimized Prompts

For voice synthesis, use conversational language:

```json
{
  "voice_friendly": "Hey there! {agent} is asking permission to {action}. This is pretty risky at {risk_level} level. What do you think?"
}
```

### Multi-Language Support

Create separate items for different languages:

```
Fifth Symphony Prompts - Permission Requests (English)
Fifth Symphony Prompts - Permission Requests (Spanish)
Fifth Symphony Prompts - Permission Requests (French)
```

Configure language in `config/orchestrator.yaml`:

```yaml
onepassword:
  language: "English"  # or "Spanish", "French", etc.
```

## 🛡️ Security Best Practices

1. **Vault Permissions**: Use a dedicated vault with restricted access
2. **Audit Logging**: Enable 1Password audit logs for prompt access
3. **Biometric Lock**: Require Touch ID/YubiKey for 1Password access
4. **Regular Reviews**: Periodically review and update prompts
5. **No Fallbacks in Production**: Disable `fallback_to_generic` in production
6. **Prompt Versioning**: Use git-style versioning in prompt keys:
   ```json
   {
     "file_deletion_v1": "old prompt",
     "file_deletion_v2": "new improved prompt"
   }
   ```

## 📊 Benefits Summary

| Benefit | Description |
|---------|-------------|
| **Zero Hardcoding** | No prompts in source code or configs |
| **Centralized** | Single source of truth in 1Password |
| **Secure** | Encrypted storage with audit trail |
| **Dynamic** | Update without code deployment |
| **Consistent** | Same prompts across all environments |
| **Professional** | Clean, maintainable architecture |

## 🚀 Advanced Features

### Prompt Templates with Logic

For complex prompts, use JSON structure:

```json
{
  "conditional_prompt": {
    "base": "{agent} requests: {action}",
    "conditions": {
      "if_critical": " ⚠️ THIS IS EXTREMELY DANGEROUS!",
      "if_reversible": " (This can be undone later)",
      "if_network": " This will connect to: {destination}"
    }
  }
}
```

### Prompt Analytics

Track which prompts are used most:

```python
# In prompt_manager.py
async def get_prompt(self, category, prompt_key, **format_args):
    # Log prompt usage
    self._track_usage(category, prompt_key)

    # ... retrieve and return prompt
```

Store analytics in `memory/logs/prompt_usage.json` for optimization.

---

**This pattern provides enterprise-grade security while maintaining flexibility and ease of use!** 🎵🔒
