import axios from 'axios'

const api = axios.create({
  // In Docker/Production, this will usually be the same host
  // In development, this points to your FastAPI dev server
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export default api
