# Edgerunners

Android call-safety hackathon monorepo: Kotlin + Compose, FastAPI, Python phrase checks,
and an asynchronous AI adapter boundary. Twilio is the selected call transport and
Sarvam the selected STT service; both still need integration. No database is needed.

The repository began empty. This scaffold runs a health API and an Android setup screen;
it does not yet place calls, transcribe audio, authenticate users, or protect live calls.
The source project brief is preserved in `PROJECT_CONTEXT.md` as design context.

## Layout

```text
.
├── apps/
│   ├── api/
│   │   ├── pyproject.toml
│   │   └── src/edgerunners_api/main.py
│   └── android/
│       ├── app/src/main/             # Compose activity, manifest, en/hi/pa strings
│       ├── app/build.gradle.kts
│       ├── build.gradle.kts
│       ├── settings.gradle.kts       # includes shared :contracts project
│       ├── gradle/libs.versions.toml
│       ├── gradle/wrapper/
│       ├── gradlew
│       └── gradlew.bat
├── packages/
│   ├── contracts/
│   │   ├── src/edgerunners_contracts/__init__.py  # source of truth
│   │   ├── generated/               # committed JSON Schema + Kotlin models
│   │   ├── android/build.gradle.kts  # shared Kotlin JVM library
│   │   └── pyproject.toml
│   └── detection/
│       ├── src/edgerunners_detection/
│       │   ├── phrases.py           # English starter advisories only
│       │   └── adapter.py           # async AI protocol; unavailable by default
│       └── pyproject.toml
├── scripts/                         # contract export and process supervisor
├── tests/                           # health, wire validation, phrase examples
├── docs/SETUP.md                     # commands, dependency links, delivery plan
├── .github/workflows/ci.yml
├── .env.example                     # working local defaults; no dummy secrets
├── .python-version
├── pyproject.toml
├── uv.lock
├── Makefile
├── Dockerfile
├── render.yaml
└── railway.toml
```

## Start

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), GNU Make,
JDK 21, and Android Studio with Android SDK 36 and Build Tools 35.0.0.
Use Python 3.12.13 (uv can install it). Point `JAVA_HOME` at JDK 21 and `ANDROID_HOME`
at your SDK. Android Studio can also write its untracked `local.properties`.

```sh
uv python install 3.12.13
make setup
make dev-api
```

API: http://127.0.0.1:8000/docs. `/healthz` returns 200 for process health;
`/readyz` intentionally returns 503 while live protection is unimplemented.

```sh
make dev                # API + contract watcher + continuous Android APK build
make android-install    # install debug APK on a running emulator/USB device
make build              # contract export, Python wheels/sdists + Android APK in parallel
make check              # generated-file drift, Python syntax, tests
```

`make dev` requires the Android toolchain. Android continuous builds produce a new
APK after source changes; install it again to update the running app. Compose does
not get browser-style hot reload from this command. Open `apps/android` in Android
Studio for Run/Apply Changes. Ctrl+C stops the development processes together.

No Node, pnpm, Turbo, web frontend, database, or separate remote worker is required.
The Android app is the frontend. Keep audio/session work inside the single API
process initially so in-memory state and queues stay together.

## Deployment

Deploy the root Dockerfile on Render using `render.yaml`, or Railway using
`railway.toml`. Render selects a paid Starter instance to avoid free-service sleeping.
Use one instance and one Uvicorn worker for in-memory call state. The process reads
`PORT`; `/healthz` is the infrastructure health check. Deployment does not establish
provider readiness. The scaffold currently has no public voice-control routes.

```sh
docker build -t edgerunners-api .
docker run --rm -p 8000:8000 edgerunners-api
```

Do not use Vercel functions for the persistent audio server. Android APKs are built
with Gradle and distributed separately. No cloud resources are created by this scaffold.

See [the complete setup and implementation plan](docs/SETUP.md) for exact dependency
links, commands, provider configuration boundaries, and next milestones.
