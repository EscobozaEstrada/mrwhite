import { useState, useEffect } from 'react';

/**
 * Custom hook for creating an image carousel effect
 * @param images Array of image paths to cycle through
 * @param interval Time in milliseconds between image changes (default: 5001ms)
 * @returns Current image index
 */
export const useImageCarousel = (images: string[], interval: number = 5001) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentIndex(prevIndex => (prevIndex + 1) % images.length);
    }, interval);

    return () => clearInterval(timer);
  }, [images.length, interval]);

  return currentIndex;
}; 