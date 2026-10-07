# Brahma Connect for Android

Native Android apps for Brahma AI Evo, built as two installable editions:

- **Companion** pairs with the Brahma desktop gateway over a persistent WebSocket connection.
- **Mobile** runs standalone and connects directly to supported AI providers, with supported phone actions.

Both editions are native Android apps, not ports of the Windows desktop UI. The mobile edition can send prompts to Google Gemini, OpenAI, Anthropic, OpenRouter, Groq, DeepSeek, Mistral, Together AI, Fireworks AI, xAI, or Cerebras. Provider API keys are stored using Android encrypted preferences, and each provider's model ID can be changed in Mobile setup.

Mobile chat currently exposes 16 callable phone actions for device information, battery, flashlight, media volume, installed apps, web links, Maps, sharing, SMS/email drafts, calendar event drafts, alarms, and selected Android settings. These capabilities are also advertised to the paired Brahma desktop gateway. Communication-oriented actions open the relevant Android app for the user to review; the app does not silently send messages or create calendar entries.

The mobile edition also includes a searchable library of 200 categorized assistant workflows: 100 coding workflows across 20 languages, plus game/performance, apps/system, file-organization, and learning/productivity workflows. Selecting one prepares a task prompt; the model can explain, write, review, or plan, but the card does not grant arbitrary desktop access or silently mutate files/processes. Only actions listed as callable phone tools execute directly.

Both editions support six saved color themes, four short Compose boot animations, and four speech presets. Speech uses the Android Text-to-Speech engine; “Get voices” opens the device's system TTS settings so users can install voices from their selected engine. No third-party voice files are bundled or fetched by Brahma.

Build requirements:
- Android Studio or Android Gradle Plugin toolchain
- JDK 17
- Android SDK 35

Build the installable debug APKs from this directory:
```bash
bash gradlew --no-daemon :app:assembleCompanionDebug :app:assembleMobileDebug
```

Run the local pairing-payload tests with:
```bash
bash gradlew --no-daemon :app:testCompanionDebugUnitTest
```

GitHub Actions publishes both APKs in the `Brahma-Evo-Android-APKs` artifact and attaches them to releases for `v*` or legacy `android-v*` tags. Pairing QR codes must contain a valid, unexpired `_BRAHMA._tcp.local.` offer. Manual gateway addresses accept a hostname or IP address and a port from 1 to 65535.
