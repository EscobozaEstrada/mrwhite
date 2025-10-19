'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogFooter 
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { Loader2, Upload, X, Image, Check, Heart, Apple, Dumbbell, Clock, BookOpen, MessageCircle, HelpCircle, Lightbulb, Calendar, Target, Mountain, Trophy } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import toast from '@/components/ui/sound-toast';
import { enhancedBookService } from '@/services/enhancedBookService';
import { ToneType, TextStyle } from '@/types/enhanced-book';
import axios, { AxiosError } from 'axios';
import CustomDropdown from './CustomDropdown';
import BookCreationProgress from './BookCreationProgress';

interface EnhancedBookCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId?: string;
}

const BOOK_TYPE_OPTIONS = [
  { id: 'relationship', name: 'Relationship Book', description: 'Inspirational piece about your bond' },
  { id: 'historical', name: 'Historical Book', description: 'Chronological life story with photos' },
  { id: 'medical', name: 'Medical Record', description: 'Health tracking and records' },
  { id: 'training', name: 'Training Book', description: 'Training journey and skills' },
  { id: 'family', name: 'Family & Friends', description: 'Social connections and relationships' },
  { id: 'memorial', name: "Dog's Life Book (Memorial)", description: 'Comprehensive tribute' },
  { id: 'general', name: 'General Book', description: 'Custom categories' }
];

// Categories removed - book types now determine chapter structure automatically

const TONE_OPTIONS = [
  { id: 'friendly', name: 'Friendly' },
  { id: 'narrative', name: 'Narrative' },
  { id: 'playful', name: 'Playful' }
];

const TEXT_STYLE_OPTIONS = [
  { id: 'poppins', name: 'Poppins' },
  { id: 'times new roman', name: 'Times New Roman' },
  { id: 'arial', name: 'Arial' },
  { id: 'georgia', name: 'Georgia' },
  { id: 'courier', name: 'Courier' }
];

