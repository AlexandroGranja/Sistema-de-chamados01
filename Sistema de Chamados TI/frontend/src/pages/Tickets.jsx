import { useEffect, useState } from 'react'
import { useSearchParams, useParams } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Divider,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import toast from 'react-hot-toast'
import { ticketsAPI, usersAPI } from '../services/api'
import StatusBadge from '../components/StatusBadge'

const STATUS_LABELS = {
  open: 'Aberto',
  in_analysis: 'Em análise',
  in_progress: 'Em andamento',
  waiting_user: 'Aguardando usuário',
  waiting_third_party: 'Aguardando terceiros',
  resolved: 'Resolvido',
  closed: 'Fechado',
  cancelled: 'Cancelado',
}

const STATUS_COLORS = {
  open: 'default',
  in_analysis: 'info',
  in_progress: 'primary',
  waiting_user: 'warning',
  waiting_third_party: 'secondary',
  resolved: 'success',
  closed: 'success',
  cancelled: 'default',
}

const CLOSED_STATUSES = ['closed', 'resolved', 'cancelled']
const formatDate = (value) => (value ? new Date(value).toLocaleString('pt-BR') : '-')
const ACTION_LABELS = {
  device_ok: 'Aparelho OK',
  offboarding_with_maintenance: 'Desligamento com manutenção',
  maintenance_only: 'Somente manutenção',
  without_charger: 'Recebido sem carregador',
  not_delivered: 'Não entregou aparelho e o carregador',
}

const DEVICE_CONDITION_LABELS = {
  ok: 'Em condições de uso',
  maintenance: 'Precisa manutenção',
}

const getMetadata = (ticket) => {
  if (!ticket?.equipment_info) return {}
  if (typeof ticket.equipment_info === 'object') return ticket.equipment_info
  try {
    return JSON.parse(ticket.equipment_info)
  } catch {
    return {}
  }
}

const getRequesterLevelLabel = (requester) => {
  if (!requester) return '-'
  const position = String(requester.position || '').toUpperCase()
  if (position === 'N1' || position === 'N2' || position === 'N3') return position
  if (requester.role === 'admin') return 'Admin'
  if (requester.role === 'technician') return 'Técnico'
  if (requester.role === 'supervisor') return 'Supervisor'
  return 'Usuário'
}

const getReasonFromTicket = (ticket) => {
  const metadata = getMetadata(ticket)
  return (
    metadata.maintenance_reason ||
    metadata.resolution_text ||
    ACTION_LABELS[metadata.action] ||
    ticket.internal_notes ||
    ''
  )
}

const extractAdditionalObservation = (description) => {
  if (!description) return ''
  const lines = String(description).split('\n')
  const obsLine = lines.find((line) => {
    const normalized = line.trim().toLowerCase()
    return normalized.startsWith('observacao:') || normalized.startsWith('observação:')
  })
  if (!obsLine) return ''
  return obsLine
    .replace(/^observacao:\s*/i, '')
    .replace(/^observação:\s*/i, '')
    .trim()
}

const getDescriptionWithoutDuplicatedHeader = (description) => {
  if (!description) return '-'
  const lines = String(description).split('\n')
  const filtered = lines
    .map((line) => {
      const trimmed = line.trim()
      const normalized = trimmed.toLowerCase()
      if (normalized.startsWith('ação:') || normalized.startsWith('acao:')) {
        return trimmed.replace(/^ação:\s*/i, '').replace(/^acao:\s*/i, '')
      }
      return line
        .replace(/\s*motivo(?:\s+manutenção)?\s*:\s*.*$/i, '')
        .replace(/\s*motivo(?:\s+manutencao)?\s*:\s*.*$/i, '')
    })
    .filter((line) => {
    const trimmed = line.trim().toLowerCase()
    return !(
      trimmed.startsWith('colaborador:') ||
      trimmed.startsWith('equipe:') ||
      trimmed.startsWith('data de devolução:') ||
      trimmed.startsWith('data de devolucao:') ||
      trimmed.startsWith('ativo:') ||
      trimmed.startsWith('modelo:') ||
      trimmed.startsWith('motivo:') ||
      trimmed.startsWith('motivo manutenção:') ||
      trimmed.startsWith('motivo manutencao:') ||
      trimmed.startsWith('condição do aparelho:') ||
      trimmed.startsWith('condicao do aparelho:')
    )
    })
  const result = filtered.join('\n').trim()
  return result || '-'
}

