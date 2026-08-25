import { useState, useEffect, useRef, useMemo } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  ComposedChart,
  Area,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  YAxis as RechartsYAxis,
  XAxis as RechartsXAxis
} from 'recharts';

const ScanningCar = () => (
  <div className="flex flex-col items-center justify-center h-full w-full relative">
    <motion.div 
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="relative w-48 h-20 border-2 border-indigo-500/30 rounded-t-3xl rounded-b-xl overflow-hidden"
    >
      {/* Laser scanner */}
      <motion.div
        animate={{ left: ['-10%', '110%', '-10%'] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
        className="absolute top-0 bottom-0 w-1 bg-indigo-400 shadow-[0_0_15px_#818cf8] z-10"
      />
      {/* Fake wireframe lines */}
      <div className="absolute inset-0 flex items-center justify-center opacity-30">
        <div className="w-full h-px bg-indigo-400" />
        <div className="absolute h-full w-px bg-indigo-400" />
      </div>
    </motion.div>
    <p className="text-indigo-400 mt-6 font-bold tracking-widest uppercase text-sm animate-pulse">Running Market Analysis...</p>
  </div>
);

const CustomTooltip = ({ active, payload, label, xAxisKey }) => {
  if (active && payload && payload.length) {
    const val = label || payload[0]?.payload?.[xAxisKey || 'year'];
    
    // Find the predicted price line value if present in the payload
    const predictedData = payload.find(p => p.name === "AI Predicted Curve");
    const predictedPrice = predictedData ? predictedData.value : null;

    if (!predictedPrice) return null;

    return (
      <div className="bg-[#0c0d12]/95 border border-indigo-500/20 p-4 rounded-xl shadow-2xl backdrop-blur-md">
        <p className="text-white font-bold mb-1">
          {xAxisKey === 'mileage' ? `${Number(val).toLocaleString()} mi` : `Year ${val}`}
        </p>
        <p className="text-indigo-400 font-bold text-sm">Predicted Value:</p>
        <p className="text-white text-xl font-extrabold">${predictedPrice.toLocaleString(undefined, {maximumFractionDigits:0})}</p>
      </div>
    );
  }
  return null;
};

// Custom Dropdown Component
const CustomDropdown = ({ value, options, onChange, placeholder, disabled, formatOption }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className={`relative w-full md:w-64 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`} ref={dropdownRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className="w-full bg-[#0c0d12]/80 border border-white/10 text-white rounded-xl px-4 py-3 text-left focus:outline-none focus:border-indigo-500/60 transition-colors flex justify-between items-center backdrop-blur-md"
      >
        <span className="truncate">
          {value ? (formatOption ? formatOption(value) : value.toUpperCase()) : placeholder}
        </span>
        <svg className={`w-5 h-5 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
      </button>

      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="absolute z-50 w-full mt-2 bg-[#0c0d12] border border-white/10 rounded-xl shadow-2xl max-h-60 overflow-y-auto custom-scrollbar"
        >
          {options.map((opt) => (
            <button
              key={opt}
              type="button"
              className={`w-full text-left px-4 py-3 hover:bg-indigo-500/20 transition-colors ${value === opt ? 'bg-indigo-500/10 text-indigo-300' : 'text-gray-300'}`}
              onClick={() => {
                onChange(opt);
                setIsOpen(false);
              }}
            >
              {formatOption ? formatOption(opt) : opt.toUpperCase()}
            </button>
          ))}
        </motion.div>
      )}
    </div>
  );
};

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const Insights = ({ initialMake = '', initialModel = '', selectedRegion = 'sfbay', renderCarCard, user, setShowAuthModal }) => {
  const [makes, setMakes] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedMake, setSelectedMake] = useState(initialMake);
  const [selectedModel, setSelectedModel] = useState(initialModel);
  
  useEffect(() => {
    if (initialMake && initialModel) {
      setSelectedMake(initialMake);
      setSelectedModel(initialModel);
    }
  }, [initialMake, initialModel]);
  
  const [depreciationData, setDepreciationData] = useState([]);
  const [liveData, setLiveData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hoveredXValue, setHoveredXValue] = useState(null);
  const [xAxisKey, setXAxisKey] = useState('year');

  // Clear hovered value when switching tabs or cars
  useEffect(() => {
    setHoveredXValue(null);
  }, [xAxisKey, selectedMake, selectedModel]);

  // Fetch makes on mount
  useEffect(() => {
    axios.get(`${API_URL}/insights/makes`)
      .then(res => setMakes(res.data))
      .catch(err => console.error("Failed to load makes:", err));
  }, []);

  // Fetch models when make changes
  useEffect(() => {
    if (selectedMake) {
      axios.get(`${API_URL}/insights/models?make=${selectedMake}`)
        .then(res => setModels(res.data))
        .catch(err => console.error("Failed to load models:", err));
    } else {
      setTimeout(() => setModels([]), 0);
    }
  }, [selectedMake]);

  // Fetch graph data when both are selected
  useEffect(() => {
    if (selectedMake && selectedModel) {
      setTimeout(() => setLoading(true), 0);
      
      Promise.all([
        axios.get(`${API_URL}/insights/depreciation?make=${selectedMake}&model_name=${selectedModel}`),
        axios.get(`${API_URL}/insights/live_data?make=${selectedMake}&model_name=${selectedModel}`)
      ]).then(([depRes, liveRes]) => {
        setDepreciationData(depRes.data);
        setLiveData(liveRes.data);
      }).catch(err => {
        console.error("Failed to fetch insights data", err);
      }).finally(() => {
        setLoading(false);
      });
    }
  }, [selectedMake, selectedModel]);

  const annualDep = useMemo(() => {
    if (!depreciationData || depreciationData.length < 2) return null;
    const sorted = [...depreciationData].sort((a, b) => a.year - b.year);
    const oldest = sorted[0];
    const newest = sorted[sorted.length - 1];
    const years = newest.year - oldest.year;
    if (years === 0 || newest.price <= 0) return null;
    const rate = Math.pow((oldest.price / newest.price), (1 / years)) - 1;
    return (rate * 100).toFixed(1);
  }, [depreciationData]);

  const quickStats = useMemo(() => {
    if (!depreciationData || depreciationData.length < 2) return null;
    const sorted = [...depreciationData].sort((a, b) => b.year - a.year);
    
    const newestYear = sorted[0];
    const prevYear = sorted[1];
    
    const oneYearLoss = newestYear.price - prevYear.price;
    
    let bestYear = null;
    let maxDropPct = 0;
    for (let i = 0; i < sorted.length - 1; i++) {
      const drop = sorted[i].price - sorted[i+1].price;
      const pct = drop / sorted[i].price;
      if (pct > maxDropPct) {
        maxDropPct = pct;
        bestYear = sorted[i+1].year;
      }
    }

    return {
      loss: oneYearLoss,
      bestYear: bestYear || prevYear.year,
      inventory: liveData.length
    }
  }, [depreciationData, liveData]);

  const dealQualityData = useMemo(() => {
    if (!liveData.length) return [];
    let buckets = { 'Excellent': 0, 'Great': 0, 'Fair': 0, 'Overpriced': 0 };
    liveData.forEach(car => {
      if (car.predicted_price && car.predicted_price > 0) {
        const pct = (car.difference / car.predicted_price) * 100;
        if (pct > 10) buckets['Excellent']++;
        else if (pct > 3) buckets['Great']++;
        else if (pct >= -3) buckets['Fair']++;
        else buckets['Overpriced']++;
      }
    });
    return [
      { name: 'Excellent (>10%)', count: buckets['Excellent'], fill: '#34d399' },
      { name: 'Great (3-10%)', count: buckets['Great'], fill: '#60a5fa' },
      { name: 'Fair (±3%)', count: buckets['Fair'], fill: '#9ca3af' },
      { name: 'Overpriced (<-3%)', count: buckets['Overpriced'], fill: '#f87171' }
    ];
  }, [liveData]);

  const regionalData = useMemo(() => {
    if (!liveData.length) return [];
    let map = {};
    liveData.forEach(car => {
      const loc = car.location;
      if (!map[loc]) {
        map[loc] = { price: car.price, url: car.url, trim: car.trim, mileage: car.mileage, year: car.year };
      } else if (car.price < map[loc].price) {
        map[loc] = { price: car.price, url: car.url, trim: car.trim, mileage: car.mileage, year: car.year };
      }
    });
    const arr = Object.keys(map).map(loc => ({
      name: loc,
      price: map[loc].price,
      url: map[loc].url,
      trim: map[loc].trim,
      mileage: map[loc].mileage,
      year: map[loc].year
    }));
    return arr.sort((a, b) => a.price - b.price).slice(0, 5);
  }, [liveData]);

  const trimData = useMemo(() => {
    if (!liveData.length) return [];
    let map = {};
    liveData.forEach(car => {
      let trim = car.trim.toUpperCase();
      if (trim === 'UNSPECIFIED' || trim === 'ERROR' || trim === 'OTHER') return;
      map[trim] = (map[trim] || 0) + 1;
    });
    const arr = Object.keys(map).map(k => ({ name: k, value: map[k] }));
    return arr.sort((a, b) => b.value - a.value).slice(0, 5);
  }, [liveData]);

  const COLORS = ['#818cf8', '#34d399', '#60a5fa', '#f472b6', '#fbbf24'];

  const chartData = useMemo(() => {
    let base = [...depreciationData].sort((a, b) => a[xAxisKey] - b[xAxisKey]);
    
    if (xAxisKey === 'mileage' && base.length > 1) {
      let combinedMap = new Map();
      base.forEach(p => combinedMap.set(p.mileage, p));
      
      liveData.forEach(car => {
        let targetM = car.mileage;
        if (combinedMap.has(targetM)) return;
        
        let lower = base[0];
        let upper = base[base.length - 1];
        
        for(let i=0; i<base.length-1; i++) {
          if (base[i].mileage <= targetM && base[i+1].mileage >= targetM) {
            lower = base[i];
            upper = base[i+1];
            break;
          }
        }
        
        if (lower && upper && lower.mileage !== upper.mileage) {
          let ratio = (targetM - lower.mileage) / (upper.mileage - lower.mileage);
          combinedMap.set(targetM, {
            year: lower.year + ratio * (upper.year - lower.year),
            price: lower.price + ratio * (upper.price - lower.price),
            mileage: targetM
          });
        }
      });
      return Array.from(combinedMap.values()).sort((a, b) => a.mileage - b.mileage);
    }
    
    return base;
  }, [depreciationData, xAxisKey, liveData]);

  return (
    <div className="w-full max-w-6xl mx-auto px-6 py-12 relative z-10">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <h2 className="text-3xl md:text-[3.25rem] font-extrabold tracking-tighter text-white mb-4">
          Market <span className="text-indigo-400">Insights</span>
        </h2>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto font-light">
          Visualize real-time depreciation curves mapped by our AI.
        </p>
      </motion.div>

      <div className="flex flex-col md:flex-row gap-4 justify-center mb-12 relative z-40">
        <CustomDropdown
          value={selectedMake}
          options={makes}
          onChange={(val) => { setSelectedMake(val); setSelectedModel(''); }}
          placeholder="Select Make..."
        />
        
        <CustomDropdown
          value={selectedModel}
          options={models}
          onChange={(val) => setSelectedModel(val)}
          placeholder="Select Model..."
          disabled={!selectedMake || models.length === 0}
          formatOption={(m) => (selectedMake === 'tesla' && ['3', 's', 'x', 'y'].includes(m.toLowerCase())) ? `Model ${m.toUpperCase()}` : m.toUpperCase()}
        />
      </div>

      <div className="flex flex-col gap-6 w-full relative z-30">
        <div className="w-full h-[500px] md:h-[600px] bg-[#030308]/50 border border-white/5 rounded-3xl p-4 md:p-8 backdrop-blur-md shadow-2xl relative flex flex-col">
        {!selectedMake || !selectedModel ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-lg font-light">
            Select a make and model to view depreciation curve
          </div>
        ) : loading ? (
          <div className="absolute inset-0"><ScanningCar /></div>
        ) : (
          <div className="w-full h-full flex flex-col relative z-10">
            {quickStats && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 z-20 relative">
                <div className="bg-white/5 border border-white/10 rounded-2xl p-4 flex flex-col justify-center items-center backdrop-blur-md hover:bg-white/10 transition">
                  <span className="text-gray-400 text-xs uppercase tracking-widest font-bold mb-1">Live Inventory</span>
                  <span className="text-2xl font-extrabold text-white">{quickStats.inventory} <span className="text-sm font-medium text-gray-500">listings</span></span>
                </div>
                <div className="bg-white/5 border border-white/10 rounded-2xl p-4 flex flex-col justify-center items-center backdrop-blur-md hover:bg-white/10 transition group relative cursor-help">
                  <span className="text-gray-400 text-xs uppercase tracking-widest font-bold mb-1">1-Year Dep.</span>
                  <span className="text-2xl font-extrabold text-rose-400">
                    {Math.round(quickStats.loss) <= 0 
                      ? `$0` 
                      : `-$${Math.round(quickStats.loss).toLocaleString()}`}
                  </span>
                  <div className="absolute bottom-full mb-3 hidden group-hover:block w-56 bg-[#0c0d12] text-gray-300 text-xs rounded-xl p-3 text-center border border-white/10 shadow-2xl z-50">
                    The AI-predicted value lost during the first year of ownership.
                  </div>
                </div>
              </div>
            )}
            
            <div className="flex justify-center mb-6 z-20 relative">
              <div className="bg-white/5 backdrop-blur-md p-1 rounded-full inline-flex border border-white/10">
                <button
                  onClick={() => setXAxisKey('year')}
                  className={`px-6 py-2 rounded-full text-sm font-bold transition-all ${xAxisKey === 'year' ? 'bg-indigo-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
                >
                  View by Year
                </button>
                <button
                  onClick={() => setXAxisKey('mileage')}
                  className={`px-6 py-2 rounded-full text-sm font-bold transition-all ${xAxisKey === 'mileage' ? 'bg-indigo-500 text-white shadow-lg' : 'text-gray-400 hover:text-white'}`}
                >
                  View by Mileage
                </button>
              </div>
            </div>

            <div className="flex-1 min-h-0 relative mt-4">
              <ResponsiveContainer width="100%" height="100%" className="relative z-10">
            <ComposedChart
              margin={{ top: 20, right: 30, bottom: 50, left: 20 }}
              onMouseMove={(e) => {
                if (e && e.activeLabel) {
                  setHoveredXValue(e.activeLabel);
                }
              }}
            >
              <defs>
                <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#818cf8" stopOpacity={0.5}/>
                  <stop offset="95%" stopColor="#818cf8" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis 
                dataKey={xAxisKey} 
                type="number" 
                domain={['dataMin', 'dataMax']} 
                tick={{ fill: '#9ca3af' }}
                tickFormatter={(val) => xAxisKey === 'year' ? Math.floor(val) : `${(val/1000).toFixed(0)}k mi`}
                allowDecimals={false}
                axisLine={false}
                tickLine={false}
                dy={10}
              />
              <YAxis 
                yAxisId="left"
                tick={{ fill: '#9ca3af' }}
                tickFormatter={(val) => `$${(val/1000)}k`}
                axisLine={false}
                tickLine={false}
                dx={-10}
              />
              <Tooltip shared={true} content={<CustomTooltip xAxisKey={xAxisKey} />} cursor={{ stroke: 'rgba(255,255,255,0.05)', strokeWidth: 40 }} />
              <Legend verticalAlign="bottom" height={20} wrapperStyle={{ paddingTop: '10px' }} />
              
              <Area 
                data={chartData}
                type="monotone" 
                dataKey="price" 
                name="AI Predicted Curve" 
                stroke="#818cf8" 
                fillOpacity={1}
                fill="url(#colorPrice)"
                strokeWidth={4} 
                activeDot={{ r: 8, fill: '#818cf8', stroke: '#fff', strokeWidth: 2 }}
                yAxisId="left"
                animationDuration={1500}
              />
              
              <Scatter 
                data={liveData}
                name="Live Market Listings" 
                dataKey="price" 
                fill="#34d399" 
                yAxisId="left"
                animationDuration={1500}
                shape="circle"
              />
            </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
        </div>

        {/* Horizontal Panel for Listings Below Chart */}
        {selectedMake && selectedModel && !loading && (
          <div className="w-full h-auto bg-[#030308]/50 border border-white/5 rounded-3xl p-6 backdrop-blur-md shadow-2xl flex flex-col">
            <div className="flex flex-col gap-4 mb-4 border-b border-white/10 pb-4">
              {!hoveredXValue && (
                <h3 className="text-xl font-bold text-white">Market Listings</h3>
              )}
              
              {hoveredXValue && (
                <div className="flex flex-col gap-2 w-full">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-3 py-1 rounded-full text-sm font-medium">
                      AI Predicts: ${chartData.find(d => d[xAxisKey] === hoveredXValue)?.price?.toLocaleString(undefined, {maximumFractionDigits: 0}) || 'N/A'}
                    </span>
                    <span className="bg-white/5 text-gray-300 border border-white/10 px-3 py-1 rounded-full text-sm font-medium">
                      {xAxisKey === 'year' 
                        ? `Est. Mileage: ${((new Date().getFullYear() - hoveredXValue) * 12000).toLocaleString()} mi` 
                        : `Est. Year: ${Math.floor(chartData.find(d => d.mileage === hoveredXValue)?.year || (new Date().getFullYear() - Math.round(hoveredXValue / 12000)))}`}
                    </span>
                  </div>
                </div>
              )}
            </div>
            
            <div className="w-full overflow-y-auto pb-4 pt-2 px-1 custom-scrollbar">
              {!hoveredXValue ? (
                <div className="h-32 flex items-center justify-center text-gray-500 text-sm italic text-center px-4">
                  Hover over the chart to see live listings.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
                  {(() => {
                    const carsForYear = liveData.filter(c => {
                      if (xAxisKey === 'year') return c.year === hoveredXValue;
                      return Math.abs(c.mileage - hoveredXValue) <= 8000; // within 8k miles for mileage view
                    }).sort((a, b) => a.price - b.price);
                    
                    if (carsForYear.length === 0) {
                      return <p className="text-gray-500 text-sm italic h-32 flex items-center px-8 mx-auto col-span-full justify-center">No live listings found near {xAxisKey === 'year' ? hoveredXValue : `${(hoveredXValue/1000).toFixed(0)}k miles`}.</p>;
                    }
                    return carsForYear.map((car, idx) => (
                      <a key={idx} href={car.url} target="_blank" rel="noopener noreferrer" className="w-full block bg-white/5 rounded-xl p-4 hover:bg-white/10 hover:border-indigo-500/50 transition-colors border border-white/5 cursor-pointer shadow-lg">
                        <div className="flex justify-between items-start mb-2">
                          <span className="text-emerald-400 font-bold text-lg">${car.price?.toLocaleString()}</span>
                          <span className="text-gray-400 text-sm font-medium bg-white/5 px-2 py-0.5 rounded-full">{car.mileage?.toLocaleString()} mi</span>
                        </div>
                        <p className="text-gray-300 text-sm truncate">{car.location}</p>
                      </a>
                    ));
                  })()}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      
      {/* Lower Dashboard Panels */}
      {selectedMake && selectedModel && !loading && (
        <div className="flex flex-col gap-6 w-full relative z-30 mt-6 mb-12">
          
          {/* Regional Leaderboard (Full Width) */}
          <div className="bg-[#030308]/50 border border-white/5 rounded-3xl p-6 backdrop-blur-md shadow-2xl flex flex-col w-full">
            <h3 className="text-white font-extrabold mb-4 tracking-wider w-full text-center uppercase text-lg">Cheapest Markets</h3>
            <div className="flex-1 flex flex-col gap-3 mt-4">
              {regionalData.length > 0 ? (
                regionalData.map((loc, idx) => (
                  <a 
                    key={idx} 
                    href={loc.url}
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex justify-between items-center px-6 py-4 bg-white/5 rounded-xl border border-white/5 hover:bg-white/10 hover:border-indigo-500/50 transition-colors cursor-pointer group"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      <span className="text-indigo-400 font-black text-xl w-6">{idx + 1}</span>
                      <span className="text-gray-200 font-bold text-lg truncate group-hover:text-white transition-colors">{loc.name}</span>
                    </div>
                    
                    <div className="flex justify-end items-center gap-4 shrink-0">
                      <div className="flex gap-2 items-center hidden md:flex mr-4">
                        {loc.trim && loc.trim.toLowerCase() !== 'unspecified' && (
                          <span className="text-gray-400 bg-black/40 border border-white/5 px-4 py-1.5 rounded-lg text-sm font-semibold tracking-wider truncate max-w-[150px] uppercase">{loc.trim}</span>
                        )}
                        <span className="text-gray-400 bg-black/40 border border-white/5 px-4 py-1.5 rounded-lg text-sm font-semibold tracking-wider">{loc.year}</span>
                        <span className="text-gray-400 bg-black/40 border border-white/5 px-4 py-1.5 rounded-lg text-sm font-semibold tracking-wider">{loc.mileage.toLocaleString()} mi</span>
                      </div>
                      <span className="text-emerald-400 font-black text-2xl w-24 text-right">${loc.price.toLocaleString()}</span>
                    </div>
                  </a>
                ))
              ) : (
                <p className="text-gray-500 italic text-sm w-full text-center mt-6 h-64 flex items-center justify-center">Not enough location data.</p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
            {/* Deal Quality Bar Chart */}
            <div className="bg-[#030308]/50 border border-white/5 rounded-3xl p-6 backdrop-blur-md shadow-2xl flex flex-col items-center">
              <h3 className="text-white font-extrabold mb-4 tracking-wider w-full text-center uppercase text-lg">Deal Quality</h3>
              <div className="w-full h-[22rem] mt-4 flex flex-col justify-between">
                {dealQualityData.some(d => d.count > 0) ? (
                  <>
                    <ResponsiveContainer width="100%" height="90%">
                      <BarChart data={dealQualityData} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                        <RechartsXAxis type="number" hide />
                        <RechartsYAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#f3f4f6', fontSize: 15, fontWeight: 'bold', dx: -5 }} width={175} />
                        <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={45} isAnimationActive={false}>
                          {dealQualityData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.fill} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <p className="text-gray-400 text-xs italic text-center mt-4">
                      Based on AI market value predictions.
                    </p>
                  </>
                ) : (
                  <p className="text-gray-500 italic text-sm w-full text-center mt-10">Not enough AI prediction data.</p>
                )}
              </div>
            </div>

            {/* Trim Popularity Donut */}
            <div className="bg-[#030308]/50 border border-white/5 rounded-3xl p-6 backdrop-blur-md shadow-2xl flex flex-col items-center">
            <h3 className="text-white font-extrabold mb-0 tracking-wider w-full text-center uppercase text-lg">Top Trims</h3>
            <div className="w-full h-[22rem] mt-4">
              {trimData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={trimData}
                      cx="50%"
                      cy="45%"
                      innerRadius={90}
                      outerRadius={120}
                      paddingAngle={5}
                      dataKey="value"
                      stroke="none"
                    >
                      {trimData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0c0d12', borderColor: '#374151', borderRadius: '12px', color: '#fff' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Legend verticalAlign="bottom" height={40} iconType="circle" wrapperStyle={{ fontSize: '15px', fontWeight: 'bold', color: '#f3f4f6', paddingTop: '20px' }} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-gray-500 italic text-sm w-full text-center mt-10">Not enough trim data.</p>
              )}
            </div>
          </div>
          </div>
        </div>
      )}



    </div>
  );
};

export default Insights;
