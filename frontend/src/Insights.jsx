import { useState, useEffect } from 'react';
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
    const scatterData = payload.find(p => p.payload.url)?.payload;
    const lineData = payload.find(p => !p.payload.url)?.payload || payload.find(p => p.dataKey === 'price' && !p.payload.url)?.payload;
    const val = lineData?.value || payload[0]?.value;

    return (
      <div className="flex flex-col gap-2">
        {scatterData && (
          <div className="bg-[#0c0d12] border border-white/10 p-4 rounded-xl shadow-2xl backdrop-blur-md">
            <p className="text-white font-bold mb-1">{scatterData.year} Model</p>
            <p className="text-gray-300 text-sm mb-1">{scatterData.location}</p>
            <p className="text-emerald-400 font-bold mb-1">${scatterData.price?.toLocaleString()}</p>
            <p className="text-gray-400 text-xs">{scatterData.mileage?.toLocaleString()} miles</p>
          </div>
        )}
        {val && (
          <div className="bg-[#0c0d12] border border-indigo-500/20 p-4 rounded-xl shadow-2xl backdrop-blur-md">
            <p className="text-white font-bold mb-1">Year {label || scatterData?.year}</p>
            <p className="text-indigo-400 font-bold text-sm">Predicted Value:</p>
            <p className="text-white text-xl font-extrabold">${val?.toLocaleString(undefined, {maximumFractionDigits:0})}</p>
          </div>
        )}
      </div>
    );
  }
  return null;
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

      <div className="flex flex-col md:flex-row gap-4 justify-center mb-12 relative z-20">
        <select 
          className="bg-white/5 border border-white/10 text-white rounded-xl px-6 py-3 outline-none focus:border-indigo-500/60 backdrop-blur-md w-full md:w-64 cursor-pointer appearance-none"
          value={selectedMake}
          onChange={e => { setSelectedMake(e.target.value); setSelectedModel(''); }}
        >
          <option value="" className="bg-[#0c0d12]">Select Make...</option>
          {makes.map(m => <option key={m} value={m} className="bg-[#0c0d12]">{m.toUpperCase()}</option>)}
        </select>
        
        <select 
          value={selectedModel} 
          onChange={(e) => setSelectedModel(e.target.value)}
          disabled={!selectedMake || models.length === 0}
          className="w-full sm:w-64 bg-transparent border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-50 appearance-none bg-[#0c0d12]"
        >
          <option value="">Select Model...</option>
          {models.map(m => (
            <option key={m} value={m} className="bg-[#1a1b26]">
              {(selectedMake === 'tesla' && ['3', 's', 'x', 'y'].includes(m.toLowerCase())) ? `Model ${m.toUpperCase()}` : m.toUpperCase()}
            </option>
          ))}
        </select>
      </div>

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
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              margin={{ top: 20, right: 30, bottom: 20, left: 20 }}
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
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 2 }} />
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
                onClick={(e) => {
                   if (e && e.url) window.open(e.url, '_blank');
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default Insights;
