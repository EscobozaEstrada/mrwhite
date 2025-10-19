'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Sparkles, ChevronDown, Trash2 } from "lucide-react";
import { useRouter } from 'next/navigation';
import { enhancedBookService } from '@/services/enhancedBookService';
import { EnhancedBook } from '@/types/enhanced-book';
import { FaCirclePlus } from 'react-icons/fa6';
import { FaBook } from 'react-icons/fa';
import { Skeleton } from "@/components/ui/skeleton";
import toast from '@/components/ui/sound-toast';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { RiBook2Line } from 'react-icons/ri';

interface EnhancedBookDropdownProps {
  openUploadModal: (type: 'file' | 'image' | 'book-generator' | 'enhanced-book-generator') => void;
}

const EnhancedBookDropdown: React.FC<EnhancedBookDropdownProps> = ({ openUploadModal }) => {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [userBooks, setUserBooks] = useState<EnhancedBook[]>([]);
  const [loading, setLoading] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [bookToDelete, setBookToDelete] = useState<EnhancedBook | null>(null);
  const [deleting, setDeleting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Fetch user books when dropdown is opened
  useEffect(() => {
    if (dropdownOpen && userBooks.length === 0) {
      fetchUserBooks();
    }
  }, [dropdownOpen]);

  const fetchUserBooks = async () => {
    try {
      setLoading(true);
      const books = await enhancedBookService.getUserBooks();
      setUserBooks(books);
    } catch (error) {
      console.error('Error fetching user books:', error);
    } finally {
      setLoading(false);
    }
  };

  const navigateToBook = (bookId: number) => {
    router.push(`/book/creation/${bookId}`);
    setDropdownOpen(false);
  };

  const handleCreateBook = () => {
    openUploadModal('enhanced-book-generator');
    setDropdownOpen(false);
  };

  const openDeleteDialog = (e: React.MouseEvent, book: EnhancedBook) => {
    e.stopPropagation();
    setBookToDelete(book);
    setDeleteDialogOpen(true);
  };

  const handleDeleteBook = async () => {
    if (!bookToDelete) return;
    
    setDeleting(true);
    try {
      await enhancedBookService.deleteBook(bookToDelete.id);
      setUserBooks(books => books.filter(book => book.id !== bookToDelete.id));
      toast.success('Book deleted successfully');
      setDeleteDialogOpen(false);
    } catch (error) {
      console.error('Error deleting book:', error);
      toast.error('Failed to delete book');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="relative flex-shrink-0" ref={dropdownRef}>
      <Button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        className="font-public-sans font-light  flex items-center gap-1 lg:gap-2 text-white p-1 md:p-2 lg:p-3"
        variant="ghost"
      >
        <RiBook2Line className="w-4 h-4" />
        <span className="hidden sm:inline">Generate Book</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
      </Button>

      {dropdownOpen && (
        <div className="absolute z-50 font-public-sans overflow-hidden mt-2 min-w-[180px] w-56 max-w-[90vw] sm:max-w-none rounded-md shadow-lg bg-neutral-900 ring-1 ring-black ring-opacity-5 focus:outline-none right-0 sm:right-auto">
          <div className="" role="menu" aria-orientation="vertical" aria-labelledby="options-menu">
            <button
              onClick={handleCreateBook}
              className="block w-full text-left px-4 py-2 text-sm cursor-pointer text-white hover:bg-neutral-800"
              role="menuitem"
            >
                <FaCirclePlus className="w-4 h-4 inline-block mr-2 text-[var(--mrwhite-primary-color)]" />
              Create New Book
            </button>
            
            {loading && (
              <div className="px-4 py-2 space-y-2">
                <Skeleton className="h-4 w-full bg-neutral-800" />
                <Skeleton className="h-4 w-3/4 bg-neutral-800" />
                <Skeleton className="h-4 w-full bg-neutral-800" />
                <Skeleton className="h-4 w-3/4 bg-neutral-800" />
              </div>
            )}

            {userBooks.length > 0 && (
              <>
                <div className="border-t border-neutral-800"></div>
                <div className="px-4 py-1 text-xs text-neutral-500">Your Books</div>
                <div className="overflow-y-auto max-h-[40vh] sm:max-h-[20vh] custom-scrollbar">
                {userBooks.map((book) => (
                  <div
                    key={book.id}
                    className="flex items-center justify-between px-4 py-2 text-sm text-white hover:bg-neutral-800 cursor-pointer"
                  >
                    <div 
                      className="flex items-center truncate"
                      onClick={() => navigateToBook(book.id)}
                    >
                      <FaBook className="w-3 h-3 inline-block mr-2 text-[var(--mrwhite-primary-color)]" />
                      <span className="truncate">{book.title}</span>
                    </div>
                    <button
                      onClick={(e) => openDeleteDialog(e, book)}
                      className="text-red-500 hover:text-red-400 ml-2"
                      aria-label={`Delete ${book.title}`}
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                </div>
              </>
            )}

            {userBooks.length === 0 && !loading && (
              <div className="px-4 py-2 text-sm text-neutral-500">No books found</div>
            )}
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Delete Book</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>Are you sure you want to delete "{bookToDelete?.title}"?</p>
            <p className="text-sm text-muted-foreground mt-2">This action cannot be undone.</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleDeleteBook} 
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EnhancedBookDropdown; 