import { useEffect, useState } from 'react'
import api from '../lib/api'
import { Card } from '../components/ui/Card'
import { toast } from 'sonner'
import { Sparkles, Upload, Play, AlertCircle, CheckCircle, RefreshCw, FileText } from 'lucide-react'

export default function MLModels() {
  const [models, setModels] = useState<any[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [uploadResult, setUploadResult] = useState<any>(null)
  const [uploadLoading, setUploadLoading] = useState(false)
  const [trainLoading, setTrainLoading] = useState(false)

  const fetchModels = () => {
    api.get('/ml/models')
      .then(r => setModels(r.data))
      .catch(() => {})
  }

  useEffect(() => {
    fetchModels()
  }, [])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null
    if (!selectedFile) return
    if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
      toast.error('Only .csv files are supported for training data')
      return
    }
    if (selectedFile.size > 5 * 1024 * 1024) {
      toast.error('File size exceeds 5MB limit')
      return
    }

    setFile(selectedFile)
    setUploadLoading(true)
    setUploadResult(null)

    const fd = new FormData()
    fd.append('file', selectedFile)

    try {
      const r = await api.post('/ml/upload-dataset', fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setUploadResult(r.data)
      toast.success('Dataset validated and staged successfully')
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to upload dataset'
      toast.error(msg)
      setUploadResult({ error: msg })
    } finally {
      setUploadLoading(false)
    }
  }

  const handleTrain = async () => {
    setTrainLoading(true)
    try {
      const r = await api.post('/ml/train')
      if (r.data.status === 'trained') {
        toast.success('Transaction Categorizer and all ML models trained successfully!')
        fetchModels()
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed during model training'
      toast.error(msg)
    } finally {
      setTrainLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="text-sky-500 animate-pulse" /> ML Models & Training
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">
            Manage your AI model configurations, upload training datasets, and train predictions.
          </p>
        </div>
        <button 
          onClick={fetchModels} 
          className="p-2 border rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800 transition text-slate-600 dark:text-slate-300 transition-colors"
          title="Refresh models status"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Model Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {models.length > 0 ? (
          models.map((m: any) => (
            <Card key={m.name} className="relative overflow-hidden group hover:shadow-md transition duration-200">
              <div className="absolute top-0 right-0 p-3 opacity-5 text-slate-400 group-hover:scale-110 transition-transform">
                <Sparkles size={40} />
              </div>
              <div className="space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Model Status</div>
                <h3 className="font-bold text-lg text-slate-800 dark:text-slate-200">{m.name}</h3>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`w-2.5 h-2.5 rounded-full ${m.status === 'loaded' ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                  <span className={`text-sm font-semibold ${m.status === 'loaded' ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                    {m.status === 'loaded' ? 'Active & Loaded' : 'Training Required'}
                  </span>
                </div>
              </div>
            </Card>
          ))
        ) : (
          <div className="col-span-3 text-center py-6 text-slate-500">Loading model information...</div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* ML Training Dataset Section */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="border-t-4 border-t-sky-500">
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
              <FileText className="text-sky-500" size={20} /> ML Training Dataset
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Select and validate a dataset to train the Transaction Categorizer model.
            </p>

            <div className="mt-4 space-y-4">
              <div className="border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-xl p-6 text-center hover:border-sky-400 dark:hover:border-sky-500 transition-colors duration-200 relative bg-slate-50/50 dark:bg-slate-900/30">
                <input 
                  type="file" 
                  accept=".csv" 
                  onChange={handleUpload} 
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  disabled={uploadLoading || trainLoading}
                />
                <div className="flex flex-col items-center justify-center space-y-2 pointer-events-none">
                  <div className="p-3 bg-white dark:bg-slate-800 rounded-full shadow-sm">
                    <Upload className="text-slate-400 dark:text-slate-500" size={24} />
                  </div>
                  <div className="font-semibold text-slate-700 dark:text-slate-300">
                    {uploadLoading ? 'Validating CSV...' : file ? file.name : 'Upload Training CSV'}
                  </div>
                  <div className="text-xs text-slate-400 max-w-sm">
                    Supports columns: Description, Merchant, Amount (INR), Payment Method, Category. Header row detected automatically.
                  </div>
                </div>
              </div>

              {/* Upload & Validation Result */}
              {uploadResult && (
                <div className={`p-4 rounded-xl text-sm ${uploadResult.error ? 'bg-red-50 dark:bg-red-950/20 text-red-700 dark:text-red-400 border border-red-200/50 dark:border-red-900/50' : 'bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800'}`}>
                  {uploadResult.error ? (
                    <div className="flex gap-2">
                      <AlertCircle className="shrink-0 mt-0.5 text-red-500" size={16} />
                      <div>
                        <div className="font-semibold">Validation Failed</div>
                        <div className="text-xs mt-1">{uploadResult.error}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold">
                        <CheckCircle size={18} />
                        Dataset Validated & Staged Successfully
                      </div>
                      
                      <div className="grid grid-cols-3 gap-2 text-center mt-2">
                        <div className="p-3 bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-slate-100 dark:border-slate-800">
                          <div className="text-xl font-bold text-slate-800 dark:text-slate-200">{uploadResult.total_rows}</div>
                          <div className="text-xs text-slate-400">Total Rows Detected</div>
                        </div>
                        <div className="p-3 bg-emerald-50/50 dark:bg-emerald-950/10 rounded-lg shadow-sm border border-emerald-100/50 dark:border-emerald-900/10">
                          <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400">{uploadResult.valid_count}</div>
                          <div className="text-xs text-slate-400 font-medium">Valid Training Rows</div>
                        </div>
                        <div className="p-3 bg-amber-50/50 dark:bg-amber-950/10 rounded-lg shadow-sm border border-amber-100/50 dark:border-amber-900/10">
                          <div className="text-xl font-bold text-amber-600 dark:text-amber-400">{uploadResult.invalid_count}</div>
                          <div className="text-xs text-slate-400 font-medium">Invalid Rows</div>
                        </div>
                      </div>

                      {uploadResult.categories_detected && uploadResult.categories_detected.length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Categories Detected ({uploadResult.categories_detected.length})</div>
                          <div className="flex flex-wrap gap-1.5 mt-1.5">
                            {uploadResult.categories_detected.map((cat: string) => (
                              <span key={cat} className="px-2.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded-full text-xs font-semibold text-slate-600 dark:text-slate-300">
                                {cat}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Training Action Section */}
        <div className="space-y-4">
          <Card className="h-full flex flex-col justify-between border-t-4 border-t-violet-500">
            <div className="space-y-3">
              <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <Play className="text-violet-500" size={20} /> Train Model
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Train the Transaction Categorizer model on the staged dataset.
              </p>
              <div className="text-xs text-slate-400 mt-2 space-y-1">
                <p>• Uses standard TF-IDF feature extraction.</p>
                <p>• Trains a Random Forest Classifier.</p>
                <p>• Takes 5–15 seconds depending on rows.</p>
              </div>
            </div>

            <div className="pt-6 mt-auto">
              <button 
                onClick={handleTrain} 
                disabled={trainLoading || !uploadResult || uploadResult.error || uploadResult.valid_count === 0} 
                className="btn-primary w-full py-3 flex items-center justify-center gap-2 bg-gradient-to-r from-sky-600 to-violet-600 hover:from-sky-700 hover:to-violet-700 transition shadow-sm hover:shadow active:scale-[0.98]"
              >
                {trainLoading ? (
                  <>
                    <RefreshCw className="animate-spin" size={18} />
                    Training Model...
                  </>
                ) : (
                  <>
                    <Play size={18} />
                    Train Transaction Categorizer
                  </>
                )}
              </button>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
