from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import pandas as pd
import joblib
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os
from fastapi import Response
from sqlalchemy import create_engine, text
import uuid

# 1. Initialize the App
app = FastAPI(title="AutoValuate API")

@app.get("/")
def read_root():
    return {"status": "AutoValuate API is running!"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return Response(status_code=200)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows React app to connect to backend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Load the ML Artifacts
print("Loading ML models...")
model = joblib.load('api/model.pkl')
ohe = joblib.load('api/ohe.pkl')
model_columns = joblib.load('api/model_columns.pkl')
print("Models loaded successfully!")

# 3. Initialize Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")
db_engine = create_engine(DATABASE_URL) if DATABASE_URL else None
print("Database engine created!")

# 4. In-Memory Job Queue for Async Tasks
jobs = {}

# 5. Define Input Schemas
class CarData(BaseModel):
    age: int
    make: str
    model: str
    mileage: float
    location: str

class URLData(BaseModel):
    url: str

# HELPER FUNCTIONS - copied from previous work done in Jupyter notebook.
manufacturers = [
    'Toyota', 'Honda', 'Ford', 'Chevrolet', 'Chevy', 'Nissan', 'BMW', 'Mercedes', 'Benz', 
    'Audi', 'Lexus', 'Subaru', 'Volkswagen', 'Vw', 'Hyundai', 'Kia', 'Mazda', 'Acura', 'Jeep', 
    'Dodge', 'Ram', 'GMC', 'Cadillac', 'Infiniti', 'Volvo', 'Mitsubishi', 'Mini',
    'Porsche', 'Tesla', 'Land Rover', 'Jaguar', 'Chrysler', 'Buick', 'Pontiac', 'Saturn',
    'Lucid', 'Rivian', 'Polestar', 'Fisker', 'Bentley'
]

car_models_dict = {
    'Toyota': ['Camry', 'Corolla', 'Prius', 'Sienna', 'Tacoma', 'Tundra', 'Rav4', 'Highlander', '4Runner', 'Avalon', 'Yaris', 'Sequoia', 'Matrix', 'Fj Cruiser', 'Venza', 'Mirai', 'C-Hr', 'C-HR', 'Supra', 'Land Cruiser', 'Celica', 'MR2', 'Echo', 'Solara', 'Paseo', 'Previa', 'MR2 Spyder', 'Tercel', 'Camry Solara', 'Cressida', 'Venza', 'Corolla Hatchback', 'Corolla Cross', 'Corolla Hybrid', 'Camry Hybrid', 'Rav4 Hybrid', 'Highlander Hybrid', 'Sienna Hybrid', 'Tacoma TRD', 'Tundra TRD',],
    'Honda': ['Civic', 'Accord', 'Cr-v', 'Crv', 'Odyssey', 'Pilot', 'Fit', 'Hr-v', 'Hrv', 'Element', 'Ridgeline', 'Insight', 'Passport', 'S2000', 'Prelude', 'Clarity', 'Crosstour', 'Del Sol', 'S2000', 'CR-Z', 'NSX', 'Integra', 'Vigor', 'Ascot', 'Civic Si', 'Accord Hybrid', 'CR-V Hybrid', 'Insight Hybrid', 'Clarity Plug-in', 'Clarity Electric', 'Fit EV', 'HR-V Sport', 'Ridgeline Black Edition', 'Odyssey Elite', 'Pilot Black Edition', 'Civic Type R', 'Accord Sport', 'CR-V Touring', 'HR-V EX-L', 'Fit Sport', 'Ridgeline RTL-E', 'Odyssey Touring', 'Pilot Touring'],
    'Ford': ['F150', 'F-150', 'F250', 'F-250', 'F350', 'F-350', 'Escape', 'Explorer', 'Focus', 'Fusion', 'Mustang', 'Edge', 'Transit', 'Ranger', 'Expedition', 'Taurus', 'Bronco', 'Flex', 'EcoSport', 'C-Max', 'Fiesta', 'GT', 'Lightning', 'Maverick', 'Thunderbird', 'Econoline', 'Excursion', 'Windstar', 'Probe', 'Tempo', 'Aspire', 'Contour', 'Escape Hybrid', 'Fusion Hybrid', 'C-Max Hybrid', 'Transit Connect', 'Transit Connect Wagon', 'Transit Connect Van', 'Transit Connect Cargo', 'Transit Connect Passenger', 'Transit Connect XL', 'Transit Connect XLT', 'Transit Connect Titanium', 'Transit Connect Limited', 'Transit Connect Sport', 'Transit Connect SE', 'Transit Connect SEL', 'Transit Connect LWB', 'Transit Connect SWB'],
    'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Cruze', 'Tahoe', 'Impala', 'Colorado', 'Camaro', 'Corvette', 'Suburban', 'Traverse', 'Spark', 'Sonic', 'Volt', 'Bolt', 'Trax', 'Blazer', 'Express', 'Avalanche', 'SSR', 'HHR', 'Cobalt', 'Caprice', 'Lumina', 'Monte Carlo', 'Uplander', 'Venture', 'Astro', 'Tracker', 'S-10', 'G-Series Van', 'G-Series Truck', 'K-Series Truck', 'R-Series Truck', 'S-10 Blazer', 'S-10 Pickup', 'C/K Series', 'Chevelle', 'Nova', 'El Camino', 'Bel Air', 'Impala SS', 'Caprice Classic', 'Monte Carlo SS', 'Camaro ZL1', 'Corvette Z06', 'Silverado HD', 'Colorado ZR2', 'Tahoe RST', 'Suburban RST'],
    'Nissan': ['Altima', 'Sentra', 'Rogue', 'Maxima', 'Murano', 'Pathfinder', 'Versa', 'Frontier', 'Titan', 'Armada', 'Leaf', '350Z', '370Z', 'Juke', 'Kicks', 'GT-R', 'Xterra', 'Cube', 'Quest', 'NV200', 'NV1500', 'NV2500', 'NV3500', 'NV Cargo', 'NV Passenger', 'NV Van', 'NV Wagon', 'NV200 Compact Cargo', 'NV200 Compact Passenger', 'NV200 Compact Van', 'NV200 Compact Wagon', 'NV200 Compact Truck', 'NV200 Compact SUV', 'NV200 Compact Crossover', 'NV200 Compact Minivan', 'NV200 Compact Pickup', 'NV200 Compact Utility', 'NV200 Compact Commercial', 'NV200 Compact Fleet', 'NV200 Compact Delivery', 'NV200 Compact Service', 'NV200 Compact Work', 'NV200 Compact Business', 'NV200 Compact Professional', 'NV200 Compact Industrial', 'NV200 Compact Construction', 'NV200 Compact Maintenance', 'NV200 Compact Repair', 'NV200 Compact Technician', 'NV200 Compact Installer', 'NV200 Compact Operator'],
    'Bmw': ['328I', '335I', '325I', 'X5', 'X3', 'M3', 'M4', 'M5', '528I', '535I', '750Li', 'X1', 'X6', 'Z4', 'I3', 'I8', 'M2', 'M6', 'X4', 'X7', '330I', '340I', '430I', '440I', '530I', '540I', '640I', '650I', '740I', '750I', '840I', '850I', 'M550I', 'M760I', 'X2', 'X5 M', 'X6 M', 'Z3', 'Z8', 'I4', 'I5', 'I6', 'I7', 'I8 Roadster', 'M1', 'M3 E30', 'M3 E36', 'M3 E46', 'M3 E92', 'M4 GTS', 'M5 E28', 'M5 E34', 'M5 E39', 'M5 E60', 'M6 E63', 'M6 E64', 'M6 F12', 'M6 F13', 'M8', 'X3 M', 'X4 M', 'X5 M50i', 'X6 M50i', 'Z4 M40i'],
    'Mercedes': ['C300', 'E350', 'E320', 'E300', 'Ml350', 'Glk350', 'S550', 'S500', 'Gle', 'Glc', 'Gla', 'Sprinter', 'C63', 'Amg', 'C230', 'C240', 'C250', 'C280', 'C320', 'C350', 'E320', 'E350', 'E500', 'E550', 'S430', 'S500', 'S550', 'S600', 'S63', 'S65', 'G550', 'G63', 'G65', 'Gla250', 'Glc300', 'Glc43', 'Gle350', 'Gle43', 'Metris', 'Sprinter 2500', 'Sprinter 3500', 'Sprinter 2500 Cargo', 'Sprinter 3500 Cargo', 'Sprinter 2500 Passenger', 'Sprinter 3500 Passenger', 'Sprinter 2500 Crew', 'Sprinter 3500 Crew', 'Sprinter 2500 Van', 'Sprinter 3500 Van', 'Sprinter 2500 Chassis', 'Sprinter 3500 Chassis', 'Sprinter 2500 Cab', 'Sprinter 3500 Cab'],
    'Subaru': ['Outback', 'Forester', 'Impreza', 'Legacy', 'Crosstrek', 'Wrx', 'Brz', 'Ascent', 'Tribeca', 'Baja', 'Justy', 'Alcyone', 'Vivio', 'Sambar', 'R1', 'R2', 'Exiga', 'Trezia', 'Levorg', 'WRX STI', 'WRX Premium', 'WRX Limited', 'WRX Base', 'WRX Sport', 'WRX Touring', 'WRX Series.Gray', 'WRX Series.Blue', 'WRX Series.Red', 'WRX Series.White', 'WRX Series.Black', 'WRX Series.Silver', 'WRX Series.Gold', 'WRX Series.Green', 'WRX Series.Yellow', 'WRX Series.Orange', 'WRX Series.Purple', 'WRX Series.Bronze', 'WRX Series.Copper', 'WRX Series.Platinum', 'WRX Series.Titanium', 'WRX Series.Carbon', 'WRX Series.Aluminum', 'WRX Series.Steel', 'WRX Series.Iron', 'WRX Series.Nickel', 'WRX Series.Chrome'],
    'Volkswagen': ['Jetta', 'Passat', 'Golf', 'Gti', 'Tiguan', 'Touareg', 'Atlas', 'Beetle', 'Arteon', 'CC', 'Eos', 'R32', 'Scirocco', 'Vanagon', 'Eurovan', 'Rabbit', 'Fox', 'Dasher', 'Thing', 'Karmann Ghia', 'Phaeton', 'New Beetle', 'New Beetle Convertible', 'Golf R', 'Golf Alltrack', 'Golf SportWagen', 'Golf GTI', 'Golf TDI', 'Golf R32', 'Golf R-Line', 'Golf SE', 'Golf SEL', 'Golf S', 'Golf Wolfsburg Edition', 'Golf GTI Rabbit Edition', 'Golf GTI Autobahn', 'Golf GTI Performance', 'Golf GTI S', 'Golf GTI SE', 'Golf GTI SEL', 'Golf GTI Wolfsburg Edition', 'Golf GTI Clubsport', 'Golf GTI TCR', 'Golf GTI Edition 35', 'Golf GTI Edition 30', 'Golf GTI Edition 20', 'Golf GTI Edition 10', 'Golf GTI Edition 5', 'Golf GTI Edition 1'],
    'Vw': ['Jetta', 'Passat', 'Golf', 'Gti', 'Tiguan', 'Touareg', 'Atlas', 'Beetle', 'Arteon', 'CC', 'Eos', 'R32', 'Scirocco', 'Vanagon', 'Eurovan', 'Rabbit', 'Fox', 'Dasher', 'Thing', 'Karmann Ghia', 'Phaeton', 'New Beetle', 'New Beetle Convertible', 'Golf R', 'Golf Alltrack', 'Golf SportWagen', 'Golf GTI', 'Golf TDI', 'Golf R32', 'Golf R-Line', 'Golf SE', 'Golf SEL', 'Golf S', 'Golf Wolfsburg Edition', 'Golf GTI Rabbit Edition', 'Golf GTI Autobahn', 'Golf GTI Performance', 'Golf GTI S', 'Golf GTI SE', 'Golf GTI SEL', 'Golf GTI Wolfsburg Edition', 'Golf GTI Clubsport', 'Golf GTI TCR', 'Golf GTI Edition 35', 'Golf GTI Edition 30', 'Golf GTI Edition 20', 'Golf GTI Edition 10', 'Golf GTI Edition 5', 'Golf GTI Edition 1'],
    'Lexus': ['Rx', 'Es', 'Is', 'Nx', 'Gx', 'Lx', 'Gs', 'Ls', 'Ct', 'Rc', 'Ux', 'Lfa', 'Rx Hybrid', 'Es Hybrid', 'Is F', 'Gs F', 'Ls F', 'Rc F', 'Ux Hybrid', 'Nx Hybrid', 'Gx 460', 'Gx 470', 'Lx 570', 'Rx 350', 'Rx 450h', 'Es 350', 'Es 300h', 'Is 250', 'Is 350', 'Gs 350', 'Gs 450h', 'Ls 460', 'Ls 600h', 'Rc 350', 'Rc F', 'Ux 200', 'Ux 250h'],
    'Audi': ['A4', 'A6', 'Q5', 'Q7', 'A3', 'S4', 'Tt', 'Q3', 'S5', 'S3', 'A5', 'A7', 'A8', 'Q8', 'R8', 'E-Tron', 'E-Tron Sportback', 'E-Tron GT', 'E-Tron Quattro', 'E-Tron 55', 'E-Tron 50', 'E-Tron 40', 'E-Tron 35', 'E-Tron 30', 'E-Tron 25', 'E-Tron 20', 'E-Tron 15', 'E-Tron 10'],
    'Jeep': ['Grand Cherokee', 'Wrangler', 'Cherokee', 'Compass', 'Renegade', 'Patriot', 'Gladiator', 'Commander', 'Liberty', 'Wagoneer', 'Grand Wagoneer', 'Cherokee Trailhawk', 'Cherokee Latitude', 'Cherokee Limited', 'Cherokee Overland', 'Cherokee High Altitude', 'Cherokee Altitude', 'Cherokee Sport', 'Cherokee North Edition', 'Cherokee Freedom Edition', 'Cherokee Upland Edition', 'Cherokee 80th Anniversary Edition', 'Wrangler Unlimited', 'Wrangler Rubicon', 'Wrangler Sahara', 'Wrangler Sport', 'Wrangler Willys Wheeler', 'Wrangler Freedom Edition', 'Wrangler Islander Edition'],
    'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Accent', 'Kona', 'Palisade', 'Veloster', 'Genesis', 'Ioniq', 'Venue', 'Nexo', 'Azera', 'Entourage', 'Equus', 'Excel', 'Scoupe', 'Sante Fe Sport', 'Sante Fe XL', 'Tiburon', 'XG350', 'XG300', 'Veloster N', 'Kona N', 'Ioniq Hybrid', 'Ioniq Electric', 'Ioniq Plug-in Hybrid', 'Genesis G70', 'Genesis G80', 'Genesis G90', 'Genesis GV70', 'Genesis GV80'],
    'Kia': ['Optima', 'Sorento', 'Soul', 'Forte', 'Sportage', 'Telluride', 'Sedona', 'Rio', 'Stinger', 'Cadenza', 'Seltos', 'Niro', 'K900', 'Amanti', 'Carens', 'Cerato', 'Mohave', 'Opirus', 'Pride', 'Sephia', 'Shuma', 'Spectra', 'Venga', 'XCeed', 'EV6', 'Niro EV', 'Niro Plug-in Hybrid', 'Stonic', 'Sonet', 'Carnival', 'K5', 'K7', 'K8', 'K9', 'KX3', 'KX5', 'KX7', 'KX8', 'KX9', 'KX10', 'KX11', 'KX12', 'KX13', 'KX14', 'KX15', 'KX16', 'KX17', 'KX18', 'KX19', 'KX20'],
    'Mazda': ['Mazda3', 'Mazda6', 'Cx-5', 'Cx5', 'Cx-9', 'Cx9', 'Miata', 'Mx-5', 'Rx-8', 'Rx-7', 'B-Series', 'Tribute', '5', '2', '3 Hatchback', '3 Sedan', '6 Hatchback', '6 Sedan', 'Cx-30', 'Cx-50', 'Cx-90', 'Mx-30', 'Mx-5 Miata RF', 'Mx-5 Miata Club', 'Mx-5 Miata Grand Touring', 'Mx-5 Miata Sport', 'Mx-5 Miata Base', 'Mx-5 Miata Touring', 'Mx-5 Miata Premium', 'Mx-5 Miata Limited', 'Mx-5 Miata Special Edition', 'Mx-5 Miata Anniversary Edition', 'Mx-5 Miata 30th Anniversary Edition', 'Mx-5 Miata 25th Anniversary Edition', 'Mx-5 Miata 20th Anniversary Edition', 'Mx-5 Miata 15th Anniversary Edition', 'Mx-5 Miata 10th Anniversary Edition', 'Mx-5 Miata 5th Anniversary Edition'],
    'Dodge': ['Charger', 'Challenger', 'Grand Caravan', 'Durango', 'Journey', 'Dart', 'Ram 1500', 'Ram 2500', 'Ram 3500', 'Viper', 'Neon', 'Stratus', 'Avenger', 'Caliber', 'Nitro', 'Dakota', 'Magnum', 'Ram ProMaster', 'Ram ProMaster City', 'Ram Chassis Cab', 'Ram 1500 Classic', 'Ram 2500 Heavy Duty', 'Ram 3500 Heavy Duty', 'Ram 4500 Chassis Cab', 'Ram 5500 Chassis Cab', 'Ram 3500 Cab Chassis', 'Ram 4500 Cab Chassis', 'Ram 5500 Cab Chassis', 'Ram 1500 Tradesman', 'Ram 1500 Big Horn', 'Ram 1500 Laramie', 'Ram 1500 Rebel', 'Ram 1500 Limited', 'Ram 1500 Sport', 'Ram 1500 Warlock', 'Ram 2500 Tradesman', 'Ram 2500 Big Horn', 'Ram 2500 Laramie', 'Ram 2500 Power Wagon', 'Ram 2500 Limited', 'Ram 3500 Tradesman', 'Ram 3500 Big Horn', 'Ram 3500 Laramie', 'Ram 3500 Limited'],
    'Ram': ['1500', '2500', '3500', 'Promaster', 'Promaster City', 'Chassis Cab', '1500 Classic', '2500 Heavy Duty', '3500 Heavy Duty', '4500 Chassis Cab', '5500 Chassis Cab', '3500 Cab Chassis', '4500 Cab Chassis', '5500 Cab Chassis', '1500 Tradesman', '1500 Big Horn', '1500 Laramie', '1500 Rebel', '1500 Limited', '1500 Sport', '1500 Warlock', '2500 Tradesman', '2500 Big Horn', '2500 Laramie', '2500 Power Wagon', '2500 Limited', '3500 Tradesman', '3500 Big Horn', '3500 Laramie', '3500 Limited', 'Promaster 1500', 'Promaster 2500', 'Promaster 3500', 'Promaster City 1500', 'Promaster City 2500', 'Promaster City 3500'],
    'Gmc': ['Sierra', 'Acadia', 'Terrain', 'Yukon', 'Canyon', 'Savana', 'Denali', 'Envoy', 'Jimmy', 'Sierra 1500', 'Sierra 2500', 'Sierra 3500', 'Sierra Denali', 'Sierra SLT', 'Sierra Elevation', 'Sierra AT4', 'Sierra Denali Ultimate', 'Sierra Denali Ultimate Edition', 'Sierra Denali Ultimate Edition 2021', 'Sierra Denali Ultimate Edition 2022', 'Sierra Denali Ultimate Edition 2023', 'Sierra Denali Ultimate Edition 2024', 'Sierra Denali Ultimate Edition 2025', 'Sierra Denali Ultimate Edition 2026', 'Sierra Denali Ultimate Edition 2027', 'Sierra Denali Ultimate Edition 2028', 'Sierra Denali Ultimate Edition 2029', 'Sierra Denali Ultimate Edition 2030', 'Sierra Denali Ultimate Edition 2031', 'Sierra Denali Ultimate Edition 2032', 'Sierra Denali Ultimate Edition 2033', 'Sierra Denali Ultimate Edition 2034', 'Sierra Denali Ultimate Edition 2035', 'Sierra Denali Ultimate Edition 2036', 'Sierra Denali Ultimate Edition 2037', 'Sierra Denali Ultimate Edition 2038', 'Sierra Denali Ultimate Edition 2039', 'Sierra Denali Ultimate Edition 2040'],
    'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cybertruck', 'Roadster', 'Semi', 'Model 3 Performance', 'Model 3 Long Range', 'Model 3 Standard Range Plus', 'Model Y Performance', 'Model Y Long Range', 'Model Y Standard Range', 'Model S Plaid', 'Model S Long Range', 'Model S Standard Range', 'Model X Plaid', 'Model X Long Range', 'Model X Standard Range', 'Cybertruck Tri Motor', 'Cybertruck Dual Motor', 'Cybertruck Single Motor', 'Roadster Sport', 'Roadster Base', 'Semi Long Range', 'Semi Standard Range'],
    'Mini': ['Cooper', 'Countryman', 'Clubman', 'Hardtop', 'Paceman', 'Cooper S', 'Cooper SE', 'Cooper JCW', 'Cooper Convertible', 'Cooper Roadster', 'Cooper Coupe', 'Cooper Clubman S', 'Cooper Countryman S', 'Cooper Paceman S', 'Cooper Hardtop S', 'Cooper Convertible S', 'Cooper Roadster S', 'Cooper Coupe S', 'Cooper Clubman JCW', 'Cooper Countryman JCW', 'Cooper Paceman JCW', 'Cooper Hardtop JCW', 'Cooper Convertible JCW', 'Cooper Roadster JCW', 'Cooper Coupe JCW'],
    'Acura': ['Mdx', 'Rdx', 'Tlx', 'Ilx', 'Integra', 'Tsx', 'Tl', 'Rsx', 'Rl', 'Rlx', 'Zdx', 'Nsx', 'Mdx Sport Hybrid', 'Rdx A-Spec', 'Tlx Type S', 'Ilx Premium', 'Integra Type R', 'Tsx Wagon', 'Tl Type S', 'Rsx Type S', 'RlX Advance', 'Rlx Sport Hybrid', 'Zdx Technology', 'Nsx Type S', 'Mdx Advance', 'Rdx Advance', 'Tlx Advance', 'Ilx Advance', 'Integra Advance', 'Tsx Advance', 'Tl Advance', 'Rsx Advance', 'RlX Advance', 'Rlx Advance', 'Zdx Advance', 'Nsx Advance'],
    'Lucid': ['Air', 'Gravity', 'Aero', 'Air Touring', 'Air Grand Touring', 'Air Dream Edition', 'Air Pure', 'Air Sapphire', 'Air Performance', 'Air Base', 'Air Plus', 'Air Max', 'Air Ultra', 'Air Elite', 'Air Signature', 'Air Limited', 'Air Special Edition'],
    'Rivian': ['R1T', 'R1S', 'R2T', 'R2S', 'R3T', 'R3S', 'R4T', 'R4S', 'R5T', 'R5S', 'R6T', 'R6S', 'R7T', 'R7S', 'R8T', 'R8S'],
    'Polestar': ['Polestar 2', 'Polestar 3', 'Polestar 1', 'Polestar 4', 'Polestar 5'], 
    'Fisker': ['Ocean', 'Karma'],
    'Cadillac': ['Escalade', 'Cts', 'Ats', 'Xt5', 'Xt4', 'Srx', 'Xts', 'Deville', 'Seville', 'Eldorado', 'Fleetwood', 'Brougham', 'Allante', 'Cimarron', 'Dts', 'Sts', 'Catera', 'Xlr', 'Escalade ESV', 'Escalade EXT', 'Escalade Platinum', 'Escalade Luxury', 'Escalade Premium Luxury'],
    'Infiniti': ['G37', 'G35', 'Q50', 'Qx60', 'Qx80', 'Q60', 'Fx35', 'M35', 'Qx50', 'Qx70', 'Qx30', 'Qx56', 'Qx4', 'I30', 'I35', 'J30', 'M45', 'Q45', 'Ex35', 'Ex37', 'Ex25', 'Ex30', 'Ex20', 'Ex15', 'Ex10', 'Ex5', 'Ex3', 'Ex2', 'Ex1', 'Qx90', 'Qx100', 'Qx110', 'Qx120', 'Qx130', 'Qx140', 'Qx150', 'Qx160', 'Qx170', 'Qx180', 'Qx190'],
    'Volvo': ['Xc90', 'Xc60', 'Xc40', 'S60', 'S90', 'V60', 'V90', 'C30', 'C70', 'S40', 'S80', 'V40', 'V50', 'V70', 'V90 Cross Country', 'Xc90 T8', 'Xc60 T8', 'Xc40 Recharge', 'S60 Recharge', 'S90 Recharge', 'V60 Recharge', 'V90 Recharge', 'C30 Electric', 'C70 Electric', 'S40 Electric', 'S80 Electric', 'V40 Electric', 'V50 Electric', 'V70 Electric'],
    'Mitsubishi': ['Outlander', 'Lancer', 'Eclipse', 'Mirage', 'Galant', 'Endeavor', 'Montero', 'Pajero', 'Raider', 'Diamante', 'Challenger', 'Cordia', 'Starion', 'Precis', 'Tredia', 'Sigma', 'Sapporo', 'GTO', '3000GT', 'Eclipse Spyder', 'Lancer Evolution', 'Outlander Sport', 'Outlander PHEV'],
    'Porsche': ['911', 'Cayenne', 'Macan', 'Panamera', 'Boxster', 'Cayman', 'Taycan', '918 Spyder', 'Carrera', 'Turbo', 'GT3', 'GT2', 'GT4', 'Cayenne S', 'Cayenne GTS', 'Cayenne Turbo', 'Macan S', 'Macan GTS', 'Macan Turbo', 'Panamera 4S', 'Panamera Turbo', 'Panamera GTS', 'Panamera E-Hybrid', 'Boxster S', 'Boxster GTS', 'Boxster Spyder', 'Cayman S', 'Cayman GTS', 'Cayman GT4', 'Taycan 4S', 'Taycan Turbo', 'Taycan Turbo S'],
    'Land Rover': ['Range Rover', 'Discovery', 'Defender', 'Evoque', 'Lr4', 'Lr3', 'Freelander', 'Discovery Sport', 'Range Rover Sport', 'Range Rover Velar', 'Range Rover Evoque', 'Range Rover Autobiography', 'Range Rover HSE', 'Range Rover SE', 'Range Rover SVAutobiography', 'Range Rover SVR', 'Range Rover LWB', 'Range Rover SWB', 'Range Rover PHEV'],
    'Jaguar': ['Xf', 'Xj', 'F-Type', 'F-Pace', 'E-Pace', 'I-Pace', 'Xe', 'S-Type', 'X-Type', 'XK', 'XKR', 'XJR', 'XFR', 'XFR-S', 'XJ8', 'XJ6', 'XJ12', 'XJ-S', 'XJ40', 'XJ6 Series II', 'XJ6 Series III', 'XJ6 Series IV', 'XJ6 Series V', 'XJ6 Series VI', 'XJ6 Series VII'],
    'Chrysler': ['300', 'Pacifica', 'Town & Country', 'Sebring', 'Pt Cruiser', 'Aspen', 'Crossfire', 'Voyager', 'Concorde', 'LHS', 'New Yorker', 'Cirrus', 'Saratoga', 'Imperial', 'Royal', 'Fifth Avenue', 'LeBaron', 'Newport', 'Town & Country Touring', 'Town & Country Limited', 'Town & Country LX', 'Town & Country Touring L', 'Town & Country Touring Plus'],
    'Buick': ['Enclave', 'Encore', 'Envision', 'Lacrosse', 'Regal', 'Lucerne', 'Rendezvous', 'Rainier', 'Terraza', 'Skyhawk', 'Skylark', 'Reatta', 'Electra', 'Century', 'LeSabre', 'Roadmaster', 'Park Avenue', 'Riviera', 'Gran Sport'],
    'Pontiac': ['Grand Prix', 'G6', 'Grand Am', 'Vibe', 'Firebird', 'G8', 'Bonneville', 'G5', 'G3', 'Solstice', 'Torrent', 'Aztek', 'Sunfire', 'Montana', 'Wave', 'Fiero', 'LeMans', 'Tempest', 'Catalina', 'Safari', 'Parisienne', 'GTO'],
    'Saturn': ['Vue', 'Ion', 'Aura', 'Sky', 'Outlook', 'L-Series', 'S-Series', 'SL', 'SC', 'SW', 'LW', 'VUE Red Line', 'VUE Green Line', 'VUE Hybrid', 'VUE Sport', 'VUE XR', 'VUE XE', 'VUE XRE', 'VUE XRS', 'VUE XRT', 'VUE XRV', 'VUE XRW', 'VUE XRX', 'VUE XRY', 'VUE XRZ'],
    'Bentley': ['Continental', 'Flying Spur', 'Mulsanne', 'Arnage', 'Azure', 'Brooklands', 'Turbo R', 'Turbo S', 'Turbo RT', 'Turbo RT Speed', 'Turbo RT Mulliner', 'Turbo RT Le Mans', 'Turbo RT Le Mans Edition', 'Turbo RT Le Mans Edition 2003', 'Turbo RT Le Mans Edition 2004', 'Turbo RT Le Mans Edition 2005', 'Turbo RT Le Mans Edition 2006', 'Turbo RT Le Mans Edition 2007', 'Turbo RT Le Mans Edition 2008', 'Turbo RT Le Mans Edition 2009', 'Turbo RT Le Mans Edition 2010'],
}

