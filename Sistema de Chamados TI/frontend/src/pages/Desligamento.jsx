import { useState, useEffect } from 'react'
import {
  Container,
  Typography,
  Paper,
  Box,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
  Chip,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from '@mui/material'
import { useAuth } from '../contexts/AuthContext'
import { usersAPI, desligamentoAPI, ticketsAPI } from '../services/api'
import toast from 'react-hot-toast'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import BuildIcon from '@mui/icons-material/Build'

const CONDICAO_OK = false
const CONDICAO_MANUTENCAO = true

const OFFBOARDING_ACTIONS = [
  { value: 'device_ok', label: 'Aparelho OK (finalizar desligamento)' },
  { value: 'offboarding_with_maintenance', label: 'Desligamento com manutenção' },
  { value: 'without_charger', label: 'Recebido sem carregador' },
  { value: 'not_delivered', label: 'Não entregou aparelho e o carregador' },
]

const formatApiError = (err, fallback) => {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0]
    if (typeof first === 'string') return first
    if (first?.msg) return first.msg
    return JSON.stringify(first)
  }
  if (detail && typeof detail === 'object') {
    if (detail.msg) return detail.msg
    return JSON.stringify(detail)
  }
  return fallback
}

const CLOSED_TICKET_STATUSES = ['resolved', 'closed', 'cancelled']
const TICKET_STATUS_LABELS = {
  open: 'Aberto',
  in_analysis: 'Em análise',
  in_progress: 'Em andamento',
  waiting_user: 'Aguardando usuário',
  waiting_third_party: 'Aguardando terceiros',
  resolved: 'Resolvido',
  closed: 'Fechado',
  cancelled: 'Cancelado',
}

const OFFBOARDING_ACTION_LABELS = {
  device_ok: 'Aparelho OK',
  offboarding_with_maintenance: 'Desligamento com manutenção',
  maintenance_only: 'Somente manutenção',
  without_charger: 'Recebido sem carregador',
  not_delivered: 'Não entregou aparelho e o carregador',
}

const DEVICE_MODELS = ['A10s', 'A02', 'A03', 'A05']

const formatDateTime = (value) => (value ? new Date(value).toLocaleString('pt-BR') : '-')

const getTicketMetadata = (ticket) => {
  if (!ticket?.equipment_info) return {}
  if (typeof ticket.equipment_info === 'object') return ticket.equipment_info
  try {
    return JSON.parse(ticket.equipment_info)
  } catch {
    return {}
  }
}

const getOffboardingReason = (ticket) => {
  const metadata = getTicketMetadata(ticket)
  return (
    metadata.maintenance_reason ||
    metadata.resolution_text ||
    OFFBOARDING_ACTION_LABELS[metadata.action] ||
    ticket.internal_notes ||
    '-'
  )
}

