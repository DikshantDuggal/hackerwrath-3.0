# Setup and implementation plan

## Architecture decision

Use uv workspaces plus Gradle. This fits the selected Python backend and Kotlin
frontend directly. Shared Python packages use editable workspace dependencies and
one lockfile. Kotlin consumes generated contracts as a local Gradle subproject.
No shared web UI package or SQL types are appropriate before a web app or database
exists. A separate deployed worker adds coordination overhead to the in-memory MVP.

Initial deployment is a single always-on Linux container with HTTPS/WSS terminated
by Render or Railway. Keep one process/replica until sessions and event delivery
are externalized; horizontal scaling currently loses routing consistency.

## Exact initialization and team commands

The files are already initialized in this checkout, which already had an empty
Git repository. No commit or remote was created. When copying this scaffold to a
new directory without Git, initialize it with:

```sh
git init -b main
```

From the repository root, after installing uv and GNU Make:

```sh
uv python install 3.12.13
uv sync --all-packages --locked
uv run python scripts/contracts.py
uv run pytest
make dev-api
```

`make setup` combines sync and contract generation. No `.env` file is required.
Optional local environment overrides:

```sh
EDGERUNNERS_HOST=127.0.0.1 EDGERUNNERS_PORT=8001 make dev-api
```

`.env.example` is documentation, not an automatically loaded dotenv file. Environment
variables are inherited by the supervisor. Keep it bound to loopback for development.
The Docker startup binds to `0.0.0.0` and uses the hosting platform's `PORT` instead.

Android setup (JDK 21 selected in Android Studio or `JAVA_HOME`):

```sh
sdkmanager 'platforms;android-36' 'build-tools;35.0.0' 'platform-tools'
sdkmanager --licenses
make dev
make android-install
```

Use an emulator or a consented USB-debugging phone for installation. Build tools
and SDK licenses must be installed/accepted by the developer. The Gradle 8.13
wrapper downloads its distribution and checks its official SHA-256. AGP 8.13.0,
Kotlin/Compose compiler 2.2.20 and Compose BOM 2025.09.00 are pinned in the catalog.
JDK 21 runs Gradle and the toolchain; both modules emit JVM 17 bytecode.

Outputs:

- `dist/`: API, detection and contracts wheels and source archives.
- `apps/android/app/build/outputs/apk/debug/app-debug.apk`: installable debug app.
- `packages/contracts/generated/`: committed, reproducible wire artifacts.

A release signing key is deliberately not invented. Team debug APKs work without one;
store distribution needs an actual signing setup and provider integrations.

## Dependency wiring

Root `pyproject.toml` declares these workspace members:

```toml
[tool.uv.workspace]
members = ["apps/api", "packages/contracts", "packages/detection"]
```

The API imports `edgerunners_contracts` and `edgerunners_detection`. Its complete
local-package mapping is:

```toml
[tool.uv.sources]
edgerunners-contracts = { workspace = true }
edgerunners-detection = { workspace = true }
```

Detection has its own `edgerunners-contracts = { workspace = true }` mapping.
Run `uv sync --all-packages --locked` at the root; no `PYTHONPATH` hacks or manual
editable installs are needed. Use `uv add --package edgerunners-api twilio` when
implementing Twilio, and commit the resulting manifest and lockfile change. Provider
SDKs and model names have not been guessed or installed ahead of implementation.
A provider-neutral async detector protocol leaves the AI vendor undecided.

Gradle `settings.gradle.kts` maps the shared module:

```kotlin
include(":app", ":contracts")
project(":contracts").projectDir = file("../../packages/contracts/android")
```

The app links it with `implementation(project(":contracts"))`. The contracts module
compiles `../generated/kotlin` and uses Kotlin serialization. Edit Pydantic models,
then run `make contracts`. JSON Schema is emitted for WarningEvent and Assessment;
Kotlin currently emits WarningEvent and its referenced enums, since Assessment stays
backend-only. The small generator intentionally rejects unsupported property types;
extend it with tests when adding new wire types. Python performs authoritative
validation. Kotlin serializers do not enforce schema ranges, lengths or cross-field
policy, so the future event consumer must also validate session/revision/state.

Generated artifacts are committed for Android-only developers. `make check` and CI
reject stale artifacts without rewriting them. `make dev` regenerates them after
contract source changes while the Android continuous build observes the output.

## Commands

| Command | Effect |
|---|---|
| `make setup` | Install locked workspace + dev tools; generate contracts |
| `make dev-api` | API autoreload and contract watcher |
| `make dev` | Same plus continuous Android assembly |
| `make api` | Only API autoreload |
| `make contracts` | Generate Kotlin + JSON Schema |
| `make contracts-check` | Reject drift without modifying artifacts |
| `make build` | Generate, then build Python and Android concurrently |
| `make check` | Contract drift, Python syntax, pytest |
| `make android-install` | Generate contracts and install debug APK |

