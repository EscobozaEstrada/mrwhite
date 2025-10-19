import axios from 'axios';
import { EnhancedBook, AIEditResponse } from '@/types/enhanced-book';

// Define API base URL
const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

// Enhanced Book Service
export const enhancedBookService = {
  // Create a new enhanced book
  createBook: async (bookData: {
    title: string;
    book_type?: string;
    tone_type: string;
    text_style: string;
    cover_image?: string | null;
  }): Promise<EnhancedBook> => {
    console.log('Creating enhanced book with API URL:', API_URL);
    const response = await axios.post(
      `${API_URL}/api/enhanced-book/enhanced-books`,
      bookData,
      {
        withCredentials: true
      }
    );
    return response.data.book;
  },

  // Categorize messages for a book (deprecated - now automatic based on book type)
  categorizeMessages: async (bookId: number, categories: string[]): Promise<any> => {
    // This is now handled automatically by book type configuration
    return { success: true, message: 'Categorization handled automatically by book type' };
  },

  // Generate chapters for a book
  generateChapters: async (bookId: number): Promise<any> => {
    const response = await axios.post(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}/generate`,
      {},
      {
        withCredentials: true
      }
    );
    return response.data;
  },

  // Get a specific book
  getBook: async (bookId: number): Promise<EnhancedBook> => {
    const response = await axios.get(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}`,
      {
        withCredentials: true
      }
    );
    return response.data.book;
  },

  // Get all books for the current user
  getUserBooks: async (): Promise<EnhancedBook[]> => {
    const response = await axios.get(
      `${API_URL}/api/enhanced-book/enhanced-books`,
      {
        withCredentials: true
      }
    );
    return response.data.books;
  },

  // Update a chapter
  updateChapter: async (bookId: number, chapterId: number, data: { title?: string, content?: string }): Promise<any> => {
    const response = await axios.put(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}/chapters/${chapterId}`,
      data,
      {
        withCredentials: true
      }
    );
    return response.data;
  },

  // Delete a chapter
  deleteChapter: async (bookId: number, chapterId: number): Promise<any> => {
    const response = await axios.delete(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}/chapters/${chapterId}`,
      {
        withCredentials: true
      }
    );
    return response.data;
  },

  // Generate PDF for a book
  generatePdf: async (bookId: number): Promise<string> => {
    const response = await axios.post(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}/pdf`,
      {},
      {
        withCredentials: true
      }
    );
    return response.data.pdf_url;
  },

  // Generate EPUB for a book
  generateEpub: async (bookId: number): Promise<string> => {
    const response = await axios.post(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}/epub`,
      {},
      {
        withCredentials: true
      }
    );
    return response.data.epub_url;
  },
  
  // AI-assisted chapter editing
  aiChatEdit: async (
    bookId: number, 
    message: string, 
    bookContext: {
      bookTitle: string;
      chapterTitle: string;
      chapterContent: string;
      tone?: string;
      textStyle?: string;
    },
    chatHistory?: Array<{role: 'user' | 'assistant', content: string}>,
    onProgress?: (progress: number) => void
  ): Promise<AIEditResponse> => {
    // Estimate if content is long enough to require chunking
    const estimatedTokens = bookContext.chapterContent.split(/\s+/).length * 1.3;
    const isLongContent = estimatedTokens > 2000;
    
    // If this is likely to be chunked processing, show initial progress
    if (isLongContent && onProgress) {
      onProgress(0);
    }
    
    try {
      const response = await axios.post(
        `${API_URL}/api/enhanced-book/enhanced-books/${bookId}/ai-chat-edit`,
        {
          message,
          bookContext,
          chatHistory
        },
        {
          withCredentials: true,
          onDownloadProgress: isLongContent ? (progressEvent) => {
            // This is just an approximation since we don't know the exact chunk count
            // But it gives users feedback that something is happening
            if (onProgress && progressEvent.total) {
              const percentComplete = Math.round((progressEvent.loaded / progressEvent.total) * 100);
              onProgress(Math.min(percentComplete, 90)); // Cap at 90% until fully complete
            }
          } : undefined
        }
      );
      
      // Complete progress when done
      if (isLongContent && onProgress) {
        onProgress(100);
      }
      
      return response.data;
    } catch (error) {
      // Reset progress on error
      if (isLongContent && onProgress) {
        onProgress(0);
      }
      throw error;
    }
  },
  
  // Get latest chats formatted for a book
  getLatestChats: async (bookId: number, category?: string, chapterId?: number): Promise<{
    success: boolean;
    formattedContent: string;
    messageCount: number;
  }> => {
    const response = await axios.get(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}/latest-chats`,
      {
        params: {
          category,
          chapterId
        },
        withCredentials: true
      }
    );
    return response.data;
  },

  // Delete a book
  deleteBook: async (bookId: number): Promise<any> => {
    const response = await axios.delete(
      `${API_URL}/api/enhanced-book/enhanced-books/${bookId}`,
      {
        withCredentials: true
      }
    );
    return response.data;
  }
}; 