# A.U.R.O.R.A

**Autonomous Unified Responsive Operating & Reasoning Assistant**

A.U.R.O.R.A is a native desktop voice assistant with a real-time animated HUD,
Gemini Live voice and vision, persistent memory, system telemetry, and an
extensible action/plugin system. The supplied Aurora desktop runtime is the
application entry point; it brings the overlapping assistant code into one
coherent experience rather than launching separate legacy interfaces.

## Capabilities

- Live voice conversation with configurable Gemini voice, microphone, speaker,
  push-to-talk, and optional screen/camera vision.
- Animated holographic face/reactor HUD, live audio response, system metrics,
  clipboard helper, video playback, and event/activity log.
- Persistent memory, session summaries, reminders, proactive briefings, and
  user-configurable assistant identity.
- Discoverable actions for desktop and system controls, app launching, files,
  web search, weather, travel, coding help, video, and YouTube.
- Drop-in plugins, per-plugin settings, guarded actions, undo support, and
  live customization without restarting.
- Six accent presets—Cyber Cyan, Plasma Violet, Solar Ember, Matrix Green,
  Glacier Blue, and Crimson Core—plus a live color wheel and custom hex colors.
- Integrated plugins for calendar scheduling, live-weather briefings, circuit
  schematics, Spotify, video publishing, calorie tracking, and workout tracking.
  Some plugins require service credentials, a connected browser, camera access,
  or other optional integrations.

The broader bundle also contains Android, MCP, geospatial, and server-only
sources. These remain available for reference but are not included in the
Windows desktop executable.

## Run

For a Windows release, download `A.U.R.O.R.A.exe` from the project's GitHub
Releases page and launch it. The first run creates the local configuration
folder and prompts for a Gemini API key. Releases contain only the `.exe`.

For source installation: Python 3.11 or newer, a working microphone/speaker,
and a Gemini API key. From this directory:

```bash
python setup.py
python main.py
```

The first-run setup screen stores the Gemini API key locally in
`config/api_keys.json`. Do not commit that file or share it. The setup script
installs the application/plugin packages in `requirements.txt` and attempts to
install Playwright's Chromium and Firefox browsers for browser automation.
Packaged browser automation uses locally installed browsers (such as Edge or
Chrome); browser binaries are not embedded in the single-file executable.

For microphone, screen, or camera access on macOS/Linux, grant the relevant OS
permissions to the terminal/application. Linux desktop actions may also need
native tools such as `xdg-utils`, `pactl`, or `brightnessctl`.

## Optional integrations

- Wake-word mode: enable it in **Controls** and follow the in-app installer.
  The available pretrained model listens for the legacy phrase **“Hey Jarvis”**;
  it does not listen for “Hey A.U.R.O.R.A.” The feature is opt-in.
- Browser automation: source setup installs Playwright and its Chromium and
  Firefox engines. The Windows executable uses compatible browsers installed
  on the user's system.
- Remote dashboard: install `fastapi`, `uvicorn[standard]`, `cryptography`, and
  `python-multipart` if using dashboard routes that depend on those packages.
- Plugins with missing optional credentials or integrations report unavailable
  status rather than blocking application startup.

## Extending A.U.R.O.R.A.

Place a Python action in `actions/` and expose a module-level `TOOL` dictionary
with a valid name, description, Gemini-compatible `OBJECT` parameters, and a
callable handler. Plugins in `plugins/` use a `PLUGIN` dictionary and a
`run(parameters, ...)` function. See `core/action_loader.py`,
`core/plugin_loader.py`, and `plugins/_template.py` for the contracts and
validation behavior.

The desktop application is launched from `main.py`; settings and user data live
under `config/`, while persistent memory is managed by `memory/`.
