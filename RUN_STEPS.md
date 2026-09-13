# 🚀 Run the Mini Project (Expo)

## Quick Start

Open **Command Prompt** or **PowerShell** and run:

```cmd
cd "C:\05D0\mini project"
npm start
```

A QR code + menu appears in the terminal.

### Run on your phone (easiest)
1. Install the **Expo Go** app from the Play Store / App Store.
2. Make sure phone and PC are on the same Wi-Fi.
3. Scan the QR code with the Expo Go app.
4. The app opens on your phone — edits hot-reload instantly.

### Run in a browser
Press **`w`** in the terminal after `npm start` (or run `npm run web`).

### Run on an Android emulator
Press **`a`** after `npm start` (requires Android Studio emulator installed).

---

## Project structure

```
mini project/
├── app.json            # App name, icons, splash screen config
├── package.json        # Dependencies and scripts
├── src/
│   ├── app/            # SCREENS (expo-router: file = URL/screen)
│   │   ├── _layout.tsx # Root layout / navigation
│   │   ├── index.tsx   # Home screen  ("/")
│   │   └── explore.tsx # Explore screen
│   ├── components/     # Reusable UI components
│   ├── constants/      # Colors, theme
│   └── hooks/          # Custom hooks
└── assets/             # Images, icons, fonts
```

## Useful commands

| Command | What it does |
|---|---|
| `npm start` | Start the dev server |
| `npm run web` | Open in browser |
| `npm run android` | Open on Android emulator/device |
| `npm run lint` | Check code style |

## Next steps — ideas to build
- Rename the app in `app.json` (`"name"` field)
- Add new screens: create a file in `src/app/` (e.g. `profile.tsx` → route `/profile`)
- Add a bottom tab navigator
- Connect a backend (Firebase / Supabase)
