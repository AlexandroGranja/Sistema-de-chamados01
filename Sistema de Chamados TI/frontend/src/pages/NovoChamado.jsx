import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from '@mui/material'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { ticketsAPI } from '../services/api'

/** Valores internos do select principal */
const LOCAL_PRINCIPAL = {
  JARDIM: 'jardim_america',
  RECREIO: 'recreio',
  COMERCIAL: 'comercial',
}

const SUB_UNIDADES = [
  { value: LOCAL_PRINCIPAL.JARDIM, label: 'Jardim América' },
  { value: LOCAL_PRINCIPAL.RECREIO, label: 'Recreio' },
]

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

function ticketStatusKey(ticket) {
  if (!ticket?.status) return ''
  return typeof ticket.status === 'string' ? ticket.status : ticket.status?.value || ''
}

function isTerminalStatus(ticket) {
  const k = ticketStatusKey(ticket).toLowerCase()
  return ['resolved', 'closed', 'cancelled'].includes(k)
}

function montarLocalizacao(principal, comercialUnidade) {
  if (!principal) return ''
  if (principal === LOCAL_PRINCIPAL.JARDIM) return 'Jardim América'
  if (principal === LOCAL_PRINCIPAL.RECREIO) return 'Recreio'
  if (principal === LOCAL_PRINCIPAL.COMERCIAL) {
    if (comercialUnidade === LOCAL_PRINCIPAL.JARDIM) return 'Comercial — Jardim América'
    if (comercialUnidade === LOCAL_PRINCIPAL.RECREIO) return 'Comercial — Recreio'
    return ''
  }
  return ''
}

/** Converte texto salvo em `location` de volta aos selects */
function parseLocationString(loc) {
  if (!loc) return { principal: '', comercial: '' }
  const s = String(loc).trim()
  if (s === 'Jardim América') return { principal: LOCAL_PRINCIPAL.JARDIM, comercial: '' }
  if (s === 'Recreio') return { principal: LOCAL_PRINCIPAL.RECREIO, comercial: '' }
  if (s.includes('Comercial')) {
    if (s.includes('Jardim')) return { principal: LOCAL_PRINCIPAL.COMERCIAL, comercial: LOCAL_PRINCIPAL.JARDIM }
    if (s.includes('Recreio')) return { principal: LOCAL_PRINCIPAL.COMERCIAL, comercial: LOCAL_PRINCIPAL.RECREIO }
  }
  return { principal: '', comercial: '' }
}

