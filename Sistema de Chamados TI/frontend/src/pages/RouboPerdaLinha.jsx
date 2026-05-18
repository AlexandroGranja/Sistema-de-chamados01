// frontend/src/pages/RouboPerdaLinha.jsx
import { useState } from 'react'
import {
  Container, Typography, Paper, Box, TextField, Button,
  CircularProgress, Alert, Divider, RadioGroup, FormControlLabel,
  Radio, FormLabel,
} from '@mui/material'
import ReportProblemIcon from '@mui/icons-material/ReportProblem'
import LinhaSearch from '../components/LinhaSearch'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const RouboPerdaLinha = () => {
  const [linhaId, setLinhaId] = useState(null)
  const [cenario, setCenario] = useState('A')  // 'A' | 'B'
  const [form, setForm] = useState({
    imei_a: '', imei_b: '', marca: '', modelo: '',
    aparelho: '', numero_serie: '', ativo: '', chip: '',
    nova_linha: '', observacao: '',
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
    if (cenario === 'B' && !form.nova_linha.trim()) {
      toast.error('Informe o novo número da linha para o cenário B.')
      return
    }
    setSubmitting(true)
    try {
      const payload = {
        ...form,
        linha_id: linhaId,
        nova_linha: cenario === 'B' ? form.nova_linha : '',
      }
      const data = await telefonesAPI.rouboPenda(payload)
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Roubo/Perda registrado com sucesso!')
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao registrar roubo/perda.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <ReportProblemIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Roubo e Perda
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Registra substituição de aparelho por roubo ou perda.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Buscar Colaborador</Typography>
        <LinhaSearch
          onLinhaFound={(l) => {
            setLinhaId(l.id)
            setForm((prev) => ({
              ...prev,
              imei_a: l.imei_a || '',
              imei_b: l.imei_b || '',
              marca: l.marca || '',
              modelo: l.modelo || '',
              aparelho: l.aparelho || '',
              numero_serie: l.numero_serie || '',
              ativo: l.ativo || '',
              chip: l.chip || '',
            }))
          }}
          onLinhaClear={() => {
            setLinhaId(null)
            setForm({ imei_a: '', imei_b: '', marca: '', modelo: '', aparelho: '', numero_serie: '', ativo: '', chip: '', nova_linha: '', observacao: '' })
          }}
        />

        <Divider sx={{ my: 3 }} />
        <FormLabel component="legend" sx={{ mb: 1, fontWeight: 600 }}>Cenário</FormLabel>
        <RadioGroup row value={cenario} onChange={(e) => setCenario(e.target.value)}>
          <FormControlLabel value="A" control={<Radio />} label="A — Mesma linha, aparelho novo" />
          <FormControlLabel value="B" control={<Radio />} label="B — Linha nova + aparelho reserva" />
        </RadioGroup>

        {cenario === 'B' && (
          <TextField
            label="Novo número de linha" value={form.nova_linha}
            onChange={handleChange('nova_linha')} size="small"
            sx={{ mt: 1, width: 220 }} placeholder="21999990000"
          />
        )}

        <Divider sx={{ my: 3 }} />
        <Typography variant="subtitle1" fontWeight={600} gutterBottom>Dados do Novo Aparelho</Typography>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
          <TextField label="IMEI A" value={form.imei_a} onChange={handleChange('imei_a')} size="small" />
          <TextField label="IMEI B" value={form.imei_b} onChange={handleChange('imei_b')} size="small" />
          <TextField label="Marca" value={form.marca} onChange={handleChange('marca')} size="small" />
          <TextField label="Modelo" value={form.modelo} onChange={handleChange('modelo')} size="small" />
          <TextField label="Aparelho (descrição)" value={form.aparelho} onChange={handleChange('aparelho')} size="small" />
          <TextField label="Número de Série" value={form.numero_serie} onChange={handleChange('numero_serie')} size="small" />
          <TextField label="Ativo" value={form.ativo} onChange={handleChange('ativo')} size="small" />
          <TextField label="Chip" value={form.chip} onChange={handleChange('chip')} size="small" />
          <TextField label="Observação" value={form.observacao} onChange={handleChange('observacao')}
            size="small" multiline rows={2} sx={{ gridColumn: '1 / -1' }} />
        </Box>

        {resultado && (
          <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
            {resultado.mensagem}
          </Alert>
        )}

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained" color="warning" size="large"
            onClick={handleSubmit} disabled={submitting || !linhaId}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <ReportProblemIcon />}
          >
            Confirmar Roubo/Perda
          </Button>
        </Box>
      </Paper>
    </Container>
  )
}

export default RouboPerdaLinha
