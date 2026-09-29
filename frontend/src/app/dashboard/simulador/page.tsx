import { redirect } from 'next/navigation'

// Rota antiga, mantida para não quebrar links salvos (docs/ux/arquitetura-telas.md).
export default function Redirecionar() {
  redirect('/dashboard/oportunidades')
}
