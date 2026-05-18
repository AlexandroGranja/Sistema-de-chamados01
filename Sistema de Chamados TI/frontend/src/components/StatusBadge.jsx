import { Box } from '@mui/material'
import { STATUS_COLORS } from '../theme'

/**
 * Badge de status reutilizável.
 * Usa as cores funcionais definidas em theme.js.
 *
 * Props:
 *   status  — chave do STATUS_COLORS (ex: 'open', 'closed')
 *   label   — override do label (opcional)
 */
const StatusBadge = ({ status, label }) => {
  const config = STATUS_COLORS[status] ?? {
    color: '#6b7280',
    bg: '#f3f4f6',
    label: status ?? '—',
  }
  const displayLabel = label ?? config.label

  return (
    <Box
      component="span"
      sx={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '5px',
        px: 1.25,
        py: 0.35,
        borderRadius: '12px',
        backgroundColor: config.bg,
        fontSize: '0.75rem',
        fontWeight: 600,
        color: config.color,
        whiteSpace: 'nowrap',
        lineHeight: 1.5,
      }}
    >
      <Box
        component="span"
        sx={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          backgroundColor: config.color,
          flexShrink: 0,
        }}
      />
      {displayLabel}
    </Box>
  )
}

export default StatusBadge