def extract_make(title):
    title_lower = title.lower()
    for make in manufacturers:
        if make.lower() in title_lower:
            if make.lower() == 'chevy': return 'Chevrolet'
            if make.lower() == 'vw': return 'Volkswagen'
            if make.lower() == 'benz': return 'Mercedes'
            return make.title()
    return None

def extract_model(title, make):
    if not make: return None
    title_lower = title.lower()
    if make in car_models_dict:
        for model in car_models_dict[make]:
            if model.lower() in title_lower:
                return model.replace('-', '').title()
    return None

# --- ENDPOINTS ---

@app.post("/predict")
def predict_price(car: CarData):
    input_df = pd.DataFrame([car.model_dump()])
    # Add condition/title_status to match the new model
    input_df['condition'] = 'unspecified'
    input_df['title_status'] = 'unspecified'
    
    cat_encoded = ohe.transform(input_df[['make', 'model', 'location', 'condition', 'title_status']])
    cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
    num_df = input_df[['age', 'mileage']]
    final_df = pd.concat([num_df, cat_df], axis=1)
    final_df = final_df.reindex(columns=model_columns, fill_value=0)
    
    predicted_price = model.predict(final_df)[0]
    return {"predicted_price": float(predicted_price), "currency": "USD"}

def process_url_task(job_id: str, url: str):
    try:
        # 1. Scrape the live URL
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"})
            
            try:
                page.goto(url, timeout=15000)
                page.wait_for_selector("h1.postingtitle", timeout=10000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                browser.close()
            except Exception as e:
                browser.close()
                jobs[job_id] = {"status": "failed", "error": f"Failed to scrape URL: {str(e)}"}
                return

        # 2. Extract Title and Price
        title_tag = soup.find("h1", class_="postingtitle")
        if not title_tag:
            jobs[job_id] = {"status": "failed", "error": "Could not find posting title."}
            return
        
        full_title_text = title_tag.text.strip()
        price_match = re.search(r'\$([\d,]+)', full_title_text)
        if not price_match:
            jobs[job_id] = {"status": "failed", "error": "Could not find a valid price."}
            return
        
        price_str = price_match.group(1).replace(',', '')
        try:
            listing_price = int(price_str)
        except ValueError:
            jobs[job_id] = {"status": "failed", "error": "Invalid price format."}
            return

        title_text = re.sub(r'\$[\d,]+', '', full_title_text).strip().title()

        # 3. Extract Mileage
        mileage = None
        miles_div = soup.find("div", class_="attr auto_miles")
        if miles_div:
            value_span = miles_div.find("span", class_="valu")
            if value_span:
                mileage_str = value_span.text.replace(',', '').strip()
                try:
                    mileage = float(mileage_str)
                except:
                    pass

        # 4. Extract Condition & Title Status
        condition = None
        cond_tag = soup.find('div', class_='attr condition')
        if cond_tag:
            cond_span = cond_tag.find('span', class_='valu')
            if cond_span:
                condition = cond_span.text.strip()
                
        title_status = None
        title_tag_attr = soup.find('div', class_='attr auto_title_status')
        if title_tag_attr:
            title_span = title_tag_attr.find('span', class_='valu')
            if title_span:
                title_status = title_span.text.strip()


        # 5. Engineer Features (Make, Model, Year, Age)
        make = extract_make(title_text)
        model_name = extract_model(title_text, make)
        
        year_match = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', title_text)
        if not year_match:
            jobs[job_id] = {"status": "failed", "error": "Could not extract year."}
            return
        
        year = int(year_match.group(0))
        age = datetime.datetime.now().year - year
        location = "sanjose" 

        if not make or not model_name or not mileage:
            jobs[job_id] = {"status": "failed", "error": f"Missing data -> Make: {make}, Model: {model_name}, Mileage: {mileage}"}
            return

        # 6. Run through ML Model
        final_cond = condition if condition else "unspecified"
        final_title = title_status if title_status else "unspecified"

        input_data = {
            "age": age, 
            "make": make, 
            "model": model_name,
            "mileage": mileage, 
            "location": location,
            "condition": final_cond, 
            "title_status": final_title
        }
        input_df = pd.DataFrame([input_data])
        cat_encoded = ohe.transform(input_df[['make', 'model', 'location', 'condition', 'title_status']])
        cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
        num_df = input_df[['age', 'mileage']]
        final_df = pd.concat([num_df, cat_df], axis=1)
        final_df = final_df.reindex(columns=model_columns, fill_value=0)
        
        predicted_price = float(model.predict(final_df)[0])
        difference = predicted_price - listing_price
        pct_diff = (difference / predicted_price) * 100
        
        if pct_diff > 10:
            verdict = "Excellent Deal! (Significantly Underpriced)"
        elif pct_diff > 3:
            verdict = "Great Deal! (Underpriced)"
        elif pct_diff >= -3:
            verdict = "Fair Market Price"
        elif pct_diff >= -10:
            verdict = "Slightly Overpriced"
        else:
            verdict = "Overpriced! (Significantly Above Market)"

        # 7. Save the result to our in-memory dictionary
        jobs[job_id] = {
            "status": "completed",
            "listing_title": title_text,
            "listing_price": listing_price,
            "predicted_price": predicted_price,
            "difference": difference,
            "verdict": verdict
        }

    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}

