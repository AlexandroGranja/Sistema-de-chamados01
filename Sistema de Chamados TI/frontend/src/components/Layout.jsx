import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  Typography,
  Avatar,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material'
import { useAuth } from '../contexts/AuthContext'
import CompanyLogo from './CompanyLogo'
import StaffRequesterAlerts from './StaffRequesterAlerts'

// Ícones
import DashboardIcon from '@mui/icons-material/Dashboard'
import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'
import PersonAddIcon from '@mui/icons-material/PersonAdd'
import BuildIcon from '@mui/icons-material/Build'
import ReportProblemIcon from '@mui/icons-material/ReportProblem'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline'
import ExitToAppIcon from '@mui/icons-material/ExitToApp'
import ManageAccountsIcon from '@mui/icons-material/ManageAccounts'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import LightModeIcon from '@mui/icons-material/LightMode'
import DarkModeIcon from '@mui/icons-material/DarkMode'

const SIDEBAR_WIDTH = 240
const SIDEBAR_BG = '#111827'
const GOLD = '#f2c230'
const GOLD_HOVER = 'rgba(242,194,48,0.08)'
const TEXT_MUTED = 'rgba(255,255,255,0.5)'
const TEXT_ACTIVE = '#fff'

const NavItem = ({ icon, label, path, onClick, active, indent = false }) => (
  <ListItemButton
    onClick={onClick || (() => {})}
    selected={active}
    sx={{
      pl: indent ? 4 : 2,
      pr: 2,
      py: 0.85,
      borderRadius: 1.5,
      mx: 1,
      mb: 0.25,
      color: active ? TEXT_ACTIVE : TEXT_MUTED,
      borderLeft: active ? `3px solid ${GOLD}` : '3px solid transparent',
      '&:hover': {
        backgroundColor: GOLD_HOVER,
        color: TEXT_ACTIVE,
      },
      '&.Mui-selected': {
        backgroundColor: GOLD_HOVER,
        '&:hover': { backgroundColor: GOLD_HOVER },
      },
    }}
  >
    {icon && (
      <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>
        {icon}
      </ListItemIcon>
    )}
    <ListItemText
      primary={label}
      primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: active ? 600 : 400 }}
    />
  </ListItemButton>
)

