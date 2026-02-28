# AgriMesh Web Frontend

Interactive farm planning application with OpenStreetMap integration, built with Next.js 14 and React.

## Features

### 🗺️ Interactive Map (OpenStreetMap + Leaflet)
- Click anywhere to select farm location
- Automatic AEZ zone detection for Zimbabwe
- Zone polygon rendering for crop/pasture/building areas
- Zoom and pan controls

### 🌾 Farm Configuration
- **Farm Type Selection**: Crops only, Livestock only, or Mixed farming
- **Livestock Management**: Configure chickens, cattle, goats, sheep, pigs
- **Crop Planning**: Add multiple crops with area allocation
- **Infrastructure**: Place buildings (barns, sheds, storage, greenhouses, water tanks)

### 📊 Simulation & Analysis
- Real-time sustainability simulation
- Crop suitability scoring by AEZ zone
- Profit estimation with pessimistic/expected/optimistic scenarios
- Synergy detection (e.g., manure → fertilizer, crop residues → feed)
- Resource requirements calculation

### 📈 Results Dashboard
- Sustainability score visualization
- Crop suitability bar charts
- Profit breakdown pie chart
- Sustainability radar chart
- Actionable improvement suggestions
- Export farm plan as JSON

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework with App Router |
| TypeScript | Type-safe development |
| Tailwind CSS | Utility-first styling |
| Leaflet + react-leaflet | Map rendering with OSM tiles |
| Zustand | State management |
| Recharts | Data visualization |
| Lucide React | Icons |

## Project Structure

```
web-frontend/
├── src/
│   ├── app/
│   │   ├── globals.css      # Global styles + Tailwind
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Main page component
│   ├── components/
│   │   ├── map/
│   │   │   └── FarmMap.tsx  # Leaflet map component
│   │   ├── farm/
│   │   │   └── FarmConfigPanel.tsx  # Farm configuration UI
│   │   └── dashboard/
│   │       └── ResultsDashboard.tsx # Results visualization
│   ├── store/
│   │   └── farmStore.ts     # Zustand state management
│   ├── lib/
│   │   └── api.ts           # Simulation logic + API calls
│   └── types/
│       └── farm.ts          # TypeScript interfaces
├── package.json
├── tailwind.config.ts
├── tsconfig.json
└── next.config.js
```

## Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Navigate to web-frontend directory
cd web-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the app.

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## How It Works

### 1. Location Selection
Click anywhere on the Zimbabwe map to select a farm location. The system automatically:
- Detects the Agro-Ecological Zone (AEZ)
- Fetches weather/rainfall data
- Suggests suitable crops and livestock

### 2. Farm Configuration
In the sidebar, configure your farm:
- Set farm type (crops/livestock/mixed)
- Add livestock with quantities
- Allocate land to different crops
- Place infrastructure buildings

### 3. Run Simulation
Click "Run Simulation" to analyze your farm. The system calculates:
- Crop suitability scores based on AEZ and weather
- Expected yields and profit margins
- Sustainability metrics
- Synergies between farm components
- Resource requirements

### 4. Review Results
Switch to the Results tab to see:
- Net profit estimates with confidence ranges
- Sustainability score breakdown
- Crop suitability ranking
- Active synergies and suggestions

### 5. Export Plan
Download your complete farm plan as JSON for:
- Record keeping
- Sharing with advisors
- Integration with other systems

## Simulation Logic

### AEZ Zone Mapping
Zimbabwe's 5 agro-ecological zones are encoded with:
- Rainfall ranges
- Suitable crops
- Livestock carrying capacity

### Crop Suitability
Each crop is scored based on:
- Zone suitability (is this crop grown here?)
- Weather conditions (rainfall, drought risk)
- Crop-specific modifiers

### Sustainability Score
Calculated from:
- **Water Efficiency**: Irrigation vs rainfed ratio
- **Soil Health**: Manure input, legume rotation
- **Biodiversity**: Crop diversity + livestock mix
- **Carbon Footprint**: Livestock emissions

### Profit Estimation
Based on:
- Crop yields × market prices
- Livestock production × prices
- Input costs (feed, fertilizer, fuel)
- Synergy discounts (e.g., manure reduces fertilizer costs)

## Backend Integration

Currently uses mock simulation. To connect to the Python backend:

1. Start the FastAPI backend (when available):
```bash
cd ../src/api
uvicorn main:app --reload
```

2. Set the API URL:
```bash
export NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. The frontend will send farm configs to `/api/simulate` and display results.

## Customization

### Adding New Crops
Edit `src/lib/api.ts`:
1. Add to `CROP_BASE_YIELDS`
2. Add to `CROP_PRICES_USD`
3. Add to `availableCrops` in `FarmConfigPanel.tsx`

### Adding New Buildings
Edit `src/components/farm/FarmConfigPanel.tsx`:
1. Add to `buildingTypes` array
2. Add icon and label

### Styling
- Colors: Edit `tailwind.config.ts` → `colors.agri` and `colors.earth`
- Components: Use Tailwind classes throughout

## Roadmap

- [ ] Drawing mode for custom zone polygons
- [ ] Drag-and-drop building placement
- [ ] Real weather API integration
- [ ] Multi-year simulation
- [ ] Save/load farm plans
- [ ] Collaborative planning

## License

Part of the AgriMesh Autonomous project.
