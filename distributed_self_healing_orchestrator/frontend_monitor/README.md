# Bots Monitor Frontend (React)

A React-based real-time monitoring dashboard for the distributed self-healing orchestrator bot system.

## Features

- **Real-time Bot Monitoring**: Track bot heartbeats and status updates every 3 seconds
- **Interactive Charts**: 
  - Doughnut chart showing running vs failed bots
  - Line chart displaying active bot history over time
- **Failure Tracking**: View detailed failure information including:
  - Error messages and stack traces
  - DOM snapshots
  - Page HTML rendering
  - Comprehensive metadata
- **Responsive Design**: Fully responsive UI that works on desktop and mobile devices

## Getting Started

### Prerequisites

- Node.js (v16 or higher)
- npm or yarn

### Installation

```bash
# Install dependencies
npm install
```

### Development

```bash
# Start development server (runs on port 3000)
npm run dev
```

The frontend will automatically proxy API requests to `http://localhost:5002` for the `/status` endpoint.

### Build for Production

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend_monitor/
├── src/
│   ├── components/          # React components
│   │   ├── Header.jsx       # Header with refresh controls
│   │   ├── BotsTable.jsx    # Bot status table
│   │   ├── ChartsPanel.jsx  # Charts container
│   │   ├── StatusDoughnut.jsx    # Doughnut chart component
│   │   ├── ActiveBotsLine.jsx    # Line chart component
│   │   ├── RecentFailures.jsx    # Failures list
│   │   └── FailureModal.jsx      # Detailed failure modal
│   ├── services/
│   │   └── api.js           # API service functions
│   ├── utils/
│   │   └── helpers.js       # Utility functions
│   ├── App.jsx              # Main app component
│   ├── main.jsx             # React entry point
│   └── index.css            # Global styles
├── index.html               # HTML entry point
├── vite.config.js           # Vite configuration
└── package.json             # Dependencies and scripts
```

## Technology Stack

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Chart.js**: Chart rendering
- **react-chartjs-2**: React wrapper for Chart.js

## API Integration

The frontend expects a `/status` endpoint that returns:

```json
{
  "bots": {
    "bot_id": {
      "status": "RUNNING",
      "last_seen": 1234567890,
      "meta": {}
    }
  },
  "failures": [
    {
      "botId": "bot_id",
      "timestamp": 1234567890,
      "error": "Error message",
      "category": "locator",
      "confidence": 0.95,
      "page_url": "https://example.com",
      "dom": "<html>...",
      "page_html": "<html>..."
    }
  ]
}
```

## License

MIT
