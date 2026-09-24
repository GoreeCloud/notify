export const GLAZE_UI_VERSION = '1.6.0' as const
export const GLAZE_UI_REVIEWED_IMPLEMENTATION_ANCHOR = 'a7180679ea851389e0f3004515f9a25f420e716d' as const
export const GLAZE_UI_SOURCE_QUALIFICATION_ANCHOR = 'c7509c79256b04b0aa67cb9dd0737d7588e0ae4a' as const

export type NotifyGlazeServiceState = 'available' | 'unavailable' | 'unknown'
export type NotifyGlazeStreamState = 'idle' | 'connecting' | 'live' | 'reconnecting' | 'offline'
export type NotifyGlazeNotificationPermission = NotificationPermission | 'unsupported'
export type NotifyGlazeCapabilityState =
  | 'available'
  | 'degraded'
  | 'temporarily-unavailable'
  | 'offline'
  | 'permission-required'
  | 'restricted'
  | 'unsupported'
  | 'disabled'
  | 'unknown'

export type NotifyGlazeEnvironment = {
  viewportWidth: number
  reducedMotion: boolean
  reducedTransparency: boolean
  increasedContrast: boolean
  forcedColors: boolean
  serviceState: NotifyGlazeServiceState
  streamState: NotifyGlazeStreamState
  notificationPermission: NotifyGlazeNotificationPermission
  notificationsEnabled: boolean
}

export type NotifyGlazeResolution = {
  version: typeof GLAZE_UI_VERSION
  lifecycle: 'stable-consumer-adoption-candidate'
  paneMode: 'single' | 'stacked' | 'split'
  controlDensity: 'compact' | 'standard' | 'comfortable'
  materialPreference: 'glaze' | 'reduced-optical' | 'solid-accessible'
  motionPreference: 'standard' | 'reduced'
  connectivityPresentation: 'live' | 'connecting' | 'degraded' | 'offline' | 'idle'
  capabilities: {
    service: NotifyGlazeCapabilityState
    realtime: NotifyGlazeCapabilityState
    systemAlerts: NotifyGlazeCapabilityState
  }
  systemAlertsRecovery: null | {
    kind: 'request-permission'
    userInitiated: true
    automaticExecutionAllowed: false
  }
  authority: {
    glazeAuthority: 'presentation-only'
    authorizationInferred: false
    permissionGranted: false
    providerPrecedenceInferred: false
    operationalAuthorityGranted: false
    automaticNavigationAllowed: false
    automaticPermissionRequestAllowed: false
    automaticConsequentialExecutionAllowed: false
    automaticFallbackExecutionAllowed: false
  }
  privacy: {
    telemetryRequired: false
    remoteAnalysisRequired: false
    rawNotificationContentIncluded: false
    providerIdentityIncluded: false
  }
}

function serviceCapability(state: NotifyGlazeServiceState): NotifyGlazeCapabilityState {
  if (state === 'available') return 'available'
  if (state === 'unavailable') return 'temporarily-unavailable'
  return 'unknown'
}

function realtimeCapability(state: NotifyGlazeStreamState): NotifyGlazeCapabilityState {
  if (state === 'live') return 'available'
  if (state === 'connecting' || state === 'reconnecting') return 'degraded'
  if (state === 'offline') return 'offline'
  if (state === 'idle') return 'disabled'
  return 'unknown'
}

function systemAlertsCapability(
  permission: NotifyGlazeNotificationPermission,
  enabled: boolean,
): NotifyGlazeCapabilityState {
  if (permission === 'unsupported') return 'unsupported'
  if (permission === 'denied') return 'restricted'
  if (permission === 'default') return 'permission-required'
  return enabled ? 'available' : 'disabled'
}

export function resolveNotifyGlazePresentation(
  environment: NotifyGlazeEnvironment,
): NotifyGlazeResolution {
  const paneMode = environment.viewportWidth < 600
    ? 'single'
    : environment.viewportWidth < 1024
      ? 'stacked'
      : 'split'

  const accessibilityPriority = environment.forcedColors
    || environment.reducedTransparency
    || environment.increasedContrast

  const materialPreference: NotifyGlazeResolution['materialPreference'] = accessibilityPriority
    ? 'solid-accessible'
    : environment.streamState === 'reconnecting'
      ? 'reduced-optical'
      : 'glaze'

  const controlDensity: NotifyGlazeResolution['controlDensity'] = paneMode === 'single'
    ? 'compact'
    : environment.increasedContrast
      ? 'comfortable'
      : 'standard'

  const connectivityPresentation: NotifyGlazeResolution['connectivityPresentation'] =
    environment.streamState === 'live'
      ? 'live'
      : environment.streamState === 'connecting'
        ? 'connecting'
        : environment.streamState === 'reconnecting'
          ? 'degraded'
          : environment.streamState === 'offline'
            ? 'offline'
            : 'idle'

  const systemAlerts = systemAlertsCapability(
    environment.notificationPermission,
    environment.notificationsEnabled,
  )

  return Object.freeze({
    version: GLAZE_UI_VERSION,
    lifecycle: 'stable-consumer-adoption-candidate',
    paneMode,
    controlDensity,
    materialPreference,
    motionPreference: environment.reducedMotion ? 'reduced' : 'standard',
    connectivityPresentation,
    capabilities: Object.freeze({
      service: serviceCapability(environment.serviceState),
      realtime: realtimeCapability(environment.streamState),
      systemAlerts,
    }),
    systemAlertsRecovery: systemAlerts === 'permission-required'
      ? Object.freeze({
          kind: 'request-permission',
          userInitiated: true,
          automaticExecutionAllowed: false,
        })
      : null,
    authority: Object.freeze({
      glazeAuthority: 'presentation-only',
      authorizationInferred: false,
      permissionGranted: false,
      providerPrecedenceInferred: false,
      operationalAuthorityGranted: false,
      automaticNavigationAllowed: false,
      automaticPermissionRequestAllowed: false,
      automaticConsequentialExecutionAllowed: false,
      automaticFallbackExecutionAllowed: false,
    }),
    privacy: Object.freeze({
      telemetryRequired: false,
      remoteAnalysisRequired: false,
      rawNotificationContentIncluded: false,
      providerIdentityIncluded: false,
    }),
  })
}
