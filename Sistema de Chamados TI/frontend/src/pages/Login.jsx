import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert } from '@mui/material'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'
import CompanyLogo from '../components/CompanyLogo'

/* ─── Ícones inline (sem dependência extra) ─────────────────────────── */
const EyeIcon = ({ open }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {open ? (
      <>
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
        <circle cx="12" cy="12" r="3"/>
      </>
    ) : (
      <>
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
        <line x1="1" y1="1" x2="23" y2="23"/>
      </>
    )}
  </svg>
)

const LockIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
  </svg>
)

const UserIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
)

/* ─── CSS injetado ───────────────────────────────────────────────────── */
const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

  .login-root {
    min-height: 100vh;
    display: flex;
    font-family: 'Plus Jakarta Sans', sans-serif;
    background: #0d1117;
  }

  /* ── Painel esquerdo ── */
  .login-brand {
    width: 44%;
    position: relative;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px;
    background: #0d1117;
    border-right: 1px solid rgba(242, 194, 48, 0.12);
  }

  .login-brand-bg {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 80% 60% at 50% 0%, rgba(242,194,48,0.08) 0%, transparent 70%),
      radial-gradient(ellipse 60% 80% at 100% 100%, rgba(242,194,48,0.05) 0%, transparent 60%);
  }

  .login-grid {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(242,194,48,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(242,194,48,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    mask-image: radial-gradient(ellipse 90% 80% at 50% 50%, black 30%, transparent 100%);
  }

  .login-brand-content {
    position: relative;
    z-index: 2;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .login-brand-logo-wrap {
    width: 88px;
    height: 88px;
    border-radius: 22px;
    background: linear-gradient(135deg, #f2c230, #d4a820);
    border: 1px solid rgba(242,194,48,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 48px rgba(242,194,48,0.4), 0 8px 24px rgba(0,0,0,0.5);
    margin-bottom: 28px;
    animation: logoPulse 3s ease-in-out infinite;
    overflow: hidden;
  }

  @keyframes logoPulse {
    0%, 100% { box-shadow: 0 0 48px rgba(242,194,48,0.45), 0 8px 24px rgba(0,0,0,0.5); }
    50%       { box-shadow: 0 0 80px rgba(242,194,48,0.65), 0 8px 24px rgba(0,0,0,0.5); }
  }

  .login-brand-name {
    font-size: 2rem;
    font-weight: 800;
    color: #f9fafb;
    letter-spacing: -0.03em;
    line-height: 1.1;
    margin-bottom: 8px;
  }

  .login-brand-name span { color: #f2c230; }

  .login-brand-sub {
    font-size: 0.875rem;
    color: rgba(255,255,255,0.4);
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 48px;
  }

  .login-brand-features {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
    width: 100%;
    max-width: 280px;
  }

  .login-brand-features li {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font-size: 0.8125rem;
    color: rgba(255,255,255,0.55);
    font-weight: 500;
    text-align: left;
  }

  .login-brand-features li span.login-feature-dot {
    margin-top: 5px;
  }

  .login-feature-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #f2c230;
    flex-shrink: 0;
    opacity: 0.7;
  }

  /* ── Painel direito ── */
  .login-form-panel {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 24px;
    background: #111827;
  }

  .login-card {
    width: 100%;
    max-width: 400px;
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 0.5s ease, transform 0.5s ease;
  }

  .login-card.visible {
    opacity: 1;
    transform: translateY(0);
  }

  .login-card-header {
    margin-bottom: 36px;
  }

  .login-card-header h1 {
    font-size: 1.625rem;
    font-weight: 800;
    color: #f9fafb;
    margin: 0 0 6px 0;
    letter-spacing: -0.02em;
  }

  .login-card-header p {
    font-size: 0.875rem;
    color: rgba(255,255,255,0.4);
    margin: 0;
    font-weight: 400;
  }

  /* ── Inputs ── */
  .login-field {
    margin-bottom: 16px;
  }

  .login-field label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: rgba(255,255,255,0.5);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }

  .login-input-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }

  .login-input-icon {
    position: absolute;
    left: 14px;
    color: rgba(255,255,255,0.3);
    display: flex;
    align-items: center;
    pointer-events: none;
  }

  .login-input {
    width: 100%;
    background: #1e293b;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 10px;
    padding: 13px 44px;
    font-size: 0.9375rem;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 500;
    color: #f9fafb;
    outline: none;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
    box-sizing: border-box;
  }

  .login-input::placeholder { color: rgba(255,255,255,0.25); }

  .login-input:focus {
    border-color: #f2c230;
    background: rgba(242,194,48,0.04);
    box-shadow: 0 0 0 3px rgba(242,194,48,0.12);
  }

  .login-eye-btn {
    position: absolute;
    right: 12px;
    background: none;
    border: none;
    cursor: pointer;
    color: rgba(255,255,255,0.3);
    display: flex;
    align-items: center;
    padding: 4px;
    border-radius: 4px;
    transition: color 0.15s;
  }

  .login-eye-btn:hover { color: rgba(255,255,255,0.7); }

  /* ── Botão ── */
  .login-btn {
    width: 100%;
    padding: 14px;
    background: #f2c230;
    border: none;
    border-radius: 10px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.9375rem;
    font-weight: 700;
    color: #0d1117;
    cursor: pointer;
    margin-top: 8px;
    letter-spacing: 0.01em;
    transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
    position: relative;
    overflow: hidden;
  }

  .login-btn:hover:not(:disabled) {
    background: #d4a820;
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(242,194,48,0.3);
  }

  .login-btn:active:not(:disabled) { transform: translateY(0); }

  .login-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .login-spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(0,0,0,0.3);
    border-top-color: #0d1117;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 8px;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Rodapé ── */
  .login-footer {
    margin-top: 28px;
    text-align: center;
    font-size: 0.75rem;
    color: rgba(255,255,255,0.2);
    font-weight: 500;
  }

  /* ── Responsivo ── */
  @media (max-width: 768px) {
    .login-brand { display: none; }
  }
`

/* ─── Componente ─────────────────────────────────────────────────────── */
const Login = ({ portal = false }) => {
  const [email, setEmail]           = useState('')
  const [password, setPassword]     = useState('')
  const [showPass, setShowPass]     = useState(false)
  const [error, setError]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [visible, setVisible]       = useState(false)
  const { login }                   = useAuth()
  const navigate                    = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 60)
    return () => clearTimeout(t)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const userData = await login(email.trim(), password)
      toast.success('Login realizado com sucesso!')
      if (userData?.role === 'requester') {
        navigate('/portal/novo-chamado')
      } else {
        navigate('/')
      }
    } catch (err) {
      const d = err.response?.data?.detail
      const message = Array.isArray(d)
        ? d.map((x) => (typeof x === 'string' ? x : x?.msg || JSON.stringify(x))).join(' ')
        : d || 'E-mail ou senha incorretos.'
      setError(typeof message === 'string' ? message : 'Erro ao fazer login.')
      toast.error(typeof message === 'string' ? message : 'Erro ao fazer login.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <style>{STYLES}</style>
      <div className="login-root">

        {/* ── Painel de marca ── */}
        <div className="login-brand">
          <div className="login-brand-bg" />
          <div className="login-grid" />
          <div className="login-brand-content">
            <div className="login-brand-logo-wrap">
              <CompanyLogo size={56} rounded={false} alt="Prosper" sx={{ objectFit: 'contain' }} />
            </div>
            <div className="login-brand-name">
              Prosper<br /><span>Distribuidora</span>
            </div>
            <div className="login-brand-sub">Sistema de Chamados TI</div>
            <ul className="login-brand-features">
              <li><span className="login-feature-dot" />Abertura e acompanhamento de chamados</li>
              <li><span className="login-feature-dot" />Gestão de linhas telefônicas</li>
              <li><span className="login-feature-dot" />Auditoria e histórico completo</li>
              <li><span className="login-feature-dot" />Integração entre sistemas</li>
            </ul>
          </div>
        </div>

        {/* ── Painel do formulário ── */}
        <div className="login-form-panel">
          <div className={`login-card${visible ? ' visible' : ''}`}>

            <div className="login-card-header">
              <h1>Bem-vindo de volta</h1>
              <p>
                {portal
                  ? 'Entre com o e-mail e a senha do seu cadastro.'
                  : 'Acesse com suas credenciais de TI.'}
              </p>
            </div>

            {error && (
              <Alert
                severity="error"
                sx={{ mb: 2.5, borderRadius: 2, fontSize: '0.8125rem', fontFamily: 'Plus Jakarta Sans, sans-serif' }}
              >
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className="login-field">
                <label htmlFor="login-email">
                  {portal ? 'E-mail' : 'E-mail ou usuário'}
                </label>
                <div className="login-input-wrap">
                  <span className="login-input-icon"><UserIcon /></span>
                  <input
                    id="login-email"
                    className="login-input"
                    type="text"
                    placeholder={portal ? 'seu@email.com.br' : 'usuário ou e-mail'}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="username"
                    required
                  />
                </div>
              </div>

              <div className="login-field">
                <label htmlFor="login-senha">Senha</label>
                <div className="login-input-wrap">
                  <span className="login-input-icon"><LockIcon /></span>
                  <input
                    id="login-senha"
                    className="login-input"
                    type={showPass ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                  />
                  <button
                    type="button"
                    className="login-eye-btn"
                    onClick={() => setShowPass((v) => !v)}
                    tabIndex={-1}
                    aria-label={showPass ? 'Ocultar senha' : 'Mostrar senha'}
                  >
                    <EyeIcon open={showPass} />
                  </button>
                </div>
              </div>

              <button type="submit" className="login-btn" disabled={loading}>
                {loading && <span className="login-spinner" />}
                {loading ? 'Entrando...' : 'Entrar'}
              </button>
            </form>

            <div className="login-footer">
              Prosper Distribuidora &mdash; TI Interno
            </div>
          </div>
        </div>

      </div>
    </>
  )
}

export default Login
