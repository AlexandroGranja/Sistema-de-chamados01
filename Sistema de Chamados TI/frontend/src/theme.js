import { createTheme } from '@mui/material/styles'

// Tokens de cor por modo
const tokens = {
  light: {
    sidebarBg: '#111827',
    gold: '#f2c230',
    goldHover: '#d4a820',
    bgDefault: '#f9fafb',
    bgPaper: '#ffffff',
    bgSubtle: '#f3f4f6',
    textPrimary: '#111827',
    textSecondary: '#6b7280',
    border: '#e5e7eb',
  },
  dark: {
    sidebarBg: '#0d1117',
    gold: '#f2c230',
    goldHover: '#d4a820',
    bgDefault: '#111827',
    bgPaper: '#1f2937',
    bgSubtle: '#374151',
    textPrimary: '#f9fafb',
    textSecondary: '#9ca3af',
    border: '#374151',
  },
}

// Cores funcionais de status (mesmas nos dois modos)
export const STATUS_COLORS = {
  open:                { color: '#3b82f6', bg: '#eff6ff', label: 'Aberto' },
  in_analysis:         { color: '#f59e0b', bg: '#fffbeb', label: 'Em análise' },
  in_progress:         { color: '#f59e0b', bg: '#fffbeb', label: 'Em andamento' },
  waiting_user:        { color: '#f59e0b', bg: '#fffbeb', label: 'Aguardando usuário' },
  waiting_third_party: { color: '#f59e0b', bg: '#fffbeb', label: 'Aguardando terceiros' },
  resolved:            { color: '#10b981', bg: '#ecfdf5', label: 'Resolvido' },
  closed:              { color: '#10b981', bg: '#ecfdf5', label: 'Fechado' },
  cancelled:           { color: '#6b7280', bg: '#f3f4f6', label: 'Cancelado' },
  urgent:              { color: '#ef4444', bg: '#fef2f2', label: 'Urgente' },
}

export const buildTheme = (mode = 'light') => {
  const t = tokens[mode] ?? tokens.light
  const isDark = mode === 'dark'

  return createTheme({
    palette: {
      mode,
      primary: {
        main: t.gold,
        dark: t.goldHover,
        contrastText: '#111827',
      },
      secondary: {
        main: '#3b82f6',
        contrastText: '#fff',
      },
      background: {
        default: t.bgDefault,
        paper: t.bgPaper,
      },
      text: {
        primary: t.textPrimary,
        secondary: t.textSecondary,
      },
      divider: t.border,
    },
    typography: {
      fontFamily: '"Plus Jakarta Sans", "Helvetica", "Arial", sans-serif',
      h1: { fontWeight: 700 },
      h2: { fontWeight: 700 },
      h3: { fontWeight: 700, fontSize: '2rem' },
      h4: { fontWeight: 700, fontSize: '1.375rem' },
      h5: { fontWeight: 600 },
      h6: { fontWeight: 600, fontSize: '1rem' },
      body1: { fontSize: '0.875rem' },
      body2: { fontSize: '0.875rem' },
      caption: { fontSize: '0.75rem' },
      overline: { fontSize: '0.6875rem', letterSpacing: '0.08em' },
    },
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: `
          @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
          * { box-sizing: border-box; }
          body { background-color: ${t.bgDefault}; }
        `,
      },
      MuiButton: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 600,
            borderRadius: 6,
            boxShadow: 'none',
            '&:hover': { boxShadow: 'none' },
          },
          containedPrimary: {
            backgroundColor: t.gold,
            color: '#111827',
            '&:hover': { backgroundColor: t.goldHover },
          },
        },
      },
      MuiTextField: {
        defaultProps: { variant: 'outlined', size: 'small' },
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                borderColor: t.gold,
                borderWidth: 2,
              },
            },
            '& .MuiInputLabel-root.Mui-focused': {
              color: t.gold,
            },
          },
        },
      },
      MuiSelect: {
        styleOverrides: {
          root: {
            '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: t.gold,
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
          },
        },
      },
      MuiTableHead: {
        styleOverrides: {
          root: {
            backgroundColor: t.bgSubtle,
            '& .MuiTableCell-head': {
              fontSize: '0.6875rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: t.textSecondary,
              borderBottom: `1px solid ${t.border}`,
            },
          },
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: {
            '&:hover': {
              backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
            },
            '& .MuiTableCell-body': {
              borderBottom: `1px solid ${t.border}`,
              borderLeft: 'none',
              borderRight: 'none',
            },
          },
        },
      },
    },
    // Tokens extras acessíveis via theme.prosper
    prosper: t,
  })
}
