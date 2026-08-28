import { useQuery } from '@tanstack/react-query'
import api from '../lib/api'
export const useDashboard = ()=> useQuery({ queryKey:['dashboard'], queryFn: async()=> (await api.get('/dashboard')).data, refetchInterval: 30000 })
