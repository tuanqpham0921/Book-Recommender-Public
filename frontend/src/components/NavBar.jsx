import { useState } from 'react';
import { Menu, Briefcase, Linkedin, Github, FileText } from 'lucide-react';

const NavBar = () => {
    const [isOpen, setIsOpen] = useState(false);

    const toggleNavbar = () => {
        setIsOpen(!isOpen);
    };

    const navigationItems = [
        { icon: Briefcase, label: 'Portfolio', href: 'https://www.tuanqpham0921.com', external: false },
        { icon: Linkedin, label: 'LinkedIn', href: 'https://linkedin.com/in/tuanqpham0921', external: true },
        { icon: Github, label: 'GitHub', href: 'https://github.com/tuanqpham0921', external: true },
        // { icon: FileText, label: 'Resume', href: '/resume', external: false }
    ];

    return (
        <>
            {/* Hamburger Menu Button */}
            <button
                onClick={toggleNavbar}
                className=" z-35 p-2 hover:bg-gray-200 rounded-full transition-colors"
                aria-label="Toggle navigation menu"
            >
                <Menu size={24} strokeWidth={1.5} className="text-gray-500" />
            </button>

            {/* Overlay */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-gray bg-opacity-50 backdrop-blur-xs z-40"
                    onClick={toggleNavbar}
                />
            )}

            {/* Vertical Sidebar */}
            <nav
                className={`fixed top-0 right-0 h-full flex flex-col bg-[var(--bg-secondary)] transform transition-transform duration-700 ease-in-out z-40 ${isOpen ? 'translate-x-0' : 'translate-x-full'
                    }`}
            >
                {/* Navbar Header */}
                <div className="p-6 border-b border-gray-200">
                    <h2 className="text-xl font-semibold text-gray-800">
                        Navigation
                    </h2>
                </div>

                {/* Navigation Items*/}
                <div className="py-4">
                    {navigationItems.map((item, index) => (
                        <a
                            key={index}
                            href={item.href}
                            target={item.external ? "_blank" : undefined}
                            rel={item.external ? "noopener noreferrer" : undefined}
                            className="flex items-center px-6 py-3 transition-colors duration-200"
                            onClick={toggleNavbar} // Close navbar when item is clicked
                        >
                            <item.icon size={20} className="mr-3" />
                            <span className="underline-animated underline-link">
                                {item.label}
                            </span>
                        </a>
                    ))}
                </div>

                {/* Footer/Bottom Section - naturally flows to bottom */}
                <div className="p-6 border-t border-gray-200 mt-auto">
                    <div className="text-left space-y-2 text-gray-500">
                        <div className="text-sm">
                            tuanqpham0921@gmail.com
                        </div>
                        <div className="text-sm">
                            San Marcos, TX
                        </div>
                    </div>
                </div>
            </nav>
        </>
    );
};

export default NavBar;