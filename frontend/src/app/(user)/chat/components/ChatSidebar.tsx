"use client";

import { useState, useEffect, useRef } from "react";
import { FiPlus, FiTrash2, FiDownload, FiEdit2 } from "react-icons/fi";
import { IoBook, IoStarSharp } from "react-icons/io5";
import { FaPaw, FaCrown } from "react-icons/fa";
import { ChevronDown, Trash2 } from "lucide-react";
import { FaBook } from "react-icons/fa";
import { FaCirclePlus } from "react-icons/fa6";
import DogFormDialog from "./DogFormDialog";
import EnhancedBookCreationModal from "@/components/EnhancedBookCreationModal";
import { enhancedBookService } from '@/services/enhancedBookService';
import { EnhancedBook } from '@/types/enhanced-book';
import { useRouter } from 'next/navigation';
import { Skeleton } from "@/components/ui/skeleton";
import toast from '@/components/ui/sound-toast';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from "@/components/ui/button";
import { listDogProfiles, createDogProfile, updateDogProfile, deleteDogProfile, uploadDogImage, uploadVetReport, DogProfile } from "@/services/dogProfileApi";

interface Dog {
  id: number;
  name: string;
  breed?: string;
  age?: number;
  dateOfBirth?: string;
  weight?: number;
  gender?: string;
  color?: string;
  additionalDetails?: string;
  image?: string;
  vetReport?: File;
}

interface ChatSidebarProps {
  onDogAdded?: (dogName: string, dogId: number) => void;
  onDogEdited?: (dogName: string, dogId: number, changes: string[]) => void;
  onDogDeleted?: (dogName: string) => void;
}

