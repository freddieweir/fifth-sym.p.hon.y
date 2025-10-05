# Brain Dump - Don't Forget This Stuff!

**Purpose**: Capture random important thoughts before they vanish forever.

---

## 🎯 Current Session (2025-10-04)

### 1Password Vault Structure
- **Collection**: `Services`
- **Vaults**:
  - `API` - All API keys (ElevenLabs, AniList, etc.)
  - `ElevenLabs Voice IDs` - Voice configurations
  - `SSL` - Certificates and private keys
  - `Webhooks` - Webhook URLs and secrets

### AniList Integration
- API token is in: `Services` → `API` → `AniList API`
- Created `modules/anilist_client.py` for GraphQL API
- Can track anime/manga progress
- Get currently watching list
- Update progress and scores

### Eye-Grabbing Features Added
- CHANGELOG.md with emoji sections
- ADHD-friendly CLI UI with colors
- Risk-level color coding (🟢🟡🟠🔴)
- Rich library for visual impact

### Commit Strategy
- Small frequent commits (good for GitHub profile)
- No AI signatures (recruiter-friendly)
- Natural developer voice
- Made 8 commits today! 🟩🟩🟩🟩🟩🟩🟩🟩

---

## 💡 Random Important Things

### TODO: Things to Remember
- [ ] Check CHANGELOG.md when you forget what's new
- [ ] Use `recycled/` directory for old files
- [ ] All prompts go in 1Password (zero hardcoded)
- [ ] Services collection has the good stuff

### Cool Features to Use
- Run `python modules/cli_ui.py` to see eye-grabbing UI demo
- Check `docs/internal/1PASSWORD-VAULT-STRUCTURE.md` when you forget vault names
- CHANGELOG.md tracks everything that's been added

### Don't Commit These
- Anything in `recycled/`
- Audio/video/image files
- `memory/` directory (runtime state)
- CLAUDE.md files (gitignored)

---

## 🎮 AniList Features

### What You Can Do
- Get currently watching anime
- Update progress/scores
- Search for anime/manga
- Get user statistics

### Example Usage
```python
from modules.anilist_client import AniListClient

client = AniListClient()

# Get what you're watching
watching = await client.get_currently_watching("YourUsername")
for anime in watching:
    print(f"{anime.title}: {anime.progress}/{anime.episodes}")

# Update progress
await client.update_anime_progress(
    media_id=123456,
    progress=5,
    score=8.5
)
```

---

## 📝 Quick Notes

### When You're Under the Influence
- Write thoughts here immediately
- Don't worry about organization
- Can clean up later
- Better written down messy than forgotten forever

### Random API Keys Locations
- **ElevenLabs**: `Services` → `API` → `ElevenLabs API Key`
- **AniList**: `Services` → `API` → `AniList API`
- **Voice IDs**: `Services` → `ElevenLabs Voice IDs` → (various)

### If Something Breaks
1. Check CHANGELOG.md for recent changes
2. Look at `tasks/REORGANIZATION-COMPLETE.md` for structure
3. Check git log: `git log --oneline --graph`
4. Ask Claude (that's me!)

---

## 🔮 Future Ideas (Don't Forget These)

### Orchestrator Features
- [ ] Terminal UI with mobile SSH support
- [ ] Voice feedback for permission requests
- [ ] Auto-approve rules from 1Password
- [ ] Session persistence

### AniList Integration Ideas
- [ ] Voice announce when new episode available
- [ ] Auto-update progress from video player
- [ ] Recommendations based on watching
- [ ] Stats dashboard in CLI

### ADHD-Friendly Improvements
- [ ] More colors and animations
- [ ] Progress bars for everything
- [ ] Reminder system for tasks
- [ ] Visual changelog viewer

---

## 🎨 Visual Reminders

### Color Meanings
- 🟢 **Green** - Safe/Low risk
- 🟡 **Yellow** - Caution/Medium risk
- 🟠 **Orange** - Warning/High risk
- 🔴 **Red** - Danger/Critical risk

### Emoji Quick Reference
- 🔒 Security
- 🎵 Orchestrator
- 🎨 Visual/UI
- 📁 Structure
- 🚀 Features
- 🐛 Bugs
- 📚 Docs

---

**Last Updated**: 2025-10-04 (Update this when you add new stuff!)

**Pro Tip**: Search this file when you can't remember where something is or how to do something!
