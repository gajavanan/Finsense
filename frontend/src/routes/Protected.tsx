import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { getToken } from '../lib/auth'
export default function Protected({children}:any){
  const {user, loading} = useAuthStore()
  if(loading) return <div className="p-10 text-center text-sm text-slate-500">Loading...</div>
  if(!user && !getToken()) return <Navigate to="/login" replace/>
  return children
}
