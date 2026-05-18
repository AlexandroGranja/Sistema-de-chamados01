import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { CircularProgress, Box } from '@mui/material'

/**
 * Rotas só para quem fez cadastro pelo link público (perfil requester).
 */
const PortalPrivateRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth()

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/portal/login" replace />
  }

  if (user?.role !== 'requester') {
    return <Navigate to="/" replace />
  }

  return children
}

export default PortalPrivateRoute
