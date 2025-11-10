import { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

const VersionDropdown = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [selectedVersion, setSelectedVersion] = useState('3');
    const dropdownRef = useRef(null);

    const versions = [
        { id: '1', name: 'V1.0.0', description: 'Pre-defined filters and limited', url: 'https://tuanqpham0921.com/book-recommender-v1' },
        { id: '2', name: 'V2.1.0', description: 'Smart filters to parse query', url: 'https://tuanqpham0921.com/book-recommender-v2' },
        { id: '3', name: 'V3.0.0', description: 'Conversational recommender', url: null } // Current page
    ];

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleVersionSelect = (version) => {
        setSelectedVersion(version.id);
        setIsOpen(false);
        console.log('Selected version:', version.name);

        // Navigate to different URLs for v1 and v2, stay on current page for v3
        if (version.url) {
            window.location.href = version.url;
        }
    };

    return (
        <div className="relative inline-block" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="underline-animated underline-button flex items-center"
            >
                Versions 3
                <ChevronDown size={16} className="text-gray-500 ml-1 mt-1" />
            </button>

            {isOpen && (
                <div className="absolute top-full left-0 w-56 bg-[var(--bg-secondary)] border border-gray-200 rounded-b-2xl rounded-tr-2xl shadow-2xl z-50 overflow-hidden">
                    {versions.map((version) => (
                        <button
                            key={version.id}
                            onClick={() => handleVersionSelect(version)}
                            className={`block w-full px-4 py-3 text-left text-base font-medium transition-all duration-150 hover:bg-gray-100 hover:text-gray-900 ${version.id === selectedVersion ? 'text-gray-800 bg-[var(--bg-secondary)]' : 'text-gray-700'}`}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex flex-col text-left">
                                    <span className="text-left text-small">{version.name}</span>
                                    <span className="text-xs text-gray-10000 font-normal text-left">{version.description}</span>
                                </div>
                                {version.id === selectedVersion && (
                                    <span className="text-gray-600 ml-3">✓</span>
                                )}
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

export default VersionDropdown;
