import { useState, useEffect, useRef } from 'react'
import { useImmer } from 'use-immer';
import ChatInput from '@/components/chatbot/ChatInput'
import ChatMessages from '@/components/chatbot/ChatMessages'
import api from '@/api';
import { parseSSEStream } from '@/utils';

function ChatBot() {
    const messagesEndRef = useRef(null)

    const [turn, setTurn] = useImmer([])

    const [sessionId, setSessionId] = useState(null);
    const [newMessage, setNewMessage] = useState('');

    const isStreaming = turn.length && turn[turn.length - 1].response.isStreaming;

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [turn, !isStreaming])

    async function handleSendMessage() {
        const trimmedMessage = newMessage.trim();
        if (!trimmedMessage || isStreaming) return;

        const turnID = Date.now()
        const userMessage = {
            id: turnID + '--user',
            turnId: turnID,
            text: trimmedMessage,
            isUser: true,
        }

        const botMessage = {
            id: turnID + '--bot',
            turnId: turnID,
            isUser: false,
            isLoading: true,
            loadingText: 'Sending Request...',
            isStreaming: true,
            sections: [
                // Each section is a distinct unit of response.
                // They are ordered and can be streamed incrementally.
                // Examples:
                // { id: ..., type: 'text', content: 'Analyzing Dune...' }
                // { id: ..., type: 'books', books: [...] }
                // { id: ..., type: 'diagram', mermaid: 'graph TD; ...' }
            ],
        };

        const curTurn = { id: turnID, user: userMessage, response: botMessage }
        setTurn(draft => { draft.push(curTurn) })
        setNewMessage('')

        let sessionIdOrNew = sessionId;
        let stream = null;
        const abortController = new AbortController();
        let safetyTimer = null;

        try {
            // Safety timer - abort the request after 3 minutes
            safetyTimer = setTimeout(() => {
                console.warn('Safety timer triggered - aborting request');
                abortController.abort('Request timeout after 3 minutes');
            }, 180_000); // 3 minutes

            if (!sessionId) {
                const { id } = await api.createSession();
                setSessionId(id);
                sessionIdOrNew = id;
            }

            // Pass abort signal to API call
            stream = await api.sendChatMessage(sessionIdOrNew, trimmedMessage, abortController.signal);

            for await (const event of parseSSEStream(stream)) {
                if (abortController.signal.aborted) {
                    console.log('Stream aborted by controller');
                    break;
                }

                console.log("event: ", event.type);

                if (event.type === 'step.complete') {
                    setTurn(draft => {
                        const last = draft[draft.length - 1];
                        last.response.isLoading = false;
                        last.response.loadingText = null;
                        last.response.isStreaming = false;
                    });
                    break;
                }

                // 🔴 ERROR HANDLING
                if (event.type === 'error') {
                    console.error('Error in handleSendMessage:', event.data);
                    setTurn(draft => {
                        const last = draft[draft.length - 1];
                        last.response.isLoading = false;
                        last.response.error = true;
                        last.response.errorText = event.data;
                        last.response.loadingText = null;
                        last.response.isStreaming = false;

                        const sectionId = `${last.response.id}-section-${last.response.sections.length + 1}`;
                        last.response.sections.push({
                            id: sectionId,
                            type: 'error',
                            content: event.data
                        });
                    });
                    break;
                }

                if (event.type === 'ui.loading') {
                    setTurn(draft => {
                        draft[draft.length - 1].response.loadingText = event.data || 'Thinking...';
                        draft[draft.length - 1].response.isLoading = true;
                        draft[draft.length - 1].response.isStreaming = true;
                    });
                }

                /// 🟢 TEXT (streaming text deltas)
                if (event.type === 'content.delta') {
                    setTurn(draft => {
                        const last = draft[draft.length - 1];
                        last.response.isLoading = false;
                        last.response.loadingText = null;
                        last.response.isStreaming = true;

                        // Find or create the current text section
                        const lastSection = last.response.sections.at(-1);
                        if (!lastSection || lastSection.type !== 'text') {
                            const sectionId = `${last.response.id}-section-${last.response.sections.length + 1}`;
                            last.response.sections.push({
                                id: sectionId,
                                type: 'text',
                                content: ''
                            });
                        }
                        last.response.sections.at(-1).content += event.data || '';
                    });
                    continue;
                }

                // 📘 BOOK CARD EVENTS
                if (event.type === 'book_card') {
                    setTurn(draft => {
                        const last = draft[draft.length - 1];
                        last.response.isStreaming = true;

                        // Check if a books section already exists
                        const lastSection = last.response.sections.at(-1);
                        if (!lastSection || lastSection.type !== 'books') {
                            const sectionId = `${last.response.id}-section-${last.response.sections.length + 1}`;
                            last.response.sections.push({
                                id: sectionId,
                                type: 'books',
                                books: []
                            });
                        }

                        // Append book data
                        last.response.sections.at(-1).books.push(event.data);
                    });
                    continue;
                }

                // 🧭 MERMAID DIAGRAM EVENTS
                if (event.type === 'mermaid.diagram') {
                    setTurn(draft => {
                        const last = draft[draft.length - 1];
                        last.response.isStreaming = true;
                        const sectionId = `${last.response.id}-section-${last.response.sections.length + 1}`;
                        last.response.sections.push({
                            id: sectionId,
                            type: 'diagram',
                            mermaid: event.data
                        });
                    });
                    continue;
                }

                console.log("----------------------------")
                console.log(turn)
                console.log("----------------------------")

            }

        } catch (err) {
            console.error(err);

            // Handle abort error specifically
            if (err.name === 'AbortError' || abortController.signal.aborted) {
                setTurn(draft => {
                    if (!draft.length) return;
                    const last = draft[draft.length - 1];
                    last.response.isLoading = false;
                    last.response.loadingText = null;
                    last.response.isStreaming = false;

                    const sectionId = `${last.response.id}-section-${last.response.sections.length + 1}`;
                    last.response.sections.push({
                        id: sectionId,
                        type: 'error',
                        content: "Request timed out after 3 minutes"
                    });
                });
            } else {
                // Handle other errors
                setTurn(draft => {
                    if (!draft.length) return;
                    const last = draft[draft.length - 1];
                    last.response.isLoading = false;
                    last.response.loadingText = null;
                    last.response.isStreaming = false;

                    const sectionId = `${last.response.id}-section-${last.response.sections.length + 1}`;
                    last.response.sections.push({
                        id: sectionId,
                        type: 'error',
                        content: "Oops something went wrong..."
                    });
                });
            }
        } finally {
            // Clear safety timer
            if (safetyTimer) {
                clearTimeout(safetyTimer);
                safetyTimer = null;
            }

            // Abort any ongoing request if still active
            if (abortController && !abortController.signal.aborted) {
                abortController.abort('Cleanup');
            }

            // Safety net to ensure that we set streaming is done
            setTurn(draft => {
                if (!draft.length) return;
                const last = draft[draft.length - 1];
                last.response.isLoading = false;
                last.response.loadingText = null;
                last.response.isStreaming = false;
            });
        }
    }

    return (
        <div className="flex flex-col h-full w-full min-w-0 min-h-0">
            <div className="flex-1 min-h-0 min-w-0 overflow-hidden pl-3 mr-3">
                {turn.length === 0 ? (
                    <div className="h-full w-full flex items-center justify-center text-gray-800 italic text-2xl">
                        What are you in the mood to read today?
                    </div>
                ) : (
                    <ChatMessages
                        messages={turn}
                        isStreaming={isStreaming}
                    />
                )}
            </div>
            <div className="flex-shrink-0 min-w-0">
                <ChatInput
                    newMessage={newMessage}
                    isStreaming={isStreaming}
                    setNewMessage={setNewMessage}
                    onSendMessage={handleSendMessage}
                />
            </div>
        </div>
    )
}

export default ChatBot
