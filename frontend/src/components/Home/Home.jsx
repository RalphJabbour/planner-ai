import React, { useState, useRef, useEffect } from 'react';
import WeeklyCalendar from '../WeeklyCalendar/WeeklyCalendar'; // Adjust path if necessary
import styles from './Home.module.css';

// --- Placeholder Components (Replace or enhance these) ---
const Navbar = () => (
  <nav className={styles.navbar}>
    <span>Planner AI</span>
    <div>
      {/* Add Navbar items here */}
      <span>Profile</span>
      <span>Settings</span>
    </div>
  </nav>
);

const Sidebar = ({ isExpanded, toggleSidebar }) => (
  <aside className={`${styles.sidebar} ${isExpanded ? styles.sidebarExpanded : styles.sidebarCollapsed}`}>
    <button onClick={toggleSidebar} className={styles.toggleButton}>
      {isExpanded ? '<' : '>'}
    </button>
    <div className={styles.sidebarContent}>
      {/* Add Sidebar items here */}
      <div className={styles.sidebarItem}>
        <span className={styles.sidebarIcon}>📅</span>
        {isExpanded && <span className={styles.sidebarText}>Calendar</span>}
      </div>
      <div className={styles.sidebarItem}>
        <span className={styles.sidebarIcon}>📝</span>
        {isExpanded && <span className={styles.sidebarText}>Tasks</span>}
      </div>
      <div className={styles.sidebarItem}>
        <span className={styles.sidebarIcon}>⚙️</span>
        {isExpanded && <span className={styles.sidebarText}>Settings</span>}
      </div>
    </div>
    {/* --- Chat Component --- */}
    {isExpanded && <ChatInterface />}
  </aside>
);
// --- End Placeholder Components ---


// --- Basic Chat Interface Component ---
const ChatInterface = () => {
  const [messages, setMessages] = useState([{ sender: 'ai', text: 'How can I help you plan today?' }]);
  const [input, setInput] = useState('');
  const [chatId, setChatId] = useState(() => `chat_${Date.now()}_${Math.random().toString(36).substring(7)}`); // Simple unique ID
  const [pendingConfirmation, setPendingConfirmation] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setPendingConfirmation(false); // Reset confirmation state

    try {
      const token = localStorage.getItem("accessToken");
      const response = await fetch('/api/ai-assistant/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: input, chat_id: chatId })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }

      const data = await response.json();
      setMessages(prev => [...prev, { sender: 'ai', text: data.reply }]);
      setChatId(data.chat_id); // Update chat ID if backend changes it (though unlikely here)
      setPendingConfirmation(data.requires_confirmation);

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, { sender: 'ai', text: `Error: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirm = async () => {
    setIsLoading(true);
    setPendingConfirmation(false);
     try {
      const token = localStorage.getItem("accessToken");
      const response = await fetch('/api/ai-assistant/chat/confirm', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ chat_id: chatId })
      });

       if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error: ${response.status}`);
      }

      const data = await response.json();
      setMessages(prev => [...prev, { sender: 'ai', text: data.message || "Actions confirmed!" }]);
      // Optionally trigger a calendar refresh here if needed

    } catch (error) {
      console.error("Confirmation error:", error);
      setMessages(prev => [...prev, { sender: 'ai', text: `Confirmation failed: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
     setMessages(prev => [...prev, { sender: 'ai', text: 'Okay, I won\'t make those changes.' }]);
     setPendingConfirmation(false);
     // Optionally call a backend endpoint to clear the draft state if needed
  };


  return (
    <div className={styles.chatContainer}>
      <div className={styles.chatMessages}>
        {messages.map((msg, index) => (
          <div key={index} className={`${styles.chatMessage} ${styles[msg.sender]}`}>
            {msg.text}
          </div>
        ))}
         {isLoading && <div className={`${styles.chatMessage} ${styles.ai}`}>Thinking...</div>}
        <div ref={messagesEndRef} />
      </div>
      {pendingConfirmation && (
        <div className={styles.confirmationControls}>
          <button onClick={handleConfirm} disabled={isLoading}>Confirm</button>
          <button onClick={handleCancel} disabled={isLoading}>Cancel</button>
        </div>
      )}
      <div className={styles.chatInputArea}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !isLoading && handleSend()}
          placeholder="Ask Planner AI..."
          disabled={isLoading || pendingConfirmation}
        />
        <button onClick={handleSend} disabled={isLoading || pendingConfirmation}>Send</button>
      </div>
    </div>
  );
};
// --- End Chat Interface Component ---


const Home = () => {
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);

  const toggleSidebar = () => {
    setIsSidebarExpanded(!isSidebarExpanded);
  };

  return (
    <div className={styles.homeLayout}>
      <Navbar />
      <div className={styles.mainContainer}>
        <div className={`${styles.contentArea} ${isSidebarExpanded ? styles.contentAreaShifted : ''}`}>
          {/* Wrap WeeklyCalendar in a div if needed for specific styling */}
          <div className={styles.calendarWrapper}>
            <WeeklyCalendar />
          </div>
        </div>
        {/* Pass props to Sidebar */}
        <Sidebar isExpanded={isSidebarExpanded} toggleSidebar={toggleSidebar} />
      </div>
    </div>
  );
};

export default Home;