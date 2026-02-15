import { useState, useEffect } from 'react'
import Header from './components/Header'
import BotsTable from './components/BotsTable'
import ChartsPanel from './components/ChartsPanel'
import FailureModal from './components/FailureModal'
import { fetchBotStatus } from './services/api'

function App() {
  const [bots, setBots] = useState({})
  const [failures, setFailures] = useState([])
  const [lastUpdate, setLastUpdate] = useState('--')
  const [selectedFailure, setSelectedFailure] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const loadStatus = async () => {
    try {
      const data = await fetchBotStatus()
      setBots(data.bots || {})
      setFailures(data.failures || [])
      setLastUpdate(new Date().toLocaleString())
    } catch (error) {
      console.error('Error loading status:', error)
    }
  }

  useEffect(() => {
    loadStatus()
    const interval = setInterval(loadStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleFailureClick = (failure) => {
    setSelectedFailure(failure)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedFailure(null)
  }

  return (
    <>
      <Header lastUpdate={lastUpdate} onRefresh={loadStatus} />
      
      <div className="card">
        <div className="card-left">
          <BotsTable bots={bots} />
        </div>
        
        <div className="card-right">
          <ChartsPanel bots={bots} failures={failures} onFailureClick={handleFailureClick} />
        </div>
      </div>

      {isModalOpen && selectedFailure && (
        <FailureModal failure={selectedFailure} onClose={handleCloseModal} />
      )}
    </>
  )
}

export default App
