UV ?= uv
.PHONY: setup dev dev-api api contracts contracts-check build build-python build-android check test android-install
setup:
	$(UV) sync --all-packages --locked
	$(UV) run --locked python scripts/contracts.py
contracts:
	$(UV) run --locked python scripts/contracts.py
contracts-check:
	$(UV) run --locked python scripts/contracts.py --check
api:
	$(UV) run --locked --package edgerunners-api uvicorn edgerunners_api.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir apps/api/src --reload-dir packages
# Android continuously assembles; install on a device with make android-install.
dev:
	$(UV) run --locked python scripts/dev.py --android
dev-api:
	$(UV) run --locked python scripts/dev.py
build: contracts
	$(MAKE) -j2 build-python build-android
build-python:
	$(UV) build --all-packages
build-android:
	cd apps/android && ./gradlew :app:assembleDebug
android-install: contracts
	cd apps/android && ./gradlew :app:installDebug
check: contracts-check
	$(UV) run --locked python -m compileall -q apps/api/src packages/contracts/src packages/detection/src scripts
	$(UV) run --locked pytest
test:
	$(UV) run --locked pytest
