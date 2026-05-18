// frontend/src/components/LinhaCard.jsx
import { Box, Typography, Divider } from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import PhoneAndroidIcon from '@mui/icons-material/PhoneAndroid'

const LinhaCard = ({ linha }) => {
  if (!linha) return null
  return (
    <Box
      sx={{
        border: '1px solid',
        borderColor: 'success.main',
        borderRadius: 2,
        p: 2,
        bgcolor: 'success.50',
        mt: 1,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <CheckCircleIcon color="success" fontSize="small" />
        <Typography variant="subtitle2" color="success.dark" fontWeight={600}>
          Linha encontrada
        </Typography>
      </Box>
      <Divider sx={{ mb: 1.5 }} />
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5 }}>
        {[
          ['Colaborador', linha.nome],
          ['Linha', linha.linha],
          ['Equipe', linha.equipe],
          ['Cargo', linha.cargo],
          ['Setor', linha.setor],
          ['Código', linha.codigo],
        ].map(([label, val]) =>
          val ? (
            <Typography key={label} variant="body2">
              <strong>{label}:</strong> {val}
            </Typography>
          ) : null
        )}
      </Box>
      {(linha.aparelho || linha.modelo || linha.marca) && (
        <>
          <Divider sx={{ my: 1 }} />
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
            <PhoneAndroidIcon fontSize="small" color="action" />
            <Typography variant="caption" color="text.secondary">
              Aparelho
            </Typography>
          </Box>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0.5 }}>
            {[
              ['Modelo', linha.modelo || linha.aparelho],
              ['Marca', linha.marca],
              ['IMEI A', linha.imei_a],
              ['Ativo', linha.ativo],
            ].map(([label, val]) =>
              val ? (
                <Typography key={label} variant="body2">
                  <strong>{label}:</strong> {val}
                </Typography>
              ) : null
            )}
          </Box>
        </>
      )}
    </Box>
  )
}

export default LinhaCard