const buildOffboardingDescription = ({
  employeeName,
  team,
  returnDate,
  assetTag,
  deviceModel,
  action,
  reason,
  extraDescription,
}) => {
  const lines = [
    `Colaborador: ${employeeName || '-'}`,
    `Equipe: ${team || '-'}`,
    `Data de devolucao: ${returnDate || '-'}`,
    `Ativo: ${assetTag || '-'}`,
    `Modelo: ${deviceModel || '-'}`,
    `Acao: ${ACTION_LABELS[action] || action || '-'}`,
  ]

  if (reason) lines.push(`Motivo: ${reason}`)
  if (extraDescription) lines.push(`Observacao: ${extraDescription}`)

  return lines.join('\n')
}

const InfoItem = ({ label, value, full = false }) => (
  <Box
    sx={{
      py: 0.12,
      gridColumn: full ? { xs: '1', md: '1 / -1' } : undefined,
    }}
  >
    <Typography variant="caption" sx={{ lineHeight: 1.25 }}>
      <strong>{label}:</strong> {value || '-'}
    </Typography>
  </Box>
)

/**
 * Card completo (colaborador, modelo/condição do aparelho, nível, etc.):
 * apenas quando quem abriu o chamado é **administrador**, ou quando é fluxo de **desligamento**
 * (`metadata.action`). Demais perfis (usuário comum/requester, técnico, supervisor, …) → card resumido.
 */
const useFullDetailTicketCard = (requester, metadata) => {
  if (metadata?.action) return true
  return requester?.role === 'admin'
}

const isSimpleTicketCard = (requester, metadata) => !useFullDetailTicketCard(requester, metadata)

const statusKey = (ticket) =>
  typeof ticket.status === 'string' ? ticket.status : ticket.status?.value || ''

