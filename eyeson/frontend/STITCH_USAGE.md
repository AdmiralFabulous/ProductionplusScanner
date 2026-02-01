# Using Stitch for EYESON UI Design

## What Stitch Does

**Stitch is a DESIGN GENERATION tool** - it creates visual mockups from text prompts using AI. It does NOT generate working code.

### Stitch Workflow:
1. You write a prompt: *"Mobile camera screen with pose overlay and progress bar"
2. Stitch generates a design image/mockup
3. You manually implement the design in React/Vue/etc
4. You add the interactive features (camera, voice, etc)

### What Stitch CANNOT Do:
- ❌ Generate working React components
- ❌ Create MediaPipe camera integration
- ❌ Build WebSocket connections
- ❌ Implement real-time features
- ❌ Create 3D viewers

## Using Your API Key

**SECURITY WARNING**: Never commit API keys to Git!

### Setup:

1. **Store your key in `.env.local`** (already created):
```bash
# frontend/.env.local
STITCH_API_KEY=AQ.Ab8RN6LanbGl8__podbOk4vm4pnbHGMewfvZ4yoPsSlAZOOYZw
```

2. **Configure MCP Client** (choose one):

**Cursor:**
Create `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "stitch": {
      "url": "https://stitch.googleapis.com/mcp",
      "headers": {
        "X-Goog-Api-Key": "AQ.Ab8RN6LanbGl8__podbOk4vm4pnbHGMewfvZ4yoPsSlAZOOYZw"
      }
    }
  }
}
```

**VSCode:**
Add to MCP settings:
```json
{
  "servers": {
    "stitch": {
      "url": "https://stitch.googleapis.com/mcp",
      "type": "http",
      "headers": {
        "Accept": "application/json",
        "X-Goog-Api-Key": "AQ.Ab8RN6LanbGl8__podbOk4vm4pnbHGMewfvZ4yoPsSlAZOOYZw"
      }
    }
  }
}
```

## Example Prompts for EYESON

### 1. Welcome Screen
```
Create a mobile welcome screen for a body scanning app called "EYESON".
- Clean, modern design
- Logo at top
- "Start Scan" button (large, primary)
- Tagline: "Professional measurements in 90 seconds"
- Subtle animated body outline graphic
- Bottom text: "Works on any device • No app needed"
- Color scheme: Deep blue (#1a365d) with white accents
```

### 2. Camera Capture Screen
```
Create a mobile camera capture screen for body scanning app.
- Full-screen camera view (mock)
- Skeleton overlay showing body pose
- Progress ring at bottom (30 seconds)
- "Keep turning slowly" instruction text
- Waveform animation showing voice active
- Cancel button (secondary)
- Safe area padding for iPhone notch
- Dark theme with green accent for skeleton
```

### 3. Calibration Screen
```
Create a calibration screen for body scanning app.
- Camera view with AR overlay
- ArUco marker detection visualization
- "Place calibration card on floor" instruction
- Animated arrows pointing to marker position
- Green checkmark when detected
- "Continue" button (disabled until detected)
- Help icon in corner
- Clean, minimal UI
```

### 4. Results Screen
```
Create a measurement results screen for body scanning app.
- List of body measurements (Chest, Waist, Hip, etc.)
- Each measurement shows: name, value in cm, confidence indicator
- Green/yellow/red confidence badges
- 3D body preview (simplified human figure)
- "Export" and "Share" buttons
- "Scan Again" option
- Scrollable list
- Clean data table design
```

### 5. Processing Screen
```
Create a processing/waiting screen for body scanning app.
- Animated 3D mesh being constructed
- Progress percentage (0-100%)
- Status messages: "Building 3D model...", "Extracting measurements..."
- Cancel button
- Estimated time remaining
- Skeleton to mesh morph animation
- Dark background with blue glow effects
```

## Workflow: Design → Implementation

### Step 1: Generate Designs with Stitch
Use the prompts above in your MCP-enabled editor to generate mockups.

### Step 2: Export Assets
- Download generated images
- Note color schemes and spacing
- Extract typography styles

### Step 3: Implement in React
Create actual working components:
```tsx
// CameraCapture.tsx - YOU implement this
export function CameraCapture() {
  // Real MediaPipe integration
  // Real camera access
  // Real voice streaming
}
```

## Important: What You Need to Build

Stitch only helps with the **visual design**. You still need to build:

| Feature | Stitch Helps? | You Build |
|---------|---------------|-----------|
| Button styles | ✅ Yes | CSS/Tailwind |
| Layout structure | ✅ Yes | HTML/JSX |
| Color scheme | ✅ Yes | Theme config |
| Camera integration | ❌ No | MediaPipe |
| Voice streaming | ❌ No | WebSocket |
| 3D viewer | ❌ No | Three.js |
| Recording logic | ❌ No | MediaRecorder |
| API integration | ❌ No | Fetch/Axios |

## Recommendation

**Use Stitch for:**
- Initial UI concepts
- Color palette exploration
- Layout ideas
- Marketing mockups

**Build separately:**
- Interactive React components
- Camera/MediaPipe integration
- Voice/WebSocket features
- 3D visualization

## Next Steps

1. Configure Stitch in your editor (Cursor/VSCode)
2. Generate designs using prompts above
3. I'll help you build the working React implementation
4. We connect it to your FastAPI backend

**Want me to start building the React frontend while you generate designs with Stitch?**