## Fast implementation sequence

1. **Call probe:** add signed Twilio incoming/status webhooks, explicit participant
   mapping, Voice SDK integration and authenticated short-lived token issuance.
   Prove a controlled two-way call on the demo phone before adding enforcement.
2. **Audio probe:** validate the Twilio WSS handshake and stream identity. Fork only
   the untrusted caller leg. Use bounded queues and separate asynchronous loops;
   adapt 8 kHz mu-law payloads to the currently documented Sarvam envelope. Measure
   Hindi, Punjabi and English partial transcripts with real account access.
3. **Detection:** expand phrase patterns against observed scripts/code-switching;
   implement one provider adapter behind ContextDetector. Add constrained output
   validation, deterministic policy, call/revision checks, timeout handling and
   account-wide rate limits before emitting confirmed warnings.
4. **App event path:** authenticate warning delivery; validate sequence and session;
   connect reviewed localized resources, vibration, Continue and End actions.
   Current translations are starter text requiring fluent-speaker review; no audio
   clips are supplied or claimed reviewed. Implement proper foreground microphone
   permissions/services only alongside the actual Voice SDK flow.
5. **Evidence:** build at least 30 human-reviewed scenarios across the three
   languages, including benign examples, prompt injection and held-out cases.
   Measure warning median/p95, disconnects, duplicate webhooks, stale assessments,
   hang-up and mute-state preservation. The included English tests are scaffold
   checks, not a multilingual evaluation or accuracy claim.

Optional hold/private announcements follow ordinary alerts. Carrier forwarding,
phone provisioning, AI provider, authentication and consent/retention choices remain
explicit integration decisions. LiveKit is an alternative architecture, not included.

## Secrets and deployments

No fake provider keys, fixed demo token, model identifier or deployment URL is used.
The scaffold starts without secrets because provider operations are unimplemented;
`/readyz` stays unavailable. Add real provider secrets through hosting environment
settings after implementing adapters; never put them into Android resources or Git.

Twilio integration will need account SID, auth token, API key SID/secret, a TwiML app,
number and authorized SDK identity mapping. Sarvam needs a real account key and
verified endpoint/model configuration. Incoming SDK delivery may require FCM setup.
These account-specific values cannot truthfully be supplied in repository files.

Push this repository to the team's actual remote. In Render choose New Blueprint
and select the repo; it reads `render.yaml`. On Railway create a project from the
repo; `railway.toml` chooses Docker and health checking. The Docker context is always
the repository root so sibling workspace packages and `uv.lock` are available.
Use one always-on instance, verify HTTPS/WSS and set real provider URLs only after
the hostname exists. Deploying the bootstrap creates a healthy process, not a working
protected-call service. Active calls need reconnect handling because redeploys and
network interruptions can terminate sockets.

## Official references checked for the scaffold

- uv workspaces: https://docs.astral.sh/uv/concepts/projects/workspaces/
- AGP compatibility: https://developer.android.com/build/releases/agp-8-13-0-release-notes
- Kotlin Compose compiler: https://developer.android.com/jetpack/androidx/releases/compose-kotlin
- Gradle wrapper: https://docs.gradle.org/8.13/userguide/gradle_wrapper.html
- Render Blueprint: https://render.com/docs/blueprint-spec
- Render WebSockets: https://render.com/docs/websocket
- Twilio Android integration: https://www.twilio.com/docs/voice/sdks/android

Provider streaming wire formats and permissions must be rechecked against official
SDK documentation when their implementations begin.

## Verification in this workspace

- Eight scaffold tests passed with the available Python 3.14.8 environment
  (FastAPI 0.141.1, Pydantic 2.14.1, pytest 9.1.1, HTTPX 0.28.1).
- Generated contract drift checking, Python compilation, TOML parsing and Android
  XML parsing passed.
- `uv build --all-packages --offline` successfully built wheels and source archives
  for all three packages using the configured Python 3.12 toolchain.
- The Python 3.12 dependency lockfile was resolved. Full locked runtime installation
  was not verified because provider download connections repeatedly stalled.
- The Android build did not run: the wrapper download timed out before compilation.
  This machine also has SDK 37 installed rather than the requested SDK 36.
- Docker execution was not verified because the sandbox could not access the local
  Docker socket. No Docker image or hosting service was deployed.

Run `make setup`, `make check`, and `make build` with normal package-network access
and the documented Android SDK/JDK before relying on the complete toolchain.
