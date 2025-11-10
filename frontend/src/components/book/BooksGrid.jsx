import { BookCard, BookCardDetailed } from '@/components/book/BookCard';

// Grid layout for full-screen book display
export const BooksGrid = ({ books }) => {
  // If no books, show empty state
  if (!books || books.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500 space-y-2">
            <h3 className="text-xl font-medium">No books to display</h3>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col overflow-y-auto min-h-0 min-w-0">
      {books.map((book, index) => (
        <BookCardDetailed book={book} key={book.isbn13} />
      ))}
    </div>
  );
};

// Stack layout for horizontal scrolling book display (mobile)
export const BookGridStack = ({ books }) => {
  if (!books || books.length === 0) {
    return null;
  }

  return (
    <div className="w-full flex flex-row p-4 bg-transparent rounded-lg min-w-0 h-full">
      <div className="flex gap-4 overflow-x-auto pb-2 min-w-0">
        {books.map((book, index) => (
          <div key={index} className="flex-shrink-0 w-64">
            <BookCard book={book} key={book.isbn13} />
          </div>
        ))}
      </div>
    </div>
  );
};