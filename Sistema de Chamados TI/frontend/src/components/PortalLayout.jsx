import { Outlet, useNavigate } from 'react-router-dom'
import { AppBar, Toolbar, Typography, Button, Box, IconButton, Menu, MenuItem } from '@mui/material'
import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import PersonIcon from '@mui/icons-material/Person'
import LogoutIcon from '@mui/icons-material/Logout'
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline'
import CompanyLogo from './CompanyLogo'

const PortalLayout = () => {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [anchorEl, setAnchorEl] = useState(null)

  const handleLogout = () => {
    setAnchorEl(null)
    logout()
    navigate('/portal/login')
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 1.1 }}>
            <CompanyLogo size={30} alt="Logo Prosper" />
            <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
              Chamados — Área do solicitante
            </Typography>
          </Box>
          <Button
            color="inherit"
            startIcon={<AddCircleOutlineIcon />}
            onClick={() => navigate('/portal/novo-chamado')}
            sx={{ mx: 0.5 }}
          >
            Abrir chamado
          </Button>
          <IconButton color="inherit" onClick={(e) => setAnchorEl(e.currentTarget)} size="large">
            <PersonIcon />
          </IconButton>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
            <MenuItem disabled>{user?.name}</MenuItem>
            <MenuItem disabled>{user?.phone ? `Tel. ${user.phone}` : user?.email}</MenuItem>
            <MenuItem onClick={handleLogout}>
              <LogoutIcon sx={{ mr: 1 }} fontSize="small" />
              Sair
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ p: 0 }}>
        <Outlet />
      </Box>
    </Box>
  )
}

export default PortalLayout
