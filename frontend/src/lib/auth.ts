export const TOKEN_KEY = "finsense-token"
export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t:string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)
export const isAuthenticated = () => !!getToken()
