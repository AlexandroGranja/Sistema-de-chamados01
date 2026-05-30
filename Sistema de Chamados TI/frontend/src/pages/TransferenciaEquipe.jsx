// frontend/src/pages/TransferenciaEquipe.jsx
import { useState } from 'react'
import {
  Container, Typography, Paper, Box, TextField, Button,
  CircularProgress, Alert, Divider, Checkbox, FormControlLabel,
} from '@mui/material'
import SwapHorizIcon from '@mui/icons-material/SwapHoriz'
import LinhaSearch from '../components/LinhaSearch'
import EditarNoGerenciamentoButton from '../components/EditarNoGerenciamentoButton'
import { useTicketContext } from '../hooks/useTicketContext'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const TransferenciaEquipe = () => {
  const { ticketId } = useTicketContext()
  const [linhaId, setLinhaId] = useState(null)
  const [linhaPreview, setLinhaPreview] = useState(null)
  const [isPromocao, setIsPromocao] = useState(false)
  const [form, setForm] = useState({
    equipe: '', setor: '', gestor: '', cargo: '', empresa: '', observacao: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [resultado, setResultado] = useState(null)

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async () => {
    if (!linhaId) {
      toast.error('Busque e selecione uma linha antes de prosseguir.')
      return
    }
    if (!form.equipe.trim() || !form.setor.trim() || !form.gestor.trim()) {
      toast.error('Equipe, setor e gestor são obrigatórios.')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        ...form,
        linha_id: linhaId,
        cargo: isPromocao ? form.cargo : '',
        ticket_id: ticketId || undefined,
      }
      const data = await telefonesAPI.transferencia(payload)
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Transferência registrada com sucesso!')
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao registrar transferência.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <SwapHorizIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Transferência entre Equipes
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Atualiza equipe, setor e gestor. Todos os outros dados do colaborador e aparelho são preservados.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Buscar Colaborador</Typography>
        <LinhaSearch
          onLinhaFound={(l) => {
            setLinhaId(l.id)
            setLinhaPreview(l)
            setForm((prev) => ({
              ...prev,
              equipe: l.equipe || '',
              setor: l.setor || '',
              gestor: l.gestor || '',
              cargo: l.cargo || '',
            }))
          }}
          onLinhaClear={() => {
            setLinhaId(null)
            setLinhaPreview(null)
            setForm({ equipe: '', setor: '', gestor: '', cargo: '', empresa: '', observacao: '' })
          }}
        />

        {linhaPreview && (
          <Box sx={{ mt: 2 }}>
            <EditarNoGerenciamentoButton
              linha={linhaPreview.linha || ''}
              equipe={linhaPreview.equipe || ''}
            />
          </Box>
        )}

        <Divider sx={{ my: 3 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Nova Equipe</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <TextField required label="Equipe" value={form.equipe}
            onChange={handleChange('equipe')} size="small" />
          <TextField required label="Setor" value={form.setor}
            onChange={handleChange('setor')} size="small" />
          <TextField required label="Gestor" value={form.gestor}
            onChange={handleChange('gestor')} size="small" />
          <TextField label="Empresa (se mudar)" value={form.empresa}
            onChange={handleChange('empresa')} size="small" />
        </Box>

        <FormControlLabel
          sx={{ mt: 2 }}
          control={<Checkbox checked={isPromocao} onChange={(e) => setIsPromocao(e.target.checked)} />}
          label="É promoção? (alterar cargo)"
        />

        {isPromocao && (
          <TextField label="Novo Cargo" value={form.cargo}
            onChange={handleChange('cargo')} size="small"
            sx={{ ml: 4, width: 280 }} />
        )}

        <TextField label="Observação" value={form.observacao}
          onChange={handleChange('observacao')} size="small"
          fullWidth multiline rows={2} sx={{ mt: 2 }} />

        {resultado && (
          <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
            {resultado.mensagem}
          </Alert>
        )}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained" size="large" onClick={handleSubmit}
            disabled={submitting || !linhaId}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <SwapHorizIcon />}
          >
            Confirmar Transferência
          </Button>
        </Box>
      </Paper>
    </Container>
  )
}

export default TransferenciaEquipe
