import { useState, useEffect } from 'react'
import ChatContainer from './components/ChatContainer'
import Header from './components/Header'
import { ThemeProvider } from './context/ThemeContext'

function App() {
  return (
    <ThemeProvider>
      <div className="flex flex-col h-screen">
        <Header />
        <ChatContainer />
      </div>
    </ThemeProvider>
  )
}

export default App
