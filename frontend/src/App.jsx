import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'

// Car icon, built from separate wheel, body, and window layers
const CarIcon = ({ className = "w-10 h-10 shrink-0" }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="sleek-dark" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#d1d5db" />
        <stop offset="35%" stopColor="#374151" />
        <stop offset="85%" stopColor="#030308" />
      </linearGradient>
    </defs>

    {/* Wheels */}
    <circle cx="7" cy="18" r="2.1" fill="#050505" />
    <circle cx="7" cy="18" r="0.9" fill="#9ca3af" />
    <circle cx="7" cy="18" r="0.3" fill="#050505" />

    <circle cx="17" cy="18" r="2.1" fill="#050505" />
    <circle cx="17" cy="18" r="0.9" fill="#9ca3af" />
    <circle cx="17" cy="18" r="0.3" fill="#050505" />

    {/* Body */}
    <path fill="url(#sleek-dark)" d="M 21 18 H 19.5 A 2.5 2.5 0 0 0 14.5 18 H 9.5 A 2.5 2.5 0 0 0 4.5 18 H 3 A 1.5 1.5 0 0 1 1.5 16.5 V 13.5 C 1.5 12.8 1.8 12.2 2.5 12 L 5 11 L 7.5 7.5 C 8 7 8.7 6.5 9.5 6.5 L 14.5 6.5 C 15.3 6.5 16 7 16.5 7.5 L 19 11 L 21.5 12 C 22.2 12.2 22.5 12.8 22.5 13.5 V 16.5 A 1.5 1.5 0 0 1 21 18 Z" />

    {/* Window */}
    <path fill="#030308" opacity="0.5" d="M 7 11 H 17 L 15 8 H 9 L 7 11 Z" />

    {/* Body accent line */}
    <path d="M 3.5 14.5 H 20.5" stroke="#030308" strokeWidth="0.4" strokeOpacity="0.3" fill="none" />
  </svg>
)