export default function EnhancedBookCreationModal({
  isOpen,
  onClose,
  conversationId
}: EnhancedBookCreationModalProps) {
  const { user } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [bookTitle, setBookTitle] = useState('');
  const [bookType, setBookType] = useState('general');
  // Categories removed - book types determine chapter structure automatically
  const [toneType, setToneType] = useState('friendly');
  const [textStyle, setTextStyle] = useState('poppins');
  const [coverImage, setCoverImage] = useState<File | null>(null);
  const [coverImagePreview, setCoverImagePreview] = useState<string | null>(null);
  const [uploadingCover, setUploadingCover] = useState(false);
  const [creationProgress, setCreationProgress] = useState(0);
  const [creationStatus, setCreationStatus] = useState('');
  const [showProgress, setShowProgress] = useState(false);

  // Reset state when modal is opened
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setBookTitle('');
      setBookType('general');
      // Categories removed - book types determine content automatically
      setToneType('friendly');
      setTextStyle('poppins');
      setCoverImage(null);
      setCoverImagePreview(null);
      setCreationProgress(0);
      setCreationStatus('');
      setShowProgress(false);
    }
  }, [isOpen]);

  // Handle modal close with custom cleanup
  const handleClose = () => {
    setShowProgress(false);
    onClose();
  };

  // Category toggle removed - book types determine content automatically

  const handleNextStep = () => {
    if (step === 1) {
      if (bookTitle.trim() === '') {
        toast.error('Please enter a title for your book');
        return;
      }
      
      if (!coverImage) {
        toast.error('Please upload a cover image');
        return;
      }
    }

    // Category validation removed - book types determine content automatically

    if (step < 3) {
      setStep(step + 1);
    }
  };

  const handlePrevStep = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const handleCoverImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        toast.error('Image size should be less than 5MB');
        return;
      }
      
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
      }
      
      setCoverImage(file);
      const reader = new FileReader();
      reader.onload = () => {
        setCoverImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveCoverImage = () => {
    setCoverImage(null);
    setCoverImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const uploadCoverImage = async (): Promise<string | null> => {
    if (!coverImage) return null;
    
    try {
      setUploadingCover(true);
      const formData = new FormData();
      formData.append('file', coverImage);
      
      const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
      const response = await axios.post(`${API_URL}/api/upload/image`, formData, {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data.success) {
        return response.data.url;
      } else {
        toast.error(response.data.message || 'Failed to upload image');
        return null;
      }
    } catch (error) {
      console.error('Error uploading cover image:', error);
      toast.error('Failed to upload cover image');
      return null;
    } finally {
      setUploadingCover(false);
    }
  };

  const handleCreateBook = async () => {
    try {
      if (!user) {
        toast.error('Please log in to create a book');
        return;
      }

      setLoading(true);
      setShowProgress(true);
      setCreationProgress(0);
      setCreationStatus('Preparing to create your book...');
      
      console.log('Creating enhanced book with:', {
        title: bookTitle,
        book_type: bookType,
        tone_type: toneType,
        text_style: textStyle
      });

      // Step 1: Upload cover image if present
      let coverImageUrl = null;
      if (coverImage) {
        setCreationStatus('Uploading cover image...');
        setCreationProgress(10);
        coverImageUrl = await uploadCoverImage();
      }

      // Step 2: Create the book
      setCreationStatus('Creating book structure...');
      setCreationProgress(30);
      const book = await enhancedBookService.createBook({
        title: bookTitle,
        book_type: bookType,
        tone_type: toneType,
        text_style: textStyle,
        // categories removed - book types determine content automatically
        cover_image: coverImageUrl
      });
      
      toast.success('Book created successfully!');
      
      // Step 3: Generate chapters (content filtering is automatic based on book type)
      setCreationStatus('Generating chapters with AI...');
      setCreationProgress(75);
      await enhancedBookService.generateChapters(book.id);
      
      setCreationStatus('Finalizing your book...');
      setCreationProgress(95);
      
      // Short delay to show completion
      await new Promise(resolve => setTimeout(resolve, 500));
      setCreationProgress(100);
      setCreationStatus('Book completed successfully!');
      
      toast.success('Chapters generated successfully!');
      
      // Navigate to the book page
      router.push(`/book/creation/${book.id}`);
      onClose();
    } catch (error) {
      console.error('Error creating book:', error);
      setShowProgress(false);
      
      // Handle different types of errors with appropriate user messages
      if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError;
        const errorMessage = (axiosError.response?.data as any)?.message || '';
        
        // Check for "No messages found" error
        if (errorMessage.includes('No messages found')) {
          toast.error('No chat messages found! Please start chatting with Mr. White first to create a book from your conversations.');
        } else if (axiosError.response?.status === 500) {
          toast.error('Server error occurred. Please try again later.');
        } else if (axiosError.response?.status === 402) {
          toast.error('Insufficient credits to create book. Please check your account.');
        } else if (axiosError.response?.status === 401) {
          toast.error('Authentication failed. Please log in again.');
        } else {
          // Generic error message for other HTTP errors
          toast.error(errorMessage || 'Failed to create book. Please check your connection and try again.');
        }
      } else {
        toast.error('Failed to create book. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = () => {
    switch (step) {
      case 1:
        return (
          <div className="space-y-3 font-public-sans">
            <div>
              <Label htmlFor="book-title" className='mb-1 text-sm'>Book Title <span className="text-red-500">*</span></Label>
              <input 
                id="book-title" 
                value={bookTitle} 
                onChange={(e) => setBookTitle(e.target.value)}
                placeholder="Enter a title for your book"
                className="w-full bg-[#000000] border border-gray-700 rounded-sm py-2 pl-2 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] font-public-sans text-sm"
              />
            </div>
            
            <div>
              <Label htmlFor="book-type" className='mb-1 text-sm'>Book Type <span className="text-red-500">*</span></Label>
              <select
                id="book-type"
                value={bookType}
                onChange={(e) => setBookType(e.target.value)}
                className="w-full bg-[#000000] border border-gray-700 rounded-sm py-2 pl-2 pr-4 text-white focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] font-public-sans text-sm"
              >
                {BOOK_TYPE_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name} - {option.description}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-400 mt-1">
                Choose how your content will be organized
              </p>
            </div>
            
            <div>
              <Label className="text-sm">Cover Image <span className="text-red-500">*</span></Label>
              <div className="mt-1 space-y-2">
                {coverImagePreview ? (
                  <div className="relative w-full bg-gray-100 rounded-md overflow-hidden">
                    <img 
                      src={coverImagePreview} 
                      alt="Cover Preview" 
                      className="w-full h-auto object-contain max-h-48"
                    />
                    <button 
                      onClick={handleRemoveCoverImage}
                      className="absolute top-2 right-2 p-1 bg-red-500 rounded-full text-white"
                      type="button"
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div 
                    onClick={() => fileInputRef.current?.click()}
                    className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-gray-300 rounded-md cursor-pointer hover:bg-neutral-800"
                  >
                    <Image className="mb-1" size={24} />
                    <p className="text-xs text-gray-500">Click to upload cover image</p>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleCoverImageChange}
                  className="hidden"
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                <span className="text-red-500">*</span> Required fields
              </p>
            </div>
          </div>
        );
      
      case 2:
        return (
          <div className="space-y-4 font-public-sans">
            <div>
              <Label htmlFor="tone-type" className="mb-1 text-sm">Tone</Label>
              <CustomDropdown
                options={TONE_OPTIONS}
                value={toneType}
                onChange={(value) => setToneType(value)}
                placeholder="Select tone"
                label=""
              />
            </div>
            
            <div>
              <Label htmlFor="text-style" className="mb-1 text-sm">Text Style</Label>
              <CustomDropdown
                options={TEXT_STYLE_OPTIONS}
                value={textStyle}
                onChange={(value) => setTextStyle(value)}
                placeholder="Select text style"
                label=""
              />
            </div>
          </div>
        );
      
      case 3:
        return (
          <div className="space-y-4 font-public-sans">
            {showProgress ? (
              <BookCreationProgress 
                progress={creationProgress} 
                status={creationStatus} 
              />
            ) : (
              <>
                <h3 className="text-base font-medium">Summary</h3>
                
                <div className="space-y-1.5 text-sm">
                  <div>
                    <span className="font-medium">Title:</span> {bookTitle}
                  </div>
                  
                  <div>
                    <span className="font-medium">Cover Image:</span>
                    <div className="w-full h-16 mt-1 bg-gray-100 rounded-md overflow-hidden">
                      <img 
                        src={coverImagePreview || ''}
                        alt="Cover Preview" 
                        className="w-full h-full object-cover"
                      />
                    </div>
                  </div>
                  
                  <div>
                    <span className="font-medium">Book Type:</span> {BOOK_TYPE_OPTIONS.find(t => t.id === bookType)?.name}
                  </div>
                  
                  <div>
                    <span className="font-medium">Tone:</span> {TONE_OPTIONS.find(t => t.id === toneType)?.name}
                  </div>
                  
                  <div>
                    <span className="font-medium">Text Style:</span> {TEXT_STYLE_OPTIONS.find(s => s.id === textStyle)?.name}
                  </div>
                </div>
                
                <p className="text-xs text-gray-500">
                  Click 'Create Book' to generate your enhanced book. This may take a few moments.
                </p>
              </>
            )}
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose} modal={true}>
      <DialogContent className="sm:max-w-lg w-[95vw] max-w-[95vw] custom-scrollbar sm:w-full max-h-[90vh] overflow-y-auto mx-2" onPointerDownOutside={(e) => e.preventDefault()}>
        <DialogHeader>
          <DialogTitle className="font-work-sans">Create Your Book</DialogTitle>
        </DialogHeader>
        
        <div className="py-3 font-public-sans">
          <div className="flex items-center justify-center mb-4 mt-1 overflow-x-auto">
            <div className="flex items-center">
              {[1, 2, 3].map((s, index) => (
                <React.Fragment key={s}>
                  <div 
                    className={`flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 rounded-full border-2 ${
                      s < step || s === step ? 'border-green-500' : 'border-gray-300'
                    } ${
                      s < step || s === step ? 'bg-green-500 text-white' : 'bg-transparent text-gray-500'
                    } font-medium text-sm`}
                  >
                    {s}
                  </div>
                  {index < 2 && (
                    <div className={`h-0.5 w-8 sm:w-16 ${s < step ? 'bg-green-500' : 'bg-gray-300'}`} />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
          
          {renderStepContent()}
        </div>
        
        <DialogFooter className="flex flex-col sm:flex-row gap-2 sm:justify-between">
          <Button
            variant="outline"
            onClick={step === 1 ? onClose : handlePrevStep}
            disabled={loading || showProgress}
            className="font-public-sans cursor-pointer w-full sm:w-auto"
          >
            {step === 1 ? 'Cancel' : 'Back'}
          </Button>
          
          <Button
            onClick={step === 3 ? handleCreateBook : handleNextStep}
            disabled={loading || (showProgress && step === 3)}
            className="font-public-sans cursor-pointer w-full sm:w-auto"
          >
            {loading && !showProgress ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {step === 3 ? 'Creating...' : 'Processing...'}
              </>
            ) : (
              step === 3 ? 'Create Book' : 'Next'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
} 