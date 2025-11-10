// Utility functions for book data formatting

// Utility function to format authors with smart truncation
export const formatAuthors = (book, maxAuthors = 2) => {
    if (!book.authors && !book.author) return '';

    const authorsString = book.authors || book.author;
    const authors = authorsString.split(';').map(author => author.trim());

    if (authors.length === 1) {
        return authors[0];
    } else if (authors.length <= maxAuthors) {
        return authors.join(', ');
    } else {
        return `${authors.slice(0, maxAuthors).join(', ')} & ${authors.length - maxAuthors} more`;
    }
};

// Mobile-optimized author formatting (even more compact)
export const formatAuthorsMobile = (book) => {
    if (!book.authors && !book.author) return '';

    const authorsString = book.authors || book.author;
    const authors = authorsString.split(';').map(author => author.trim());

    if (authors.length === 1) {
        return authors[0];
    } else if (authors.length === 2) {
        return authors.join(' & ');
    } else {
        return `${authors[0]} & ${authors.length - 1} others`;
    }
};

// Helper function to truncate text with ellipsis
export const truncateText = (text, maxLength = 300) => {
    if (!text) return '';
    return text.length > maxLength ? text.slice(0, maxLength) : text;
};
