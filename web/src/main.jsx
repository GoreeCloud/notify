import React from 'react'
import { createRoot } from 'react-dom/client'
import '@goreecloud/ui/tokens.css'
import '@goreecloud/ui/components.css'
import './notify.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
