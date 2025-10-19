import React from 'react';
import Sidebar from '@/components/Sidebar';
import BookGenerator from '@/components/BookGenerator';

interface BookGeneratorSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const BookGeneratorSidebar: React.FC<BookGeneratorSidebarProps> = ({ isOpen, onClose }) => {
  return (
    <Sidebar
      isOpen={isOpen}
      onClose={onClose}
      title="Generate Book"
      isBookGenerated={true}
    >
      <BookGenerator isOpen={isOpen} onClose={onClose} />
    </Sidebar>
  );
};

export default BookGeneratorSidebar; 