const Layout = ({ onToggleMode, mode }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const [telefoniaOpen, setTelefoniaOpen] = useState(
    ['/onboarding', '/manutencao-aparelho', '/roubo-perda', '/transferencia'].some(
      (p) => location.pathname === p
    )
  )
  const [chamadoOpen, setChamadoOpen] = useState(
    location.pathname === '/desligamento' || location.pathname === '/novo-chamado'
  )

  const isActive = (path) => location.pathname === path

  const go = (path) => navigate(path)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Box
        component="nav"
        sx={{
          width: SIDEBAR_WIDTH,
          flexShrink: 0,
          backgroundColor: SIDEBAR_BG,
          display: 'flex',
          flexDirection: 'column',
          position: 'fixed',
          top: 0,
          left: 0,
          height: '100vh',
          zIndex: 1200,
          overflowY: 'auto',
        }}
      >
        {/* Logo */}
        <Box sx={{ px: 3, pt: 3, pb: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <CompanyLogo size={32} alt="Prosper" />
          <Typography
            variant="body2"
            sx={{ color: '#fff', fontWeight: 700, fontSize: '0.9rem', lineHeight: 1.2 }}
          >
            Sistema de<br />Chamados
          </Typography>
        </Box>

        <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', mx: 2, mb: 1 }} />

        {/* Navegação principal */}
        <List dense disablePadding sx={{ flex: 1, pt: 0.5 }}>
          <NavItem
            icon={<DashboardIcon fontSize="small" />}
            label="Dashboard"
            active={isActive('/')}
            onClick={() => go('/')}
          />
          <NavItem
            icon={<ConfirmationNumberIcon fontSize="small" />}
            label="Chamados"
            active={isActive('/tickets')}
            onClick={() => go('/tickets')}
          />

          {/* Abrir Chamado — submenu */}
          <ListItemButton
            onClick={() => setChamadoOpen((v) => !v)}
            sx={{
              pl: 2, pr: 2, py: 0.85,
              borderRadius: 1.5, mx: 1, mb: 0.25,
              color: chamadoOpen ? TEXT_ACTIVE : TEXT_MUTED,
              borderLeft: '3px solid transparent',
              '&:hover': { backgroundColor: GOLD_HOVER, color: TEXT_ACTIVE },
            }}
          >
            <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>
              <AddCircleOutlineIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText
              primary="Abrir chamado"
              primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: chamadoOpen ? 600 : 400 }}
            />
            {chamadoOpen ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </ListItemButton>
          <Collapse in={chamadoOpen} unmountOnExit>
            <NavItem
              indent
              label="Desligamento"
              active={isActive('/desligamento')}
              onClick={() => go('/desligamento')}
            />
            <NavItem
              indent
              label="Diversos de TI"
              active={isActive('/novo-chamado')}
              onClick={() => go('/novo-chamado')}
            />
          </Collapse>

          {/* Telefonia — submenu */}
          <ListItemButton
            onClick={() => setTelefoniaOpen((v) => !v)}
            sx={{
              pl: 2, pr: 2, py: 0.85,
              borderRadius: 1.5, mx: 1, mb: 0.25,
              color: telefoniaOpen ? TEXT_ACTIVE : TEXT_MUTED,
              borderLeft: '3px solid transparent',
              '&:hover': { backgroundColor: GOLD_HOVER, color: TEXT_ACTIVE },
            }}
          >
            <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>
              <PhoneAndroidIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText
              primary="Telefonia"
              primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: telefoniaOpen ? 600 : 400 }}
            />
            {telefoniaOpen ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
          </ListItemButton>
          <Collapse in={telefoniaOpen} unmountOnExit>
            <NavItem
              indent
              icon={<PersonAddIcon fontSize="small" />}
              label="Novo Usuário"
              active={isActive('/onboarding')}
              onClick={() => go('/onboarding')}
            />
            <NavItem
              indent
              icon={<BuildIcon fontSize="small" />}
              label="Manutenção"
              active={isActive('/manutencao-aparelho')}
              onClick={() => go('/manutencao-aparelho')}
            />
            <NavItem
              indent
              icon={<ReportProblemIcon fontSize="small" />}
              label="Roubo e Perda"
              active={isActive('/roubo-perda')}
              onClick={() => go('/roubo-perda')}
            />
            <NavItem
              indent
              icon={<SwapHorizIcon fontSize="small" />}
              label="Transferência"
              active={isActive('/transferencia')}
              onClick={() => go('/transferencia')}
            />
          </Collapse>

          {user?.role === 'admin' && (
            <NavItem
              icon={<ManageAccountsIcon fontSize="small" />}
              label="Usuários"
              active={isActive('/users')}
              onClick={() => go('/users')}
            />
          )}
        </List>

        {/* Rodapé: avatar + toggle modo */}
        <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', mx: 2 }} />
        <Box sx={{ px: 2, py: 2, display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Avatar
            sx={{ width: 32, height: 32, bgcolor: GOLD, color: '#111827', fontSize: '0.8rem', fontWeight: 700 }}
          >
            {(user?.name || user?.email || '?')[0].toUpperCase()}
          </Avatar>
          <Box sx={{ flex: 1, overflow: 'hidden' }}>
            <Typography
              noWrap
              sx={{ color: TEXT_ACTIVE, fontSize: '0.8rem', fontWeight: 600, lineHeight: 1.2 }}
            >
              {user?.name || user?.email}
            </Typography>
            <Typography noWrap sx={{ color: TEXT_MUTED, fontSize: '0.7rem' }}>
              {user?.role === 'admin' ? 'Administrador' : 'Técnico'}
            </Typography>
          </Box>
          <Tooltip title={mode === 'dark' ? 'Modo claro' : 'Modo escuro'}>
            <IconButton size="small" onClick={onToggleMode} sx={{ color: TEXT_MUTED, '&:hover': { color: GOLD } }}>
              {mode === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Sair">
            <IconButton size="small" onClick={handleLogout} sx={{ color: TEXT_MUTED, '&:hover': { color: '#ef4444' } }}>
              <ExitToAppIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Área de conteúdo */}
      <Box
        component="main"
        sx={{
          flex: 1,
          ml: `${SIDEBAR_WIDTH}px`,
          minHeight: '100vh',
          backgroundColor: 'background.default',
          overflowY: 'auto',
        }}
      >
        <Outlet />
        <StaffRequesterAlerts />
      </Box>
    </Box>
  )
}

export default Layout