const NovoChamado = ({ portal = false }) => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [team, setTeam] = useState('')
  /** Jardim América, Recreio ou Comercial */
  const [localPrincipal, setLocalPrincipal] = useState('')
  /** Se principal = Comercial: Jardim América ou Recreio */
  const [comercialUnidade, setComercialUnidade] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [editingTicketId, setEditingTicketId] = useState(null)
  const [myTickets, setMyTickets] = useState([])
  const [loadingTickets, setLoadingTickets] = useState(false)

  const resetForm = useCallback(() => {
    setTitle('')
    setDescription('')
    setLocalPrincipal('')
    setComercialUnidade('')
    setEditingTicketId(null)
    const d = (user?.department || '').trim()
    setTeam(d)
  }, [user?.department])

  const loadMyTickets = useCallback(async () => {
    if (!portal) return
    setLoadingTickets(true)
    try {
      const rows = await ticketsAPI.getAll({ limit: 50 })
      setMyTickets(Array.isArray(rows) ? rows : [])
    } catch {
      setMyTickets([])
    } finally {
      setLoadingTickets(false)
    }
  }, [portal])

  // Preenche "Equipe / Setor" com o setor cadastrado no perfil (department)
  useEffect(() => {
    if (editingTicketId) return
    const d = (user?.department || '').trim()
    if (d) setTeam(d)
  }, [user?.id, user?.department, editingTicketId])

  useEffect(() => {
    loadMyTickets()
  }, [loadMyTickets])

  const openTicketForEdit = (ticket) => {
    if (isTerminalStatus(ticket)) {
      toast.error('Este chamado não pode mais ser editado.')
      return
    }
    setEditingTicketId(ticket.id)
    setTitle(ticket.title || '')
    setDescription(ticket.description || '')
    setTeam(ticket.category || '')
    const { principal, comercial } = parseLocationString(ticket.location || '')
    setLocalPrincipal(principal)
    setComercialUnidade(comercial)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const trimmedTitle = title.trim()
    const trimmedDescription = description.trim()

    if (!trimmedTitle || !trimmedDescription) {
      toast.error('Título e descrição são obrigatórios.')
      return
    }

    const locationStr = montarLocalizacao(localPrincipal, comercialUnidade)
    if (localPrincipal === LOCAL_PRINCIPAL.COMERCIAL && !comercialUnidade) {
      toast.error('Em Comercial, informe se o atendimento é no Jardim América ou no Recreio.')
      return
    }

    setSubmitting(true)
    try {
      if (editingTicketId) {
        await ticketsAPI.update(editingTicketId, {
          title: trimmedTitle,
          description: trimmedDescription,
          category: team.trim() || null,
          location: locationStr || null,
        })
        toast.success('Chamado atualizado com sucesso.')
        resetForm()
        await loadMyTickets()
        return
      }

      const payload = {
        title: trimmedTitle,
        description: trimmedDescription,
        category: team.trim() || null,
        location: locationStr || null,
      }

      const ticket = await ticketsAPI.create(payload)
      toast.success(`Chamado #${ticket.id} registrado com sucesso.`)
      resetForm()
      await loadMyTickets()
      if (!portal) {
        navigate('/tickets')
      }
    } catch (error) {
      console.error('Erro ao salvar chamado:', error)
      const msg = error?.response?.data?.detail
      toast.error(typeof msg === 'string' ? msg : 'Não foi possível salvar. Tente novamente.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = () => {
    if (editingTicketId) {
      resetForm()
      return
    }
    navigate(portal ? '/portal/novo-chamado' : '/tickets')
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {editingTicketId ? `Editar chamado #${editingTicketId}` : 'Diversos de TI'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {editingTicketId
            ? 'Altere título, descrição, setor ou local enquanto o chamado não estiver resolvido, encerrado ou cancelado.'
            : 'Canal de atendimento para colaboradores de outros setores. Use este formulário para solicitar suporte de TI — acesso a sistemas, equipamentos, dúvidas, ajustes e qualquer outra demanda com a equipe de TI.'}
        </Typography>
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
          gap: 3,
          alignItems: 'flex-start',
        }}
      >
        <Paper
          component="form"
          onSubmit={handleSubmit}
          sx={{
            p: 3,
            borderRadius: 2,
            display: 'flex',
            flexDirection: 'column',
            gap: 2.2,
            boxShadow: (theme) => theme.shadows[1],
            border: (theme) => `1px solid ${theme.palette.divider}`,
            flex: 1,
            minWidth: 0,
          }}
        >
          {editingTicketId ? (
            <Alert severity="warning" sx={{ mb: 0 }}>
              Você está editando este chamado. Após a TI alterar o status para <strong>resolvido</strong>,{' '}
              <strong>encerrado</strong> ou <strong>cancelado</strong>, a edição pelo portal será bloqueada.
            </Alert>
          ) : (
            <Alert severity="info" sx={{ mb: 1 }}>
              <strong>Título</strong> e <strong>Descrição</strong> são obrigatórios. Informe o máximo de detalhes
              possível para agilizar o atendimento. Os demais campos ajudam a encaminhar para a equipe correta.
            </Alert>
          )}

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: '1.5fr 1fr' },
              gap: 3,
            }}
          >
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Dados principais do chamado
              </Typography>
              <TextField
                label="Título do chamado *"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                fullWidth
                placeholder="Ex.: Erro ao acessar o sistema de vendas"
                sx={{ mb: 2 }}
              />

              <TextField
                label="Descrição detalhada *"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                fullWidth
                multiline
                minRows={5}
                placeholder="Descreva o que está acontecendo, quando começou, mensagens de erro, usuários impactados, etc."
              />
            </Box>

            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Contexto do atendimento (opcional)
              </Typography>
              <TextField
                label="Equipe / Setor"
                value={team}
                onChange={(e) => setTeam(e.target.value)}
                fullWidth
                placeholder="Ex.: TI, Financeiro, Vendas"
                helperText={
                  !editingTicketId && (user?.department || '').trim()
                    ? 'Preenchido com o setor do seu cadastro; você pode alterar se precisar.'
                    : undefined
                }
                sx={{ mb: 2 }}
              />
              <FormControl
                fullWidth
                sx={{ mb: localPrincipal === LOCAL_PRINCIPAL.COMERCIAL ? 1.5 : 2 }}
              >
                <InputLabel id="local-principal-label">Local / Ponto de atendimento</InputLabel>
                <Select
                  labelId="local-principal-label"
                  label="Local / Ponto de atendimento"
                  value={localPrincipal}
                  onChange={(e) => {
                    const v = e.target.value
                    setLocalPrincipal(v)
                    if (v !== LOCAL_PRINCIPAL.COMERCIAL) setComercialUnidade('')
                  }}
                >
                  <MenuItem value="">
                    <em>Selecione (opcional)</em>
                  </MenuItem>
                  <MenuItem value={LOCAL_PRINCIPAL.JARDIM}>Jardim América</MenuItem>
                  <MenuItem value={LOCAL_PRINCIPAL.RECREIO}>Recreio</MenuItem>
                  <MenuItem value={LOCAL_PRINCIPAL.COMERCIAL}>Comercial</MenuItem>
                </Select>
              </FormControl>

              {localPrincipal === LOCAL_PRINCIPAL.COMERCIAL ? (
                <FormControl fullWidth required sx={{ mb: 2 }}>
                  <InputLabel id="comercial-unidade-label">Comercial — onde se encontra?</InputLabel>
                  <Select
                    labelId="comercial-unidade-label"
                    label="Comercial — onde se encontra?"
                    value={comercialUnidade}
                    onChange={(e) => setComercialUnidade(e.target.value)}
                  >
                    <MenuItem value="">
                      <em>Selecione Jardim América ou Recreio</em>
                    </MenuItem>
                    {SUB_UNIDADES.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ) : null}

              <Typography variant="caption" color="text.secondary">
                Essas informações ajudam a priorizar e encaminhar a solicitação para a equipe correta.
              </Typography>
            </Box>
          </Box>

          <Box display="flex" justifyContent="flex-end" gap={1} mt={1}>
            <Button type="button" variant="text" onClick={handleCancel} disabled={submitting}>
              {editingTicketId ? 'Cancelar edição' : 'Cancelar'}
            </Button>
            <Button type="submit" variant="contained" disabled={submitting}>
              {submitting
                ? 'Salvando...'
                : editingTicketId
                  ? 'Salvar alterações'
                  : 'Registrar solicitação'}
            </Button>
          </Box>
        </Paper>

        {portal ? (
          <Paper
            sx={{
              p: 2,
              width: { xs: '100%', md: 340 },
              flexShrink: 0,
              maxHeight: { md: '70vh' },
              overflow: 'auto',
            }}
          >
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>
              Meus chamados
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
              Status atual e edição (enquanto não estiver encerrado).
            </Typography>
            {loadingTickets ? (
              <Box display="flex" justifyContent="center" py={2}>
                <CircularProgress size={28} />
              </Box>
            ) : myTickets.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Nenhum chamado ainda.
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
                {myTickets.map((t) => {
                  const sk = ticketStatusKey(t)
                  const label = STATUS_LABELS[sk] || sk || '—'
                  const color = STATUS_COLORS[sk] || 'default'
                  const canEdit = !isTerminalStatus(t)
                  return (
                    <Paper key={t.id} variant="outlined" sx={{ p: 1.5 }}>
                      <Box display="flex" justifyContent="space-between" alignItems="flex-start" gap={1} mb={0.5}>
                        <Typography variant="body2" fontWeight={600} sx={{ lineHeight: 1.3 }}>
                          #{t.id} — {t.title || 'Sem título'}
                        </Typography>
                        <Chip size="small" label={label} color={color} sx={{ flexShrink: 0 }} />
                      </Box>
                      <Button
                        size="small"
                        variant="outlined"
                        fullWidth
                        disabled={!canEdit}
                        onClick={() => openTicketForEdit(t)}
                      >
                        {canEdit ? 'Editar' : 'Não editável'}
                      </Button>
                    </Paper>
                  )
                })}
              </Box>
            )}
          </Paper>
        ) : null}
      </Box>
    </Container>
  )
}

export default NovoChamado
