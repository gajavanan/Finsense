import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../lib/api'
import { Card } from '../components/ui/Card'

export default function Notifications(){
  const qc=useQueryClient()
  const {data} = useQuery({queryKey:['notifications'], queryFn: async()=> (await api.get('/notifications')).data})
  const readMut=useMutation({mutationFn: async(id:string)=> (await api.post(`/notifications/${id}/read`)).data, onSuccess:()=> qc.invalidateQueries({queryKey:['notifications']})})
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Notifications</h1>
      {(data||[]).length===0 ? <Card>Empty: No notifications.</Card> :
        <div className="space-y-2">{(data||[]).map((n:any)=><Card key={n.id} className={n.read?'opacity-60':''}><div className="font-semibold text-sm">{n.title}</div><div className="text-sm">{n.message}</div><div className="text-xs text-slate-500 flex justify-between"><span>{new Date(n.created_at).toLocaleString()}</span>{!n.read && <button onClick={()=>readMut.mutate(n.id)} className="text-sky-600">Mark read</button>}</div></Card>)}</div>}
    </div>
  )
}
