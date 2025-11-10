import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import Header from '@/components/Header'
import DisplayPanel from '@/components/DisplayPanel'

function BookRecommenderPage() {
  const [activeView, setActiveView] = useState('chat')
  const [backendReady, setBackendReady] = useState(true)
  const navigate = useNavigate()
  const location = useLocation()

  // Sync URL with activeView state
  useEffect(() => {
    const path = location.pathname
    if (path === '/blog') {
      setActiveView('blog')
    } else {
      setActiveView('chat') // Default to chat for any other path
    }
  }, [location.pathname])

  // Custom setActiveView that also updates URL
  const handleViewChange = (view) => {
    setActiveView(view)
    if (view === 'blog') {
      navigate('/blog')
    } else {
      navigate('/')
    }
  }

  return (
    <div className="w-screen h-screen bg-[var(--bg-secondary)]" style={{ height: '100dvh' }}>
      <div className="mobile-safe-area w-full h-full relative max-w-4xl mx-auto bg-[var(--bg-secondary)]" style={{ height: '100dvh' }}>
        <div className="grid grid-rows-[auto_1fr] w-full h-full">
          <Header activeView={activeView} setActiveView={handleViewChange} />
          <DisplayPanel activeView={activeView} setActiveView={handleViewChange} />
        </div>
      </div>
    </div>
  )
}

export default BookRecommenderPage
