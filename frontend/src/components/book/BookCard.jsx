import { useState } from 'react';
import { formatAuthors, formatAuthorsMobile, truncateText } from '@/utils/bookUtils';

export const BookCard = ({ book }) => {
  return (
    <div className="bg-white rounded-2xl shadow-sm flex flex-col h-full p-3">
      <div className="flex flex-col h-full">
        <img
          src={book.thumbnail}
          alt={book.title}
          className="w-full h-36 object-cover rounded-lg bg-gray-600 grayscale mb-2"
          onError={(e) => {
            // Prevent infinite loop if fallback image also fails
            if (e.target.src !== window.location.origin + '/cover-not-found.jpg') {
              e.target.src = '/cover-not-found.jpg';
            }
          }}
        />

        <h3 className="font-bold text-base sm:text-lg md:text-xl text-gray-900 mb-2 line-clamp-2">
          {book.title}
        </h3>

        <div className="mt-auto">
          <p className="text-gray-600 text-sm md:text-md line-clamp-2">
            <span className="hidden sm:inline">{formatAuthors(book, 2)}</span>
            <span className="sm:hidden">{formatAuthorsMobile(book)}</span>
          </p>
          <p className="text-gray-600 text-xs md:text-sm line-clamp-1">
            {book.categories} • {book.published_year} • {book.num_pages} pages
          </p>
        </div>
      </div>
    </div>
  );
};

// Detailed list card layout with descriptions
export const BookCardDetailed = ({ book }) => {
  const DESCRIPTION_CHAR_LIMIT = 300;
  const [isExpanded, setIsExpanded] = useState(false);

  const toggleDescription = () => {
    setIsExpanded(prev => !prev);
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 mb-2 flex-shrink-0">
      <div className="flex gap-4">
        <img
          src={book.thumbnail}
          alt={book.title}
          className="w-24 h-32 object-cover rounded bg-gray-600 flex-shrink-0 grayscale"
          onError={(e) => {
            // Prevent infinite loop if fallback image also fails
            if (e.target.src !== window.location.origin + '/cover-not-found.jpg') {
              e.target.src = '/cover-not-found.jpg';
            }
          }}
        />
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-base sm:text-lg text-gray-900 mb-1 line-clamp-2">
            {book.title} <span className="text-gray-400 text-xs sm:text-sm ml-1"> - {book.published_year}</span>
          </h3>

          <div className="flex flex-col gap-1 text-sm text-gray-600 mb-2">
            <p className="m-0">
              {formatAuthors(book, 3)}
            </p>
            <span className="">{book.categories}</span>
            {book.num_pages && (
              <span className="">{book.num_pages} pages</span>
            )}
            {book.average_rating && (
              <div className="flex items-center gap-1">
                <div className="flex text-gray-400">
                  {'★'.repeat(Math.floor(book.average_rating))}
                  {'☆'.repeat(5 - Math.floor(book.average_rating))}
                </div>
                <span>{book.average_rating}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {book.description && (
        <div className="border-t pt-3">
          <div className="text-sm text-gray-600">
            <p className="break-words">
              {isExpanded
                ? book.description
                : truncateText(book.description, DESCRIPTION_CHAR_LIMIT)
              }
              {book.description.length > DESCRIPTION_CHAR_LIMIT && !isExpanded && '...'}
            </p>
            {book.description.length > DESCRIPTION_CHAR_LIMIT && (
              <button
                onClick={toggleDescription}
                className="text-[(--text-inactive)] hover:text-gray-800 font-medium mt-2 text-sm"
              >
                {isExpanded ? 'See less' : 'See more'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
