import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  ComposedChart,
  Line,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const year = label || payload[0]?.payload?.year;
    
    // Find the predicted price line value if present in the payload
    const predictedData = payload.find(p => p.name === "AI Predicted Curve");
    const predictedPrice = predictedData ? predictedData.value : null;

    if (!predictedPrice) return null;

    return (
      <div className="bg-[#0c0d12]/95 border border-indigo-500/20 p-4 rounded-xl shadow-2xl backdrop-blur-md">
        <p className="text-white font-bold mb-1">Year {year}</p>
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

const Insights = () => {
  const [makes, setMakes] = useState([]);
  const [models, setModels] = useState([]);
  const [selectedMake, setSelectedMake] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  
  const [depreciationData, setDepreciationData] = useState([]);
  const [liveData, setLiveData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hoveredYear, setHoveredYear] = useState(null);

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
        <div className="w-full h-[500px] md:h-[600px] bg-[#030308]/50 border border-white/5 rounded-3xl p-4 md:p-8 backdrop-blur-md shadow-2xl relative">
        {!selectedMake || !selectedModel ? (
          <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-lg font-light">
            Select a make and model to view depreciation curve
          </div>
        ) : loading ? (
          <div className="absolute inset-0 flex items-center justify-center text-indigo-400 animate-pulse text-lg">
            Running Market Analysis...
          </div>
        ) : (
          <div className="w-full h-full flex flex-col">
            <div className="flex justify-center px-4 mb-2">
              <div className="bg-indigo-500/10 border border-indigo-500/20 px-4 py-1.5 rounded-full backdrop-blur-sm flex items-center gap-2">
                <span className="text-indigo-200 text-xs font-medium tracking-wide">
                  AI Assumes: Clean Title • Good Condition • 12k miles/yr
                </span>
              </div>
            </div>
            <div className="flex-1 min-h-0">
              <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              margin={{ top: 20, right: 30, bottom: 20, left: 20 }}
              onMouseMove={(e) => {
                if (e && e.activeLabel) {
                  setHoveredYear(e.activeLabel);
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis 
                dataKey="year" 
                type="number" 
                domain={['dataMin', 'dataMax']} 
                tick={{ fill: '#9ca3af' }}
                tickFormatter={(val) => Math.floor(val)}
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
              <Tooltip shared={true} content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.05)', strokeWidth: 40 }} />
              <Legend wrapperStyle={{ paddingTop: '20px' }} />
              
              <Line 
                data={depreciationData}
                type="monotone" 
                dataKey="price" 
                name="AI Predicted Curve" 
                stroke="#818cf8" 
                strokeWidth={4} 
                dot={false}
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
            <h3 className="text-xl font-bold text-white mb-4 border-b border-white/10 pb-4">
              {hoveredYear ? `${hoveredYear} Market` : 'Market Listings'}
            </h3>
            
            <div className="w-full overflow-y-auto pb-4 pt-2 px-1 custom-scrollbar">
              {!hoveredYear ? (
                <div className="h-32 flex items-center justify-center text-gray-500 text-sm italic text-center px-4">
                  Hover over the chart to see live listings for a specific year.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
                  {(() => {
                    const carsForYear = liveData.filter(c => c.year === hoveredYear).sort((a, b) => a.price - b.price);
                    if (carsForYear.length === 0) {
                      return <p className="text-gray-500 text-sm italic h-32 flex items-center px-8 mx-auto col-span-full justify-center">No live listings found for {hoveredYear}.</p>;
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
    </div>
  );
};

export default Insights;
