import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { usersAPI } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import toast from 'react-hot-toast'

const LEVEL_OPTIONS = [
  { value: 'admin', label: 'Administrador' },
  { value: 'n1', label: 'N1' },
  { value: 'n2', label: 'N2' },
  { value: 'n3', label: 'N3' },
]

const ROLE_LABELS = {
  admin: 'Administrador',
  technician: 'Técnico',
  user: 'Usuário',
  supervisor: 'Supervisor',
  requester: 'Só abre chamado',
}

const formatApiError = (err, fallback) => {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail[0]?.msg || detail[0] || fallback
  if (detail && typeof detail === 'object') return detail.msg || JSON.stringify(detail)
  return fallback
}

const getLevelFromUser = (user) => {
  if (user.role === 'admin') return 'admin'
  if (user.role === 'requester') return 'requester'
  const p = String(user.position || '').toUpperCase()
  if (p === 'N1' || p === 'N2' || p === 'N3') return p.toLowerCase()
  return 'n1'
}

const mapLevelToPayload = (level) => {
  if (level === 'admin') return { role: 'admin', position: 'Administrador' }
  return { role: 'technician', position: level.toUpperCase() }
}

const splitName = (full) => {
  const t = (full || '').trim()
  if (!t) return { first: '', last: '' }
  const parts = t.split(/\s+/)
  if (parts.length === 1) return { first: parts[0], last: '' }
  return { first: parts[0], last: parts.slice(1).join(' ') }
}

