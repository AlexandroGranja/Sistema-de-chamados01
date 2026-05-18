import { useMemo, useState } from 'react'
import { Box } from '@mui/material'

const DEFAULT_LOGO_CANDIDATES = [
  '/assets/logo.png',
  '/assets/logo.jpg',
  '/assets/logo.jpeg',
  '/assets/logo.svg',
  '/assets/prosper-logo.png',
  '/assets/prosper.png',
]

const CompanyLogo = ({ size = 34, rounded = true, alt = 'Logo da empresa', sx = {} }) => {
  const candidates = useMemo(() => DEFAULT_LOGO_CANDIDATES, [])
  const [index, setIndex] = useState(0)

  const handleError = () => {
    setIndex((prev) => prev + 1)
  }

  if (index >= candidates.length) {
    return (
      <Box
        aria-label={alt}
        sx={{
          width: size,
          height: size,
          borderRadius: rounded ? 1 : 0,
          bgcolor: 'rgba(255,255,255,0.2)',
          border: '1px solid rgba(255,255,255,0.4)',
          color: 'inherit',
          fontWeight: 700,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: Math.max(10, Math.round(size * 0.36)),
          ...sx,
        }}
      >
        P
      </Box>
    )
  }

  return (
    <Box
      component="img"
      src={candidates[index]}
      alt={alt}
      onError={handleError}
      sx={{
        width: size,
        height: size,
        objectFit: 'contain',
        borderRadius: rounded ? 1 : 0,
        ...sx,
      }}
    />
  )
}

export default CompanyLogo

