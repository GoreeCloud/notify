import { useEffect, useMemo, useState } from 'react'
import { useBrowserNotificationsContext } from './BrowserNotificationsContext'
import {
  GLAZE_UI_REVIEWED_IMPLEMENTATION_ANCHOR,
  GLAZE_UI_SOURCE_QUALIFICATION_ANCHOR,
  GLAZE_UI_VERSION,
  resolveNotifyGlazePresentation,
  type NotifyGlazeServiceState,
  type NotifyGlazeStreamState,
} from './glaze-v1.6.0'

type HookOptions = {
  serviceState: NotifyGlazeServiceState
  streamState: NotifyGlazeStreamState
}

type BrowserEnvironment = {
  viewportWidth: number
  reducedMotion: boolean
  reducedTransparency: boolean
  increasedContrast: boolean
  forcedColors: boolean
}

function readBrowserEnvironment(): BrowserEnvironment {
  return {
    viewportWidth: window.innerWidth,
    reducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    reducedTransparency: window.matchMedia('(prefers-reduced-transparency: reduce)').matches,
    increasedContrast: window.matchMedia('(prefers-contrast: more)').matches,
    forcedColors: window.matchMedia('(forced-colors: active)').matches,
  }
}

export default function useNotifyGlazePresentation({
  serviceState,
  streamState,
}: HookOptions) {
  const notifications = useBrowserNotificationsContext()
  const [environment, setEnvironment] = useState<BrowserEnvironment>(readBrowserEnvironment)

  useEffect(() => {
    const queries = [
      window.matchMedia('(prefers-reduced-motion: reduce)'),
      window.matchMedia('(prefers-reduced-transparency: reduce)'),
      window.matchMedia('(prefers-contrast: more)'),
      window.matchMedia('(forced-colors: active)'),
    ]
    const update = () => setEnvironment(readBrowserEnvironment)
    window.addEventListener('resize', update)
    for (const query of queries) query.addEventListener('change', update)
    return () => {
      window.removeEventListener('resize', update)
      for (const query of queries) query.removeEventListener('change', update)
    }
  }, [])

  const resolution = useMemo(() => resolveNotifyGlazePresentation({
    ...environment,
    serviceState,
    streamState,
    notificationPermission: notifications.permission,
    notificationsEnabled: notifications.enabled,
  }), [
    environment,
    notifications.enabled,
    notifications.permission,
    serviceState,
    streamState,
  ])

  useEffect(() => {
    const root = document.documentElement
    root.dataset.glazeUi = GLAZE_UI_VERSION
    root.dataset.glazeUiTarget = GLAZE_UI_VERSION
    root.dataset.glazeUiStatus = 'source-adoption-candidate'
    root.dataset.glazeReviewedAnchor = GLAZE_UI_REVIEWED_IMPLEMENTATION_ANCHOR
    root.dataset.glazeQualificationAnchor = GLAZE_UI_SOURCE_QUALIFICATION_ANCHOR
    root.dataset.glazeAuthority = resolution.authority.glazeAuthority
    root.dataset.glazePaneMode = resolution.paneMode
    root.dataset.glazeControlDensity = resolution.controlDensity
    root.dataset.glazeMaterial = resolution.materialPreference
    root.dataset.glazeMotion = resolution.motionPreference
    root.dataset.glazeConnectivity = resolution.connectivityPresentation
    root.dataset.glazeService = resolution.capabilities.service
    root.dataset.glazeRealtime = resolution.capabilities.realtime
    root.dataset.glazeSystemAlerts = resolution.capabilities.systemAlerts
  }, [resolution])

  return resolution
}
