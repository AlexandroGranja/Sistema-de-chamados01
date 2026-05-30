import { useSearchParams } from 'react-router-dom'

/** Lê ticket_id da URL (?ticket_id= ou ?chamado_id=). */
export function useTicketContext() {
  const [params] = useSearchParams()
  const raw = (params.get('ticket_id') || params.get('chamado_id') || '').trim()
  const parsed = raw ? Number.parseInt(raw, 10) : NaN
  return {
    ticketId: Number.isFinite(parsed) && parsed > 0 ? parsed : null,
    ticketIdRaw: raw,
  }
}