const Users = () => {
  const { user: currentUser } = useAuth()
  const [loading, setLoading] = useState(true)
  const [users, setUsers] = useState([])
  const [submitting, setSubmitting] = useState(false)

  const [createMode, setCreateMode] = useState('staff')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [department, setDepartment] = useState('TI')
  const [level, setLevel] = useState('n1')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [phone, setPhone] = useState('')

  const [editOpen, setEditOpen] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [editName, setEditName] = useState('')
  const [editFirstName, setEditFirstName] = useState('')
  const [editLastName, setEditLastName] = useState('')
  const [editEmail, setEditEmail] = useState('')
  const [editPhone, setEditPhone] = useState('')
  const [editDepartment, setEditDepartment] = useState('')
  const [editLevel, setEditLevel] = useState('n1')
  const [editActive, setEditActive] = useState(true)

  const [passOpen, setPassOpen] = useState(false)
  const [passwordUser, setPasswordUser] = useState(null)
  const [newPassword, setNewPassword] = useState('')

  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteUser, setDeleteUser] = useState(null)

  const [createOpen, setCreateOpen] = useState(false)

  /** all | admin | requester — alinhado ao filtro do GET /users?role= */
  const [roleFilter, setRoleFilter] = useState('all')

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params = { limit: 500 }
      if (roleFilter !== 'all') params.role = roleFilter
      const rows = await usersAPI.getAll(params)
      setUsers(Array.isArray(rows) ? rows : [])
    } catch (err) {
      setUsers([])
      toast.error(formatApiError(err, 'Erro ao carregar usuários.'))
    } finally {
      setLoading(false)
    }
  }, [roleFilter])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  if (currentUser?.role !== 'admin') {
    return (
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="warning">Apenas administradores podem acessar este painel.</Alert>
      </Container>
    )
  }

  const resetCreateForm = () => {
    setName('')
    setEmail('')
    setPassword('')
    setPasswordConfirm('')
    setDepartment('TI')
    setLevel('n1')
    setFirstName('')
    setLastName('')
    setPhone('')
  }

  const handleCreateUser = async () => {
    if (password !== passwordConfirm) {
      toast.error('As senhas não conferem.')
      return
    }
    if (password.length < 6) {
      toast.error('A senha deve ter pelo menos 6 caracteres.')
      return
    }

    if (createMode === 'staff') {
      if (!name.trim() || !email.trim() || !password.trim()) {
        toast.error('Preencha nome, e-mail e senha.')
        return
      }
    } else {
      if (!firstName.trim() || !lastName.trim() || !phone.trim()) {
        toast.error('Preencha nome, sobrenome, telefone e senha.')
        return
      }
      if (!department.trim()) {
        toast.error('Informe o setor.')
        return
      }
    }

    setSubmitting(true)
    try {
      if (createMode === 'requester') {
        await usersAPI.create({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone: phone.trim(),
          department: department.trim() || null,
          password,
          password_confirm: passwordConfirm,
          role: 'requester',
        })
      } else {
        const roleData = mapLevelToPayload(level)
        await usersAPI.create({
          name: name.trim(),
          email: email.trim(),
          password,
          password_confirm: passwordConfirm,
          department: department.trim() || null,
          ...roleData,
        })
      }
      toast.success('Usuário criado com sucesso.')
      resetCreateForm()
      setCreateOpen(false)
      loadUsers()
    } catch (err) {
      toast.error(formatApiError(err, 'Erro ao criar usuário.'))
    } finally {
      setSubmitting(false)
    }
  }

  const openEditDialog = (u) => {
    setEditingUser(u)
    if (u.role === 'requester') {
      const { first, last } = splitName(u.name)
      setEditFirstName(first)
      setEditLastName(last)
      setEditPhone(u.phone || '')
      const em = (u.email || '').trim()
      const internal = /^portal\+\d+@example\.com$/i.test(em)
      setEditEmail(internal ? '' : em)
    } else {
      setEditName(u.name || '')
      setEditEmail(u.email || '')
      setEditPhone('')
    }
    setEditDepartment(u.department || '')
    setEditLevel(getLevelFromUser(u) === 'requester' ? 'n1' : getLevelFromUser(u))
    setEditActive(Boolean(u.is_active))
    setEditOpen(true)
  }

  const handleSaveEdit = async () => {
    if (!editingUser) return
    setSubmitting(true)
    try {
      if (editingUser.role === 'requester') {
        if (!editFirstName.trim() || !editLastName.trim()) {
          toast.error('Preencha nome e sobrenome.')
          setSubmitting(false)
          return
        }
        await usersAPI.update(editingUser.id, {
          name: `${editFirstName.trim()} ${editLastName.trim()}`.trim(),
          department: editDepartment.trim() || null,
          is_active: editActive,
          role: 'requester',
        })
      } else {
        if (!editName.trim() || !editEmail.trim()) {
          toast.error('Nome e e-mail são obrigatórios.')
          setSubmitting(false)
          return
        }
        const roleData = mapLevelToPayload(editLevel)
        await usersAPI.update(editingUser.id, {
          name: editName.trim(),
          email: editEmail.trim(),
          department: editDepartment.trim() || null,
          is_active: editActive,
          ...roleData,
        })
      }
      toast.success('Usuário atualizado com sucesso.')
      setEditOpen(false)
      setEditingUser(null)
      loadUsers()
    } catch (err) {
      toast.error(formatApiError(err, 'Erro ao atualizar usuário.'))
    } finally {
      setSubmitting(false)
    }
  }

  const openPasswordDialog = (u) => {
    setPasswordUser(u)
    setNewPassword('')
    setPassOpen(true)
  }

  const handleResetPassword = async () => {
    if (!passwordUser) return
    if (!newPassword.trim()) {
      toast.error('Informe a nova senha.')
      return
    }
    setSubmitting(true)
    try {
      await usersAPI.updatePassword(passwordUser.id, {
        current_password: '',
        new_password: newPassword.trim(),
      })
      const label =
        passwordUser.role === 'requester'
          ? `Telefone ${passwordUser.phone || ''}`
          : passwordUser.email
      toast.success(`Senha redefinida (${label}).`)
      setPassOpen(false)
      setPasswordUser(null)
      setNewPassword('')
      loadUsers()
    } catch (err) {
      toast.error(formatApiError(err, 'Erro ao redefinir senha.'))
    } finally {
      setSubmitting(false)
    }
  }

  const openDeleteDialog = (u) => {
    setDeleteUser(u)
    setDeleteOpen(true)
  }

  const handleDeleteUser = async (permanent) => {
    if (!deleteUser) return
    setSubmitting(true)
    try {
      await usersAPI.delete(deleteUser.id, { permanent })
      toast.success(
        permanent
          ? 'Usuário removido permanentemente do banco de dados.'
          : 'Usuário desativado (pode ser reativado editando o status).'
      )
      setDeleteOpen(false)
      setDeleteUser(null)
      loadUsers()
    } catch (err) {
      toast.error(formatApiError(err, 'Erro ao processar exclusão.'))
    } finally {
      setSubmitting(false)
    }
  }

  const contactCell = (u) => {
    if (u.role !== 'requester') return u.email || '—'
    const phone = (u.phone || '').trim()
    const email = (u.email || '').trim()
    if (phone) return phone
    // Cadastro pelo portal: e-mail real, sem telefone
    if (email && !/^portal\+\d+@example\.com$/i.test(email)) return email
    // Cadastro admin por telefone: e-mail sintético portal+DDDNUM@example.com — exibe o número
    const m = email.match(/^portal\+(\d+)@example\.com$/i)
    if (m) return `Tel. ${m[1]}`
    return email || '—'
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Painel de Usuários (Admin)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Crie administradores ou técnicos, ou usuários que só abrem chamados. Edite, redefina senha ou desative
        usuários.
      </Typography>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
        <Button
          variant="contained"
          onClick={() => {
            resetCreateForm()
            setCreateMode('staff')
            setCreateOpen(true)
          }}
        >
          Criar novo usuário
        </Button>
      </Box>

      <Dialog
        open={createOpen}
        onClose={() => {
          if (!submitting) setCreateOpen(false)
        }}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Novo usuário</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Box sx={{ mb: 2 }}>
              <FormControl size="small" fullWidth sx={{ maxWidth: 400 }}>
                <InputLabel>Tipo</InputLabel>
                <Select
                  value={createMode}
                  label="Tipo"
                  onChange={(e) => {
                    setCreateMode(e.target.value)
                    resetCreateForm()
                  }}
                >
                  <MenuItem value="staff">Administrador / Técnico (N1–N3)</MenuItem>
                  <MenuItem value="requester">Usuário padrão (só abre chamado)</MenuItem>
                </Select>
              </FormControl>
            </Box>

            {createMode === 'staff' ? (
              <Box display="grid" gridTemplateColumns={{ xs: '1fr', sm: 'repeat(2, 1fr)' }} gap={1.5}>
                <TextField label="Nome" value={name} onChange={(e) => setName(e.target.value)} fullWidth />
                <TextField label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} fullWidth />
                <TextField
                  label="Departamento"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  fullWidth
                />
                <TextField
                  label="Senha"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  fullWidth
                />
                <TextField
                  label="Repete senha"
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  autoComplete="new-password"
                  fullWidth
                />
                <FormControl fullWidth>
                  <InputLabel>Nível</InputLabel>
                  <Select value={level} label="Nível" onChange={(e) => setLevel(e.target.value)}>
                    {LEVEL_OPTIONS.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Box>
            ) : (
              <Box display="grid" gridTemplateColumns={{ xs: '1fr', sm: 'repeat(2, 1fr)' }} gap={1.5}>
                <TextField label="Nome" value={firstName} onChange={(e) => setFirstName(e.target.value)} fullWidth />
                <TextField label="Sobrenome" value={lastName} onChange={(e) => setLastName(e.target.value)} fullWidth />
                <TextField label="Telefone" value={phone} onChange={(e) => setPhone(e.target.value)} fullWidth />
                <TextField
                  label="Setor"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  required
                  placeholder="Ex.: Financeiro, RH, Loja Centro"
                  fullWidth
                />
                <TextField
                  label="Senha"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  fullWidth
                />
                <TextField
                  label="Repete senha"
                  type="password"
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  autoComplete="new-password"
                  fullWidth
                />
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2, gap: 1 }}>
          <Button
            onClick={() => {
              if (!submitting) setCreateOpen(false)
            }}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button variant="contained" onClick={handleCreateUser} disabled={submitting}>
            {submitting ? 'Salvando...' : 'Criar usuário'}
          </Button>
        </DialogActions>
      </Dialog>

      <Paper sx={{ p: 2 }}>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 2,
            mb: 1.5,
          }}
        >
          <Typography variant="h6">Todos os usuários</Typography>
          <FormControl size="small" sx={{ minWidth: 240 }}>
            <InputLabel id="users-role-filter-label">Filtrar por perfil</InputLabel>
            <Select
              labelId="users-role-filter-label"
              label="Filtrar por perfil"
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
            >
              <MenuItem value="all">Todos os perfis</MenuItem>
              <MenuItem value="admin">Administrador</MenuItem>
              <MenuItem value="requester">Só abre chamado</MenuItem>
            </Select>
          </FormControl>
        </Box>
        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={120}>
            <CircularProgress />
          </Box>
        ) : users.length === 0 ? (
          <Alert severity="info">
            {roleFilter === 'all'
              ? 'Nenhum usuário cadastrado.'
              : 'Nenhum usuário encontrado com este filtro.'}
          </Alert>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Nome</TableCell>
                  <TableCell>E-mail / Telefone</TableCell>
                  <TableCell>Perfil</TableCell>
                  <TableCell>Nível / Setor</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Ações</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((u) => {
                  const levelLabel =
                    LEVEL_OPTIONS.find((l) => l.value === getLevelFromUser(u))?.label || '—'
                  const isSelf = u.id === currentUser?.id
                  return (
                    <TableRow key={u.id}>
                      <TableCell>{u.id}</TableCell>
                      <TableCell>{u.name || '—'}</TableCell>
                      <TableCell>{contactCell(u)}</TableCell>
                      <TableCell>{ROLE_LABELS[u.role] || u.role}</TableCell>
                      <TableCell>{u.role === 'requester' ? u.department || '—' : levelLabel}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={u.is_active ? 'success' : 'default'}
                          label={u.is_active ? 'Ativo' : 'Inativo'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Box display="flex" justifyContent="flex-end" gap={1} flexWrap="wrap">
                          <Button
                            size="small"
                            variant="outlined"
                            color="primary"
                            onClick={() => openEditDialog(u)}
                          >
                            Editar
                          </Button>
                          <Button
                            size="small"
                            variant="contained"
                            color="primary"
                            onClick={() => openPasswordDialog(u)}
                          >
                            Redefinir senha
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            disabled={isSelf}
                            onClick={() => openDeleteDialog(u)}
                          >
                            Excluir
                          </Button>
                        </Box>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>

      <Dialog open={editOpen} onClose={() => setEditOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Editar usuário</DialogTitle>
        <DialogContent>
          <Box display="grid" gridTemplateColumns="1fr" gap={1.25} sx={{ mt: 1 }}>
            {editingUser?.role === 'requester' ? (
              <>
                <TextField label="Nome" value={editFirstName} onChange={(e) => setEditFirstName(e.target.value)} />
                <TextField label="Sobrenome" value={editLastName} onChange={(e) => setEditLastName(e.target.value)} />
                <TextField label="Telefone" value={editPhone} disabled helperText="Para alterar o telefone, desative e crie outro cadastro." />
                {editEmail ? (
                  <TextField
                    label="E-mail"
                    value={editEmail}
                    disabled
                    helperText="Cadastro pelo link público; o e-mail não pode ser alterado aqui."
                  />
                ) : null}
                <TextField
                  label="Setor"
                  value={editDepartment}
                  onChange={(e) => setEditDepartment(e.target.value)}
                />
              </>
            ) : (
              <>
                <TextField label="Nome" value={editName} onChange={(e) => setEditName(e.target.value)} />
                <TextField label="E-mail" type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)} />
                <TextField
                  label="Departamento"
                  value={editDepartment}
                  onChange={(e) => setEditDepartment(e.target.value)}
                />
                <FormControl>
                  <InputLabel>Nível</InputLabel>
                  <Select value={editLevel} label="Nível" onChange={(e) => setEditLevel(e.target.value)}>
                    {LEVEL_OPTIONS.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )}
            <FormControl>
              <InputLabel>Status</InputLabel>
              <Select
                value={editActive ? 'active' : 'inactive'}
                label="Status"
                onChange={(e) => setEditActive(e.target.value === 'active')}
              >
                <MenuItem value="active">Ativo</MenuItem>
                <MenuItem value="inactive">Inativo</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleSaveEdit} disabled={submitting}>
            Salvar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={passOpen} onClose={() => setPassOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Redefinir senha</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 1.5 }}>
            {passwordUser
              ? passwordUser.role === 'requester'
                ? `Telefone: ${passwordUser.phone || '—'}`
                : `E-mail: ${passwordUser.email || '—'}`
              : ''}
          </Typography>
          <TextField
            fullWidth
            type="password"
            label="Nova senha"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPassOpen(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleResetPassword} disabled={submitting}>
            Redefinir
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteOpen} onClose={() => setDeleteOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Excluir — escolha uma opção</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 1.5 }}>
            Usuário: <strong>{deleteUser?.name}</strong>
          </Typography>
          <Alert severity="info" sx={{ mb: 1.5 }}>
            <strong>Apenas desativar:</strong> o cadastro continua no banco, mas o usuário não consegue entrar. Você
            pode reativar depois (Status → Ativo).
          </Alert>
          <Alert severity="warning">
            <strong>Excluir do banco:</strong> remove o cadastro permanentemente. No PostgreSQL unificado, chamados
            antigos (inclusive encerrados) continuam no histórico: o sistema <strong>reatribui</strong> o solicitante
            desses chamados a outro usuário interno, para poder apagar a conta (exigência da chave estrangeira). A
            exclusão <strong>só é bloqueada</strong> se ainda houver chamados <strong>em aberto ou em andamento</strong>.
            Se preferir, use só desativar.
          </Alert>
        </DialogContent>
        <DialogActions sx={{ flexWrap: 'wrap', gap: 1, px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteOpen(false)}>Cancelar</Button>
          <Button variant="outlined" color="primary" onClick={() => handleDeleteUser(false)} disabled={submitting}>
            Só desativar
          </Button>
          <Button variant="contained" color="error" onClick={() => handleDeleteUser(true)} disabled={submitting}>
            Excluir do banco
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}

export default Users
