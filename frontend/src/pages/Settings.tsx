import { useAuthStore } from '../store/authStore'
import { Card } from '../components/ui/Card'
import api from '../lib/api'
import { useEffect, useState } from 'react'

export default function Settings(){
  const {user} = useAuthStore()
  const [health,setHealth]=useState<any>(null)
  const [models,setModels]=useState<any[]>([])
  useEffect(()=>{
    api.get('/health').then(r=>setHealth(r.data)).catch(()=>{})
    api.get('/ml/models').then(r=>setModels(r.data)).catch(()=>{})
  },[])
  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-2xl font-bold">Settings</h1>
      <Card><h3 className="font-semibold">Profile</h3><div className="text-sm">Email: {user?.email}</div><div className="text-sm">ID: {user?.id}</div></Card>
      <Card><h3 className="font-semibold">Health Check</h3><pre className="text-xs bg-slate-100 p-2 rounded overflow-auto">{JSON.stringify(health,null,2)}</pre></Card>
      <Card><h3 className="font-semibold">ML Models</h3>{models.map((m:any)=><div key={m.name} className="text-sm flex justify-between"><span>{m.name}</span><span className={m.status==='loaded'?'text-green-600':'text-amber-600'}>{m.status}</span></div>)}</Card>
      <Card><h3 className="font-semibold">Offline</h3><div className="text-sm" id="offline-status">{typeof navigator!== 'undefined' && !navigator.onLine ? 'You are offline.' : 'Online – data will auto-refresh when back.'}</div></Card>
    </div>
  )
}
