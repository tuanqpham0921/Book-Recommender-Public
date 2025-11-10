import Markdown from 'react-markdown';
import { useRef, useEffect, lazy, Suspense } from 'react'
import { BookGridStack } from '@/components/book/BooksGrid';

// Dynamic import for MermaidDiagram (large library)
const MermaidDiagram = lazy(() => import('@/components/MermaidDiagram'));

// Loading component for Mermaid
const MermaidLoading = () => (
    <div className="message-bubble response">
        <div className="flex items-center justify-center h-32">
            <div className="loading-spinner"></div>
            <span className="ml-2 text-gray-600">Loading diagram...</span>
        </div>
    </div>
);

function ChatMessages({ messages, isStreaming }) {
    const containerRef = useRef(null)
    const userMessageRefs = useRef({})
    const turnRefs = useRef({})
    const lastUserMessageId = useRef(null)

    const scrollToNewestTurn = () => {
        if (messages.length > 0) {
            const newestTurn = messages[messages.length - 1]
            const turnRef = turnRefs.current[newestTurn.id]
            if (turnRef) {
                turnRef.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
        }
    }

    useEffect(() => {
        if (messages.length > 0) {
            const newestTurn = messages[messages.length - 1]
            if (newestTurn.user && newestTurn.user.id !== lastUserMessageId.current) {
                lastUserMessageId.current = newestTurn.user.id
                scrollToNewestTurn()
            }
        }
    }, [messages])

    return (
        <div ref={containerRef} className="chat-messages-container">
            {messages.map(({ id, user, response }, index) => (
                <div
                    key={id}
                    data-turn-id={id}
                    ref={(el) => turnRefs.current[id] = el}
                    className={`turn-container ${index === messages.length - 1 ? 'min-h-[95%]' : 'min-h-0'} `}
                >
                    {/* User message */}
                    <div data-user-id={user.id}
                        className="message-wrapper user"
                        ref={user.isUser ? (el) => userMessageRefs.current[user.id] = el : null}
                    >
                        <div className="message-bubble user">
                            {user.text}
                        </div>
                    </div>

                    <div data-response-id={response.id} className="flex flex-col message-wrapper response">

                        {/* SECTIONS-BASED RENDERING WITH STABLE IDs */}
                        {response.sections && response.sections.length > 0 && (
                            // Render sections in order using stable section IDs
                            response.sections.map((section, sectionIndex) => {
                                // Use section.id if available, otherwise fallback to index
                                const key = section.id || `${response.id}-section-${sectionIndex}`;

                                // Text section
                                if (section.type === 'text' && section.content) {
                                    return (
                                        <div key={key} className="message-bubble response markdown-container">
                                            <Markdown>{section.content}</Markdown>
                                        </div>
                                    );
                                }

                                // Books section
                                if (section.type === 'books' && section.books && section.books.length > 0) {
                                    return (
                                        <div key={key} className="book-cards-container mb-5">
                                            <BookGridStack books={section.books} />
                                        </div>
                                    );
                                }

                                // Diagram section
                                if (section.type === 'diagram' && section.mermaid) {
                                    return (
                                        <Suspense key={key} fallback={<MermaidLoading />}>
                                            <div className="message-bubble response">
                                                <MermaidDiagram
                                                    chart={section.mermaid}
                                                    className="w-full"
                                                />
                                            </div>
                                        </Suspense>
                                    );
                                }

                                // Error section
                                if (section.type === 'error' && section.content) {
                                    return (
                                        <div key={key} className="message-bubble text-red-500 italic mt-2">
                                            <span>{section.content}</span>
                                        </div>
                                    );
                                }

                                return null;
                            })
                        )}

                        {/* Loading state */}
                        {response.isLoading && response.isStreaming && (
                            <div className="loading-wrapper">
                                <div className="loading-spinner" />
                                <span className="loading-text">{response.loadingText}</span>
                            </div>
                        )}

                        {/* AI disclaimer - show on last message */}
                        {index === messages.length - 1 && !response.isLoading && !response.isStreaming && (
                            (response.sections?.length > 0 || response.text) && (
                                <div className="flex justify-end mt-5 mr-2">
                                    <span className="text-xs text-gray-400 italic">
                                        AI can make mistakes. Please double-check responses.
                                    </span>
                                </div>
                            )
                        )}

                    </div>
                </div>
            ))}
        </div>
    )
}

export default ChatMessages
