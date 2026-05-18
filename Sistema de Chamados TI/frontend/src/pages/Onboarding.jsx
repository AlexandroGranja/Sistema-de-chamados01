// frontend/src/pages/Onboarding.jsx
import { useState, useEffect } from 'react'
import {
  Container, Typography, Paper, Box, TextField, Button,
  CircularProgress, Alert, Divider, InputAdornment,
  ToggleButton, ToggleButtonGroup, Collapse, Autocomplete,
} from '@mui/material'
import PersonAddIcon from '@mui/icons-material/PersonAdd'
import SearchIcon from '@mui/icons-material/Search'
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'
import GroupsIcon from '@mui/icons-material/Groups'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

// Autocomplete que permite selecionar opção existente ou digitar valor novo
const ComboField = ({ label, value, onChange, options, required, size = 'small', helperText }) => (
  <Autocomplete
    freeSolo
    options={options}
    value={value}
    onInputChange={(_, v) => onChange(v)}
    renderInput={(params) => (
      <TextField
        {...params}
        label={label}
        size={size}
        required={required}
        helperText={helperText}
      />
    )}
  />
)

const InfoRow = ({ label, value }) =>
  value ? (
    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
      <Typography variant="body2" color="text.secondary">{label}:</Typography>
      <Typography variant="body2" fontWeight={600}>{value}</Typography>
    </Box>
  ) : null

// Hook: carrega equipes/setores/gestores/empresas do banco uma vez
const useOpcoes = () => {
  const [opcoes, setOpcoes] = useState({ equipes: [], setores: [], gestores: [], empresas: [] })
  useEffect(() => {
    telefonesAPI.opcoes().then(setOpcoes).catch(() => {})
  }, [])
  return opcoes
}

// ── Modo A: Linha existente ──────────────────────────────────────────────────

