import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:goreecloud_notify_client/glaze_theme.dart';

void main() {
  test('Glaze UI 1.6.0 identity and authority anchors are exact', () {
    expect(GlazeTokens.stableVersion, '1.6.0');
    expect(
      GlazeTokens.reviewedImplementationAnchor,
      'a7180679ea851389e0f3004515f9a25f420e716d',
    );
    expect(
      GlazeTokens.sourceQualificationAnchor,
      'c7509c79256b04b0aa67cb9dd0737d7588e0ae4a',
    );
  });

  testWidgets(
    'native presentation gives accessibility state precedence without authority escalation',
    (tester) async {
      late GlazeNativePresentationResolution resolution;

      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(
              size: Size(520, 900),
              highContrast: true,
              disableAnimations: true,
              textScaler: TextScaler.linear(1.4),
            ),
            child: Builder(
              builder: (context) {
                resolution =
                    GlazeNativePresentationResolution.fromContext(context);
                return const SizedBox();
              },
            ),
          ),
        ),
      );

      expect(resolution.paneMode, GlazeNativePaneMode.single);
      expect(
        resolution.controlDensity,
        GlazeNativeControlDensity.comfortable,
      );
      expect(
        resolution.materialPreference,
        GlazeNativeMaterialPreference.solidAccessible,
      );
      expect(
        resolution.motionPreference,
        GlazeNativeMotionPreference.reduced,
      );
      expect(resolution.authorizationInferred, isFalse);
      expect(resolution.permissionGrantedByGlaze, isFalse);
      expect(resolution.automaticNavigationAllowed, isFalse);
      expect(resolution.automaticPermissionRequestAllowed, isFalse);
      expect(resolution.automaticConsequentialExecutionAllowed, isFalse);
      expect(resolution.telemetryRequired, isFalse);
      expect(resolution.remoteAnalysisRequired, isFalse);
    },
  );

  test('system-alert capability never grants permission or executes recovery', () {
    final unknown = GlazeCapabilityPresentation.systemAlerts(
      GlazeCapabilityState.unknown,
    );
    expect(unknown.state, GlazeCapabilityState.unknown);
    expect(unknown.userInitiatedRecovery, 'request-permission');
    expect(unknown.permissionGrantedByGlaze, isFalse);
    expect(unknown.automaticExecutionAllowed, isFalse);

    final restricted = GlazeCapabilityPresentation.systemAlerts(
      GlazeCapabilityState.restricted,
    );
    expect(restricted.state, GlazeCapabilityState.restricted);
    expect(restricted.userInitiatedRecovery, isNotNull);
    expect(restricted.permissionGrantedByGlaze, isFalse);
    expect(restricted.automaticExecutionAllowed, isFalse);
  });
}
