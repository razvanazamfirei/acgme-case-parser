# Extension Icons

You need to add three PNG icon files to this directory:

- `icon16.png` - 16x16 pixels (toolbar icon)
- `icon48.png` - 48x48 pixels (extension management)
- `icon128.png` - 128x128 pixels (Chrome Web Store)

## How to Create Icons

### Option 1: Use an Online Tool
1. Go to https://www.favicon.io/ or similar
2. Create a simple icon (medical/clipboard theme recommended)
3. Download in multiple sizes
4. Rename to icon16.png, icon48.png, icon128.png

### Option 2: Use Design Software
1. Use Figma, Canva, or Photoshop
2. Create a square design
3. Export in the three required sizes
4. Save as PNG with transparency

### Option 3: Simple Colored Squares (For Testing)
You can use ImageMagick or similar:

```bash
# Create simple colored squares for testing
convert -size 16x16 xc:#667eea icon16.png
convert -size 48x48 xc:#667eea icon48.png
convert -size 128x128 xc:#667eea icon128.png
```

## Recommended Design

A medical/healthcare themed icon works best:
- 📋 Clipboard icon
- 💉 Medical symbol
- 📊 Chart/graph icon
- 🏥 Hospital cross

Use the extension's color scheme:
- Primary: #667eea (purple-blue)
- Accent: #764ba2 (purple)
- Success: #48bb78 (green)

## Copyright Notice

Ensure any icons you use are:
- Created by you, OR
- Licensed for commercial use (CC0, MIT, etc.), OR
- Purchased with appropriate license

Do not use copyrighted medical symbols without permission.