const LinhaExistente = ({ opcoes }) => {
  const [numeroLinha, setNumeroLinha] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [linhaDados, setLinhaDados] = useState(null)
  const [linhaId, setLinhaId] = useState(null)
  const [form, setForm] = useState({ nome: '', codigo: '', email: '', cargo: '' })
  const [submitting, setSubmitting] = useState(false)
  const [resultado, setResultado] = useState(null)

  const set = (field) => (v) => setForm((prev) => ({ ...prev, [field]: v }))
  const setEv = (field) => (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleBuscar = async () => {
    const num = numeroLinha.trim()
    if (!num) { toast.error('Informe o número da linha.'); return }
    setBuscando(true)
    setLinhaDados(null)
    setLinhaId(null)
    setResultado(null)
    try {
      const data = await telefonesAPI.buscarLinhaPorNumero(num)
      if (!data.encontrado) { toast.error(data.mensagem); return }
      setLinhaDados(data.linha)
      setLinhaId(data.linha.id)
      setForm((prev) => ({ ...prev, cargo: data.linha.cargo || '' }))
      toast.success('Linha encontrada!')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Erro ao buscar linha.')
    } finally {
      setBuscando(false)
    }
  }

  const handleLimpar = () => {
    setNumeroLinha('')
    setLinhaDados(null)
    setLinhaId(null)
    setForm({ nome: '', codigo: '', email: '', cargo: '' })
    setResultado(null)
  }

  const handleSubmit = async () => {
    if (!linhaId) { toast.error('Busque uma linha antes de prosseguir.'); return }
    if (!form.nome.trim()) { toast.error('Nome é obrigatório.'); return }
    if (!form.codigo.trim()) { toast.error('Código / matrícula é obrigatório.'); return }
    setSubmitting(true)
    try {
      const data = await telefonesAPI.onboarding({
        numero_linha: numeroLinha.trim(),
        nome: form.nome.trim(),
        codigo: form.codigo.trim(),
        email: form.email.trim(),
        cargo: form.cargo.trim(),
        equipe: linhaDados?.equipe || '',
        gestor: linhaDados?.gestor || '',
        setor: linhaDados?.setor || '',
        empresa: linhaDados?.empresa || '',
      })
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Usuário cadastrado na linha com sucesso!')
      handleLimpar()
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao cadastrar usuário.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  const isVago = !linhaDados?.nome ||
    ['vago', 'manutencao', 'manutenção'].includes((linhaDados?.nome || '').toLowerCase().trim())

  return (
    <>
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>Número da Linha</Typography>
      <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start', mb: 2 }}>
        <TextField
          label="Número da linha"
          value={numeroLinha}
          onChange={(e) => setNumeroLinha(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleBuscar()}
          size="small" sx={{ width: 220 }}
          placeholder="21999990000"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <PhoneAndroidIcon fontSize="small" color="action" />
              </InputAdornment>
            ),
          }}
        />
        <Button variant="outlined" onClick={handleBuscar} disabled={buscando}
          startIcon={buscando ? <CircularProgress size={16} /> : <SearchIcon />}>
          Buscar
        </Button>
        {linhaDados && (
          <Button size="small" color="inherit" sx={{ alignSelf: 'center', color: 'text.secondary' }} onClick={handleLimpar}>
            Limpar
          </Button>
        )}
      </Box>

      {linhaDados && (
        <Box sx={{
          border: '1px solid',
          borderColor: isVago ? 'success.main' : 'warning.main',
          borderRadius: 2, p: 2,
          bgcolor: isVago ? 'success.50' : 'warning.50',
          mb: 3,
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <CheckCircleIcon color={isVago ? 'success' : 'warning'} fontSize="small" />
            <Typography variant="subtitle2" color={isVago ? 'success.dark' : 'warning.dark'} fontWeight={600}>
              {isVago
                ? `Linha ${linhaDados.linha} disponível`
                : `Linha ${linhaDados.linha} — atualmente com colaborador`}
            </Typography>
          </Box>
          <Divider sx={{ mb: 1.5 }} />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <GroupsIcon fontSize="small" color="action" />
            <Typography variant="caption" color="text.secondary">Equipe / Setor / Gestor</Typography>
          </Box>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5 }}>
            <InfoRow label="Equipe" value={linhaDados.equipe} />
            <InfoRow label="Setor" value={linhaDados.setor} />
            <InfoRow label="Gestor" value={linhaDados.gestor} />
            <InfoRow label="Empresa" value={linhaDados.empresa} />
            {!isVago && <InfoRow label="Colaborador atual" value={linhaDados.nome} />}
          </Box>
          {(linhaDados.aparelho || linhaDados.modelo) && (
            <>
              <Divider sx={{ my: 1 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                <PhoneAndroidIcon fontSize="small" color="action" />
                <Typography variant="caption" color="text.secondary">Aparelho</Typography>
              </Box>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5 }}>
                <InfoRow label="Modelo" value={linhaDados.modelo || linhaDados.aparelho} />
                <InfoRow label="Marca" value={linhaDados.marca} />
              </Box>
            </>
          )}
        </Box>
      )}

      {linhaDados && (
        <>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>Dados do Novo Colaborador</Typography>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
            <TextField required label="Nome Completo" value={form.nome} onChange={setEv('nome')} size="small" />
            <TextField required label="Código / Matrícula" value={form.codigo} onChange={setEv('codigo')} size="small" />
            <TextField label="Cargo" value={form.cargo} onChange={setEv('cargo')} size="small"
              helperText="Pré-preenchido da linha se disponível" />
            <TextField label="E-mail" value={form.email} onChange={setEv('email')} size="small" type="email" />
          </Box>
        </>
      )}

      {resultado && (
        <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
          {resultado.mensagem}
        </Alert>
      )}

      {linhaDados && (
        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button variant="contained" size="large" onClick={handleSubmit} disabled={submitting}
            startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <PersonAddIcon />}>
            Confirmar Cadastro
          </Button>
        </Box>
      )}
    </>
  )
}

// ── Modo B: Nova linha ───────────────────────────────────────────────────────

const EMPTY_NOVA = {
  numero_linha: '', nome: '', codigo: '', equipe: '', setor: '',
  gestor: '', empresa: '', cargo: '', email: '',
  imei_a: '', imei_b: '', marca: '', modelo: '', aparelho: '',
  numero_serie: '', ativo: '', chip: '', operadora: '',
}

