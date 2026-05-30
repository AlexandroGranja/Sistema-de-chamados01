import { createContext, useContext, useState, useEffect, useRef } from 'react'
import { authAPI } from '../services/api'
import toast from 'react-hot-toast'

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth deve ser usado dentro de AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const ssoExchangeInFlightRef = useRef(false)

  useEffect(() => {
    if (token) {
      loadUser()
    } else {
      // Login automático via SSO quando a URL vier com `?sso_code=...`
      const urlParams = new URLSearchParams(window.location.search)
      const ssoCode = (urlParams.get('sso_code') || '').trim()

      if (ssoCode) {
        if (ssoExchangeInFlightRef.current) {
          return
        }
        const redirectPath = (urlParams.get('redirect') || '').trim()
        const storageKey = `sso_exchange_done:${ssoCode}`
        if (typeof window !== 'undefined' && window.sessionStorage.getItem(storageKey)) {
          setLoading(false)
          return
        }
        ssoExchangeInFlightRef.current = true
        setLoading(true)
        try {
          if (typeof window !== 'undefined') window.sessionStorage.setItem(storageKey, '1')
        } catch {
          // se sessionStorage falhar, seguimos mesmo assim
        }
        ;(async () => {
          try {
            const response = await authAPI.ssoExchange(ssoCode)
            localStorage.setItem('token', response.access_token)
            localStorage.setItem('refreshToken', response.refresh_token)
            setToken(response.access_token)

            const safeRedirect =
              redirectPath.startsWith('/') && !redirectPath.startsWith('//')
                ? redirectPath
                : ''
            if (safeRedirect) {
              window.location.replace(safeRedirect)
              return
            }

            // Limpa a query para não reutilizar o mesmo código.
            try {
              const cleanUrl = window.location.pathname
              window.history.replaceState({}, document.title, cleanUrl)
            } catch {
              // nao bloqueia o fluxo se falhar
            }
          } catch (error) {
            localStorage.removeItem('token')
            localStorage.removeItem('refreshToken')
            setToken(null)
            setUser(null)
            const detail = error?.response?.data?.detail || 'Falha no SSO.'
            console.error('[SSO] Erro:', detail)
            toast.error(detail)
            try {
              if (typeof window !== 'undefined') window.sessionStorage.removeItem(storageKey)
            } catch {
              // ignorar
            }
            window.location.href = '/login'
          } finally {
            ssoExchangeInFlightRef.current = false
          }
        })()
      } else {
        setLoading(false)
      }
    }
  }, [token])

  const loadUser = async () => {
    try {
      const userData = await authAPI.getMe()
      setUser(userData)
    } catch (error) {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      setToken(null)
    } finally {
      setLoading(false)
    }
  }

  const login = async (email, password) => {
    const response = await authAPI.login(email, password)
    localStorage.setItem('token', response.access_token)
    localStorage.setItem('refreshToken', response.refresh_token)
    setToken(response.access_token)
    const userData = await authAPI.getMe()
    setUser(userData)
    setLoading(false)
    return userData
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    setToken(null)
    setUser(null)
  }

  const value = {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!token,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

