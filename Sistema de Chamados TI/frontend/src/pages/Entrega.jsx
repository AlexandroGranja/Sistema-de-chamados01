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
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Autocomplete,
} from '@mui/material'
import { desligamentoAPI } from '../services/api'
import toast from 'react-hot-toast'
import AddCircleIcon from '@mui/icons-material/AddCircle'

const Entrega = () => {
  const [snipeConfigured, setSnipeConfigured] = useState(true)
  const [loading, setLoading] = useState(false)
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [loadingAssets, setLoadingAssets] = useState(false)
  const [snipeUsers, setSnipeUsers] = useState([])
  const [availableAssets, setAvailableAssets] = useState([])
  const [selectedSnipeUser, setSelectedSnipeUser] = useState(null)
  const [selectedAsset, setSelectedAsset] = useState(null)
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [userSearch, setUserSearch] = useState('')
  const [mode, setMode] = useState('existing')
  const [newCollaboratorName, setNewCollaboratorName] = useState('')
  const [assetTagInput, setAssetTagInput] = useState('')
  const [diagMessage, setDiagMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const res = await desligamentoAPI.getSnipeStatus()
        console.log('[Entrega] snipe-status resposta:', res, 'configured=', res?.configured)
        if (!cancelled) setSnipeConfigured(Boolean(res?.configured))
      } catch (err) {
        console.warn('[Entrega] snipe-status erro:', err?.response?.status, err?.message, err?.response?.data)
        if (!cancelled) setSnipeConfigured(false)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!snipeConfigured) return
    let cancelled = false
    setLoadingUsers(true)
    desligamentoAPI.getSnipeUsers(userSearch)
      .then((r) => { if (!cancelled) setSnipeUsers(r?.data || []) })
      .catch(() => { if (!cancelled) setSnipeUsers([]) })
      .finally(() => { if (!cancelled) setLoadingUsers(false) })
  }, [snipeConfigured, userSearch])

  useEffect(() => {
    if (!snipeConfigured) return
    setLoadingAssets(true)
    desligamentoAPI.getAvailableAssets()
      .then((r) => setAvailableAssets(r?.data || []))
      .catch(() => setAvailableAssets([]))
      .finally(() => setLoadingAssets(false))
  }, [snipeConfigured])

  const runDiagnostics = async () => {
    try {
      const diag = await desligamentoAPI.getSnipeDiagnostics()
      const failed = (diag?.checks || []).filter((c) => !c.ok)
      if (failed.length === 0) {
        setDiagMessage('')
        return
      }
      const parts = failed.map((f) => `${f.endpoint}: ${f.status_code ?? 'erro'}`)
      setDiagMessage(
        `A API do Gerenciamento de Ativos retornou falha em ${parts.join(', ')}. Verifique a instância do Snipe e permissões do token.`
      )
    } catch {
      setDiagMessage('Não foi possível executar diagnóstico do Gerenciamento de Ativos.')
    }
  }

  useEffect(() => {
    if (!snipeConfigured) return
    if (!loadingUsers && !loadingAssets && snipeUsers.length === 0 && availableAssets.length === 0) {
      runDiagnostics()
    } else if (snipeUsers.length > 0 || availableAssets.length > 0) {
      setDiagMessage('')
    }
  }, [snipeConfigured, loadingUsers, loadingAssets, snipeUsers.length, availableAssets.length])

  const handleEntrega = async () => {
    setSubmitting(true)
    try {
      if (mode === 'existing') {
        if (!selectedSnipeUser?.id || !selectedAsset?.id) {
          toast.error('Selecione o colaborador e o ativo.')
          return
        }
        await desligamentoAPI.checkout({
          asset_id: selectedAsset.id,
          snipe_user_id: selectedSnipeUser.id,
          note: note || undefined,
        })
        toast.success(`Ativo ${selectedAsset.asset_tag || selectedAsset.name} entregue a ${selectedSnipeUser.name}.`)
        setSelectedAsset(null)
        setAvailableAssets((prev) => prev.filter((a) => a.id !== selectedAsset.id))
      } else {
        if (!newCollaboratorName.trim() || !assetTagInput.trim()) {
          toast.error('Informe nome completo e patrimônio do ativo.')
          return
        }
        const res = await desligamentoAPI.checkoutByTag({
          collaborator_name: newCollaboratorName.trim(),
          asset_tag: assetTagInput.trim(),
          note: note || undefined,
        })
        toast.success(
          `Ativo ${res?.asset?.asset_tag || assetTagInput} entregue para ${res?.snipe_user?.name || newCollaboratorName}.`
        )
        setNewCollaboratorName('')
        setAssetTagInput('')
      }
      setNote('')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao entregar ativo.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    )
  }

  if (!snipeConfigured) {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h5" gutterBottom>Entrega de ativo</Typography>
        <Alert severity="warning">
          Integração com o Gerenciamento de Ativos não configurada. No backend (.env) configure SNIPE_BASE_URL e SNIPE_API_TOKEN.
          Se já configurou, reinicie o backend (uvicorn) e atualize esta página.
        </Alert>
      </Container>
    )
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom>
        Entrega de ativo
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Atribua um aparelho a um colaborador. A atualização é feita automaticamente no Gerenciamento de Ativos e o registro fica salvo aqui.
      </Typography>

      <Paper sx={{ p: 3 }}>
        {diagMessage && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            {diagMessage}
          </Alert>
        )}
        <ToggleButtonGroup
          value={mode}
          exclusive
          onChange={(_, v) => {
            if (!v) return
            setMode(v)
          }}
          sx={{ mb: 2 }}
        >
          <ToggleButton value="existing">Selecionar colaborador existente</ToggleButton>
          <ToggleButton value="new">Novo colaborador + patrimônio</ToggleButton>
        </ToggleButtonGroup>

        {mode === 'existing' ? (
          <>
        <Autocomplete
          options={snipeUsers}
          getOptionLabel={(opt) => opt.name || opt.username || String(opt.id)}
          loading={loadingUsers}
          value={selectedSnipeUser}
          onChange={(_, v) => setSelectedSnipeUser(v)}
          onInputChange={(_, v) => setUserSearch(v)}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Colaborador que vai receber (Gerenciamento de Ativos)"
              placeholder="Buscar por nome..."
            />
          )}
          sx={{ mb: 2 }}
        />

        <FormControl fullWidth sx={{ mb: 2 }}>
          <InputLabel>Ativo a entregar</InputLabel>
          <Select
            value={selectedAsset?.id ?? ''}
            label="Ativo a entregar"
            onChange={(e) => {
              const id = e.target.value
              setSelectedAsset(availableAssets.find((a) => a.id === id) || null)
            }}
          >
            <MenuItem value="">Selecione o ativo...</MenuItem>
            {availableAssets.map((a) => (
              <MenuItem key={a.id} value={a.id}>
                {a.asset_tag || a.name || `ID ${a.id}`}
                {a.serial ? ` — ${a.serial}` : ''}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
          </>
        ) : (
          <>
            <TextField
              fullWidth
              label="Nome completo do colaborador"
              placeholder="Ex.: João da Silva"
              value={newCollaboratorName}
              onChange={(e) => setNewCollaboratorName(e.target.value)}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="Patrimônio do ativo"
              placeholder="Ex.: PAT-00123"
              value={assetTagInput}
              onChange={(e) => setAssetTagInput(e.target.value)}
              sx={{ mb: 2 }}
            />
          </>
        )}

        <TextField
          fullWidth
          label="Observação (opcional)"
          multiline
          rows={2}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          sx={{ mb: 2 }}
        />

        <Button
          variant="contained"
          startIcon={<AddCircleIcon />}
          disabled={
            submitting ||
            (mode === 'existing' && (!selectedSnipeUser?.id || !selectedAsset?.id)) ||
            (mode === 'new' && (!newCollaboratorName.trim() || !assetTagInput.trim()))
          }
          onClick={handleEntrega}
        >
          {submitting ? 'Enviando...' : 'Registrar entrega (atualizar no Gerenciamento)'}
        </Button>
      </Paper>
    </Container>
  )
}

export default Entrega