const NovaLinha = ({ opcoes }) => {
  const [form, setForm] = useState(EMPTY_NOVA)
  const [mostrarAparelho, setMostrarAparelho] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [resultado, setResultado] = useState(null)

  const setEv = (field) => (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))
  const setVal = (field) => (v) => setForm((prev) => ({ ...prev, [field]: v ?? '' }))

  const handleSubmit = async () => {
    if (!form.numero_linha.trim()) { toast.error('Número da linha é obrigatório.'); return }
    if (!form.nome.trim()) { toast.error('Nome do colaborador é obrigatório.'); return }
    if (!form.codigo.trim()) { toast.error('Código / matrícula é obrigatório.'); return }
    setSubmitting(true)
    try {
      const data = await telefonesAPI.novaLinha(form)
      setResultado({ sucesso: true, mensagem: data.mensagem })
      toast.success('Linha criada com sucesso!')
      setForm(EMPTY_NOVA)
      setMostrarAparelho(false)
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Erro ao criar linha.'
      setResultado({ sucesso: false, mensagem: msg })
      toast.error(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      {/* Linha e colaborador */}
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>Linha e Colaborador</Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
        <TextField
          required label="Número da Linha" value={form.numero_linha}
          onChange={setEv('numero_linha')} size="small" placeholder="21999990000"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <PhoneAndroidIcon fontSize="small" color="action" />
              </InputAdornment>
            ),
          }}
        />
        <TextField required label="Nome Completo" value={form.nome} onChange={setEv('nome')} size="small" />
        <TextField required label="Código / Matrícula" value={form.codigo} onChange={setEv('codigo')} size="small" />
        <TextField label="Cargo" value={form.cargo} onChange={setEv('cargo')} size="small" />
        <TextField label="E-mail" value={form.email} onChange={setEv('email')} size="small" type="email"
          sx={{ gridColumn: '1 / -1' }} />
      </Box>

      {/* Equipe / Setor */}
      <Divider sx={{ mb: 2 }} />
      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
        <GroupsIcon fontSize="small" sx={{ mr: 0.75, verticalAlign: 'middle' }} />
        Equipe / Setor
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
        Selecione uma opção existente ou digite para criar uma nova.
      </Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
        <ComboField
          label="Equipe" value={form.equipe}
          onChange={setVal('equipe')}
          options={opcoes.equipes}
        />
        <ComboField
          label="Setor" value={form.setor}
          onChange={setVal('setor')}
          options={opcoes.setores}
        />
        <ComboField
          label="Gestor" value={form.gestor}
          onChange={setVal('gestor')}
          options={opcoes.gestores}
        />
        <ComboField
          label="Empresa" value={form.empresa}
          onChange={setVal('empresa')}
          options={opcoes.empresas}
        />
        <TextField label="Operadora" value={form.operadora} onChange={setEv('operadora')} size="small" />
      </Box>

      {/* Aparelho (colapsável) */}
      <Divider sx={{ mb: 1 }} />
      <Button
        size="small" variant="text" color="inherit"
        startIcon={<PhoneAndroidIcon fontSize="small" />}
        onClick={() => setMostrarAparelho((v) => !v)}
        sx={{ mb: 1, color: 'text.secondary' }}
      >
        {mostrarAparelho ? 'Ocultar dados do aparelho' : 'Adicionar dados do aparelho (opcional)'}
      </Button>
      <Collapse in={mostrarAparelho}>
        <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2, mb: 3 }}>
          <TextField label="IMEI A" value={form.imei_a} onChange={setEv('imei_a')} size="small" />
          <TextField label="IMEI B" value={form.imei_b} onChange={setEv('imei_b')} size="small" />
          <TextField label="Marca" value={form.marca} onChange={setEv('marca')} size="small" />
          <TextField label="Modelo" value={form.modelo} onChange={setEv('modelo')} size="small" />
          <TextField label="Aparelho (descrição)" value={form.aparelho} onChange={setEv('aparelho')} size="small" />
          <TextField label="Número de Série" value={form.numero_serie} onChange={setEv('numero_serie')} size="small" />
          <TextField label="Ativo" value={form.ativo} onChange={setEv('ativo')} size="small" />
          <TextField label="Chip" value={form.chip} onChange={setEv('chip')} size="small" />
        </Box>
      </Collapse>

      {resultado && (
        <Alert severity={resultado.sucesso ? 'success' : 'error'} sx={{ mt: 2 }}>
          {resultado.mensagem}
        </Alert>
      )}

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" size="large" onClick={handleSubmit} disabled={submitting}
          startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <AddCircleOutlineIcon />}>
          Criar Linha
        </Button>
      </Box>
    </>
  )
}

// ── Componente principal ─────────────────────────────────────────────────────

const NovoUsuario = () => {
  const [modo, setModo] = useState('existente')
  const opcoes = useOpcoes()

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        <PersonAddIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
        Novo Usuário
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Atribua um colaborador a uma linha existente ou crie uma nova linha do zero.
      </Typography>

      <Paper sx={{ p: 3 }}>
        <ToggleButtonGroup
          value={modo} exclusive
          onChange={(_, v) => { if (v) setModo(v) }}
          size="small" sx={{ mb: 3 }}
        >
          <ToggleButton value="existente" sx={{ gap: 0.75 }}>
            <SearchIcon fontSize="small" />
            Linha existente
          </ToggleButton>
          <ToggleButton value="nova" sx={{ gap: 0.75 }}>
            <AddCircleOutlineIcon fontSize="small" />
            Nova linha
          </ToggleButton>
        </ToggleButtonGroup>

        {modo === 'existente'
          ? <LinhaExistente opcoes={opcoes} />
          : <NovaLinha opcoes={opcoes} />}
      </Paper>
    </Container>
  )
}

export default NovoUsuario
