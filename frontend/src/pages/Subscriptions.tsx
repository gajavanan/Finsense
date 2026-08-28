import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
import { Card } from '../components/ui/Card'

export default function Subscriptions(){
  const {data, isLoading} = useQuery({queryKey:['subscriptions'], queryFn: async()=> (await api.get('/subscriptions')).data})
  if(isLoading) return <div>Loading...</div>
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Subscriptions</h1>
      <Card><div className="text-sm text-slate-500">Detected from actual transaction history (recurring merchants). No hardcoded list.</div></Card>
      <div className="grid md:grid-cols-2 gap-4">
        {(data||[]).map((s:any)=> <Card key={s.merchant}><div className="font-semibold">{s.merchant}</div><div className="text-sm">Avg ₹{s.avg_amount} • {s.frequency} • {s.count} occurrences</div><div className="text-xs text-slate-500">Next expected: {s.next_expected} • Last: {s.last_date}</div></Card>)}
        {(data||[]).length===0 && <Card>No recurring transactions detected yet. Need at least 2 transactions with same merchant.</Card>}
      </div>
    </div>
  )
}
