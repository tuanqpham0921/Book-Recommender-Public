import { useMemo, lazy, Suspense } from "react";

// Dynamic imports for code splitting
const ChatBot = lazy(() => import("@/components/ChatBot"));
const BlogPost = lazy(() => import("@/components/BlogPost"));

// Loading component
const LoadingSpinner = () => (
    <div className="absolute inset-0 flex items-center justify-center">
        <div className="loading-spinner"></div>
        <span className="ml-2 text-gray-600">Loading...</span>
    </div>
);

const DisplayPanel = ({ activeView, setActiveView }) => {
    const renderContent = useMemo(() => {
        return (
            <div className="absolute inset-0 h-full w-full min-h-0">
                <Suspense fallback={<LoadingSpinner />}>
                    {activeView === 'chat' && <ChatBot />}
                    {activeView === 'blog' && <BlogPost />}
                </Suspense>
            </div>
        );
    }, [activeView]);

    return (
        <div className="relative h-full w-full overflow-hidden">
            {renderContent}
        </div>
    );
};

export default DisplayPanel;