const TicketCard = ({ ticket, closed = false, isUpdating = false, onEdit }) => {
  const metadata = getMetadata(ticket)
  const requester = ticket._requester
  const requesterName = requester?.name || '-'
  const requesterLevel = getRequesterLevelLabel(requester)
  const simpleCard = isSimpleTicketCard(requester, metadata)
  const action = metadata.action
  const actionLabel = ACTION_LABELS[action] || '-'
  const technicalReason = metadata.maintenance_reason || metadata.resolution_text || '-'
  const deviceModel = metadata.device_model || '-'
  const employeeName = metadata.employee_name || '-'
  const deviceCondition = (
    action === 'not_delivered'
      ? '-'
      : (action === 'offboarding_with_maintenance' || action === 'maintenance_only'
      ? technicalReason
      : (DEVICE_CONDITION_LABELS[metadata.device_condition] || metadata.device_condition || '-'))
  )
  const teamName = metadata.user_department || ticket.category || '-'
  const displayDescription = getDescriptionWithoutDuplicatedHeader(ticket.description)
  const compactDescription = displayDescription.replace(/\n+/g, ' ').trim()
  const reason = actionLabel !== '-' ? actionLabel : (ticket.internal_notes || '-')
  const sk = statusKey(ticket)

  if (simpleCard) {
    const displayDescription = getDescriptionWithoutDuplicatedHeader(ticket.description)
    const compactDescription = displayDescription.replace(/\n+/g, ' ').trim()
    const setor = ticket.category || metadata.user_department || '-'
    const local = ticket.location || '-'
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 1.1,
          borderRadius: 2,
          borderColor: 'divider',
          bgcolor: 'background.paper',
          boxShadow: 0,
          opacity: closed ? 0.96 : 1,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" gap={1} sx={{ mb: 0.8 }}>
          <Box>
            <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 0.4 }}>
              Chamado #{ticket.id}
            </Typography>
            <Typography variant="caption" color="text.secondary" fontWeight={600} display="block" sx={{ mt: 0.5 }}>
              Título / motivo do chamado
            </Typography>
            <Typography variant="subtitle1" fontWeight={700} sx={{ lineHeight: 1.3 }}>
              {ticket.title || 'Sem título'}
            </Typography>
          </Box>
          <StatusBadge status={sk} label={STATUS_LABELS[sk] || sk} />
        </Box>

        <Box
          sx={{
            mb: 1,
            px: 1,
            py: 0.75,
            borderRadius: 1.2,
            bgcolor: 'rgba(242, 194, 48, 0.10)',
            border: '1px solid',
            borderColor: 'rgba(242, 194, 48, 0.45)',
            borderLeft: '4px solid',
            borderLeftColor: 'primary.main',
          }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.25 }}>
            Descrição
          </Typography>
          <Typography
            variant="body2"
            sx={{
              lineHeight: 1.35,
              display: '-webkit-box',
              WebkitLineClamp: 8,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {compactDescription || '—'}
          </Typography>
        </Box>

        <Box
          sx={{
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1.5,
            p: 0.85,
            flex: 1,
          }}
        >
          <Typography variant="overline" color="text.secondary" sx={{ fontSize: 10, letterSpacing: 0.5 }}>
            Dados do chamado
          </Typography>
          <InfoItem label="Aberto por" value={requesterName} />
          <InfoItem label="Setor" value={setor} />
          <InfoItem label="Local" value={local} />
          <InfoItem label="Criado em" value={formatDate(ticket.created_at)} />
          {closed ? (
            <InfoItem label="Finalizado em" value={formatDate(ticket.closed_at || ticket.resolved_at)} />
          ) : (
            <InfoItem label="Última atualização" value={formatDate(ticket.updated_at)} />
          )}
        </Box>

        {closed && (
          <Box
            sx={{
              mt: 0.8,
              px: 1,
              py: 0.65,
              borderRadius: 1.2,
              bgcolor: 'rgba(56, 142, 60, 0.08)',
              border: '1px solid',
              borderColor: 'rgba(56, 142, 60, 0.35)',
              borderLeft: '4px solid',
              borderLeftColor: 'success.main',
            }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.2 }}>
              Fechamento do chamado
            </Typography>
            <Typography variant="body2" sx={{ lineHeight: 1.25 }}>
              {ticket.internal_notes || 'Chamado encerrado sem descrição informada.'}
            </Typography>
          </Box>
        )}

        <Divider sx={{ my: 0.6 }} />

        <Box display="flex" justifyContent="flex-end" sx={{ mt: 'auto', pt: 0.5 }}>
          <Button
            size="small"
            variant="contained"
            color="primary"
            onClick={() => onEdit?.(ticket)}
            disabled={isUpdating}
            sx={{ fontWeight: 700 }}
            fullWidth
          >
            Editar chamado
          </Button>
        </Box>
      </Paper>
    )
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.1,
        borderRadius: 2,
        borderColor: 'divider',
        bgcolor: 'background.paper',
        boxShadow: 0,
        opacity: closed ? 0.96 : 1,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="center" gap={1} sx={{ mb: 0.6 }}>
        <Box>
          <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 0.4 }}>
            ID / Número #{ticket.id}
          </Typography>
          <Typography variant="subtitle2" fontWeight={700}>
            {ticket.title}
          </Typography>
        </Box>
        <StatusBadge status={sk} label={STATUS_LABELS[sk] || sk} />
      </Box>

      <Box
        sx={{
          mb: 0.8,
          px: 1,
          py: 0.65,
          borderRadius: 1.2,
          bgcolor: 'rgba(242, 194, 48, 0.10)',
          border: '1px solid',
          borderColor: 'rgba(242, 194, 48, 0.45)',
          borderLeft: '4px solid',
          borderLeftColor: 'primary.main',
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.2 }}>
          Descrição
        </Typography>
        <Typography
          variant="body2"
          sx={{
            lineHeight: 1.25,
            display: '-webkit-box',
            WebkitLineClamp: 5,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {compactDescription}
        </Typography>
      </Box>

      <Box display="grid" gridTemplateColumns="1fr" gap={0.8} sx={{ flex: 1 }}>
        <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1.5, p: 0.75 }}>
          <Typography variant="overline" color="text.secondary" sx={{ fontSize: 10, letterSpacing: 0.5 }}>
            Abertura do chamado
          </Typography>
          <InfoItem label="Criado por" value={requesterName} />
          <InfoItem label="Nível do usuário" value={requesterLevel} />
          <InfoItem label="Criado em" value={formatDate(ticket.created_at)} />
          {closed ? (
            <InfoItem label="Finalizado em" value={formatDate(ticket.closed_at || ticket.resolved_at)} />
          ) : (
            <InfoItem label="Última atualização" value={formatDate(ticket.updated_at)} />
          )}
        </Box>

        <Box sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 1.5, p: 0.75 }}>
          <Typography variant="overline" color="text.secondary" sx={{ fontSize: 10, letterSpacing: 0.5 }}>
            Dados do colaborador
          </Typography>
          <InfoItem label="Colaborador" value={employeeName} />
          <InfoItem label="Equipe" value={teamName} />
          <InfoItem label="Modelo do aparelho" value={deviceModel} />
          <InfoItem label="Condição do aparelho" value={deviceCondition} />
          <InfoItem label="Motivo do chamado" value={reason} />
        </Box>
      </Box>

      {closed && (
        <Box
          sx={{
            mt: 0.8,
            px: 1,
            py: 0.65,
            borderRadius: 1.2,
            bgcolor: 'rgba(56, 142, 60, 0.08)',
            border: '1px solid',
            borderColor: 'rgba(56, 142, 60, 0.35)',
            borderLeft: '4px solid',
            borderLeftColor: 'success.main',
          }}
        >
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.2 }}>
            Fechamento do chamado
          </Typography>
          <Typography variant="body2" sx={{ lineHeight: 1.25 }}>
            {ticket.internal_notes || 'Chamado encerrado sem descrição informada.'}
          </Typography>
        </Box>
      )}

      <Divider sx={{ my: 0.6 }} />

      <Box display="flex" justifyContent="flex-end" sx={{ mt: 'auto', pt: 0.5 }}>
        <Button
          size="small"
          variant="contained"
          color="primary"
          onClick={() => onEdit?.(ticket)}
          disabled={isUpdating}
          sx={{ fontWeight: 700 }}
          fullWidth
        >
          Editar chamado
        </Button>
      </Box>
    </Paper>
  )
}

