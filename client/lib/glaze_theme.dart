import 'dart:ui';

import 'package:flutter/material.dart';

/// GoreeCloud Notify native consumer mapping for Glaze UI 1.6.0.
///
/// This is a repository-local source adoption candidate, not a completed
/// conformance or production claim. Presentation resolves only from bounded
/// Flutter/runtime/accessibility state and never manufactures authorization,
/// permission, privacy, security, identity, or service truth.
enum GlazeMaterialRole {
  canvas,
  surface,
  softGlaze,
  glaze,
  deepGlaze,
  liveGlaze,
}

abstract final class GlazeTokens {
  static const String stableVersion = '1.6.0';
  static const String reviewedImplementationAnchor =
      'a7180679ea851389e0f3004515f9a25f420e716d';
  static const String sourceQualificationAnchor =
      'c7509c79256b04b0aa67cb9dd0737d7588e0ae4a';

  static const double radiusSmall = 12;
  static const double radiusMedium = 16;
  static const double radiusControl = 18;
  static const double radiusLarge = 24;
  static const double radiusXLarge = 30;
  static const double radiusPill = 999;

  // V1.6.0 preserves the accepted ergonomic target floors while extending semantic state/recovery governance.
  static const double targetMin = 48;
  static const double targetComfortable = 48;
  static const double targetTouchAssistance = 56;
  static const double targetFarView = 56;

  static const double space1 = 4;
  static const double space2 = 8;
  static const double space3 = 12;
  static const double space4 = 16;
  static const double space5 = 20;
  static const double space6 = 24;
  static const double space8 = 32;
  static const double space10 = 40;
  static const double space12 = 48;

  static const Color accent = Color(0xFF5D66B8);
  static const Color accentStrong = Color(0xFF4A54A2);
  static const Color info = Color(0xFF3F78C5);
  static const Color warning = Color(0xFFB87525);
  static const Color danger = Color(0xFFB65361);
  static const Color success = Color(0xFF3E8B6B);

  static double effectiveTarget({
    bool touchAssistance = false,
    bool farView = false,
  }) {
    if (touchAssistance) return targetTouchAssistance;
    if (farView) return targetFarView;
    return targetMin;
  }
}


enum GlazeNativePaneMode { single, stacked, split }

enum GlazeNativeControlDensity { compact, standard, comfortable }

enum GlazeNativeMaterialPreference { glaze, solidAccessible }

enum GlazeNativeMotionPreference { standard, reduced }

enum GlazeCapabilityState {
  available,
  degraded,
  temporarilyUnavailable,
  restricted,
  unsupported,
  unknown,
}

@immutable
class GlazeNativePresentationResolution {
  const GlazeNativePresentationResolution({
    required this.paneMode,
    required this.controlDensity,
    required this.materialPreference,
    required this.motionPreference,
    required this.largeText,
    required this.highContrast,
  });

  final GlazeNativePaneMode paneMode;
  final GlazeNativeControlDensity controlDensity;
  final GlazeNativeMaterialPreference materialPreference;
  final GlazeNativeMotionPreference motionPreference;
  final bool largeText;
  final bool highContrast;

  static GlazeNativePresentationResolution fromContext(BuildContext context) {
    final media = MediaQuery.of(context);
    final width = media.size.width;
    final largeText = media.textScaler.scale(16) >= 20;
    final paneMode = width < 600
        ? GlazeNativePaneMode.single
        : width < 980
            ? GlazeNativePaneMode.stacked
            : GlazeNativePaneMode.split;
    return GlazeNativePresentationResolution(
      paneMode: paneMode,
      controlDensity: largeText
          ? GlazeNativeControlDensity.comfortable
          : paneMode == GlazeNativePaneMode.single
              ? GlazeNativeControlDensity.compact
              : GlazeNativeControlDensity.standard,
      materialPreference: media.highContrast
          ? GlazeNativeMaterialPreference.solidAccessible
          : GlazeNativeMaterialPreference.glaze,
      motionPreference: media.disableAnimations
          ? GlazeNativeMotionPreference.reduced
          : GlazeNativeMotionPreference.standard,
      largeText: largeText,
      highContrast: media.highContrast,
    );
  }

  bool get authorizationInferred => false;
  bool get permissionGrantedByGlaze => false;
  bool get automaticNavigationAllowed => false;
  bool get automaticPermissionRequestAllowed => false;
  bool get automaticConsequentialExecutionAllowed => false;
  bool get telemetryRequired => false;
  bool get remoteAnalysisRequired => false;
}

@immutable
class GlazeCapabilityPresentation {
  const GlazeCapabilityPresentation({
    required this.state,
    required this.explanation,
    this.userInitiatedRecovery,
  });

  final GlazeCapabilityState state;
  final String explanation;
  final String? userInitiatedRecovery;

