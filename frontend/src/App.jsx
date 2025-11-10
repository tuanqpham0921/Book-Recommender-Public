import '@/index.css'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import BookRecommenderPage from '@/pages/BookRecommenderPage'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<BookRecommenderPage />} />
        <Route path="/blog" element={<BookRecommenderPage />} />
        {/* Catch all other routes and redirect to home */}
        <Route path="*" element={<BookRecommenderPage />} />
      </Routes>
    </Router>
  )
}

export default App
