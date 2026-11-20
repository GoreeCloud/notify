.PHONY: test vet server web-build linux-build android-build

test:
	go test -race ./...

vet:
	go vet ./...

server:
	go run ./cmd/notifyd

web-build:
	cd web && npm ci && npm run build

linux-build:
	cmake -S linux -B build/linux
	cmake --build build/linux

android-build:
	cd android && ./gradlew :app:assembleDebug
