import React from 'react';
import { Heart } from 'lucide-react';
import Image from 'next/image';

interface MessageLoaderProps {
  healthMode?: boolean;
}

const MessageLoader: React.FC<MessageLoaderProps> = ({ healthMode = false }) => {
  return (
    <div className="flex items-start gap-5   p-6 sm:p-8 rounded-2xl w-full sm:w-1/2  ">
      <Image src="/assets/logo.png" className="animate-spin" alt="Message Loader" width={40} height={40} />
      
      <div className="flex-1 space-y-4 sm:space-y-5">
        {/* Header with typing indicator */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="h-5 sm:h-6 w-24 sm:w-28 bg-gradient-to-r from-white/8 to-white/5 rounded-lg overflow-hidden">
              <div className="h-full w-full bg-gradient-to-r from-transparent via-white/10 to-transparent animate-wave"></div>
            </div>
          </div>
          
          
          {healthMode && (
            <div className="flex items-center gap-1.5 text-rose-400 text-xs font-medium">
              <Heart className="w-3.5 h-3.5 fill-current animate-pulse" />
              <span className="tracking-wide">Health AI</span>
            </div>
          )}
        </div>
        
        {/* Content skeleton with staggered wave animation */}
        <div className="space-y-3 sm:space-y-3.5">
          {[
            { width: 'w-full', delay: '0s' },
            { width: 'w-11/12', delay: '0.1s' },
            { width: 'w-4/5', delay: '0.2s' },
            { width: 'w-5/6', delay: '0.3s' }
          ].map((item, index) => (
            <div key={index} className="relative">
              <div className={`h-4 sm:h-4.5 ${item.width} bg-gradient-to-r from-white/6 to-white/3 rounded-lg overflow-hidden`}>
                <div 
                  className="h-full w-full bg-gradient-to-r from-transparent via-white/8 to-transparent animate-wave"
                  style={{ animationDelay: item.delay }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MessageLoader;