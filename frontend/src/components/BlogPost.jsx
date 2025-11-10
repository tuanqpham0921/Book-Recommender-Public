import { useState, useEffect } from 'react';
import Markdown from 'react-markdown';

const BlogPost = ({ postId = 1 }) => {
    const [post, setPost] = useState(null);
    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Post metadata - you can move this to a separate JSON file later
    const postsData = {
        1: {
            id: 1,
            title: "An AI System for Book Discovery",
            author: "Tuan Pham",
            date: "November 5, 2025",
            contentFile: "/blog-posts/book-recommender-system.md"
        }
    };

    useEffect(() => {
        const loadBlogPost = async () => {
            try {
                // Get post metadata
                const postMeta = postsData[postId];
                if (!postMeta) {
                    throw new Error('Blog post with ID ' + postId + ' not found');
                }

                // Load markdown content from public folder
                const response = await fetch(postMeta.contentFile);
                if (!response.ok) {
                    throw new Error('Failed to load blog post content');
                }
                const markdownContent = await response.text();

                setPost(postMeta);
                setContent(markdownContent);
            } catch (err) {
                console.error('Error loading blog post:', err);
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        loadBlogPost();
    }, [postId]);

    if (loading) {
        return (
            <div className="blog-container">
                <div className="flex justify-center items-center h-64">
                    <p className="text-gray-500">Loading blog post...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="blog-container">
                <div className="flex justify-center items-center h-64">
                    <p className="text-red-500">Error: {error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="blog-container">
            <article className="blog-article">
                <header className="blog-header">
                    <h1 className="blog-title">
                        {post.title}
                    </h1>

                    <div className="blog-meta">
                        <span>By {post.author}</span>
                        <span>{post.date}</span>
                    </div>
                </header>

                <div className="markdown-body">
                    <Markdown>
                        {content}
                    </Markdown>
                </div>

                <footer className="blog-footer">
                    <p>Thank you for reading.</p>
                </footer>
            </article>
        </div>
    );
};

export default BlogPost;