@app.post("/evaluate_url")
def evaluate_url(url_data: URLData, background_tasks: BackgroundTasks):
    url = url_data.url
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(process_url_task, job_id, url)
    return {"job_id": job_id}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id in jobs:
        return jobs[job_id]
    return {"error": "Job not found"}

@app.get("/feed")
def get_market_feed():
    if not db_engine:
        return {"error": "Database not configured"}
        
    # 1. Use Pandas to read directly from the database
    query = "SELECT * FROM cars ORDER BY RANDOM() LIMIT 6"
    df = pd.read_sql(query, db_engine)

    # 2. Clean up the location names for the UI
    def clean_location(loc):
        loc = str(loc).lower().strip()
        replacements = {
            'sanjose': 'San Jose, CA',
            'sanfrancisco': 'San Francisco, CA',
            'losangeles': 'Los Angeles, CA',
            'newyork': 'New York, NY',
            'longbeach': 'Long Beach, CA',
            'santaclara': 'Santa Clara, CA',
            'sancarlos': 'San Carlos, CA',
            'sanbruno': 'San Bruno, CA',
            'sanmateo': 'San Mateo, CA',
            'sanleandro': 'San Leandro, CA'
        }
        for wrong, right in replacements.items():
            if wrong in loc:
                return right
        return loc.title()

    # 2. Format the data into JSON
    feed_data = []
    for _, row in df.iterrows():
        # Construct a perfectly clean name
        clean_name = f"{row.get('year', '')} {row.get('make', '')} {row.get('model', '')}".strip()
        
        # Safely get mileage (handle NaN)
        mileage = row.get('mileage', 0)
        if pd.isna(mileage):
            mileage = 0
            
        feed_data.append({
            "name": clean_name,
            "mileage": int(mileage),
            "location": clean_location(row.get('location', 'unknown')),
            "list_price": float(row.get('price', 0)),
            "ai_price": float(row.get('predicted_price', 0)),
            "difference": float(row.get('difference', 0)),
            "url": str(row.get('url', '#'))
        })
        
    return feed_data