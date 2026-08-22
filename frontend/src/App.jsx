import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import { supabase } from './supabaseClient'
import Insights from './Insights'

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

const GooglyEye = () => {
  const eyeRef = useRef(null);
  const pupilRef = useRef(null);

  useEffect(() => {
    let animationFrameId = null;
    let currentX = 0;
    let currentY = 0;

    const updateEye = () => {
      if (!eyeRef.current || !pupilRef.current) return;
      const eye = eyeRef.current.getBoundingClientRect();
      const eyeCenterX = eye.left + eye.width / 2;
      const eyeCenterY = eye.top + eye.height / 2;
      
      const angle = Math.atan2(currentY - eyeCenterY, currentX - eyeCenterX);
      const maxMove = eye.width / 4.5;
      const dist = Math.hypot(currentX - eyeCenterX, currentY - eyeCenterY);
      const move = Math.min(dist / 20, maxMove);

      const x = Math.cos(angle) * move;
      const y = Math.sin(angle) * move;

      pupilRef.current.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      animationFrameId = null;
    };

    const handleMouseMove = (e) => {
      currentX = e.clientX;
      currentY = e.clientY;
      if (!animationFrameId) {
        animationFrameId = requestAnimationFrame(updateEye);
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div 
      ref={eyeRef}
      className="relative w-24 h-24 md:w-36 md:h-36 rounded-full flex items-center justify-center overflow-hidden border-[6px] border-[#0a0a0f] shadow-[inset_0_0_30px_rgba(255,255,255,0.15)] bg-gradient-to-br from-gray-800 via-gray-900 to-black"
    >
      {/* Headlight Bulb */}
      <div 
        ref={pupilRef}
        className="absolute w-10 h-10 md:w-14 md:h-14 rounded-full bg-[#fefce8] flex items-center justify-center z-10"
        style={{ 
          transform: `translate3d(0px, 0px, 0)`,
          boxShadow: '0 0 30px 15px rgba(254, 240, 138, 0.3), inset 0 0 15px 5px rgba(255, 255, 255, 0.9)'
        }}
      >
      </div>
    </div>
  );
};

const GooglyEyesContainer = () => {
  return (
    <div className="flex gap-4 justify-center mt-6">
      <GooglyEye />
      <GooglyEye />
    </div>
  );
};

const SortDropdown = ({ sortBy, onSortChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const options = [
    { value: 'latest', label: 'Latest Listings' },
    { value: 'price_low', label: 'Price: Low to High' },
    { value: 'price_high', label: 'Price: High to Low' },
    { value: 'mileage_low', label: 'Mileage: Lowest' }
  ];

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedLabel = options.find(opt => opt.value === sortBy)?.label;

  return (
    <div className="relative flex items-center gap-3" ref={dropdownRef}>
      <span className="text-[15px] text-gray-400 font-medium tracking-wide">Sort by:</span>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between gap-2 bg-[#0c0d12] border border-white/[0.08] hover:border-white/[0.15] text-white text-[15px] rounded-xl px-4 py-2.5 outline-none transition-all w-48 shadow-lg"
      >
        <span className="font-medium">{selectedLabel}</span>
      </button>

      {isOpen && (
        <div className="absolute z-50 right-0 top-[110%] w-48 rounded-xl bg-[#1f2029] border border-white/[0.08] shadow-[0_8px_30px_rgb(0,0,0,0.5)] py-2 overflow-hidden backdrop-blur-xl">
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                onSortChange(option.value);
                setIsOpen(false);
              }}
              className="w-full text-left px-4 py-2.5 text-[15px] text-gray-300 hover:bg-white/[0.06] hover:text-white transition-colors flex items-center"
            >
              <span className={sortBy === option.value ? "font-semibold text-white" : "font-medium"}>
                {option.label}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

function App() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [feed, setFeed] = useState([])
  const [freshDrops, setFreshDrops] = useState([])
  const [activeTab, setActiveTab] = useState('feed')
  const [insightMake, setInsightMake] = useState('')
  const [insightModel, setInsightModel] = useState('')
  const [progress, setProgress] = useState(0)

  const navigateToInsights = (make, model) => {
    setInsightMake(make);
    setInsightModel(model);
    setActiveTab('insights');
    document.getElementById('main-content')?.scrollIntoView({ behavior: 'smooth' });
  };
  const [jobId, setJobId] = useState(null)
  const [regionCounts, setRegionCounts] = useState({})
  const [selectedRegion, setSelectedRegion] = useState('sfbay')
  const [selectedCity, setSelectedCity] = useState('all')

  const regionAbbreviations = {
    'sfbay': 'SF',
    'losangeles': 'LA',
    'newyork': 'NY',
    'seattle': 'SE',
    'chicago': 'CH',
    'dallas': 'DA',
    'miami': 'MI',
    'atlanta': 'AT',
    'boston': 'BO',
    'phoenix': 'PH'
  }
  const [availableCities, setAvailableCities] = useState([])
  const [showAllCities, setShowAllCities] = useState(false)
  const [citySearchQuery, setCitySearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('latest')
  const [offset, setOffset] = useState(0)
  const [loadingFeed, setLoadingFeed] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  
  // Auth & Watchlist States
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authMode, setAuthMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [user, setUser] = useState(null)
  const [watchlist, setWatchlist] = useState([])
  const [showWatchlist, setShowWatchlist] = useState(false)
  const [watchlistCars, setWatchlistCars] = useState([])

  const [reportingUrls, setReportingUrls] = useState({});
  const [toastMessage, setToastMessage] = useState(null);

  const handleReportSold = (e, url) => {
    e.preventDefault();
    e.stopPropagation();
    
    setReportingUrls(prev => ({ ...prev, [url]: true }));
    if (!user) return;
    axios.post(`${API_URL}/api/report-sold`, { url, user_id: user.id })
      .then(res => {
        if (res.data.status === "deleted") {
          setFeed(prev => prev.filter(car => car.url !== url));
          setToastMessage("Verified & Removed!");
        } else {
          setToastMessage(res.data.message || "Still active!");
        }
        setTimeout(() => setToastMessage(null), 3000);
      })
      .catch(err => {
        setToastMessage(err.response?.data?.detail || "Error verifying.");
        setTimeout(() => setToastMessage(null), 3000);
      })
      .finally(() => {
        setReportingUrls(prev => ({ ...prev, [url]: false }));
      });
  };


  const fetchFeed = (region = selectedRegion, city = selectedCity, sort = sortBy, currentOffset = 0, append = false) => {
    setLoadingFeed(true)
    axios.get(`${API_URL}/feed?region=${region}&city=${city}&sort_by=${sort}&offset=${currentOffset}`)
      .then(res => {
        if (res.data.length < 15) setHasMore(false)
        else setHasMore(true)
        
        if (append) {
          setFeed(prev => [...prev, ...res.data])
        } else {
          setFeed(res.data)
        }
        setOffset(currentOffset)
      })
      .catch(err => console.error("Failed to load feed:", err))
      .finally(() => setLoadingFeed(false))
  }

  const handleSortChange = (newSort) => {
    setSortBy(newSort);
    fetchFeed(selectedRegion, selectedCity, newSort, 0, false);
  }

  const handleRegionClick = (region) => {
    setSelectedRegion(region);
    setSelectedCity('all');
    setShowAllCities(false);
    setCitySearchQuery('');
    setSortBy('latest');
    fetchFeed(region, 'all', 'latest', 0, false);
    
    if (region !== 'all') {
      axios.get(`${API_URL}/cities?region=${region}`)
        .then(res => {
          const data = res.data;
          // Handle both old format (string[]) and new format ({name,count}[])
          if (data.length > 0 && typeof data[0] === 'string') {
            setAvailableCities(data.map(name => ({ name, count: null })));
          } else {
            setAvailableCities(data);
          }
        })
        .catch(err => console.error("Failed to load cities:", err));
    } else {
      setAvailableCities([]);
    }
  };

  const fetchWatchlist = async (userId) => {
    const { data, error } = await supabase
      .from('watchlist')
      .select('car_url')
      .eq('user_id', userId)
    
    if (!error && data) {
      setWatchlist(data.map(item => item.car_url))
    }
  }

  useEffect(() => {
    fetchFeed()
    
    const fetchFreshDrops = async () => {
      try {
        const response = await axios.get(`${API_URL}/feed/fresh`);
        setFreshDrops(response.data);
      } catch (error) {
        console.error('Error fetching fresh drops:', error);
      }
    };

    fetchFreshDrops();
    
    // Initial fetch for the default region (sfbay)
    axios.get(`${API_URL}/cities?region=sfbay`)
      .then(res => {
        const data = res.data;
        if (data.length > 0 && typeof data[0] === 'string') {
          setAvailableCities(data.map(name => ({ name, count: null })));
        } else {
          setAvailableCities(data);
        }
      })
      .catch(err => console.error("Failed to load initial cities:", err));

    axios.get(`${API_URL}/regions`)
      .then(res => setRegionCounts(res.data))
      .catch(err => console.error("Failed to load region counts:", err))

    const checkUser = async () => {
      try {
        const { data } = await supabase.auth.getSession()
        const currentUser = data?.session?.user || null
        setUser(currentUser)
        
        if (currentUser) {
          fetchWatchlist(currentUser.id)
        }
      } catch (error) {
        console.error("Error getting session:", error)
      }
    }
    checkUser()

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        const currentUser = session?.user || null
        setUser(currentUser)
        if (currentUser) {
          fetchWatchlist(currentUser.id)
        } else {
          setWatchlist([])
        }
      }
    )

    return () => {
      authListener.subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    const handler = setTimeout(() => {
      // Don't do anything if we haven't loaded cities yet
      if (!availableCities.length) return;

      const query = citySearchQuery.trim().toLowerCase();
      if (!query) {
        if (selectedCity !== 'all') {
          setSelectedCity('all');
          fetchFeed(selectedRegion, 'all', 'latest', 0, false);
        }
        return;
      }
      
      let match = availableCities.find(c => c.name.toLowerCase() === query);
      if (!match) {
        match = availableCities.find(c => c.name.toLowerCase().startsWith(query));
      }
      if (!match) {
        match = availableCities.find(c => c.name.toLowerCase().includes(query));
      }

      const targetCity = match ? match.name : 'all';

      if (selectedCity !== targetCity) {
        setSelectedCity(targetCity);
        setSortBy('latest'); 
        fetchFeed(selectedRegion, targetCity, 'latest', 0, false);
      }
    }, 400);

    return () => clearTimeout(handler);
  }, [citySearchQuery, availableCities, selectedRegion, selectedCity]);

  const handleAuth = async (e) => {
    e.preventDefault()
    if (authMode === 'signup') {
      const { error } = await supabase.auth.signUp({ email, password })
      if (error) alert(error.message)
      else alert('Check your email for the confirmation link!')
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) alert(error.message)
      else setShowAuthModal(false)
    }
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
  }

  const handleShowWatchlist = async () => {
    if (showWatchlist) {
      setShowWatchlist(false)
      fetchFeed()
      return
    }

    if (watchlist.length === 0) {
      alert("You haven't saved any cars yet!")
      return
    }

    try {
      const response = await axios.post(`${API_URL}/watchlist`, watchlist)
      setWatchlistCars(response.data)
      setShowWatchlist(true)
    } catch (err) {
      console.error("Failed to load watchlist:", err)
    }
  }

  const toggleSaveCar = async (carUrl) => {
    if (!user) {
      alert("Please log in to save cars to your watchlist.")
      return
    }

    if (watchlist.includes(carUrl)) {
      setWatchlist(watchlist.filter(url => url !== carUrl))
      await supabase
        .from('watchlist')
        .delete()
        .eq('user_id', user.id)
        .eq('car_url', carUrl)
    } else {
      setWatchlist([...watchlist, carUrl])
      await supabase
        .from('watchlist')
        .insert([{ user_id: user.id, car_url: carUrl }])
    }
  }

  const handleAnalyze = async (e) => {
    e.preventDefault()
    if (!url) return

    setLoading(true)
    setError('')
    setResult(null)
    setProgress(0)

    try {
      const response = await axios.post(`${API_URL}/evaluate_url`, { url })
      const id = response.data.job_id
      setJobId(id)

      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return 90; 
          const increment = Math.floor(Math.random() * 5) + 8;
          return Math.min(prev + increment, 90);
        })
      }, 700)

      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await axios.get(`${API_URL}/status/${id}`)
          const jobData = statusRes.data

          if (jobData.status === 'completed') {
            clearInterval(pollInterval)
            clearInterval(progressInterval)
            setProgress(100)
            setTimeout(() => setLoading(false), 500)
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

  const formatDifference = (difference, price, predicted) => {
    const isGoodDeal = difference > 0
    const absDiff = Math.abs(difference).toLocaleString(undefined, {maximumFractionDigits:0})
    return {
      text: isGoodDeal 
        ? `$${absDiff} under AI prediction` 
        : `$${absDiff} over AI prediction`,
      colorClass: isGoodDeal ? 'text-emerald-300/90' : 'text-rose-300/90',
      bgClass: isGoodDeal ? 'border-emerald-500/20 bg-emerald-500/10' : 'border-rose-500/20 bg-rose-500/10'
    }
  }

  let statusText = "Initializing...";
  if (progress >= 100) statusText = "Getting Result...";
  else if (progress >= 80) statusText = "Running AI Prediction...";
  else if (progress >= 40) statusText = "Analyzing Listing...";
  else if (progress > 0) statusText = "Getting URL...";

  return (
    <div className="min-h-screen font-sans relative overflow-hidden">

      {/* Toast Notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div 
            initial={{ opacity: 0, y: -20, x: "-50%" }}
            animate={{ opacity: 1, y: 0, x: "-50%" }}
            exit={{ opacity: 0, y: -20, x: "-50%" }}
            className="fixed top-10 left-1/2 z-[100] px-6 py-3 rounded-full bg-indigo-600/90 text-white font-medium border border-indigo-400/30 shadow-2xl backdrop-blur-md"
          >
            {toastMessage}
          </motion.div>
        )}
      </AnimatePresence>

      <nav className="flex justify-between items-center px-12 py-6 border-b border-white/5 backdrop-blur-sm bg-black/20 z-10 relative">
        <h1 className="flex items-center gap-4">
          <CarIcon className="w-14 h-14 scale-x-[-1] shrink-0" />
          <span className="text-gray-100 font-bold uppercase tracking-[0.2em] text-xl">
            AutoValuate
          </span>
        </h1>
        <div className="flex items-center space-x-8 text-base font-medium text-gray-400">
          <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('feed'); document.getElementById('main-content')?.scrollIntoView({ behavior: 'smooth' }); }} className={`transition ${activeTab === 'feed' ? 'text-white' : 'hover:text-white'}`}>Feed</a>
          <a href="#" onClick={(e) => { e.preventDefault(); setActiveTab('insights'); document.getElementById('main-content')?.scrollIntoView({ behavior: 'smooth' }); }} className={`transition ${activeTab === 'insights' ? 'text-white' : 'hover:text-white'}`}>Insights</a>
          <a href={`${API_URL}/docs`} target="_blank" rel="noreferrer" className="hover:text-white transition">API</a>
          {user ? (
            <button onClick={handleLogout} className="px-4 py-1.5 bg-white/5 border border-white/10 text-white hover:bg-white/10 transition rounded-lg text-base">
              Logout
            </button>
          ) : (
            <button onClick={() => { setAuthMode('signin'); setShowAuthModal(true) }} className="px-4 py-1.5 bg-white/5 border border-white/10 text-white hover:bg-white/10 transition rounded-lg text-base">
              Login
            </button>
          )}
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
            Never overpay for a <span className="text-indigo-400">used car</span>
          </h2>
          <div className="flex justify-center items-center mt-2">
            <GooglyEyesContainer />
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

        {loading && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 w-full max-w-2xl mx-auto"
          >
            <div className="relative w-full bg-gray-800/50 border border-white/10 rounded-lg h-10 overflow-hidden flex items-center justify-center">
              <motion.div 
                className="absolute left-0 top-0 h-full bg-gradient-to-r from-indigo-600 to-purple-600 opacity-40"
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: "easeInOut" }}
              />
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

              <div className={`px-8 py-5 ${getVerdictBgColor(result.difference)}`}>
                <p className="text-xs uppercase tracking-widest text-black/60 mb-1 font-bold">Verdict</p>
                <p className="text-xl font-extrabold text-black mb-0.5">
                  {result.verdict}
                </p>
                <p className="text-sm font-bold text-black/70">
                  {formatDifference(result.difference, result.listing_price, result.predicted_price).text}
                </p>
              </div>

            </div>
          </motion.section>
        )}
      </AnimatePresence>

      <div id="main-content">
      {activeTab === 'feed' ? (
      <section id="feed" className="max-w-6xl mx-auto px-6 py-12 border-t border-white/5 relative z-10">
        {/* Row 1: Main Regions */}
        <div className="flex items-center w-full gap-2 overflow-x-auto mb-4 whitespace-nowrap scrollbar-hide">
          {[
            { key: 'sfbay', label: 'Bay Area' },
            { key: 'losangeles', label: 'LA' },
            { key: 'newyork', label: 'NY' },
            { key: 'seattle', label: 'Seattle' },
            { key: 'chicago', label: 'Chicago' },
            { key: 'dallas', label: 'Dallas' },
            { key: 'miami', label: 'Miami' },
            { key: 'atlanta', label: 'Atlanta' },
            { key: 'boston', label: 'Boston' },
            { key: 'phoenix', label: 'Phoenix' }
          ].map((region) => (
            <button
              key={region.key}
              onClick={() => handleRegionClick(region.key)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition border flex items-center gap-1.5 shrink-0 ${
                selectedRegion === region.key 
                  ? 'bg-indigo-600 text-white border-indigo-500' 
                  : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white'
              }`}
            >
              {region.label}
              <span className={`text-[10px] ${selectedRegion === region.key ? 'text-indigo-200' : 'text-gray-500'}`}>
                {region.key === 'all' 
                  ? (regionCounts.total || 0) 
                  : (regionCounts[region.key] || 0)
                }
              </span>
            </button>
          ))}
        </div>

        {/* Row 2: Dynamic Sub-Cities */}
        {selectedRegion !== 'all' && availableCities.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 w-full mb-10 p-4 bg-white/[0.02] border border-white/5 rounded-2xl items-center">
            <div className="relative w-full col-span-2 sm:col-span-3 md:col-span-2 lg:col-span-2">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="w-3.5 h-3.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <input
                type="text"
                placeholder="Search cities..."
                value={citySearchQuery}
                onChange={(e) => setCitySearchQuery(e.target.value)}
                className="w-full pl-9 pr-3 py-2 rounded-xl text-[12px] font-medium transition border flex justify-center items-center bg-white/5 text-gray-300 border-white/10 hover:bg-white/10 focus:outline-none focus:border-indigo-500/50 focus:bg-indigo-600/10 placeholder-gray-500"
              />
            </div>
            <button
              onClick={() => {
                setSelectedCity('all');
                setCitySearchQuery('');
                fetchFeed(selectedRegion, 'all');
              }}
              className={`w-full px-3 py-2 rounded-xl text-xs font-medium transition border flex justify-center items-center ${
                selectedCity === 'all' 
                  ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/30' 
                  : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white'
              }`}
            >
              All Cities
            </button>
            {(citySearchQuery 
              ? availableCities.filter(c => c.name.toLowerCase().includes(citySearchQuery.toLowerCase()))
              : (showAllCities ? availableCities : availableCities.filter(c => (c.count || 0) >= 10))
            ).map((city) => (
              <button
                key={city.name}
                onClick={() => {
                  setSelectedCity(city.name);
                  setShowAllCities(false);
                  setSortBy('latest');
                  setCitySearchQuery(city.name);
                  fetchFeed(selectedRegion, city.name, 'latest', 0, false);
                }}
                className={`w-full px-3 py-2 rounded-xl text-[11px] font-medium transition border flex justify-between items-center gap-2 truncate ${
                  selectedCity === city.name 
                    ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/30' 
                    : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white'
                }`}
              >
                <span className="truncate">{city.name}</span>
                {city.count != null && <span className={`shrink-0 font-bold ${selectedCity === city.name ? 'text-white' : 'text-white/80'}`}>{city.count}</span>}
              </button>
            ))}
            
            {!citySearchQuery && availableCities.filter(c => (c.count || 0) < 10).length > 0 && (
              <button
                onClick={() => setShowAllCities(!showAllCities)}
                className="w-full px-3 py-2 rounded-xl text-[11px] font-medium transition border flex justify-center items-center gap-2 truncate bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white"
              >
                {showAllCities 
                  ? "Hide cities with <10 cars" 
                  : `Show ${availableCities.filter(c => (c.count || 0) < 10).length} cities with <10 cars`}
              </button>
            )}
          </div>
        )}

        {freshDrops.length > 0 && !showWatchlist && (
          <div className="w-full mb-12">
            <h2 className="text-2xl font-bold mb-6 text-white flex items-center gap-2">
              Live Deals Feed
              <span className="text-sm font-normal text-gray-400 ml-2">Top deals based on AI prediction</span>
            </h2>
            <div className="flex gap-4 overflow-x-auto pb-6 snap-x hide-scrollbar">
              {freshDrops.map((car, i) => {
                const diff = formatDifference(car.difference)
                return (
                  <div 
                    key={`fresh-${i}`}
                    className="min-w-[280px] md:min-w-[320px] max-w-[320px] snap-start relative group p-4 rounded-3xl overflow-hidden flex flex-col justify-end min-h-[360px] shadow-2xl border border-white/5 bg-[#0a0a0a] transition-all duration-500 hover:scale-[1.02] hover:-translate-y-1 cursor-pointer"
                  >
                    {/* Location + Mileage stacked top-left */}
                    <div className="absolute top-5 left-5 z-20 flex flex-col gap-2">
                      <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-gray-300 bg-black/50 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/10 font-medium shadow-xl">
                        <PinIcon className="w-3 h-3" />
                        {selectedRegion === 'all' && car.region && regionAbbreviations[car.region] ? `${car.location}, ${regionAbbreviations[car.region]}` : car.location}
                      </span>
                      <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-gray-300 bg-black/50 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/10 font-medium w-fit shadow-xl">
                        {car.mileage.toLocaleString()} mi
                      </span>
                    </div>

                    {/* Top Right Controls */}
                    <div className="absolute top-4 right-4 z-20 flex flex-col items-end gap-2">
                      <div className="relative z-30 flex items-center gap-2">
                        {user && (
                          <div className="relative flex justify-center group/tooltip opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0">
                            <button 
                              onClick={(e) => handleReportSold(e, car.url)}
                              disabled={reportingUrls[car.url]}
                              className="p-1.5 rounded-full bg-red-500/10 hover:bg-red-500/30 backdrop-blur-md border border-red-500/30 text-red-400 shadow-lg transition-all disabled:opacity-50"
                            >
                              {reportingUrls[car.url] ? (
                                <svg className="animate-spin h-4 w-4 text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                              ) : (
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"></path></svg>
                              )}
                            </button>
                            {/* Tooltip */}
                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-max px-2 py-1 bg-[#0a0a0a] border border-white/10 text-white text-[9px] font-bold uppercase tracking-[0.15em] rounded-md opacity-0 group-hover/tooltip:opacity-100 pointer-events-none transition-opacity shadow-xl z-50">
                              REPORT SOLD
                            </div>
                          </div>
                        )}
                        <div className="opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0">
                          <span className="bg-indigo-600 text-white px-3 py-1.5 rounded-full font-bold text-xs tracking-wide flex items-center gap-1.5 shadow-lg">
                            View
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                          </span>
                        </div>
                        <button 
                          onClick={(e) => {
                            e.preventDefault()
                            toggleSaveCar(car.url)
                          }}
                          className={`p-1.5 rounded-full border backdrop-blur-md transition ${
                            watchlist.includes(car.url) 
                              ? 'bg-indigo-600 border-indigo-500 text-white' 
                              : 'bg-black/50 border-white/10 text-gray-300 hover:bg-white/10 hover:scale-110'
                          }`}
                        >
                          <svg className="w-4 h-4" fill={watchlist.includes(car.url) ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
                        </button>
                      </div>
                      
                      <div className="opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0 w-full">
                        <button 
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            navigateToInsights(car.make, car.model);
                          }}
                          className="w-full bg-[#0a0a0f]/95 hover:bg-indigo-600 border border-white/10 hover:border-indigo-400 text-indigo-300 hover:text-white px-3 py-1.5 rounded-full font-bold text-xs tracking-wide flex items-center justify-center gap-1.5 shadow-[0_0_20px_rgba(0,0,0,0.8)] backdrop-blur-xl transition"
                        >
                          Show Insights
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
                        </button>
                      </div>
                    </div>

                    <div className="absolute inset-0 overflow-hidden rounded-2xl pointer-events-none z-0">
                      {car.image_url ? (
                        <img 
                          src={car.image_url} 
                          alt={car.name} 
                          className="w-full h-full object-cover opacity-60 mix-blend-screen group-hover:scale-105 group-hover:opacity-80 transition-all duration-700 ease-out"
                        />
                      ) : (
                        <div className="absolute -top-12 -right-16 opacity-[0.08] blur-[2px] mix-blend-screen group-hover:scale-110 group-hover:opacity-[0.15] group-hover:-translate-x-2 transition-all duration-700 ease-out">
                          <CarIcon className="w-80 h-80 scale-x-[-1]" />
                        </div>
                      )}
                    </div>

                    <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0a] via-[#0a0a0a]/80 to-transparent pointer-events-none z-10" />

                    <a 
                      href={car.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="relative z-20 flex flex-col h-full justify-end group/link mt-20"
                    >
                      <h4 className="text-xl font-bold mb-4 text-white tracking-tight line-clamp-2">{car.name}</h4>
                      
                      <div className="flex justify-between items-end pb-3 border-b border-white/10 mb-4">
                        <div>
                          <p className="text-[10px] font-bold tracking-widest text-gray-500 uppercase mb-1">Listed Price</p>
                          <div className="text-3xl font-black text-white tracking-tighter">${car.list_price.toLocaleString()}</div>
                        </div>
                        <div className="text-right">
                          <p className="text-[10px] font-bold tracking-widest text-indigo-400 uppercase mb-1">AI Prediction</p>
                          <div className="text-3xl font-black text-indigo-300 tracking-tighter">${car.ai_price.toLocaleString()}</div>
                        </div>
                      </div>

                      <div className={`text-center py-2.5 rounded-xl text-sm font-bold tracking-wide transition-colors ${diff.colorClass} border ${diff.bgClass} flex items-center justify-center gap-2`}>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                        </svg>
                        ${Math.abs(car.difference).toLocaleString()} {car.difference < 0 ? 'over' : 'under'} AI prediction
                      </div>
                    </a>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Title and Refresh Row */}
        <div className="flex justify-between items-center mb-8 gap-4">
          <div className="flex items-center gap-4">
            <h3 className="text-3xl font-bold tracking-tight text-white">
              {showWatchlist ? "My Saved Cars" : "Market Feed"}
            </h3>
            {user && (
              <button 
                onClick={handleShowWatchlist}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition border flex items-center gap-2 ${
                  showWatchlist 
                    ? 'bg-indigo-600 text-white border-indigo-500' 
                    : 'bg-white/5 text-gray-400 border-white/10 hover:bg-white/10 hover:text-white'
                }`}
              >
                <svg className="w-4 h-4" fill={showWatchlist ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
                Saved ({watchlist.length})
              </button>
            )}
          </div>
          
          {!showWatchlist && (
            <SortDropdown sortBy={sortBy} onSortChange={handleSortChange} />
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {(() => {
            const carsToShow = showWatchlist ? watchlistCars : feed;
            
            if (carsToShow && carsToShow.length > 0) {
              return carsToShow.map((car, i) => {
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
                    {/* Location + Mileage stacked top-left */}
                    <div className="absolute top-5 left-5 z-20 flex flex-col gap-2">
                      <span className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-300 bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 font-medium">
                        <PinIcon className="w-3 h-3" />
                        {selectedRegion === 'all' && car.region && regionAbbreviations[car.region] ? `${car.location}, ${regionAbbreviations[car.region]}` : car.location}
                      </span>
                      <span className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-gray-300 bg-black/50 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10 font-medium w-fit">
                        {car.mileage.toLocaleString()} mi
                      </span>
                    </div>

                    {/* Top Right Controls */}
                    <div className="absolute top-5 right-5 z-20 flex flex-col items-end gap-2">
                      <div className="relative z-30 flex items-center gap-2">
                      {user && (
                      <div className="relative flex justify-center group/tooltip opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0">
                        <button 
                          onClick={(e) => handleReportSold(e, car.url)}
                          disabled={reportingUrls[car.url]}
                          className="p-1.5 rounded-full bg-red-500/10 hover:bg-red-500/30 backdrop-blur-md border border-red-500/30 text-red-400 shadow-lg transition-all disabled:opacity-50"
                        >
                          {reportingUrls[car.url] ? (
                            <svg className="animate-spin h-4 w-4 text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                          ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"></path></svg>
                          )}
                        </button>
                        {/* Tooltip */}
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-[0px] w-max px-2 py-1 bg-[#0a0a0a] border border-white/10 text-white text-[9px] font-bold uppercase tracking-[0.15em] rounded-md opacity-0 group-hover/tooltip:opacity-100 pointer-events-none transition-opacity shadow-xl z-50">
                          REPORT SOLD
                        </div>
                      </div>
                      )}
                      <div className="opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0">
                        <span className="bg-indigo-600 text-white px-3 py-1.5 rounded-full font-bold text-xs tracking-wide flex items-center gap-1.5 shadow-lg">
                          View
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                        </span>
                      </div>
                      <button 
                        onClick={(e) => {
                          e.preventDefault()
                          toggleSaveCar(car.url)
                        }}
                        className={`p-1.5 rounded-full border backdrop-blur-md transition ${
                          watchlist.includes(car.url) 
                            ? 'bg-indigo-600 border-indigo-500 text-white' 
                            : 'bg-black/50 border-white/10 text-gray-300 hover:bg-white/10 hover:scale-110'
                        }`}
                      >
                        <svg className="w-4 h-4" fill={watchlist.includes(car.url) ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>
                      </button>
                      </div>
                      
                      <div className="opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-2 group-hover:translate-x-0 w-full">
                        <button 
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            navigateToInsights(car.make, car.model);
                          }}
                          className="w-full bg-[#0a0a0f]/95 hover:bg-indigo-600 border border-white/10 hover:border-indigo-400 text-indigo-300 hover:text-white px-3 py-1.5 rounded-full font-bold text-xs tracking-wide flex items-center justify-center gap-1.5 shadow-[0_0_20px_rgba(0,0,0,0.8)] backdrop-blur-xl transition"
                        >
                          Show Insights
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
                        </button>
                      </div>
                    </div>



                    <div className="absolute inset-0 overflow-hidden rounded-2xl pointer-events-none z-0">
                      {car.image_url ? (
                        <img 
                          src={car.image_url} 
                          alt={car.name} 
                          className="w-full h-full object-cover opacity-60 mix-blend-screen group-hover:scale-105 group-hover:opacity-80 transition-all duration-700 ease-out"
                        />
                      ) : (
                        <div className="absolute -top-12 -right-16 opacity-[0.08] blur-[2px] mix-blend-screen group-hover:scale-110 group-hover:opacity-[0.15] group-hover:-translate-x-2 transition-all duration-700 ease-out">
                          <CarIcon className="w-80 h-80 scale-x-[-1]" />
                        </div>
                      )}
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
            } else {
              return (
                <div className="col-span-3 text-center text-gray-500 py-10 flex justify-center items-center gap-2">
                  <RefreshIcon className="w-4 h-4 animate-spin opacity-50" />
                  {showWatchlist ? "No saved cars yet." : "Loading live market deals..."}
                </div>
              )
            }
          })()}
        </div>

        {!showWatchlist && hasMore && feed.length > 0 && (
          <div className="flex justify-center mt-12 mb-4">
            <button
              onClick={() => fetchFeed(selectedRegion, selectedCity, sortBy, offset + 15, true)}
              disabled={loadingFeed}
              className={`px-8 py-3 rounded-full font-medium transition border flex items-center gap-3 ${
                loadingFeed 
                  ? 'bg-white/5 text-gray-500 border-white/5 cursor-not-allowed'
                  : 'bg-white/10 text-white border-white/20 hover:bg-white/20 hover:scale-105'
              }`}
            >
              {loadingFeed ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Loading...
                </>
              ) : 'Load More Cars'}
            </button>
          </div>
        )}
      </section>
      ) : (
        <Insights initialMake={insightMake} initialModel={insightModel} />
      )}
      </div>

      <footer className="border-t border-white/5 py-8 px-12 flex flex-col md:flex-row justify-between items-center text-xs text-gray-500 relative z-10 gap-4">
        <div>© {new Date().getFullYear()} AutoValuate. All rights reserved.</div>
        <div className="flex items-center gap-6">
          <a href="https://github.com/abhiswrld" target="_blank" rel="noreferrer" className="hover:text-white transition">GitHub ↗</a>
          <a href="https://www.linkedin.com/in/abhinav-khanna06/" target="_blank" rel="noreferrer" className="hover:text-white transition">LinkedIn ↗</a>
        </div>
      </footer>

      {/* Auth Modal */}
      <AnimatePresence>
        {showAuthModal && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowAuthModal(false)}
          >
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-[#111] border border-white/10 rounded-2xl p-8 max-w-md w-full shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-2xl font-bold mb-6 text-white text-center">
                {authMode === 'signin' ? 'Welcome Back' : 'Create Account'}
              </h3>
              <form onSubmit={handleAuth} className="space-y-4">
                <input 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email" 
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 text-white rounded-lg focus:outline-none focus:border-indigo-500"
                  required
                />
                <input 
                  type="password" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password" 
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 text-white rounded-lg focus:outline-none focus:border-indigo-500"
                  required
                />
                <button 
                  type="submit"
                  className="w-full py-3 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-500 transition"
                >
                  {authMode === 'signin' ? 'Sign In' : 'Sign Up'}
                </button>
              </form>
              <p className="text-center text-sm text-gray-400 mt-6">
                {authMode === 'signin' ? "Don't have an account? " : "Already have an account? "}
                <button 
                  onClick={() => setAuthMode(authMode === 'signin' ? 'signup' : 'signin')}
                  className="text-indigo-400 hover:underline font-medium"
                >
                  {authMode === 'signin' ? 'Sign Up' : 'Sign In'}
                </button>
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default App