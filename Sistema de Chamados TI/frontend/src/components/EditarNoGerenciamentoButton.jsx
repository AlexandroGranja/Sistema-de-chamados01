import { useState } from 'react'
import { Button, CircularProgress } from '@mui/material'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { telefonesAPI } from '../services/api'
import { useTicketContext } from '../hooks/useTicketContext'
import toast from 'react-hot-toast'

/**
 * Abre o Gerenciamento de Telefones (Streamlit) com contexto de chamado/linha.
 * ticketId pode vir da prop ou de ?ticket_id= na URL.
 */
const EditarNoGerenciamentoButton = ({
  ticketId: ticketIdProp = null,
  linha = '',
  segmento = '',
  equipe = '',
  disabled = false,
  size = 'medium',
  variant = 'outlined',
  sx,
}) => {
  const { ticketId: ticketIdFromUrl } = useTicketContext()
  const ticketId = ticketIdProp ?? ticketIdFromUrl
  const [loading, setLoading] = useState(false)

  const handleClick = async () => {
    setLoading(true)
    try {
      const data = await telefonesAPI.linkGerenciamento({
        ticket_id: ticketId,
        linha: linha || undefined,
        segmento: segmento || undefined,
        equipe: equipe || undefined,
      })
      if (!data?.url) {
        toast.error('Não foi possível gerar o link do Gerenciamento.')
        return
      }
      window.open(data.url, '_blank', 'noopener,noreferrer')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Erro ao abrir o Gerenciamento.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Button
      variant={variant}
      size={size}
      startIcon={loading ? <CircularProgress size={16} /> : <OpenInNewIcon />}
      onClick={handleClick}
      disabled={disabled || loading}
      sx={sx}
    >
      Editar linha no Gerenciamento
    </Button>
  )
}

export default EditarNoGerenciamentoButton