const Desligamento = () => {
  const { user } = useAuth()
  const [snipeConfigured, setSnipeConfigured] = useState(true)
  const [loading, setLoading] = useState(true)
  const [loadingAssets, setLoadingAssets] = useState(false)
  const [ourUsers, setOurUsers] = useState([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [snipeUser, setSnipeUser] = useState(null)
  const [assets, setAssets] = useState([])
  const [conditionByAsset, setConditionByAsset] = useState({})
  const [noteByAsset, setNoteByAsset] = useState({})
  const [submitting, setSubmitting] = useState({})
  const [autoDeleteSnipeUser, setAutoDeleteSnipeUser] = useState(true)
  const [ticketSubmitting, setTicketSubmitting] = useState(false)
  const [ticketAction, setTicketAction] = useState('device_ok')
  const [ticketEmployeeName, setTicketEmployeeName] = useState('')
  const [ticketAssetTag, setTicketAssetTag] = useState('')
  const [ticketDeviceModel, setTicketDeviceModel] = useState('')
  const [ticketDeviceModelPreset, setTicketDeviceModelPreset] = useState('')
  const [ticketUserDepartment, setTicketUserDepartment] = useState('')
  const [ticketReturnDate, setTicketReturnDate] = useState(new Date().toISOString().slice(0, 10))
  const [ticketDeviceCondition, setTicketDeviceCondition] = useState('ok')
  const [ticketMaintenanceReason, setTicketMaintenanceReason] = useState('')
  const [ticketResolutionText, setTicketResolutionText] = useState(
    'O aparelho e o carregador foram conferidos e testados e se encontra em condições de dar continuidade de uso.'
  )
  const [openOffboardingTickets, setOpenOffboardingTickets] = useState([])
  const [loadingOpenOffboardingTickets, setLoadingOpenOffboardingTickets] = useState(false)
  const [closingTicketId, setClosingTicketId] = useState(null)
  const [closeModalOpen, setCloseModalOpen] = useState(false)
  const [ticketToClose, setTicketToClose] = useState(null)
  const [closeNote, setCloseNote] = useState('')
  const [prefillLoading, setPrefillLoading] = useState(false)
  const [prefillInfo, setPrefillInfo] = useState('')

  const loadOpenOffboardingTickets = async () => {
    setLoadingOpenOffboardingTickets(true)
    try {
      const data = await ticketsAPI.getAll({ limit: 100 })
      const rows = Array.isArray(data) ? data : []
      const filtered = rows.filter((ticket) => {
        if (CLOSED_TICKET_STATUSES.includes(ticket.status)) return false
        const metadata = getTicketMetadata(ticket)
        return Boolean(metadata?.action)
      })
      setOpenOffboardingTickets(filtered)
    } catch (err) {
      toast.error('Erro ao carregar chamados de desligamento abertos.')
    } finally {
      setLoadingOpenOffboardingTickets(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const [statusRes, usersRes] = await Promise.all([
          desligamentoAPI.getSnipeStatus(),
          usersAPI.getAll(),
        ])
        if (!cancelled) {
          setSnipeConfigured(statusRes.configured)
          setOurUsers(usersRes || [])
        }
      } catch (e) {
        if (!cancelled) {
          setSnipeConfigured(false)
          setOurUsers([])
          toast.error('Erro ao carregar dados.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    loadOpenOffboardingTickets()
  }, [])

  const selectedUser = ourUsers.find((u) => u.id === selectedUserId)

  useEffect(() => {
    if (!selectedUser || !snipeConfigured) {
      setSnipeUser(null)
      setAssets([])
      setConditionByAsset({})
      setNoteByAsset({})
      return
    }
    let cancelled = false
    setLoadingAssets(true)
    const run = async () => {
      try {
        let snipeId = selectedUser.snipe_user_id
        if (!snipeId) {
          const findRes = await desligamentoAPI.findSnipeUser(selectedUser.name, selectedUser.email)
          const found = findRes?.data
          if (found) snipeId = found.id
        }
        if (!cancelled && snipeId) {
          setSnipeUser({ id: snipeId, name: selectedUser.name })
          const assetsRes = await desligamentoAPI.getAssetsForUser(snipeId)
          setAssets(assetsRes?.data || [])
        } else if (!cancelled) {
          setSnipeUser(null)
          setAssets([])
          toast.error('Usuário não encontrado no Gerenciamento de Ativos. Cadastre-o lá ou vincule o ID em Usuários.')
        }
      } catch (e) {
        if (!cancelled) {
          setSnipeUser(null)
          setAssets([])
          toast.error('Erro ao buscar ativos.')
        }
      } finally {
        if (!cancelled) setLoadingAssets(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [selectedUser, snipeConfigured])

  useEffect(() => {
    if (selectedUser?.name) {
      setTicketEmployeeName(selectedUser.name)
    }
    if (selectedUser?.department) {
      setTicketUserDepartment(selectedUser.department)
    }
  }, [selectedUserId, selectedUser?.name, selectedUser?.department])

  useEffect(() => {
    let cancelled = false
    const employeeName = ticketEmployeeName.trim()

    if (employeeName.length < 4) {
      setPrefillInfo('')
      setPrefillLoading(false)
      return () => { cancelled = true }
    }

    const timer = setTimeout(async () => {
      setPrefillLoading(true)
      try {
        const res = await ticketsAPI.getOffboardingPrefill(employeeName)
        if (cancelled) return

        if (res?.ok && res?.data) {
          const data = res.data
          setTicketUserDepartment(data.user_department || '')
          setTicketAssetTag(data.asset_tag || '')
          const prefillModel = String(data.device_model || '').trim()
          if (prefillModel) {
            const matchedModel = DEVICE_MODELS.find(
              (model) => model.toLowerCase() === prefillModel.toLowerCase()
            )
            if (matchedModel) {
              setTicketDeviceModelPreset(matchedModel)
              setTicketDeviceModel(matchedModel)
            } else {
              setTicketDeviceModelPreset('custom')
              setTicketDeviceModel(prefillModel)
            }
          } else {
            setTicketDeviceModelPreset('')
            setTicketDeviceModel('')
          }
          setPrefillInfo('Dados carregados automaticamente do Gerenciamento de Telefones.')
        } else {
          setPrefillInfo(res?.message || 'Não foi possível localizar dados automáticos para este colaborador.')
        }
      } catch (err) {
        if (!cancelled) {
          setPrefillInfo('Não foi possível realizar o preenchimento automático.')
        }
      } finally {
        if (!cancelled) setPrefillLoading(false)
      }
    }, 650)

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [ticketEmployeeName])

  const ticketMustShowAsset = ticketAction !== 'not_delivered'
  const ticketMustShowMaintenanceReason =
    ticketAction === 'offboarding_with_maintenance' ||
    (ticketAction === 'without_charger' && ticketDeviceCondition === 'maintenance')
  const ticketMustShowResolution = ticketAction === 'device_ok'

  const handleCreateOffboardingTicket = async () => {
    if (!ticketEmployeeName.trim()) {
      toast.error('Informe o nome do colaborador para abrir o chamado.')
      return
    }
    if (ticketMustShowAsset && !ticketAssetTag.trim()) {
      toast.error('Informe o ativo para abrir o chamado.')
      return
    }
    if (ticketMustShowMaintenanceReason && !ticketMaintenanceReason.trim()) {
      toast.error('Informe o motivo da manutenção.')
      return
    }
    setTicketSubmitting(true)
    try {
      const payload = {
        action: ticketAction,
        employee_name: ticketEmployeeName.trim(),
        return_date: ticketReturnDate || null,
        asset_tag: ticketMustShowAsset ? ticketAssetTag.trim() : null,
        device_model: ticketDeviceModel.trim() || null,
        user_department: ticketUserDepartment.trim() || null,
        device_condition: ticketDeviceCondition,
        maintenance_reason: ticketMustShowMaintenanceReason ? ticketMaintenanceReason.trim() : null,
        resolution_text: ticketMustShowResolution ? ticketResolutionText.trim() : null,
      }
      const created = await ticketsAPI.createOffboarding(payload)
      toast.success(`Chamado ID ${created.id} aberto com sucesso.`)
      loadOpenOffboardingTickets()
    } catch (err) {
      toast.error(formatApiError(err, 'Erro ao abrir chamado de desligamento.'))
    } finally {
      setTicketSubmitting(false)
    }
  }

  const handleDarBaixa = async (asset) => {
    const id = asset.id
    setSubmitting((s) => ({ ...s, [id]: true }))
    const needsMaintenance = conditionByAsset[id] === true
    const note = noteByAsset[id] || undefined
    try {
      const res = await desligamentoAPI.checkin({
        asset_id: id,
        needs_maintenance: needsMaintenance,
        note,
        user_id: selectedUserId || undefined,
        snipe_user_id: snipeUser?.id || undefined,
        delete_user_when_no_assets: autoDeleteSnipeUser,
      })
      if (res?.deleted_snipe_user) {
        toast.success(`Baixa realizada e usuário removido do Gerenciamento: ${snipeUser?.name || 'colaborador'}`)
      } else {
        toast.success(`Baixa realizada: ${asset.asset_tag || asset.name || id}`)
      }
      setAssets((prev) => prev.filter((a) => a.id !== id))
      setConditionByAsset((c) => ({ ...c, [id]: undefined }))
      setNoteByAsset((n) => ({ ...n, [id]: '' }))
    } catch (err) {
      const msg = err.response?.data?.detail || 'Erro ao dar baixa'
      toast.error(msg)
    } finally {
      setSubmitting((s) => ({ ...s, [id]: false }))
    }
  }

  const openCloseModal = (ticket) => {
    setTicketToClose(ticket)
    setCloseNote('')
    setCloseModalOpen(true)
  }

  const handleCloseOffboardingTicket = async () => {
    if (!ticketToClose) return
    setClosingTicketId(ticketToClose.id)
    const finalNote = closeNote.trim()
    try {
      await ticketsAPI.updateStatus(ticketToClose.id, {
        status: 'closed',
        internal_notes: finalNote || 'Chamado encerrado pela aba Desligamento.',
      })
      toast.success(`Chamado ID ${ticketToClose.id} encerrado com sucesso.`)
      setOpenOffboardingTickets((prev) => prev.filter((t) => t.id !== ticketToClose.id))
      setCloseModalOpen(false)
      setTicketToClose(null)
      setCloseNote('')
    } catch (err) {
      toast.error(formatApiError(err, 'Erro ao encerrar chamado.'))
    } finally {
      setClosingTicketId(null)
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    )
  }

  const showSnipeWarning = !snipeConfigured

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Desligamento de usuário
      </Typography>
      {showSnipeWarning && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          A integração com o Gerenciamento de Ativos (Snipe-IT) não está configurada.
          Você ainda pode abrir chamados de desligamento; a parte de baixa/baixa manual em ativos ficará indisponível.
        </Alert>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Selecione o colaborador e dê baixa nos ativos no Gerenciamento de Ativos.
        Informe se o equipamento está em perfeitas condições ou precisa de manutenção.
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Abrir chamado de desligamento
        </Typography>
        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Ação do chamado</InputLabel>
          <Select
            value={ticketAction}
            label="Ação do chamado"
            onChange={(e) => setTicketAction(e.target.value)}
          >
            {OFFBOARDING_ACTIONS.map((a) => (
              <MenuItem key={a.value} value={a.value}>
                {a.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          fullWidth
          sx={{ mb: 2 }}
          label="Nome completo do colaborador"
          value={ticketEmployeeName}
          onChange={(e) => setTicketEmployeeName(e.target.value)}
          helperText={prefillLoading ? 'Buscando dados automáticos...' : prefillInfo}
        />
        <TextField
          fullWidth
          sx={{ mb: 2 }}
          label="Equipe"
          value={ticketUserDepartment}
          onChange={(e) => setTicketUserDepartment(e.target.value)}
        />
        {ticketMustShowAsset && (
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Ativo (patrimônio/série)"
            value={ticketAssetTag}
            onChange={(e) => setTicketAssetTag(e.target.value)}
          />
        )}
        <FormControl fullWidth sx={{ mb: ticketDeviceModelPreset === 'custom' ? 1 : 2 }}>
          <InputLabel>Modelo do aparelho</InputLabel>
          <Select
            value={ticketDeviceModelPreset}
            label="Modelo do aparelho"
            onChange={(e) => {
              const value = e.target.value
              setTicketDeviceModelPreset(value)
              if (value === 'custom') {
                setTicketDeviceModel('')
              } else if (value) {
                setTicketDeviceModel(value)
              } else {
                setTicketDeviceModel('')
              }
            }}
          >
            <MenuItem value="">
              <em>Selecione um modelo</em>
            </MenuItem>
            {DEVICE_MODELS.map((model) => (
              <MenuItem key={model} value={model}>
                {model}
              </MenuItem>
            ))}
            <MenuItem value="custom">Outro modelo...</MenuItem>
          </Select>
        </FormControl>
        {ticketDeviceModelPreset === 'custom' && (
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Informe o modelo do aparelho"
            value={ticketDeviceModel}
            onChange={(e) => setTicketDeviceModel(e.target.value)}
            placeholder="Ex.: Galaxy S20 FE"
          />
        )}
        <TextField
          fullWidth
          sx={{ mb: 2 }}
          label="Data da devolução"
          type="date"
          InputLabelProps={{ shrink: true }}
          value={ticketReturnDate}
          onChange={(e) => setTicketReturnDate(e.target.value)}
        />
        {ticketAction === 'without_charger' && (
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Condição do aparelho</InputLabel>
            <Select
              value={ticketDeviceCondition}
              label="Condição do aparelho"
              onChange={(e) => setTicketDeviceCondition(e.target.value)}
            >
              <MenuItem value="ok">Aparelho testado e aprovado</MenuItem>
              <MenuItem value="maintenance">Aparelho para manutenção</MenuItem>
            </Select>
          </FormControl>
        )}
        {ticketMustShowMaintenanceReason && (
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Motivo da manutenção"
            value={ticketMaintenanceReason}
            onChange={(e) => setTicketMaintenanceReason(e.target.value)}
          />
        )}
        {ticketMustShowResolution && (
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Resolução"
            multiline
            minRows={2}
            value={ticketResolutionText}
            onChange={(e) => setTicketResolutionText(e.target.value)}
          />
        )}
        <Button
          variant="contained"
          sx={{ mb: 2 }}
          onClick={handleCreateOffboardingTicket}
          disabled={ticketSubmitting}
        >
          {ticketSubmitting ? 'Abrindo chamado...' : 'Abrir chamado de desligamento'}
        </Button>
        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle1" gutterBottom>
          Chamados de desligamento abertos
        </Typography>
        {loadingOpenOffboardingTickets ? (
          <Box display="flex" alignItems="center" gap={1} sx={{ py: 1 }}>
            <CircularProgress size={20} />
            <Typography variant="body2">Carregando chamados...</Typography>
          </Box>
        ) : openOffboardingTickets.length === 0 ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            Nenhum chamado de desligamento aberto.
          </Alert>
        ) : (
          <TableContainer sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Colaborador</TableCell>
                  <TableCell>Equipe</TableCell>
                  <TableCell>Modelo</TableCell>
                  <TableCell>Ativo</TableCell>
                  <TableCell>Motivo do chamado</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Aberto em</TableCell>
                  <TableCell align="right">Ação</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {openOffboardingTickets.map((ticket) => {
                  const metadata = getTicketMetadata(ticket)
                  const reason = getOffboardingReason(ticket)
                  return (
                    <TableRow key={ticket.id}>
                      <TableCell>{ticket.id}</TableCell>
                      <TableCell>{metadata.employee_name || ticket.title || '-'}</TableCell>
                      <TableCell>{metadata.user_department || ticket.category || '-'}</TableCell>
                      <TableCell>{metadata.device_model || '-'}</TableCell>
                      <TableCell>{metadata.asset_tag || '-'}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                          {reason}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={TICKET_STATUS_LABELS[ticket.status] || ticket.status}
                          color={ticket.status === 'open' ? 'default' : 'warning'}
                        />
                      </TableCell>
                      <TableCell>{formatDateTime(ticket.created_at)}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="contained"
                          color="primary"
                          disabled={closingTicketId === ticket.id}
                          onClick={() => openCloseModal(ticket)}
                        >
                          {closingTicketId === ticket.id ? 'Encerrando...' : 'Encerrar chamado'}
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        <Divider sx={{ my: 2 }} />

        {loadingAssets && (
          <Box display="flex" alignItems="center" gap={1} sx={{ py: 2 }}>
            <CircularProgress size={24} />
            <Typography variant="body2">Carregando ativos do Gerenciamento de Ativos...</Typography>
          </Box>
        )}

        {!loadingAssets && snipeUser && assets.length === 0 && (
          <Alert severity="info">
            Nenhum ativo atribuído a este usuário no Gerenciamento de Ativos.
          </Alert>
        )}

        {!loadingAssets && snipeUser && assets.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle1" gutterBottom>
              Ativos a dar baixa
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Etiqueta / Nome</TableCell>
                    <TableCell>Condição</TableCell>
                    <TableCell>Observação</TableCell>
                    <TableCell align="right">Ação</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {assets.map((asset) => {
                    const tag = asset.asset_tag || asset.name || `ID ${asset.id}`
                    const cond = conditionByAsset[asset.id]
                    const isSubmitting = submitting[asset.id]
                    return (
                      <TableRow key={asset.id}>
                        <TableCell>
                          <Typography fontWeight={500}>{tag}</Typography>
                          {asset.serial && (
                            <Typography variant="caption" color="text.secondary">
                              {asset.serial}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <RadioGroup
                            row
                            value={cond === true ? 'manutencao' : cond === false ? 'ok' : ''}
                            onChange={(e) =>
                              setConditionByAsset((c) => ({
                                ...c,
                                [asset.id]: e.target.value === 'manutencao',
                              }))
                            }
                          >
                            <FormControlLabel
                              value="ok"
                              control={<Radio size="small" />}
                              label={
                                <Box display="flex" alignItems="center" gap={0.5}>
                                  <CheckCircleIcon color="success" fontSize="small" />
                                  Perfeitas condições
                                </Box>
                              }
                            />
                            <FormControlLabel
                              value="manutencao"
                              control={<Radio size="small" />}
                              label={
                                <Box display="flex" alignItems="center" gap={0.5}>
                                  <BuildIcon color="warning" fontSize="small" />
                                  Precisa manutenção
                                </Box>
                              }
                            />
                          </RadioGroup>
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            placeholder="Observação (opcional)"
                            value={noteByAsset[asset.id] || ''}
                            onChange={(e) =>
                              setNoteByAsset((n) => ({ ...n, [asset.id]: e.target.value }))
                            }
                            fullWidth
                          />
                        </TableCell>
                        <TableCell align="right">
                          <Button
                            variant="contained"
                            color="primary"
                            disabled={cond === undefined || isSubmitting}
                            onClick={() => handleDarBaixa(asset)}
                          >
                            {isSubmitting ? 'Enviando...' : 'Dar baixa'}
                          </Button>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
      </Paper>

      <Dialog open={closeModalOpen} onClose={() => setCloseModalOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Encerrar chamado</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {ticketToClose ? `Chamado ID ${ticketToClose.id}` : 'Chamado'}
          </Typography>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={4}
            label="Descrição de encerramento"
            placeholder="Descreva o que foi feito no encerramento"
            value={closeNote}
            onChange={(e) => setCloseNote(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCloseModalOpen(false)} disabled={closingTicketId !== null}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleCloseOffboardingTicket}
            disabled={closingTicketId !== null || !ticketToClose}
          >
            {closingTicketId !== null ? 'Encerrando...' : 'Confirmar encerramento'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default Desligamento
