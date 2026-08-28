import { create } from 'zustand'
import api from '../lib/api'
import { getToken, setToken, clearToken } from '../lib/auth'

interface AuthState {
  user:any; loading:boolean;
  init:()=>Promise<void>;
  login:(email:string,password:string)=>Promise<void>;
  register:(name:string,email:string,password:string)=>Promise<any>;
  logout:()=>Promise<void>;
  setUser:(u:any)=>void;
}

export const useAuthStore = create<AuthState>((set)=>({
  user:null, loading:true,
  init: async()=>{
    const token = getToken()
    if(!token){ set({loading:false}); return }
    try{
      const {data} = await api.get('/auth/me')
      set({user:data, loading:false})
    }catch{
      clearToken(); set({user:null, loading:false})
    }
  },
  login: async(email,password)=>{
    const norm = email.trim().toLowerCase()
    const {data} = await api.post('/auth/login', {email:norm,password})
    setToken(data.access_token)
    set({user:data.user})
  },
  register: async(name,email,password)=>{
    const normEmail = email.trim().toLowerCase()
    const {data} = await api.post('/auth/register', {name,email:normEmail,password})
    return data
  },
  logout: async()=>{
    try{ await api.post('/auth/logout')}catch{}
    clearToken()
    set({user:null})
  },
  setUser: (u:any)=> set({user:u})
}))
