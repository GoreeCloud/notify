# GoreeCloud Notify — Dependencies and Attribution

No upstream ntfy server or Android source was copied. ntfy API and documentation served as product research references only. The server is newly authored Go code with no third-party Go module dependencies.

## Included / resolved technology

| Component | Source | License and conditions | Use |
| --- | --- | --- | --- |
| GoreeCloud UI | https://github.com/GoreeCloud/gc-ui — pinned commit `c833c6cbb291e866ce25ee53c49afa00dad73130` | MIT; notice retained in `docs/licenses/gc-ui-MIT.txt` | Web CSS source via Git dependency and vendored Android palette/theme snapshot |
| React + React DOM | https://github.com/facebook/react | MIT | Web client |
| Vite | https://github.com/vitejs/vite | MIT | Web build/dev tooling |
| Qt Quick / Qt Network / Qt Quick Controls 2 | https://www.qt.io/ | Predominantly LGPLv3/GPLv3/commercial; module-specific terms and relinking duties apply | Linux native client (not copied or bundled in source) |
| Kotlin, Android Gradle plugin, AndroidX Compose Material 3 | https://developer.android.com/jetpack/compose | Kotlin Apache-2.0; AndroidX Apache-2.0; Google tooling has component-specific terms | Android native client |
| Go standard library | https://go.dev/ | BSD-style Go license | Notification service |

The Apache-2.0 license in the repository covers only original GoreeCloud-authored source. The MIT-licensed GoreeCloud UI snapshot remains MIT-licensed and retains its upstream notice. Runtime/framework licenses and required notices apply independently. Before distribution, perform a complete transitive-dependency and Gradle/Qt packaging review, including LGPLv3 dynamic linking and relinking obligations.

## Compatibility research

- ntfy publish: https://docs.ntfy.sh/publish/
- ntfy subscribe stream: https://docs.ntfy.sh/subscribe/api/
- Qt 6.12 licensing: https://doc.qt.io/qt-6.12/licensing.html
- Android Compose Material 3: https://developer.android.com/jetpack/androidx/releases/compose-material3

Research does not constitute API equivalence, certification, or permission to copy GPL-only source into differently licensed code.
