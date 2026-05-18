import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { CircularProgress, Box } from '@mui/material'

/**
 * Bloqueia usuários do cadastro público (requester) de acessar o painel interno (dashboard, chamados, etc.).
 */
const StaffOnlyGate = ({ children }) => {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="40vh">
        <CircularProgress />
      </Box>
    )
  }

  if (user?.role === 'requester') {
    return <Navigate to="/portal/novo-chamado" replace />
  }

  return children
}

export default StaffOnlyGate
