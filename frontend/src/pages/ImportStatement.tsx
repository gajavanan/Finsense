import { useState } from 'react'
import api from '../lib/api'
import { Card } from '../components/ui/Card'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'

export default function ImportStatement(){
  const qc=useQueryClient()
  const [file,setFile]=useState<File|null>(null)
  const [result,setResult]=useState<any>(null)
  const [loading,setLoading]=useState(false)

  const onUpload = async ()=>{
    if(!file){ toast.error('Select a .csv file'); return}
    if(!file.name.toLowerCase().endsWith('.csv')){ toast.error('Only .csv allowed'); return}
    if(file.size>5*1024*1024){ toast.error('File too large max 5MB'); return}
    setLoading(true); setResult(null)
    try{
      const fd=new FormData()
      fd.append('file', file)
      const r=await api.post('/transactions/import', fd, {headers: {'Content-Type':'multipart/form-data'}})
      setResult(r.data)
      toast.success(`Imported ${r.data.imported}/${r.data.total || r.data.total_rows} (${r.data.duplicates || 0} duplicates)`)
      qc.invalidateQueries({queryKey:['transactions']})
      qc.invalidateQueries({queryKey:['dashboard']})
    }catch(e:any){
      toast.error(e.message)
      setResult({error:e.message})
    }finally{ setLoading(false)}
  }

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold">Import Transactions</h1>
      <Card>
        <div className="space-y-3">
          <div><label className="text-sm font-medium">CSV / Bank Statement</label><input type="file" accept=".csv" onChange={e=>setFile(e.target.files?.[0]||null)} className="input mt-1 w-full"/></div>
          <div className="text-xs text-slate-500">
            Supported columns (flexible): Date, Description/Narration, Merchant, Amount, Debit/Credit, Transaction Type, Category.<br/>
            Examples: Debit 500 → expense ₹500, Credit 30000 → income ₹30000. Duplicate check on date+amount+description.
          </div>
          <button onClick={onUpload} disabled={loading || !file} className="btn-primary w-full">{loading?'Importing...':'Upload & Import'}</button>
          {result && (
            <div className={`p-3 rounded text-sm ${result.error?'bg-red-50 text-red-700':'bg-green-50 text-green-700'}`}>
              {result.error ? <div>Error: {result.error}</div> :
                <>
                  <div>
                    Total transactions: {result.total || result.total_rows || 0} •{' '}
                    Imported: {result.imported || 0} •{' '}
                    Duplicates: {result.duplicates || 0} •{' '}
                    Failed: {result.failed || 0}
                  </div>
                  {result.errors?.length>0 && <div className="mt-2 text-xs">Errors: {result.errors.join('; ')}</div>}
                </>
              }
            </div>
          )}
        </div>
      </Card>
      <Card>
        <h3 className="font-semibold">Expected CSV examples</h3>
        <div className="text-xs font-mono bg-slate-50 p-2 rounded mt-2 overflow-auto">
          Date,Description,Debit,Credit<br/>
          2026-08-01,Swiggy order,450,<br/>
          2026-08-02,Salary credit,,30000
        </div>
      </Card>
    </div>
  )
}
