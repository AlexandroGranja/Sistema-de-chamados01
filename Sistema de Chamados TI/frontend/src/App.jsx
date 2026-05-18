import { useState, useMemo } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { AuthProvider } from './contexts/AuthContext'
import PrivateRoute from './components/PrivateRoute'
import PortalPrivateRoute from './components/PortalPrivateRoute'
import StaffOnlyGate from './components/StaffOnlyGate'
import Layout from './components/Layout'
import PortalLayout from './components/PortalLayout'
import Login from './pages/Login'
import CadastroPortal from './pages/CadastroPortal'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import Tickets from './pages/Tickets'
import Desligamento from './pages/Desligamento'
import NovoChamado from './pages/NovoChamado'
import Onboarding from './pages/Onboarding'
import ManutencaoAparelho from './pages/ManutencaoAparelho'
import RouboPerdaLinha from './pages/RouboPerdaLinha'
import TransferenciaEquipe from './pages/TransferenciaEquipe'
import { buildTheme } from './theme'

const COLOR_MODE_KEY = 'prosper-color-mode'

function App() {
  const [mode, setMode] = useState(
    () => (localStorage.getItem(COLOR_MODE_KEY) === 'dark' ? 'dark' : 'light')
  )

  const toggleMode = () => {
    setMode((prev) => {
      const next = prev === 'light' ? 'dark' : 'light'
      localStorage.setItem(COLOR_MODE_KEY, next)
      return next
    })
  }

  const theme = useMemo(() => buildTheme(mode), [mode])

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/cadastro" element={<CadastroPortal />} />
            <Route path="/portal/login" element={<Login portal />} />
            <Route
              path="/portal"
              element={
                <PortalPrivateRoute>
                  <PortalLayout />
                </PortalPrivateRoute>
              }
            >
              <Route index element={<Navigate to="novo-chamado" replace />} />
              <Route path="novo-chamado" element={<NovoChamado portal />} />
            </Route>
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <StaffOnlyGate>
                    <Layout onToggleMode={toggleMode} mode={mode} />
                  </StaffOnlyGate>
                </PrivateRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="users" element={<Users />} />
              <Route path="tickets" element={<Tickets />} />
              <Route path="novo-chamado" element={<NovoChamado />} />
              <Route path="desligamento" element={<Desligamento />} />
              <Route path="onboarding" element={<Onboarding />} />
              <Route path="manutencao-aparelho" element={<ManutencaoAparelho />} />
              <Route path="roubo-perda" element={<RouboPerdaLinha />} />
              <Route path="transferencia" element={<TransferenciaEquipe />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
