import VersionDropdown from '@/components/subheader/VersionDropdown';

const SubHeader = ({ activeView, setActiveView }) => {
    // This is a subheader for specific pages like the portfolio page
    // useful for mobile and formatting pages (chat, blog, tips, version dropdown, etc)

    const handleViewChange = (view) => {
        setActiveView(view);
    };

    return (
        <div className="flex flex-row items-center w-full gap-8">

            <button
                onClick={() => handleViewChange('chat')}
                className={`underline-animated underline-button ${activeView === 'chat' ? 'active' : ''}`}
            >
                Chat
            </button>

            <button
                onClick={() => handleViewChange('blog')}
                className={`underline-animated underline-button ${activeView === 'blog' ? 'active' : ''}`}
            >
                Blog
            </button>

            <VersionDropdown />
        </div>
    );
};

export default SubHeader;