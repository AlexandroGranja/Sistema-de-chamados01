import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Box,
  Button,
  Paper,
  Typography,
  Slide,
  List,
  ListItem,
  ListItemText,
  IconButton,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import ConfirmationNumberOutlinedIcon from '@mui/icons-material/ConfirmationNumberOutlined'
import { useAuth } from '../contexts/AuthContext'
import { ticketsAPI } from '../services/api'

const POLL_MS = 35_000

/** Som curto e discreto (Web Audio API — sem arquivo externo). */
function playAlertChime() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return
    const ctx = new Ctx()
    const g = ctx.createGain()
    g.gain.value = 0.06
    g.connect(ctx.destination)

    const beep = (freq, start, dur) => {
      const o = ctx.createOscillator()
      o.type = 'sine'
      o.frequency.value = freq
      o.connect(g)
      o.start(start)
      o.stop(start + dur)
    }
    const t0 = ctx.currentTime
    beep(880, t0, 0.12)
    beep(660, t0 + 0.14, 0.14)
    setTimeout(() => ctx.close(), 600)
  } catch {
    // ignore (autoplay policy, etc.)
  }
}

/**
 * Lista chamados do portal ainda abertos; aviso permanece até status final (resolvido/encerrado/cancelado).
 */
const StaffRequesterAlerts = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [items, setItems] = useState([])
  /** Fechado com X; volta a aparecer no F5 ou ao mudar de rota. */
  const [dismissed, setDismissed] = useState(false)
  const mounted = useRef(true)

  useEffect(() => {
    setDismissed(false)
  }, [location.pathname])

  const isStaff = user?.role === 'admin' || user?.role === 'technician'

  const poll = useCallback(async () => {
    if (!isStaff || !mounted.current) return

    try {
      const res = await ticketsAPI.getStaffRequesterAlerts()
      const nextItems = res.items || []
      setItems(nextItems)

      const played = JSON.parse(sessionStorage.getItem('staffAlertChimePlayedIds') || '[]')
      const playedSet = new Set(played)
      const nextPlayed = [...played]
      let hasNewId = false
      for (const it of nextItems) {
        if (!playedSet.has(it.id)) {
          nextPlayed.push(it.id)
          hasNewId = true
        }
      }
      if (hasNewId) {
        sessionStorage.setItem('staffAlertChimePlayedIds', JSON.stringify(nextPlayed))
        playAlertChime()
      }
    } catch {
      // silencioso
    }
  }, [isStaff])

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  useEffect(() => {
    if (!isStaff) return undefined
    const t = setInterval(poll, POLL_MS)
    const t0 = setTimeout(poll, 2000)
    return () => {
      clearInterval(t)
      clearTimeout(t0)
    }
  }, [isStaff, poll])

  const handleGo = () => {
    navigate('/tickets')
  }

  const handleDismiss = () => setDismissed(true)

  if (!isStaff) return null

  const open = items.length > 0 && !dismissed

  return (
    <Slide direction="up" in={open} mountOnEnter unmountOnExit>
      <Paper
        elevation={4}
        role="status"
        aria-live="polite"
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          zIndex: (theme) => theme.zIndex.snackbar,
          width: 'min(400px, calc(100vw - 32px))',
          maxHeight: 280,
          display: 'flex',
          flexDirection: 'column',
          pl: 2,
          pr: 2,
          py: 1.5,
          borderLeft: 4,
          borderColor: 'primary.main',
          bgcolor: 'background.paper',
          boxShadow: 3,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1, pr: 0 }}>
          <ConfirmationNumberOutlinedIcon color="primary" fontSize="small" sx={{ mt: 0.25 }} />
          <Typography variant="subtitle2" component="p" sx={{ fontWeight: 600, flex: 1, pr: 0.5 }}>
            {items.length === 1
              ? 'Chamado do portal aberto'
              : `${items.length} chamados do portal abertos`}
          </Typography>
          <IconButton
            size="small"
            aria-label="Fechar aviso"
            onClick={handleDismiss}
            sx={{ mt: -0.5, mr: -1 }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>
        <List dense disablePadding sx={{ overflow: 'auto', flex: 1, py: 0 }}>
          {items.map((it) => (
            <ListItem key={it.id} disableGutters sx={{ py: 0.25, alignItems: 'flex-start' }}>
              <ListItemText
                primary={
                  <Typography variant="body2" component="span" sx={{ fontWeight: 600 }}>
                    #{it.ticket_number ?? it.id}
                  </Typography>
                }
                secondary={it.title || '—'}
                primaryTypographyProps={{ component: 'div' }}
                secondaryTypographyProps={{
                  variant: 'caption',
                  color: 'text.secondary',
                  sx: { display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' },
                }}
              />
            </ListItem>
          ))}
        </List>
        <Button size="small" onClick={handleGo} sx={{ mt: 1, alignSelf: 'flex-start' }} color="primary">
          Ver chamados
        </Button>
      </Paper>
    </Slide>
  )
}

export default StaffRequesterAlerts