const Tickets = () => {
  const { ticketId: routeTicketId } = useParams()
  const [searchParams] = useSearchParams()
  const [loading, setLoading] = useState(false)
  const [tickets, setTickets] = useState([])
  const [updatingTicketId, setUpdatingTicketId] = useState(null)
  const [searchTicketId, setSearchTicketId] = useState('')
  const [searchEmployeeName, setSearchEmployeeName] = useState('')
  const [editingTicket, setEditingTicket] = useState(null)
  const [editStatus, setEditStatus] = useState('open')
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editTeam, setEditTeam] = useState('')
  const [editDeviceModel, setEditDeviceModel] = useState('')
  const [editAssetTag, setEditAssetTag] = useState('')
  const [editReason, setEditReason] = useState('')
  const [editNote, setEditNote] = useState('')
  const [editIsOffboarding, setEditIsOffboarding] = useState(false)

  const loadTickets = async () => {
    setLoading(true)
    try {
      const data = await ticketsAPI.getAll({ limit: 50 })
      const rows = Array.isArray(data) ? data : []
      const missingIds = [
        ...new Set(
          rows.filter((t) => !t.requester_name).map((t) => t.requester_id).filter(Boolean)
        ),
      ]
      const requesterMap = {}
      if (missingIds.length > 0) {
        const requesterPairs = await Promise.allSettled(
          missingIds.map(async (id) => [id, await usersAPI.getById(id)])
        )
        requesterPairs.forEach((res) => {
          if (res.status === 'fulfilled') {
            const [id, user] = res.value
            requesterMap[id] = user
          }
        })
      }
      setTickets(
        rows.map((t) => ({
          ...t,
          _requester: t.requester_name
            ? { name: t.requester_name, role: t.requester_role || 'user' }
            : requesterMap[t.requester_id] || null,
        }))
      )
    } catch (err) {
      toast.error('Não foi possível carregar os chamados.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTickets()
  }, [])

  useEffect(() => {
    const tid =
      routeTicketId ||
      searchParams.get('ticket_id') ||
      searchParams.get('chamado_id') ||
      ''
    if (tid) {
      setSearchTicketId(String(tid).trim())
    }
  }, [routeTicketId, searchParams])

  const openEditModal = (ticket) => {
    const metadata = getMetadata(ticket)
    const isOffboarding = Boolean(metadata.action)
    setEditingTicket(ticket)
    setEditIsOffboarding(isOffboarding)
    setEditStatus(ticket.status || 'open')
    setEditTitle(ticket.title || '')
    setEditDescription(isOffboarding ? extractAdditionalObservation(ticket.description) : ticket.description || '')
    setEditTeam(metadata.user_department || ticket.category || '')
    setEditDeviceModel(metadata.device_model || '')
    setEditAssetTag(metadata.asset_tag || '')
    setEditReason(getReasonFromTicket(ticket))
    setEditNote(ticket.internal_notes || '')
  }

  const closeEditModal = () => {
    setEditingTicket(null)
    setEditStatus('open')
    setEditTitle('')
    setEditDescription('')
    setEditTeam('')
    setEditDeviceModel('')
    setEditAssetTag('')
    setEditReason('')
    setEditNote('')
    setEditIsOffboarding(false)
  }

  const handleSaveTicket = async (ticket) => {
    setUpdatingTicketId(ticket.id)
    try {
      const metadata = getMetadata(ticket)
      const baseDescription = editIsOffboarding
        ? buildOffboardingDescription({
            employeeName: metadata.employee_name,
            team: editTeam.trim(),
            returnDate: metadata.return_date,
            assetTag: editAssetTag.trim(),
            deviceModel: editDeviceModel.trim(),
            action: metadata.action,
            reason: editReason.trim(),
            extraDescription: editDescription.trim(),
          })
        : editDescription.trim()

      const updated = await ticketsAPI.update(ticket.id, {
        title: editTitle.trim(),
        description: baseDescription,
        status: editStatus,
        user_department: editTeam.trim() || null,
        device_model: editDeviceModel.trim() || null,
        asset_tag: editAssetTag.trim() || null,
        reason: editReason.trim() || null,
        internal_notes: editNote,
      })
      setTickets((prev) => prev.map((t) => (t.id === ticket.id ? updated : t)))
      toast.success(`Chamado ID ${ticket.id} atualizado com sucesso.`)
      closeEditModal()
    } catch (err) {
      toast.error('Não foi possível atualizar o chamado.')
    } finally {
      setUpdatingTicketId(null)
    }
  }

  const filteredTickets = tickets.filter((ticket) => {
    const metadata = getMetadata(ticket)
    const employeeName = String(metadata.employee_name || '').toLowerCase()
    const byId = searchTicketId.trim()
      ? String(ticket.id).includes(searchTicketId.trim())
      : true
    const byEmployee = searchEmployeeName.trim()
      ? employeeName.includes(searchEmployeeName.trim().toLowerCase())
      : true
    return byId && byEmployee
  })

  const openTickets = filteredTickets.filter((t) => !CLOSED_STATUSES.includes(t.status))
  const closedTickets = filteredTickets.filter((t) => CLOSED_STATUSES.includes(t.status))

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Chamados
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Visualização dos chamados abertos no sistema.
      </Typography>

      <Paper sx={{ p: 3, borderRadius: 2 }}>
        <Box display="grid" gridTemplateColumns={{ xs: '1fr', md: '1fr 1fr' }} gap={1.5} sx={{ mb: 2 }}>
          <TextField
            size="small"
            label="Pesquisar por ID do chamado"
            placeholder="Ex.: 12"
            value={searchTicketId}
            onChange={(e) => setSearchTicketId(e.target.value)}
          />
          <TextField
            size="small"
            label="Pesquisar por nome do usuário"
            placeholder="Ex.: Alexandre"
            value={searchEmployeeName}
            onChange={(e) => setSearchEmployeeName(e.target.value)}
          />
        </Box>

        {loading ? (
          <Alert severity="info">Carregando chamados...</Alert>
        ) : filteredTickets.length === 0 ? (
          <Alert severity="warning">Nenhum chamado encontrado.</Alert>
        ) : (
          <Stack spacing={2.5}>
            <Typography variant="h6">
              Abertos ({openTickets.length})
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: {
                  xs: '1fr',
                  sm: 'repeat(2, minmax(0, 1fr))',
                  lg: 'repeat(3, minmax(0, 1fr))',
                },
                gap: 2,
                alignItems: 'stretch',
              }}
            >
              {openTickets.map((ticket) => (
                <TicketCard
                  key={ticket.id}
                  ticket={ticket}
                  closed={false}
                  isUpdating={updatingTicketId === ticket.id}
                  onEdit={openEditModal}
                />
              ))}
            </Box>

            <Typography variant="h6" sx={{ mt: 1 }}>
              Fechados ({closedTickets.length})
            </Typography>
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: {
                  xs: '1fr',
                  sm: 'repeat(2, minmax(0, 1fr))',
                  lg: 'repeat(3, minmax(0, 1fr))',
                },
                gap: 2,
                alignItems: 'stretch',
              }}
            >
              {closedTickets.map((ticket) => (
                <TicketCard
                  key={ticket.id}
                  ticket={ticket}
                  closed
                  isUpdating={updatingTicketId === ticket.id}
                  onEdit={openEditModal}
                />
              ))}
            </Box>
          </Stack>
        )}
      </Paper>

      <Dialog open={Boolean(editingTicket)} onClose={closeEditModal} fullWidth maxWidth="sm">
        <DialogTitle>Editar chamado</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {editingTicket ? `Chamado ID ${editingTicket.id}` : ''}
          </Typography>
          <FormControl fullWidth sx={{ mb: 2, mt: 1 }}>
            <InputLabel>Status</InputLabel>
            <Select value={editStatus} label="Status" onChange={(e) => setEditStatus(e.target.value)}>
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Título do chamado"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
          />
          {!editIsOffboarding && (
            <TextField
              fullWidth
              sx={{ mb: 2 }}
              label="Descrição"
              multiline
              minRows={3}
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
            />
          )}
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Equipe"
            value={editTeam}
            onChange={(e) => setEditTeam(e.target.value)}
          />
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Modelo do aparelho"
            value={editDeviceModel}
            onChange={(e) => setEditDeviceModel(e.target.value)}
          />
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Ativo (patrimônio/série)"
            value={editAssetTag}
            onChange={(e) => setEditAssetTag(e.target.value)}
          />
          <TextField
            fullWidth
            sx={{ mb: 2 }}
            label="Motivo do chamado"
            multiline
            minRows={2}
            value={editReason}
            onChange={(e) => setEditReason(e.target.value)}
          />
          {(!editIsOffboarding || CLOSED_STATUSES.includes(editStatus)) && (
            <TextField
              fullWidth
              sx={{ mb: editIsOffboarding ? 2 : 0 }}
              multiline
              minRows={3}
              label={CLOSED_STATUSES.includes(editStatus) ? 'Descrição de encerramento' : 'Observação da edição'}
              placeholder={
                CLOSED_STATUSES.includes(editStatus)
                  ? 'Descreva claramente como o chamado foi encerrado'
                  : 'Descreva a atualização do chamado'
              }
              helperText={
                CLOSED_STATUSES.includes(editStatus)
                  ? 'Esse texto aparece em destaque no card quando o chamado estiver fechado.'
                  : undefined
              }
              value={editNote}
              onChange={(e) => setEditNote(e.target.value)}
            />
          )}
          {editIsOffboarding && (
            <TextField
              fullWidth
              sx={{ mt: 2 }}
              multiline
              minRows={3}
              label="Observação adicional (opcional)"
              placeholder="Informações complementares para a descrição padrão"
              helperText="Esta observação aparece no final da descrição padrão do chamado."
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeEditModal} disabled={updatingTicketId !== null}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={() => editingTicket && handleSaveTicket(editingTicket)}
            disabled={
              updatingTicketId !== null ||
              !editingTicket ||
              !editTitle.trim() ||
              (!editIsOffboarding && !editDescription.trim())
            }
          >
            {updatingTicketId !== null ? 'Salvando...' : 'Salvar alteração'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default Tickets

