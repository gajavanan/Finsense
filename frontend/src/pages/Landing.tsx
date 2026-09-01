import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { 
  BrainCircuit, 
  TrendingUp, 
  ShieldCheck, 
  PieChart, 
  Target, 
  Zap, 
  Sparkles, 
  ArrowRight, 
  CheckCircle2, 
  Lock, 
  Bell, 
  Flame, 
  CreditCard, 
  BarChart3, 
  DollarSign, 
  UserCheck, 
  ChevronRight,
  Database
} from 'lucide-react'
import { useAuthStore } from '../store/authStore'

export default function Landing() {
  const navigate = useNavigate()
  const user = useAuthStore((s: any) => s.user)

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-sky-500 selection:text-white">
      {/* Background Glow Elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-sky-500/15 rounded-full blur-3xl"></div>
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-purple-500/15 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl"></div>
      </div>

      {/* Navbar */}
      <nav className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-800/80">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
              <BrainCircuit className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              Fin<span className="text-sky-400">Sense</span>
            </span>
          </div>

          <div className="hidden md:flex items-center space-x-8 text-sm font-medium text-slate-300">
            <a href="#features" className="hover:text-sky-400 transition-colors">Features</a>
            <a href="#ai-advisor" className="hover:text-sky-400 transition-colors">AI Advisor</a>
            <a href="#how-it-works" className="hover:text-sky-400 transition-colors">How It Works</a>
            <a href="#security" className="hover:text-sky-400 transition-colors">Security</a>
          </div>

          <div className="flex items-center space-x-4">
            {user ? (
              <button 
                onClick={() => navigate('/dashboard')}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white font-medium text-sm transition-all shadow-md shadow-sky-500/20 flex items-center space-x-2"
              >
                <span>Go to Dashboard</span>
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">
                  Login
                </Link>
                <Link 
                  to="/register" 
                  className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 text-white font-medium text-sm transition-all shadow-md shadow-sky-500/25"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 pt-20 pb-16 md:pt-32 md:pb-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold uppercase tracking-wider mb-8">
          <Sparkles className="w-3.5 h-3.5 text-sky-400" />
          <span>Smarter Money. Better Decisions.</span>
        </div>

        <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold text-white tracking-tight max-w-4xl mx-auto leading-[1.15]">
          Your AI-Powered <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-sky-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
            Personal Finance Advisor
          </span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto font-normal leading-relaxed">
          Understand your money, control your spending, and build your financial future with intelligent insights powered by real machine learning.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/register"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-sky-500 via-blue-600 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white font-semibold text-base shadow-xl shadow-sky-500/25 transition-all flex items-center justify-center space-x-2"
          >
            <span>Get Started Free</span>
            <ArrowRight className="w-5 h-5" />
          </Link>
          <a
            href="#features"
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold text-base transition-all"
          >
            Explore Features
          </a>
        </div>

        {/* Dashboard Preview Mockup */}
        <div className="mt-16 sm:mt-24 relative max-w-5xl mx-auto">
          <div className="absolute -inset-1 rounded-2xl bg-gradient-to-r from-sky-500 to-indigo-600 opacity-20 blur-xl"></div>
          <div className="relative rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl overflow-hidden text-left p-4 sm:p-6">
            {/* Window bar */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
              <div className="flex items-center space-x-2">
                <div className="w-3 h-3 rounded-full bg-red-500/80"></div>
                <div className="w-3 h-3 rounded-full bg-yellow-500/80"></div>
                <div className="w-3 h-3 rounded-full bg-green-500/80"></div>
                <span className="ml-4 text-xs font-mono text-slate-500">app.finsense.ai/dashboard</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="px-2.5 py-1 rounded bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-medium">
                  Live ML Connected
                </div>
              </div>
            </div>

            {/* Dashboard Sample Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <p className="text-xs text-slate-400 font-medium">Net Worth</p>
                <p className="text-xl font-bold text-white mt-1">₹4,28,500</p>
                <span className="text-xs text-emerald-400 flex items-center mt-1">
                  <TrendingUp className="w-3 h-3 mr-1" /> +12.4% this month
                </span>
              </div>
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <p className="text-xs text-slate-400 font-medium">Monthly Income</p>
                <p className="text-xl font-bold text-emerald-400 mt-1">₹1,20,000</p>
                <span className="text-xs text-slate-400 mt-1">Verified primary salary</span>
              </div>
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <p className="text-xs text-slate-400 font-medium">Monthly Expenses</p>
                <p className="text-xl font-bold text-rose-400 mt-1">₹48,200</p>
                <span className="text-xs text-emerald-400 mt-1">18% lower than budget</span>
              </div>
              <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                <p className="text-xs text-slate-400 font-medium">Health Score</p>
                <div className="flex items-center space-x-2 mt-1">
                  <p className="text-xl font-bold text-sky-400">88/100</p>
                  <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-xs font-semibold">Excellent</span>
                </div>
              </div>
            </div>

            {/* Simulated Chart & AI Insight */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="md:col-span-2 bg-slate-950/60 p-4 rounded-xl border border-slate-800 flex flex-col justify-between">
                <div className="flex justify-between items-center mb-4">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Spending Trends & Forecasting</h4>
                  <span className="text-xs text-sky-400">ML Forecast Active</span>
                </div>
                <div className="h-32 flex items-end justify-between gap-2 pt-4 px-2 border-b border-slate-800/60">
                  <div className="w-full bg-sky-500/30 rounded-t h-[40%] hover:bg-sky-500/50 transition-all"></div>
                  <div className="w-full bg-sky-500/40 rounded-t h-[65%] hover:bg-sky-500/60 transition-all"></div>
                  <div className="w-full bg-sky-500/50 rounded-t h-[50%] hover:bg-sky-500/70 transition-all"></div>
                  <div className="w-full bg-sky-500/60 rounded-t h-[80%] hover:bg-sky-500/80 transition-all"></div>
                  <div className="w-full bg-sky-500/80 rounded-t h-[60%] hover:bg-sky-500 transition-all"></div>
                  <div className="w-full bg-gradient-to-t from-sky-500 to-indigo-500 rounded-t h-[45%] shadow-lg shadow-sky-500/20"></div>
                </div>
                <div className="flex justify-between text-[11px] text-slate-500 mt-2">
                  <span>May</span><span>Jun</span><span>Jul</span><span>Aug</span><span>Sep</span><span>Oct (Predicted)</span>
                </div>
              </div>

              <div className="bg-gradient-to-br from-slate-900 to-slate-950 p-4 rounded-xl border border-sky-500/30 flex flex-col justify-between">
                <div>
                  <div className="flex items-center space-x-2 text-sky-400 mb-2">
                    <Sparkles className="w-4 h-4" />
                    <span className="text-xs font-bold uppercase tracking-wider">AI Financial Advisor</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    "Your dining expenses increased 18% this month, but your total spending remains 12% below your target budget limit."
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Confidence: 94%</span>
                  <span className="text-sky-400 hover:underline cursor-pointer">Ask Advisor →</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 bg-slate-900/50 border-y border-slate-800/80 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <h2 className="text-xs font-bold tracking-widest text-sky-400 uppercase">Comprehensive Suite</h2>
            <p className="mt-3 text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Everything You Need for Complete Financial Mastery
            </p>
            <p className="mt-4 text-slate-400 text-base">
              Built with modern machine learning algorithms, PostgreSQL data isolation, and intuitive analytics.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<BrainCircuit className="w-6 h-6 text-sky-400" />}
              title="AI Financial Advisor"
              description="Interact with a dedicated financial intelligence assistant trained to evaluate your cash flow and provide actionable recommendations."
            />
            <FeatureCard 
              icon={<CreditCard className="w-6 h-6 text-indigo-400" />}
              title="Smart Expense Tracking"
              description="Log and monitor transactions with automated metadata enrichment, payment method tracking, and category tags."
            />
            <FeatureCard 
              icon={<TrendingUp className="w-6 h-6 text-emerald-400" />}
              title="ML Spending Predictions"
              description="Machine learning forecasting models project future monthly expenses based on historical spending cadence."
            />
            <FeatureCard 
              icon={<PieChart className="w-6 h-6 text-purple-400" />}
              title="Budget Optimization"
              description="Dynamic budget allocation tools calculate optimal thresholds (50%, 75%, 90%) per category to prevent overspending."
            />
            <FeatureCard 
              icon={<Target className="w-6 h-6 text-amber-400" />}
              title="Savings Goals & Predictor"
              description="Track target dates and monthly contributions with ML goal prediction estimating your exact completion timeline."
            />
            <FeatureCard 
              icon={<DollarSign className="w-6 h-6 text-teal-400" />}
              title="Investment Portfolio Tracking"
              description="Monitor asset breakdown across stocks, bonds, cash, and crypto with allocation analytics."
            />
            <FeatureCard 
              icon={<BarChart3 className="w-6 h-6 text-blue-400" />}
              title="Financial Reports"
              description="Generate detailed monthly and annual financial summaries with exportable analytics."
            />
            <FeatureCard 
              icon={<Zap className="w-6 h-6 text-orange-400" />}
              title="Subscription Detection"
              description="Algorithmic pattern recognition identifies recurring monthly payments and subscription fees."
            />
            <FeatureCard 
              icon={<Flame className="w-6 h-6 text-rose-400" />}
              title="FIRE Retirement Calculator"
              description="Calculate your Financial Independence, Retire Early (FIRE) target corpus, required savings rate, and timeline."
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs font-bold tracking-widest text-sky-400 uppercase">Seamless Workflow</h2>
          <p className="mt-3 text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            How FinSense Works for You
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          <StepCard 
            step="01"
            title="Connect Your Finances"
            description="Register your account securely and input your income, assets, and initial transactions."
          />
          <StepCard 
            step="02"
            title="AI Data Analysis"
            description="Machine learning engines process categories, detect recurring bills, and calculate spending anomalies."
          />
          <StepCard 
            step="03"
            title="Get Smart Advice"
            description="Receive real-time notifications, budget recommendations, and targeted goal completion dates."
          />
          <StepCard 
            step="04"
            title="Build Wealth Safely"
            description="Track net worth growth over time with clear visual charts and automated financial health scoring."
          />
        </div>
      </section>

      {/* AI Capabilities Section */}
      <section id="ai-advisor" className="py-20 bg-slate-900/40 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-semibold uppercase tracking-wider mb-6">
                <BrainCircuit className="w-3.5 h-3.5" />
                <span>Powered by Machine Learning</span>
              </div>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
                Real Statistical & ML Models Working Behind the Scenes
              </h2>
              <p className="mt-4 text-slate-400 text-base leading-relaxed">
                Unlike static spreadsheets, FinSense embeds scikit-learn classification, regression, and anomaly detection algorithms directly into your workflow.
              </p>

              <div className="mt-8 space-y-4">
                <AiFeatureRow 
                  title="Transaction Categorization" 
                  desc="Automatically assigns category labels to merchant descriptions with scikit-learn NLP models."
                />
                <AiFeatureRow 
                  title="Spending Forecasting" 
                  desc="Projects next month's expense envelope using time-series trend extrapolation."
                />
                <AiFeatureRow 
                  title="Anomaly Detection" 
                  desc="Flags unusually large transactions or irregular spending patterns instantly."
                />
                <AiFeatureRow 
                  title="Goal Completion Predictor" 
                  desc="Calculates exact expected completion dates based on historical net saving velocity."
                />
              </div>
            </div>

            <div className="bg-slate-900 p-6 sm:p-8 rounded-2xl border border-slate-800 shadow-xl space-y-6">
              <h3 className="text-lg font-bold text-white flex items-center space-x-2">
                <Sparkles className="w-5 h-5 text-sky-400" />
                <span>Sample Advisor Interaction</span>
              </h3>

              <div className="space-y-4">
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 text-sm">
                  <p className="text-xs text-sky-400 font-semibold mb-1">User Question</p>
                  <p className="text-slate-200">"Where did most of my money go this month and how can I save ₹10,000 more?"</p>
                </div>

                <div className="bg-slate-950/80 p-4 rounded-xl border border-sky-500/20 text-sm">
                  <p className="text-xs text-indigo-400 font-semibold mb-1">FinSense AI Advisor</p>
                  <p className="text-slate-300 leading-relaxed">
                    "Based on your 42 transactions this month, your top expense category was <strong>Dining & Takeout (₹16,400)</strong>, followed by <strong>Subscriptions (₹4,200)</strong>. Reducing dining out by 40% will save ₹6,500/mo, and pausing 2 unused streaming subscriptions adds another ₹1,800/mo, getting you 83% of the way to your target!"
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section id="security" className="py-20 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-4">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Bank-Grade Architecture</span>
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Security & Privacy First
          </h2>
          <p className="mt-4 text-slate-400 text-base">
            Your financial data is protected using verified cryptographic standards and isolated database schemas.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800">
            <Lock className="w-8 h-8 text-sky-400 mb-4" />
            <h3 className="text-lg font-bold text-white">JWT Authentication</h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Cryptographically signed tokens ensure only authenticated sessions can access account endpoints.
            </p>
          </div>

          <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800">
            <Database className="w-8 h-8 text-indigo-400 mb-4" />
            <h3 className="text-lg font-bold text-white">PostgreSQL Data Isolation</h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Strict relational foreign key constraints and user ownership checks ensure zero cross-account leakage.
            </p>
          </div>

          <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800">
            <ShieldCheck className="w-8 h-8 text-emerald-400 mb-4" />
            <h3 className="text-lg font-bold text-white">Bcrypt Password Hashing</h3>
            <p className="mt-2 text-sm text-slate-400 leading-relaxed">
              Passwords are salted and hashed using standard bcrypt algorithm before stored in database.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 relative overflow-hidden">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          <div className="p-10 sm:p-16 rounded-3xl bg-gradient-to-br from-sky-900/40 via-slate-900 to-indigo-950/60 border border-sky-500/30 shadow-2xl">
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
              Take Control of Your Financial Future
            </h2>
            <p className="mt-4 text-slate-300 text-lg max-w-xl mx-auto">
              Join FinSense today and unlock real machine learning insights for your personal money management.
            </p>
            <div className="mt-8">
              <Link
                to="/register"
                className="inline-flex items-center space-x-2 px-8 py-4 rounded-xl bg-sky-500 hover:bg-sky-400 text-white font-semibold text-base transition-all shadow-xl shadow-sky-500/30"
              >
                <span>Start Using FinSense</span>
                <ArrowRight className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-12 bg-slate-950 text-slate-500 text-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center">
              <BrainCircuit className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white">FinSense</span>
          </div>

          <p className="text-xs text-slate-500">
            © {new Date().getFullYear()} FinSense. All rights reserved. Smarter Money. Better Decisions.
          </p>

          <div className="flex space-x-6 text-slate-400 text-xs">
            <a href="#" className="hover:text-white transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-white transition-colors">Terms of Service</a>
            <a href="#" className="hover:text-white transition-colors">Contact Support</a>
            <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-white transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="bg-slate-900/60 p-6 rounded-2xl border border-slate-800 hover:border-sky-500/40 transition-all hover:shadow-lg hover:shadow-sky-500/5 group">
      <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
        {icon}
      </div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
    </div>
  )
}

function StepCard({ step, title, description }: { step: string; title: string; description: string }) {
  return (
    <div className="bg-slate-900/40 p-6 rounded-2xl border border-slate-800/80 relative">
      <span className="text-3xl font-black text-sky-500/30 mb-2 block">{step}</span>
      <h3 className="text-base font-bold text-white mb-2">{title}</h3>
      <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
    </div>
  )
}

function AiFeatureRow({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="flex items-start space-x-3">
      <CheckCircle2 className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
      <div>
        <h4 className="text-sm font-semibold text-white">{title}</h4>
        <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
      </div>
    </div>
  )
}