export default function ChatSidebar({ onDogAdded, onDogEdited, onDogDeleted }: ChatSidebarProps) {
  const router = useRouter();
  const [dogs, setDogs] = useState<Dog[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingDog, setEditingDog] = useState<Dog | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEnhancedBookModalOpen, setIsEnhancedBookModalOpen] = useState(false);
  
  // Book dropdown states
  const [bookDropdownOpen, setBookDropdownOpen] = useState(false);
  const [userBooks, setUserBooks] = useState<EnhancedBook[]>([]);
  const [loadingBooks, setLoadingBooks] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [bookToDelete, setBookToDelete] = useState<EnhancedBook | null>(null);
  const [deleting, setDeleting] = useState(false);
  const bookDropdownRef = useRef<HTMLDivElement>(null);

  // Load dogs from API on mount
  useEffect(() => {
    loadDogs();
  }, []);

  const loadDogs = async () => {
    try {
      setLoading(true);
      const response = await listDogProfiles();
      const mappedDogs = response.dogs.map((dog: DogProfile) => ({
        id: dog.id,
        name: dog.name,
        breed: dog.breed,
        age: dog.age,
        dateOfBirth: dog.date_of_birth,
        weight: dog.weight,
        gender: dog.gender,
        color: dog.color,
        additionalDetails: dog.comprehensive_profile?.additionalDetails,
        image: dog.image_url,
      }));
      setDogs(mappedDogs);
    } catch (error) {
      console.error("Failed to load dogs:", error);
      // Keep empty array on error
    } finally {
      setLoading(false);
    }
  };

  const handleAddDog = async (dogData: any) => {
    try {
      let imageUrl = undefined;
      let imageDescription = undefined;
      
      if (dogData.image) {
        console.log("📸 Uploading image and generating description...");
        const imageUploadResponse = await uploadDogImage({
          image_data: dogData.image,
          dog_name: dogData.name,
          breed: dogData.breed,
          age: dogData.age ? parseInt(dogData.age) : undefined,
          gender: dogData.gender,
          color: dogData.color
        });
        
        imageUrl = imageUploadResponse.image_url;
        imageDescription = imageUploadResponse.image_description;
        console.log("✅ Image uploaded and analyzed!");
      }
      
      let dogId: number;
      
      if (editingDog) {
        const updateData = {
          name: dogData.name,
          breed: dogData.breed || undefined,
          age: dogData.age ? parseInt(dogData.age) : undefined,
          date_of_birth: dogData.dateOfBirth || undefined,
          weight: dogData.weight ? parseFloat(dogData.weight) : undefined,
          gender: dogData.gender || undefined,
          color: dogData.color || undefined,
          image_url: imageUrl,
          image_description: imageDescription,
          comprehensive_profile: dogData.additionalDetails ? {
            additionalDetails: dogData.additionalDetails
          } : undefined
        };
        
        await updateDogProfile(editingDog.id, updateData);
        dogId = editingDog.id;
        setEditingDog(null);
      } else {
        const createData = {
          name: dogData.name,
          breed: dogData.breed || undefined,
          age: dogData.age ? parseInt(dogData.age) : undefined,
          date_of_birth: dogData.dateOfBirth || undefined,
          weight: dogData.weight ? parseFloat(dogData.weight) : undefined,
          gender: dogData.gender || undefined,
          color: dogData.color || undefined,
          image_url: imageUrl,
          image_description: imageDescription,
          comprehensive_profile: dogData.additionalDetails ? {
            additionalDetails: dogData.additionalDetails
          } : undefined
        };
        
        const newDog = await createDogProfile(createData);
        dogId = newDog.id;
      }
      
      // Upload vet report if provided (wait for completion before closing dialog)
      if (dogData.vetReport) {
        console.log("📋 Uploading vet report...");
        try {
          // Convert file to base64
          const fileData = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target?.result as string);
            reader.onerror = reject;
            reader.readAsDataURL(dogData.vetReport);
          });
          
          await uploadVetReport({
            dog_id: dogId,
            file_data: fileData,
            filename: dogData.vetReport.name,
            content_type: dogData.vetReport.type || 'application/pdf'
          });
          console.log("✅ Vet report uploaded and processed!");
        } catch (error) {
          console.error("Failed to upload vet report:", error);
          toast.error("Dog profile saved, but vet report upload failed. You can try uploading it again later.");
        }
      }
      
      await loadDogs();
      setIsDialogOpen(false);
      
      // Call appropriate callback
      if (editingDog) {
        // Dog was edited - determine what changed
        const changes: string[] = [];
        if (dogData.name !== editingDog.name) changes.push('name');
        if (dogData.breed !== editingDog.breed) changes.push('breed');
        if (dogData.age !== editingDog.age?.toString()) changes.push('age');
        if (dogData.dateOfBirth !== editingDog.dateOfBirth) changes.push('date of birth');
        if (dogData.weight !== editingDog.weight?.toString()) changes.push('weight');
        if (dogData.gender !== editingDog.gender) changes.push('gender');
        if (dogData.color !== editingDog.color) changes.push('color');
        if (dogData.additionalDetails !== editingDog.additionalDetails) changes.push('additional details');
        if (dogData.image) changes.push('photo');
        if (dogData.vetReport) changes.push('vet report');
        
        onDogEdited?.(dogData.name, dogId, changes);
      } else {
        // New dog was added
        onDogAdded?.(dogData.name, dogId);
      }
    } catch (error) {
      console.error("Failed to save dog:", error);
      toast.error("Failed to save dog profile. Please try again.");
    }
  };

  const handleEditDog = (dog: Dog) => {
    setEditingDog(dog);
    setIsDialogOpen(true);
  };

  const handleDeleteDog = async (id: number) => {
    const dog = dogs.find(d => d.id === id);
    const dogName = dog?.name || "this dog";
    
    if (!confirm(`Are you sure you want to delete ${dogName}'s profile? This action cannot be undone.`)) {
      return;
    }
    
    try {
      const response = await deleteDogProfile(id);
      
      toast.success(`${dogName}'s profile has been deleted successfully. The chatbot will no longer reference ${dogName} in future responses.`);
      
      // Reload dogs from API
      await loadDogs();
      
      // Call deletion callback
      onDogDeleted?.(dogName);
    } catch (error) {
      console.error("Failed to delete dog:", error);
      toast.error("Failed to delete dog profile. Please try again.");
    }
  };

  const handleCloseDialog = () => {
    setIsDialogOpen(false);
    setEditingDog(null);
  };

  const handleDownloadConversation = () => {
    // TODO: Implement download functionality
    console.log("Download conversation");
  };

  // Close book dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (bookDropdownRef.current && !bookDropdownRef.current.contains(event.target as Node)) {
        setBookDropdownOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  // Fetch user books when dropdown is opened
  useEffect(() => {
    if (bookDropdownOpen && userBooks.length === 0) {
      fetchUserBooks();
    }
  }, [bookDropdownOpen]);

  const fetchUserBooks = async () => {
    try {
      setLoadingBooks(true);
      const books = await enhancedBookService.getUserBooks();
      setUserBooks(books);
    } catch (error) {
      console.error('Error fetching user books:', error);
    } finally {
      setLoadingBooks(false);
    }
  };

  const handleCreateBook = () => {
    setIsEnhancedBookModalOpen(true);
    setBookDropdownOpen(false);
  };

  const navigateToBook = (bookId: number) => {
    router.push(`/book/creation/${bookId}`);
    setBookDropdownOpen(false);
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
    <>
      <div className="w-80 bg-[#1a1a1a] border-r border-gray-800 flex flex-col">
        {/* My Dogs Section */}
        <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
          <div className="mb-4">
            <h2 className="text-lg font-semibold mb-3 flex items-center">
              <FaPaw className="mr-2" size={20} />
              My Dogs
            </h2>

            {/* Dog List */}
            <div className="space-y-2">
              {loading ? (
                <div className="text-center py-4 text-gray-400">
                  Loading dogs...
                </div>
              ) : dogs.length === 0 ? (
                <div className="text-center py-4 text-gray-400">
                  No dogs added yet. Click "Add More Dogs" to get started!
                </div>
              ) : (
                dogs.map((dog) => (
                <div
                  key={dog.id}
                  className="flex items-center justify-between bg-[#2a2a2a] rounded-lg p-3 hover:bg-[#333333] transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    {/* Dog Image */}
                    <div className="w-10 h-10 rounded-full bg-[#333333] flex items-center justify-center overflow-hidden">
                      {dog.image ? (
                        <img src={dog.image} alt={dog.name} className="w-full h-full object-cover" />
                      ) : (
                        <FaPaw className="text-gray-400" size={18} />
                      )}
                    </div>
                    {/* Dog Name */}
                    <span className="font-medium">{dog.name}</span>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center space-x-1">
                    {/* Edit Button */}
                    <button
                      onClick={() => handleEditDog(dog)}
                      className="p-2 hover:bg-blue-500 cursor-pointer rounded-md transition-colors"
                      aria-label="Edit dog"
                    >
                      <FiEdit2 size={16} />
                    </button>
                    
                    {/* Delete Button */}
                    <button
                      onClick={() => handleDeleteDog(dog.id)}
                      className="p-2 hover:bg-red-500 cursor-pointer rounded-md transition-colors"
                      aria-label="Delete dog"
                    >
                      <FiTrash2 size={16} />
                    </button>
                  </div>
                </div>
              ))
              )}
            </div>

            {/* Add More Dogs Button */}
            <button
              onClick={() => setIsDialogOpen(true)}
              className="w-full mt-3 flex cursor-pointer items-center justify-center space-x-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg p-3 transition-colors font-medium"
            >
              <FiPlus size={20} />
              <span>Add More Dogs</span>
            </button>
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="p-4 border-t border-gray-800 space-y-3">
          

          {/* Generate Book Button */}
          <div className="relative w-full" ref={bookDropdownRef}>
            <button 
              onClick={() => setBookDropdownOpen(!bookDropdownOpen)}
              className="w-full flex items-center justify-center space-x-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg p-3 transition-colors font-medium cursor-pointer"
            >
              <IoBook size={20} />
              <span>Generate Book</span>
              <ChevronDown className={`w-4 h-4 transition-transform ${bookDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {bookDropdownOpen && (
              <div className="absolute z-50 bottom-full mb-2 w-full rounded-md shadow-lg bg-neutral-800 ring-1 ring-black ring-opacity-5 focus:outline-none">
                <div className="py-1" role="menu">
                  <button
                    onClick={handleCreateBook}
                    className="block w-full text-left px-4 py-2 text-sm cursor-pointer text-white hover:bg-neutral-700"
                    role="menuitem"
                  >
                    <FaCirclePlus className="w-4 h-4 inline-block mr-2 text-purple-500" />
                    Create New Book
                  </button>
                  
                  {loadingBooks && (
                    <div className="px-4 py-2 space-y-2">
                      <Skeleton className="h-4 w-full bg-neutral-700" />
                      <Skeleton className="h-4 w-3/4 bg-neutral-700" />
                    </div>
                  )}

                  {userBooks.length > 0 && (
                    <>
                      <div className="border-t border-neutral-700"></div>
                      <div className="px-4 py-1 text-xs text-neutral-400">Your Books</div>
                      <div className="max-h-[200px] overflow-y-auto">
                        {userBooks.map((book) => (
                          <div
                            key={book.id}
                            className="flex items-center justify-between px-4 py-2 text-sm text-white hover:bg-neutral-700 cursor-pointer"
                          >
                            <div 
                              className="flex items-center flex-1 truncate"
                              onClick={() => navigateToBook(book.id)}
                            >
                              <FaBook className="w-3 h-3 inline-block mr-2 text-purple-500 flex-shrink-0" />
                              <span className="truncate">{book.title}</span>
                            </div>
                            <button
                              onClick={(e) => openDeleteDialog(e, book)}
                              className="text-red-500 hover:text-red-400 ml-2 flex-shrink-0"
                              aria-label={`Delete ${book.title}`}
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </>
                  )}

                  {userBooks.length === 0 && !loadingBooks && (
                    <div className="px-4 py-2 text-sm text-neutral-400">No books found</div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Download Conversation */}
          {/* <button
            onClick={handleDownloadConversation}
            className="w-full flex items-center justify-center space-x-2 bg-[#2a2a2a] hover:bg-[#333333] text-gray-300 rounded-lg p-3 transition-colors"
          >
            <FiDownload size={18} />
            <span>Download Conversation</span>
          </button> */}

          {/* Elite Plan Button */}
          <button className="w-full flex cursor-pointer items-center justify-center space-x-2 bg-gradient-to-r from-[#D3B86A] to-yellow-600 hover:from-yellow-600 hover:to-yellow-700 text-white rounded-lg p-3 transition-all font-medium">
            <FaCrown size={20} />
            <span>Elite Plan</span>
          </button>

          {/* Credits Display */}
          {/* <div className="flex items-center justify-center space-x-2 text-sm text-gray-500 mt-2">
            <IoStarSharp className="text-yellow-500" size={16} />
            <span>{creditsRemaining.toLocaleString()} credits</span>
          </div> */}
        </div>
      </div>

      {/* Dog Form Dialog */}
      <DogFormDialog
        isOpen={isDialogOpen}
        onClose={handleCloseDialog}
        onSubmit={handleAddDog}
        initialData={editingDog ? {
          name: editingDog.name,
          breed: editingDog.breed || "",
          age: editingDog.age?.toString() || "",
          dateOfBirth: editingDog.dateOfBirth || "",
          weight: editingDog.weight?.toString() || "",
          gender: editingDog.gender || "",
          color: editingDog.color || "",
          additionalDetails: editingDog.additionalDetails,
          image: editingDog.image,
          vetReport: editingDog.vetReport,
        } : null}
      />

      {/* Enhanced Book Creation Modal */}
      <EnhancedBookCreationModal
        isOpen={isEnhancedBookModalOpen}
        onClose={() => setIsEnhancedBookModalOpen(false)}
        conversationId={undefined}
      />

      {/* Delete Book Confirmation Dialog */}
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
    </>
  );
}

