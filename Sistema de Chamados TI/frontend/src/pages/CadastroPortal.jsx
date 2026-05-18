import { useState } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert,
  Link,
} from '@mui/material'
import toast from 'react-hot-toast'
import CompanyLogo from '../components/CompanyLogo'
import { authAPI } from '../services/api'

const CadastroPortal = () => {
  const navigate = useNavigate()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [department, setDepartment] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== passwordConfirm) {
      setError('As senhas não conferem.')
      return
    }
    if (password.length < 6) {
      setError('A senha deve ter pelo menos 6 caracteres.')
      return
    }
    const em = email.trim()
    if (!em || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)) {
      setError('Informe um e-mail válido.')
      return
    }
    setLoading(true)
    try {
      await authAPI.registerPortal({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: em,
        department: department.trim(),
        password,
        password_confirm: passwordConfirm,
      })
      toast.success('Cadastro realizado! Faça login com seu e-mail e senha.')
      setFirstName('')
      setLastName('')
      setEmail('')
      setDepartment('')
      setPassword('')
      setPasswordConfirm('')
      navigate('/portal/login')
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        (typeof err.response?.data?.detail === 'object'
          ? JSON.stringify(err.response?.data?.detail)
          : null) ||
        'Não foi possível cadastrar.'
      setError(typeof message === 'string' ? message : 'Erro ao cadastrar.')
      toast.error(typeof message === 'string' ? message : 'Erro ao cadastrar.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Container maxWidth="sm">
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh" py={3}>
        <Paper elevation={3} sx={{ p: 4, width: '100%' }}>
          <Box display="flex" justifyContent="center" sx={{ mb: 1 }}>
            <CompanyLogo size={58} alt="Logo Prosper" sx={{ bgcolor: 'transparent', p: 0 }} />
          </Box>
          <Typography variant="h5" component="h1" gutterBottom align="center">
            Cadastro — abrir chamado com a TI
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
            Acesso restrito ao formulário de chamados (sem painel interno).
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Nome"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              margin="normal"
              required
              autoComplete="given-name"
            />
            <TextField
              fullWidth
              label="Sobrenome"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              margin="normal"
              required
              autoComplete="family-name"
            />
            <TextField
              fullWidth
              label="E-mail"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
              autoComplete="email"
            />
            <TextField
              fullWidth
              label="Setor"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              margin="normal"
              required
              placeholder="Ex.: Financeiro, RH, Loja Centro"
            />
            <TextField
              fullWidth
              label="Senha"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              autoComplete="new-password"
            />
            <TextField
              fullWidth
              label="Repete senha"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              margin="normal"
              required
              autoComplete="new-password"
            />
            <Button type="submit" fullWidth variant="contained" sx={{ mt: 3, mb: 1 }} disabled={loading}>
              {loading ? 'Cadastrando...' : 'Criar meu acesso'}
            </Button>
            <Typography variant="body2" align="center">
              Já tem cadastro?{' '}
              <Link component={RouterLink} to="/portal/login">
                Entrar com e-mail e senha
              </Link>
            </Typography>
          </form>
        </Paper>
      </Box>
    </Container>
  )
}

export default CadastroPortal
