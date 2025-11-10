import SubHeader from '@/components/subheader/SubHeader';
import NavBar from '@/components/NavBar';

const Header = ({ activeView, setActiveView }) => {
    // This is an overall header. Consistent across all pages and portfolio
    // will have a title, logo, etoc... and  (must) a side nav bar,

    return (
        <div className="flex items-start justify-between w-full border-b border-gray-200 pb-0">
            <div className='flex flex-col w-full p-4 pb-0'>
                <div className='flex items-center justify-between'>
                    <h1 className='flex flex-row text-2xl text-gray-800'>
                        Book Recommender  <p className='ml-1 mt-1 text-xl text-gray-500'>(pre-release)</p>
                    </h1>
                    
                    {/* Side nav bar here, consistent across all projects and portfolio items */}
                    <NavBar />
                </div>

                <SubHeader activeView={activeView} setActiveView={setActiveView} />
            </div>

        </div>
    );
};

export default Header;