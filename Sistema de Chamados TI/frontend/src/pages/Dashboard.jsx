import { useEffect, useMemo, useState } from 'react'
import { Container, Typography, Box, Paper, Grid, Alert, Divider, Stack } from '@mui/material'
import { useAuth } from '../contexts/AuthContext'
import { ticketsAPI } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import AssignmentIcon from '@mui/icons-material/Assignment'
import PendingActionsIcon from '@mui/icons-material/PendingActions'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'

const CLOSED_STATUSES = ['closed', 'resolved', 'cancelled']
const WAITING_STATUSES = ['waiting_user', 'waiting_third_party']

const formatDate = (value) => (value ? new Date(value).toLocaleString('pt-BR') : '-')

const MetricCard = ({ label, value, icon, color }) => (
  <Paper
    elevation={0}
    sx={{
      p: 2.5,
      borderRadius: 2,
      border: '1px solid',
      borderColor: 'divider',
      borderLeft: `4px solid ${color}`,
      display: 'flex',
      flexDirection: 'column',
      gap: 0.5,
    }}
  >
    <Box display="flex" justifyContent="space-between" alignItems="flex-start">
      <Typography variant="overline" color="text.secondary">
        {label}
      </Typography>
      <Box sx={{ color }}>{icon}</Box>
    </Box>
    <Typography sx={{ fontSize: '2rem', fontWeight: 700, color, lineHeight: 1 }}>
      {value}
    </Typography>
  </Paper>
)

const Dashboard = () => {
  const { user } = useAuth()
  const [loading, setLoading] = useState(false)
  const [tickets, setTickets] = useState([])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const data = await ticketsAPI.getAll({ limit: 100 })
        setTickets(Array.isArray(data) ? data : [])
      } catch {
        setTickets([])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const stats = useMemo(() => {
    const opened = tickets.filter((t) => !CLOSED_STATUSES.includes(t.status)).length
    const inProgress = tickets.filter((t) => ['in_analysis', 'in_progress'].includes(t.status)).length
    const pending = tickets.filter((t) => WAITING_STATUSES.includes(t.status)).length
    const today = new Date()
    const todayKey = `${today.getFullYear()}-${today.getMonth()}-${today.getDate()}`
    const resolvedToday = tickets.filter((t) => {
      const ref = t.closed_at || t.resolved_at
      if (!ref) return false
      const d = new Date(ref)
      return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}` === todayKey
    }).length
    return { opened, inProgress, resolvedToday, pending }
  }, [tickets])

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Visão geral
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Bem-vindo, {user?.name}. Acompanhe os atendimentos em tempo real.
        </Typography>
      </Box>

      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Chamados abertos"
            value={stats.opened}
            color="#f2c230"
            icon={<AssignmentIcon fontSize="small" />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Em andamento"
            value={stats.inProgress}
            color="#3b82f6"
            icon={<PendingActionsIcon fontSize="small" />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Resolvidos hoje"
            value={stats.resolvedToday}
            color="#10b981"
            icon={<CheckCircleOutlineIcon fontSize="small" />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="Aguardando retorno"
            value={stats.pending}
            color="#f59e0b"
            icon={<HourglassEmptyIcon fontSize="small" />}
          />
        </Grid>
      </Grid>

      <Paper
        elevation={0}
        sx={{ borderRadius: 2, border: '1px solid', borderColor: 'divider' }}
      >
        <Box sx={{ px: 3, py: 2, borderBottom: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h6">Últimos chamados</Typography>
        </Box>
        <Box sx={{ p: 2 }}>
          {loading ? (
            <Alert severity="info">Carregando...</Alert>
          ) : tickets.length === 0 ? (
            <Alert severity="warning">Nenhum chamado encontrado.</Alert>
          ) : (
            <Stack divider={<Divider />}>
              {tickets.slice(0, 8).map((ticket) => (
                <Box
                  key={ticket.id}
                  sx={{ py: 1.5, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}
                >
                  <Box sx={{ overflow: 'hidden' }}>
                    <Typography variant="body2" fontWeight={600} noWrap>
                      #{ticket.id} · {ticket.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {ticket.category ? `${ticket.category} · ` : ''}{formatDate(ticket.created_at)}
                    </Typography>
                  </Box>
                  <Box sx={{ flexShrink: 0 }}>
                    <StatusBadge status={ticket.status} />
                  </Box>
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      </Paper>
    </Container>
  )
}

export default Dashboard
