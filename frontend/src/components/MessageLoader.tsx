import React from 'react';
import { Heart } from 'lucide-react';

interface MessageLoaderProps {
  healthMode?: boolean;
}

const MessageLoader: React.FC<MessageLoaderProps> = ({ healthMode = false }) => {
  return (
    <div className="flex items-start gap-4 bg-neutral-900 p-4 sm:p-6 rounded-lg w-full sm:w-1/2">
      <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
        <span className="text-lg sm:text-xl font-semibold">AI</span>
      </div>
      <div className="flex-1 space-y-3 sm:space-y-4">
        <div className="flex items-center gap-2">
          <div className="h-4 sm:h-5 w-20 sm:w-24 bg-white/10 rounded animate-pulse"></div>
          {healthMode && (
            <div className="flex items-center gap-1 text-red-400 text-xs">
              <Heart className="w-3 h-3 fill-current animate-pulse" />
              <span>Health AI</span>
            </div>
          )}
        </div>
        <div className="space-y-1.5 sm:space-y-2">
          <div className="h-3 sm:h-4 w-full bg-white/10 rounded animate-pulse"></div>
          <div className="h-3 sm:h-4 w-5/6 bg-white/10 rounded animate-pulse"></div>
          <div className="h-3 sm:h-4 w-3/4 bg-white/10 rounded animate-pulse"></div>
          <div className="h-3 sm:h-4 w-4/5 bg-white/10 rounded animate-pulse"></div>
        </div>
      </div>
    </div>
  );
};

export default MessageLoader;