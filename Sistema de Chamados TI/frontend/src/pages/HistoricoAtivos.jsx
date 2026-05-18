import { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Paper,
  Box,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
  Chip,
  Alert,
} from '@mui/material'
import { desligamentoAPI } from '../services/api'
import AssignmentIcon from '@mui/icons-material/Assignment'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'
import { format } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const HistoricoAtivos = () => {
  const [tab, setTab] = useState(0)
  const [snipeConfigured, setSnipeConfigured] = useState(false)
  const [loadingAssignments, setLoadingAssignments] = useState(true)
  const [loadingLogs, setLoadingLogs] = useState(true)
  const [assignments, setAssignments] = useState([])
  const [logs, setLogs] = useState([])

  useEffect(() => {
    desligamentoAPI.getSnipeStatus().then((r) => setSnipeConfigured(r.configured)).catch(() => setSnipeConfigured(false))
  }, [])

  useEffect(() => {
    setLoadingAssignments(true)
    desligamentoAPI.getAssignments({ limit: 100 })
      .then(setAssignments)
      .catch(() => setAssignments([]))
      .finally(() => setLoadingAssignments(false))
  }, [])

  useEffect(() => {
    setLoadingLogs(true)
    desligamentoAPI.getLogs({ limit: 100 })
      .then(setLogs)
      .catch(() => setLogs([]))
      .finally(() => setLoadingLogs(false))
  }, [])

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Histórico – Gerenciamento de Ativos
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Quem recebeu aparelho (entrega) e quem devolveu (desligamento). Dados salvos no sistema e atualizados no Gerenciamento de Ativos.
      </Typography>

      {!snipeConfigured && (
        <Alert severity="info" sx={{ mb: 2 }}>
          A integração com o Gerenciamento de Ativos não está configurada. O histórico local ainda pode ser exibido.
        </Alert>
      )}

      <Paper>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab label="Entregas (quem recebeu)" icon={<AssignmentIcon />} iconPosition="start" />
          <Tab label="Devoluções (desligamento)" icon={<PhoneAndroidIcon />} iconPosition="start" />
        </Tabs>
        <Box sx={{ p: 2 }}>
          {tab === 0 && (
            <>
              {loadingAssignments ? (
                <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Data</TableCell>
                        <TableCell>Colaborador</TableCell>
                        <TableCell>Ativo</TableCell>
                        <TableCell>Observação</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {assignments.length === 0 ? (
                        <TableRow><TableCell colSpan={4} align="center">Nenhuma entrega registrada.</TableCell></TableRow>
                      ) : (
                        assignments.map((a) => (
                          <TableRow key={a.id}>
                            <TableCell>{a.assigned_at ? format(new Date(a.assigned_at), "dd/MM/yyyy HH:mm", { locale: ptBR }) : '-'}</TableCell>
                            <TableCell>{a.snipe_user_name || a.snipe_user_id}</TableCell>
                            <TableCell>{a.asset_tag || a.asset_name || a.snipe_asset_id}</TableCell>
                            <TableCell>{a.note || '-'}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </>
          )}
          {tab === 1 && (
            <>
              {loadingLogs ? (
                <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
              ) : (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Data</TableCell>
                        <TableCell>Ativo</TableCell>
                        <TableCell>Condição</TableCell>
                        <TableCell>Observação</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {logs.length === 0 ? (
                        <TableRow><TableCell colSpan={4} align="center">Nenhuma devolução registrada.</TableCell></TableRow>
                      ) : (
                        logs.map((l) => (
                          <TableRow key={l.id}>
                            <TableCell>{l.created_at ? format(new Date(l.created_at), "dd/MM/yyyy HH:mm", { locale: ptBR }) : '-'}</TableCell>
                            <TableCell>{l.asset_tag || l.asset_name || l.snipe_asset_id}</TableCell>
                            <TableCell>
                              <Chip
                                size="small"
                                label={l.needs_maintenance ? 'Precisa manutenção' : 'Perfeitas condições'}
                                color={l.needs_maintenance ? 'warning' : 'success'}
                              />
                            </TableCell>
                            <TableCell>{l.note || '-'}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </>
          )}
        </Box>
      </Paper>
    </Container>
  )
}

export default HistoricoAtivos
