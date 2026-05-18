// frontend/src/components/LinhaSearch.jsx
import { useState } from 'react'
import { Box, TextField, Button, Alert, CircularProgress } from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import LinhaCard from './LinhaCard'
import { telefonesAPI } from '../services/api'
import toast from 'react-hot-toast'

const LinhaSearch = ({ onLinhaFound, onLinhaClear }) => {
  const [codigo, setCodigo] = useState('')
  const [nome, setNome] = useState('')
  const [loading, setLoading] = useState(false)
  const [resultado, setResultado] = useState(null)   // null | { encontrado, linha }
  const [buscado, setBuscado] = useState(false)

  const buscar = async () => {
    if (!codigo.trim() && !nome.trim()) {
      toast.error('Informe o código ou nome para buscar.')
      return
    }
    setLoading(true)
    try {
      const data = await telefonesAPI.buscarLinha(codigo, nome)
      setResultado(data)
      setBuscado(true)
      if (data.encontrado && onLinhaFound) {
        onLinhaFound(data.linha)
      } else if (!data.encontrado && onLinhaClear) {
        onLinhaClear()
      }
    } catch (err) {
      toast.error('Erro ao buscar linha.')
    } finally {
      setLoading(false)
    }
  }

  const limpar = () => {
    setCodigo('')
    setNome('')
    setResultado(null)
    setBuscado(false)
    if (onLinhaClear) onLinhaClear()
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <TextField
          label="Código (matrícula)"
          value={codigo}
          onChange={(e) => setCodigo(e.target.value)}
          size="small"
          sx={{ width: 180 }}
          onKeyDown={(e) => e.key === 'Enter' && buscar()}
        />
        <TextField
          label="Nome completo (fallback)"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          size="small"
          sx={{ flex: 1, minWidth: 220 }}
          onKeyDown={(e) => e.key === 'Enter' && buscar()}
        />
        <Button
          variant="contained"
          startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <SearchIcon />}
          onClick={buscar}
          disabled={loading}
          size="small"
        >
          Buscar linha
        </Button>
        {buscado && (
          <Button variant="text" size="small" onClick={limpar}>
            Limpar
          </Button>
        )}
      </Box>

      {buscado && !resultado?.encontrado && (
        <Alert severity="warning" sx={{ mt: 1 }}>
          Linha não localizada — você pode prosseguir sem atualizar o Gerenciamento de Telefones.
        </Alert>
      )}

      {resultado?.encontrado && <LinhaCard linha={resultado.linha} />}
    </Box>
  )
}

export default LinhaSearch
