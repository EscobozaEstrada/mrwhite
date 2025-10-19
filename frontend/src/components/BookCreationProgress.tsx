'use client';

import React from 'react';
import { Progress } from '@/components/ui/progress';
import { Sparkles, BookOpen, CheckCircle2 } from 'lucide-react';

interface BookCreationProgressProps {
  progress: number;
  status: string;
}

const BookCreationProgress: React.FC<BookCreationProgressProps> = ({ progress, status }) => {
  return (
    <div className="w-full py-4 space-y-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xl font-medium">{progress}%</span>
        {progress < 100 ? (
          <Sparkles className="h-5 w-5 animate-pulse text-yellow-500" />
        ) : (
          <CheckCircle2 className="h-5 w-5 text-green-500" />
        )}
      </div>
      
      <Progress 
        value={progress} 
        className="h-3 bg-neutral-800 rounded-full" 
        indicatorClassName={`bg-gradient-to-r ${
          progress < 100 
            ? 'from-blue-500 to-green-500' 
            : 'from-green-500 to-green-400'
        } transition-all duration-500`}
      />
      
      <div className="flex items-center justify-center space-x-2 mt-3">
        <BookOpen className={`h-4 w-4 ${progress < 100 ? 'animate-pulse text-blue-400' : 'text-green-500'}`} />
        <p className="text-sm text-center text-gray-300">{status}</p>
      </div>
    </div>
  );
};

export default BookCreationProgress; 