import { create } from 'zustand'
export const useUIStore = create<any>((set:any)=>({
  dark: localStorage.getItem('theme')==='dark',
  toggle: ()=> set((s:any)=>{
    const nd=!s.dark
    localStorage.setItem('theme', nd?'dark':'light')
    document.documentElement.classList.toggle('dark', nd)
    return {dark: nd}
  }),
  sidebarOpen: true,
  setSidebar: (v:boolean)=> set({sidebarOpen:v})
}))
