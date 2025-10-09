# Visual Novel Avatar Assets

This directory contains avatar images for the Visual Novel widget.

## Required Images (Basic States)

Place the following PNG images in this directory:

### Core States
- **`idle.png`** - Default resting state
- **`talking.png`** - Voice output active (speaking)
- **`listening.png`** - Voice input active (microphone recording)
- **`processing.png`** - AI thinking/processing
- **`error.png`** - Error occurred

## Image Specifications

**Format**: PNG with transparency (recommended)
**Resolution**: 400x500px to 1200x1500px
**Aspect Ratio**: 4:5 (portrait orientation)
**Style**: Anime/Visual Novel style recommended

## Future: Emotion-Based Images

The `emotions/` subdirectory is reserved for future emotion-based image selection:

### Planned Emotions
- `emotions/happy.png` - Successful completion, positive feedback
- `emotions/sad.png` - Errors, failures
- `emotions/surprised.png` - Unexpected events
- `emotions/thinking.png` - Deep processing, complex queries
- `emotions/excited.png` - New downloads, important notifications
- `emotions/confused.png` - Unclear input, need clarification

## Placeholder Behavior

If an image file is missing, the widget will:
1. Display a placeholder with the state name
2. Show the expected file path
3. Use a dark gray background (#3d3d3d)

**Example placeholder**:
```
IDLE

Place image at:
assets/visualization/idle.png
```

## Image Sources

### Free Resources
- **VRoid Studio**: https://vroid.com/en/studio (create custom 3D models, export screenshots)
- **Picrew**: https://picrew.me/ (avatar makers)
- **Live2D Cubism**: https://www.live2d.com/ (for animated versions later)

### Commission Artists
- **Fiverr**: Search for "anime avatar" or "VTuber model"
- **VGen**: https://vgen.co/ (VTuber/anime art commissions)
- **Skeb**: https://skeb.jp/ (Japanese commission platform)

### AI Generation
- **Stable Diffusion**: Generate custom anime-style avatars
- **NovelAI**: Anime-style image generation
- **Midjourney**: High-quality AI art

## Recommended Workflow

1. **Start with placeholders** - Widget works without images
2. **Test with simple images** - Use screenshots or basic art
3. **Commission/create final art** - Get professional quality

## Animation Alternatives

For animated versions:
- **Live2D**: Animated 2D characters (future Open-LLM-VTuber integration)
- **VTube Studio**: Desktop pet mode
- **GIF animations**: Replace PNG with animated GIFs (requires code update)

## Example Prompt for AI Generation

```
anime girl, portrait, digital art, clean background,
professional illustration, soft lighting,
[emotion: happy/sad/neutral/thinking],
high quality, detailed
```

## Gitignore Note

This directory is gitignored to prevent committing large image files. Only this README is tracked in version control.

## Testing Without Images

The widget will work immediately with placeholder images. You can test all functionality before adding custom artwork.

## Integration Example

```python
from modules.visualization_widget import VisualNovelWidget

# Create widget
avatar = VisualNovelWidget()
avatar.resize(400, 500)
avatar.show()

# Change states
avatar.set_voice_speaking(True)  # Shows talking.png
avatar.set_mic_recording(True)   # Shows listening.png
avatar.set_processing(True)      # Shows processing.png
```

---

**Tip**: Start simple! Even basic colored shapes or emoji-based images work great for testing the system before investing in custom art.
