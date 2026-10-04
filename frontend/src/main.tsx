import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { App } from './App'
import { AppErrorBoundary } from './components/AppErrorBoundary'
import './styles/index.css'

const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('The application root element is missing.')
}

createRoot(rootElement, { onCaughtError: () => { /* No private exception telemetry. */ } }).render(
  <StrictMode>
    <AppErrorBoundary>
    <BrowserRouter>
      <App />
    </BrowserRouter>
    </AppErrorBoundary>
  </StrictMode>,
)
