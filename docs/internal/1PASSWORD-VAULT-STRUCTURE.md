# 1Password Vault Structure

**IMPORTANT**: This document tracks which vaults/collections to use for different credentials.

## 🗂️ Collection: `Services`

This collection contains multiple vaults organized by credential type.

### Vault: `API`
**Purpose**: API keys and tokens for external services

**Items**:
- `AniList API` - AniList GraphQL API token
- `ElevenLabs API Key` - Voice synthesis API
- `OpenAI API Key` - GPT models (if used)
- `Anthropic API Key` - Claude API (if used)
- Other API credentials...

### Vault: `ElevenLabs Voice IDs`
**Purpose**: ElevenLabs voice identifiers and settings

**Items**:
- Voice ID mappings for different use cases
- Voice settings configurations
- Custom voice profiles

### Vault: `SSL`
**Purpose**: SSL/TLS certificates and private keys

**Items**:
- Domain certificates
- Private keys
- CA bundles
- Certificate signing requests

### Vault: `Webhooks`
**Purpose**: Webhook URLs and secrets

**Items**:
- Webhook endpoints
- Signing secrets
- Integration tokens

## 📋 Fifth Symphony 1Password Configuration

### For Orchestrator Prompts
**Collection**: `Services`
**Vault**: TBD (create dedicated vault or use existing)
**Items**:
- `Fifth Symphony Prompts - Permission Requests`
- `Fifth Symphony Prompts - Risk Warnings`
- `Fifth Symphony Prompts - Approval Responses`
- `Fifth Symphony Prompts - Error Handling`
- `Fifth Symphony Prompts - System Status`

### For API Access
**Collection**: `Services`
**Vault**: `API`
**Items**:
- `ElevenLabs API Key` - Voice synthesis
- `AniList API` - AniList integration
- (Add others as needed)

## 🎯 Quick Reference

| Service | Collection | Vault | Item Name |
|---------|-----------|-------|-----------|
| ElevenLabs Voice | Services | API | ElevenLabs API Key |
| AniList | Services | API | AniList API |
| Voice IDs | Services | ElevenLabs Voice IDs | (various) |
| Prompts | Services | TBD | Fifth Symphony Prompts - * |
| SSL Certs | Services | SSL | (domain-specific) |

## 🔐 Access Patterns

### Python Code
```python
# Get API key from Services/API vault
api_key = subprocess.run(
    ["op", "item", "get", "AniList API",
     "--vault", "API",
     "--fields", "credential"],
    capture_output=True, text=True, check=True
).stdout.strip()
```

### CLI Testing
```bash
# Test access to AniList API
op item get "AniList API" --vault API --fields credential

# Test access to ElevenLabs API
op item get "ElevenLabs API Key" --vault API --fields credential
```

## 📝 Notes

- **Collection vs Vault**: Collections group related vaults. Access via: `--vault VaultName`
- **Biometric Unlock**: All access requires Touch ID/YubiKey
- **Session Tokens**: 1Password CLI caches tokens for session duration
- **Audit Logs**: All access is logged in 1Password activity feed

## 🚀 Adding New Services

When adding new API integrations:

1. **Store in correct vault**: `Services` → `API` vault
2. **Use consistent naming**: `ServiceName API` or `ServiceName API Key`
3. **Update this document** with new item
4. **Update config**: Add to `config/onepassword/vault_config.yaml`
5. **Test access**: Verify retrieval via `op` CLI

---

**Last Updated**: 2025-10-04
**Purpose**: Prevent forgetting which vaults/items to use