  static GlazeCapabilityPresentation systemAlerts(
    GlazeCapabilityState state,
  ) {
    switch (state) {
      case GlazeCapabilityState.available:
        return const GlazeCapabilityPresentation(
          state: GlazeCapabilityState.available,
          explanation:
              'Android reports persistent system alerts as enabled for this client.',
        );
      case GlazeCapabilityState.restricted:
        return const GlazeCapabilityPresentation(
          state: GlazeCapabilityState.restricted,
          explanation:
              'Android did not grant notification permission. Change the platform permission before retrying.',
          userInitiatedRecovery: 'open-platform-permission-or-retry',
        );
      case GlazeCapabilityState.unsupported:
        return const GlazeCapabilityPresentation(
          state: GlazeCapabilityState.unsupported,
          explanation:
              'Persistent Android background alerts are not available on this platform.',
        );
      case GlazeCapabilityState.degraded:
      case GlazeCapabilityState.temporarilyUnavailable:
        return GlazeCapabilityPresentation(
          state: state,
          explanation:
              'System alerts are temporarily unavailable. The authenticated Notify inbox remains available.',
          userInitiatedRecovery: 'retry',
        );
      case GlazeCapabilityState.unknown:
        return const GlazeCapabilityPresentation(
          state: GlazeCapabilityState.unknown,
          explanation:
              'System-alert permission has not been established. Notify will request it only after you choose Enable.',
          userInitiatedRecovery: 'request-permission',
        );
    }
  }

  bool get permissionGrantedByGlaze => false;
  bool get automaticExecutionAllowed => false;
}

ThemeData glazeTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme = ColorScheme.fromSeed(
    seedColor: GlazeTokens.accent,
    brightness: brightness,
    surface: dark ? const Color(0xFF17181E) : const Color(0xFFF9F8FC),
  );

  final canvas = dark ? const Color(0xFF101116) : const Color(0xFFF4F2F8);
  final raised = dark ? const Color(0xFF202129) : const Color(0xFFFEFCFF);
  final outline = dark ? const Color(0xFF373942) : const Color(0xFFE0DDE8);

  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: scheme.copyWith(
      primary: dark ? const Color(0xFFAEB6FF) : GlazeTokens.accent,
      onPrimary: dark ? const Color(0xFF20285E) : Colors.white,
      surface: raised,
      outline: outline,
      outlineVariant: outline.withValues(alpha: .68),
    ),
    scaffoldBackgroundColor: canvas,
    canvasColor: canvas,
    dividerColor: outline.withValues(alpha: .72),
    textTheme: ThemeData(brightness: brightness).textTheme.copyWith(
      headlineLarge: TextStyle(
        fontSize: 38,
        height: 1.08,
        fontWeight: FontWeight.w700,
        letterSpacing: -1.2,
        color: dark ? const Color(0xFFF5F3FA) : const Color(0xFF202027),
      ),
      headlineMedium: TextStyle(
        fontSize: 30,
        height: 1.12,
        fontWeight: FontWeight.w700,
        letterSpacing: -.7,
        color: dark ? const Color(0xFFF5F3FA) : const Color(0xFF202027),
      ),
      titleLarge: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
      titleMedium: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      bodyLarge: const TextStyle(fontSize: 16, height: 1.5),
      bodyMedium: const TextStyle(fontSize: 14, height: 1.45),
      labelLarge: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      margin: EdgeInsets.zero,
      color: raised,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusLarge),
        side: BorderSide(color: outline.withValues(alpha: .74)),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: dark ? const Color(0xFF1E2027) : const Color(0xFFFBF9FD),
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusControl),
        borderSide: BorderSide(color: outline),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusControl),
        borderSide: BorderSide(color: outline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(GlazeTokens.radiusControl),
        borderSide: BorderSide(color: scheme.primary, width: 2),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(GlazeTokens.targetMin, GlazeTokens.targetComfortable),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusPill)),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        minimumSize: const Size(GlazeTokens.targetMin, GlazeTokens.targetMin),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusPill)),
      ),
    ),
    chipTheme: ChipThemeData(
      side: BorderSide(color: outline),
      backgroundColor: dark ? const Color(0xFF24262E) : const Color(0xFFF7F5FA),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusPill)),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
    ),
    appBarTheme: const AppBarTheme(
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      backgroundColor: Colors.transparent,
      surfaceTintColor: Colors.transparent,
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusMedium)),
    ),
    dialogTheme: DialogThemeData(
      elevation: 12,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(GlazeTokens.radiusXLarge)),
    ),
  );
}

class GlazeChrome extends StatelessWidget {
  const GlazeChrome({super.key, required this.child, this.padding = EdgeInsets.zero});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    final border = Theme.of(context).colorScheme.outlineVariant;
    final resolution = GlazeNativePresentationResolution.fromContext(context);
    final solid =
        resolution.materialPreference == GlazeNativeMaterialPreference.solidAccessible;
    final surface = DecoratedBox(
      decoration: BoxDecoration(
        color: solid
            ? (dark ? const Color(0xFF252731) : Colors.white)
            : (dark ? const Color(0xFF252731) : Colors.white)
                .withValues(alpha: dark ? .72 : .76),
        borderRadius: BorderRadius.circular(GlazeTokens.radiusXLarge),
        border: Border.all(color: border.withValues(alpha: solid ? 1 : .7)),
        boxShadow: solid
            ? const []
            : [
                BoxShadow(
                  color: Colors.black.withValues(alpha: dark ? .24 : .08),
                  blurRadius: 28,
                  offset: const Offset(0, 12),
                ),
              ],
      ),
      child: Padding(padding: padding, child: child),
    );

    return ClipRRect(
      borderRadius: BorderRadius.circular(GlazeTokens.radiusXLarge),
      child: solid
          ? surface
          : BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
              child: surface,
            ),
    );
  }
}
