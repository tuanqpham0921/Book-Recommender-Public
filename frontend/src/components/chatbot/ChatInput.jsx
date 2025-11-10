import { useState, useEffect, useRef } from 'react'
import { ArrowUp, Plus } from 'lucide-react';
import { userInputSuggestions } from '@/data/chatSuggestions';

function ChatInput({ newMessage, isStreaming, setNewMessage, onSendMessage }) {
    const [showSuggestions, setShowSuggestions] = useState(true)
    const suggestionsRef = useRef(null) // Ref for the suggestions container
    const hintsButtonRef = useRef(null) // Ref for the hints button

    // Handle clicks outside the suggestions dropdown
    useEffect(() => {
        function handleClickOutside(event) {
            // Check if click is outside suggestions AND outside hints button
            if (
                suggestionsRef.current &&
                !suggestionsRef.current.contains(event.target) &&
                hintsButtonRef.current &&
                !hintsButtonRef.current.contains(event.target)
            ) {
                setShowSuggestions(false)
            }
        }

        // Add event listener when suggestions are shown
        if (showSuggestions) {
            document.addEventListener('mousedown', handleClickOutside)
        }

        // Cleanup event listener
        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
        }
    }, [showSuggestions]) // Re-run when showSuggestions changes

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !isStreaming) {
            e.preventDefault()
            onSendMessage()
        }
    }

    const handleSuggestionClick = (suggestion) => {
        setShowSuggestions(false)
        setNewMessage(suggestion.text)
    }

    return (
        <div className="bg-[var(--bg-secondary)] p-4 pt-2 pr-6">
            <div className='outline rounded-xl bg-white relative shadow-lg'>
                {/* Hints Dropup Menu */}
                {showSuggestions && (
                    <div
                        ref={suggestionsRef} // Attach ref to suggestions container
                        className="absolute bottom-full left-0 right-0 mb-2 bg-[var(--bg-secondary)] border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto z-10"
                    >
                        <div className="sticky top-0 bg-[var(--bg-secondary)] z-20 border-b border-gray-200">
                            <div className="text-xs text-gray-500 p-2 px-5">Quick suggestions:</div>
                        </div>
                        <div className="p-2 pt-0">
                            {userInputSuggestions.map((suggestion) => (
                                <button
                                    key={suggestion.id}
                                    onClick={() => handleSuggestionClick(suggestion)}
                                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded transition-colors"
                                >
                                    {suggestion.text}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                <textarea
                    className="w-full h-24 text-lg px-4 py-3 pr-20 bg-transparent border resize-none border-none rounded-lg outline-none"
                    value={newMessage}
                    onChange={e => {
                        if (e.target.value.length <= 500) {
                            setNewMessage(e.target.value)
                        }
                    }}
                    onKeyDown={handleKeyDown}
                    onFocus={() => setShowSuggestions(false)} // Hide hints when typing
                    placeholder="Hints button is available at the bottom..."
                    maxLength={500}
                    rows={1}
                    style={{
                        minHeight: '2.5rem',
                        maxHeight: '8rem'
                    }}
                />

                {/* Hints Button */}
                <button
                    ref={hintsButtonRef} // Attach ref to hints button
                    type="button"
                    className="absolute right-12 bottom-3 p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-700"
                    onClick={() => setShowSuggestions(!showSuggestions)}
                    title="Show quick suggestions"
                >
                    <Plus size={20} />
                </button>

                {/* Send Button */}
                <button
                    type="submit"
                    className={`absolute right-3 bottom-3 p-2 rounded-full transition-all duration-200 ${
                        !isStreaming && newMessage.trim() 
                            ? 'bg-gray-800 text-white'
                            : 'text-gray-700 hover:bg-gray-200 ' 
                    }`}
                    onClick={onSendMessage}
                    disabled={isStreaming || !newMessage.trim()}
                >
                    <ArrowUp size={20} />
                </button>
            </div>

            {/* Character Counter */}
            <div className="flex justify-end mt-1 px-2">
                <span className={`text-xs ${newMessage.length >= 450 ? 'text-red-500' : 'text-gray-500'}`}>
                    {newMessage.length}/500
                </span>
            </div>
        </div>
    )
}

export default ChatInput