const PinIcon = ({ className = 'w-3 h-3' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 21s-7-7.3-7-12a7 7 0 0 1 14 0c0 4.7-7 12-7 12z" />
    <circle cx="12" cy="9" r="2.4" />
  </svg>
)

const RefreshIcon = ({ className = 'w-4 h-4' }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12a9 9 0 1 1-2.64-6.36" />
    <path d="M21 3v6h-6" />
  </svg>
)

function App() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [feed, setFeed] = useState([])
  const [showWipMsg, setShowWipMsg] = useState(false)
  const [progress, setProgress] = useState(0)
  const [jobId, setJobId] = useState(null)

  const fetchFeed = () => {
    axios.get(`${API_URL}/feed`)
      .then(res => setFeed(res.data))
      .catch(err => console.error("Failed to load feed:", err))
  }

  useEffect(() => {
    fetchFeed()
  }, [])

  const handleAnalyze = async (e) => {
    e.preventDefault()
    if (!url) return

    setLoading(true)
    setError('')
    setResult(null)
    setProgress(0)

    try {
      // 1. Get the Job ID (Instant)
      const response = await axios.post(`${API_URL}/evaluate_url`, { url })
      const id = response.data.job_id
      setJobId(id)

      // 2. Start the fake progress bar (randomized 8-12% increments)
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return 90; 
          // Random number between 8 and 12
          const increment = Math.floor(Math.random() * 5) + 8;
          return Math.min(prev + increment, 90);
        })
      }, 700) // Tick slightly faster (0.7s) to make it feel active

      // 3. Start polling the backend every 2 seconds
      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await axios.get(`${API_URL}/status/${id}`)
          const jobData = statusRes.data

          if (jobData.status === 'completed') {
            clearInterval(pollInterval)
            clearInterval(progressInterval)
            setProgress(100)
            setTimeout(() => setLoading(false), 500) // Half second delay to see 100%
            setResult(jobData)
          } else if (jobData.status === 'failed') {
            clearInterval(pollInterval)
            clearInterval(progressInterval)
            setLoading(false)
            setError(jobData.error || 'Failed to analyze the URL.')
          }
        } catch (err) {
          console.error("Polling error:", err)
        }
      }, 2000)

    } catch (err) {
      setLoading(false)
      setError('Failed to connect to the server. Is the backend running?')
    }
  }

  const getVerdictColor = (difference) => {
    if (difference > 1000) return 'text-emerald-300'
    if (difference < -1000) return 'text-rose-300'
    return 'text-amber-200'
  }

  const getVerdictBgColor = (difference) => {
    if (difference > 1000) return 'bg-emerald-300'
    if (difference < -1000) return 'bg-rose-300'
    return 'bg-amber-300'
  }

  const formatDifference = (difference) => {
    const isGoodDeal = difference > 0
    const amount = Math.abs(difference / 1000).toFixed(1)
    return {
            text: isGoodDeal ? `$${amount}k under AI prediction` : `$${amount}k over AI prediction`,
      colorClass: isGoodDeal ? 'text-emerald-300/90' : 'text-rose-300/90',
    }
  }

  // Determine what text to show based on progress
  let statusText = "Initializing...";
  if (progress >= 100) statusText = "Getting Result...";
  else if (progress >= 80) statusText = "Running AI Prediction...";
  else if (progress >= 40) statusText = "Analyzing Listing...";
  else if (progress > 0) statusText = "Getting URL...";

  return (
    <div className="min-h-screen font-sans relative overflow-hidden">

      <nav className="flex justify-between items-center px-12 py-6 border-b border-white/5 backdrop-blur-sm bg-black/20 z-10 relative">
        <h1 className="flex items-center gap-4">
          <CarIcon className="w-14 h-14 scale-x-[-1] shrink-0" />
          <span className="text-gray-100 font-bold uppercase tracking-[0.2em] text-xl">
            AutoValuate
          </span>
        </h1>
        <div className="flex items-center space-x-8 text-base font-medium text-gray-400">
          <a href="#feed" className="hover:text-white transition">Feed</a>
          {/* Updated Insights link */}
          <a href="#" onClick={(e) => { e.preventDefault(); setShowWipMsg(true) }} className="hover:text-white transition">Insights</a>
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer" className="hover:text-white transition">API</a>
          {/* Updated Login button */}
          <button onClick={() => setShowWipMsg(true)} className="px-4 py-1.5 bg-white/5 border border-white/10 text-white hover:bg-white/10 transition rounded-lg text-base">
            Login
          </button>
        </div>
      </nav>

      <header className="max-w-4xl mx-auto text-center pt-16 pb-12 px-6 relative z-10 flex flex-col items-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="inline-flex flex-col items-stretch text-center mb-6"
        >
          <h2 className="text-3xl md:text-[3.25rem] font-extrabold tracking-tighter text-white whitespace-nowrap">
            Never overpay for a used car
          </h2>
          <div className="text-[6rem] md:text-[9.5rem] font-black text-white leading-none mt-1 tracking-tighter">
            PERIOD.
          </div>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="text-gray-400 text-base md:text-lg mb-8 max-w-lg mx-auto leading-relaxed font-light"
        >
          Instantly evaluate any listing against real-time nationwide market data using Artificial Intelligence.
        </motion.p>

        <motion.form
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.6 }}
          onSubmit={handleAnalyze}
          className="flex w-full max-w-2xl mx-auto space-x-2"
        >
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Paste Craigslist URL here..."
            className="flex-1 px-5 py-4 bg-white/[0.07] backdrop-blur-md border border-white/15 text-white placeholder-gray-300 font-semibold text-base focus:outline-none focus:border-indigo-500/60 transition rounded-lg shadow-inner"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-8 py-4 bg-indigo-600 text-white font-medium hover:bg-indigo-500 transition disabled:opacity-50 text-sm rounded-lg shadow-lg shadow-indigo-600/20 shrink-0"
          >
            {loading ? 'Analyzing...' : 'Analyze →'}
          </button>
        </motion.form>

        {/* Loading Progress Bar */}
        {loading && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 w-full max-w-2xl mx-auto"
          >
            <div className="relative w-full bg-gray-800/50 border border-white/10 rounded-lg h-10 overflow-hidden flex items-center justify-center">
              {/* Progress fill */}
              <motion.div 
                className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-600 to-purple-600 opacity-40"
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: "easeInOut" }}
              />
              {/* Status Text (White, bold, all caps, small) */}
              <span className="relative z-10 text-white font-bold uppercase tracking-widest text-xs">
                {statusText}
              </span>
            </div>
          </motion.div>
        )}

        {error && (
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="mt-6 text-sm text-red-300 bg-red-900/30 border border-red-500/20 px-4 py-2 rounded-lg inline-block"
          >
            {error}
          </motion.p>
        )}
      </header>

      {/* Analysis result card, only rendered once a listing has been evaluated */}
      <AnimatePresence>
        {result && (
          <motion.section
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{ duration: 0.4, type: "spring" }}
            className="w-full max-w-4xl mx-auto px-6 pb-12 relative z-10"
          >
            <div className="w-full max-w-2xl mx-auto border border-white/10 rounded-xl backdrop-blur-md bg-white/5 animated-gradient shadow-2xl overflow-hidden flex flex-col">

              <div className="p-8">
                <p className="text-xs uppercase tracking-widest text-gray-400 mb-2 font-semibold">Analysis Complete</p>
                <h3 className="text-2xl font-bold mb-8 capitalize text-white">{result.listing_title}</h3>

                <div className="flex justify-between items-center">

                  <div className="shrink-0">
                    <p className="text-sm text-gray-400 mb-1">Listed Price</p>
                    <p className="text-3xl font-bold text-white">${result.listing_price.toLocaleString()}</p>
                  </div>

                  {/* Animated beam connecting listed price to predicted price */}
                  <div className="flex-1 mx-8 relative flex items-center justify-center overflow-hidden h-15">
                    <div className="absolute w-full h-[2px] bg-white/10 rounded-full" />

                    <motion.div
                      className="absolute h-[2px] bg-gradient-to-r from-transparent via-indigo-400 to-transparent w-1/3"
                      initial={{ left: "-33%" }}
                      animate={{ left: "100%" }}
                      transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
                    />

                    <div className="relative z-10 bg-[#030308] border border-white/15 p-5 rounded-full shadow-2xl flex items-center justify-center">
                      <CarIcon className="w-14 h-14 scale-x-[-1]" />
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <p className="text-sm text-gray-400 mb-1">AI Prediction</p>
                    <p className="text-3xl font-bold text-indigo-300">${result.predicted_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                  </div>

                </div>
              </div>

              {/* Verdict banner, colored by how far the listing is from predicted value */}
              <div className={`px-8 py-5 ${getVerdictBgColor(result.difference)}`}>
                <p className="text-xs uppercase tracking-widest text-black/60 mb-1 font-bold">Verdict</p>
                <p className="text-xl font-extrabold text-black mb-0.5">
                  {result.verdict}
                </p>
                <p className="text-sm font-bold text-black/70">
                  {formatDifference(result.difference).text}
                </p>
              </div>

            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Market feed of live listings pulled from the backend */}
      <section id="feed" className="max-w-6xl mx-auto px-6 py-12 border-t border-white/5 relative z-10">
        <div className="flex justify-between items-end mb-8">
          <h3 className="text-3xl font-bold tracking-tight text-white">Market Feed</h3>
          <button
            onClick={fetchFeed}
            className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 hover:text-white transition rounded-lg text-sm font-medium"
          >
            <RefreshIcon className="w-4 h-4" />
            Refresh Feed
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {feed && feed.length > 0 ? (
            feed.map((car, i) => {
              const diff = formatDifference(car.difference)
              return (
                <motion.a
                  key={i}
                  href={car.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: i * 0.05 }}
                  whileHover={{ scale: 1.02 }}
                  className="relative h-96 rounded-2xl overflow-hidden border border-white/10 group cursor-pointer bg-gradient-to-br from-[#0f111a] to-[#0a0a0f] block shadow-lg"
                >
                  <div className="absolute top-5 left-5 z-20">
                    <span className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-300 bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 font-medium">
                      <PinIcon className="w-3 h-3" />
                      {car.location}
                    </span>
                  </div>

                  {/* Mileage Top Right*/}
                  <div className="absolute top-5 right-5 z-20">
                    <span className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-300 bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 font-medium">
                      {car.mileage.toLocaleString()} mi
                    </span>
                  </div>

                  {/* Faded car icon as a decorative background element */}
                  <div className="absolute inset-0 overflow-hidden rounded-2xl pointer-events-none z-0">
                    <div className="absolute -top-12 -right-16 opacity-[0.08] blur-[2px] mix-blend-screen group-hover:scale-110 group-hover:opacity-[0.15] group-hover:-translate-x-2 transition-all duration-700 ease-out">
                      <CarIcon className="w-80 h-80 scale-x-[-1]" />
                    </div>
                  </div>

                  <div className="absolute inset-0 p-6 flex flex-col justify-end bg-gradient-to-t from-black via-black/60 to-transparent transition-all z-10">
                    <h4 className="text-2xl font-bold mb-6 text-white tracking-tight">{car.name}</h4>

                    <div className="flex justify-between items-end mb-4">
                      <div>
                        <p className="text-xs uppercase tracking-widest text-gray-500 mb-1 font-semibold">Listed Price</p>
                        <p className="text-3xl font-extrabold text-white">${car.list_price.toLocaleString()}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs uppercase tracking-widest text-indigo-400/80 mb-1 font-semibold">AI Prediction</p>
                        <p className="text-3xl font-extrabold text-indigo-300">${car.ai_price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
                      </div>
                    </div>

                    <div className="mt-2 pt-4 border-t border-white/10 flex justify-center">
                      <span className={`text-sm font-bold tracking-wide ${diff.colorClass}`}>
                        {diff.text}
                      </span>
                    </div>
                  </div>
                </motion.a>
              )
            })
          ) : (
            <div className="col-span-3 text-center text-gray-500 py-10 flex justify-center items-center gap-2">
              <RefreshIcon className="w-4 h-4 animate-spin opacity-50" />
              Loading live market deals...
            </div>
          )}
        </div>
      </section>

      <footer className="border-t border-white/5 py-8 px-12 flex flex-col md:flex-row justify-between items-center text-xs text-gray-500 relative z-10 gap-4">
        <div>© {new Date().getFullYear()} AutoValuate. All rights reserved.</div>
        <div className="flex items-center gap-6">
          <a href="https://github.com/abhiswrld" target="_blank" rel="noreferrer" className="hover:text-white transition">GitHub ↗</a>
          <a href="https://www.linkedin.com/in/abhinav-khanna06/" target="_blank" rel="noreferrer" className="hover:text-white transition">LinkedIn ↗</a>
        </div>
      </footer>

      {/* Work in Progress Pop-up Toast (Top Right) */}
      <AnimatePresence>
        {showWipMsg && (
          <motion.div 
            key="wip-toast" 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 50 }}
            className="fixed top-[105px] right-[10px] bg-black/80 backdrop-blur-md border border-white/10 text-white px-6 py-3 rounded-xl shadow-2xl z-50 flex items-center gap-4"
          >
            <span>This feature is a work in progress!</span>
            <button onClick={() => setShowWipMsg(false)} className="text-gray-400 hover:text-white">✕</button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default App