import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { BrowserNotificationsProvider } from './BrowserNotificationsContext'
import './styles.css'
import './glaze-contract.css'
import './glaze-resilience.css'

// Repository-local Glaze UI 1.6.0 adoption candidate. Runtime context is resolved in useGlazePresentation.
document.documentElement.dataset.glazeUi = '1.6.0'
document.documentElement.dataset.glazeUiTarget = '1.6.0'
document.documentElement.dataset.glazeUiStatus = 'source-adoption-candidate'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserNotificationsProvider>
      <App />
    </BrowserNotificationsProvider>
  </StrictMode>,
)
