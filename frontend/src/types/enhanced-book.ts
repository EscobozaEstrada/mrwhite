export interface EnhancedBook {
  id: number;
  user_id: number;
  title: string;
  cover_image: string | null;
  tone_type: string;
  text_style: string;
  status: string;
  created_at: string;
  updated_at: string;
  pdf_url: string | null;
  epub_url: string | null;
  chapters: EnhancedBookChapter[];
}

export interface EnhancedBookChapter {
  id: number;
  book_id: number;
  title: string;
  content: string;
  category: string;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface MessageCategory {
  id: number;
  message_id: number;
  category: string;
  book_id: number;
  created_at: string;
}

export type ToneType = 'friendly' | 'narrative' | 'playful';

export type TextStyle = 'poppins' | 'times new roman' | 'arial' | 'georgia' | 'courier';

export interface AIEditResponse {
  success: boolean;
  message: string;
  chunks_successful?: number;
  editedContent?: string;
  intent?: 'edit' | 'information' | 'summary';
  chunks_processed?: number;
  is_chunked_processing?: boolean;
} 