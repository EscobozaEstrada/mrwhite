import { useState, useEffect, useRef } from 'react';
import ImagePop from '@/components/ImagePop';
import Image from 'next/image';

export interface Testimonial {
  name: string;
  location: string;
  rating: number;
  text: string;
  image: string;
}

interface TestimonialSliderProps {
  testimonials: Testimonial[];
  autoplaySpeed?: number;
  className?: string;
}

export default function TestimonialSlider({
  testimonials,
  autoplaySpeed = 5001,
  className = ''
}: TestimonialSliderProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isPaused && testimonials.length > 1) {
      intervalRef.current = setInterval(() => {
        setCurrentIndex(prevIndex => (prevIndex + 1) % testimonials.length);
      }, autoplaySpeed);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isPaused, testimonials.length, autoplaySpeed]);

  const handleMouseEnter = () => {
    setIsPaused(true);
  };

  const handleMouseLeave = () => {
    setIsPaused(false);
  };

  const renderStars = (rating: number) => {
    return '⭐'.repeat(rating);
  };

  return (
    <div
      className={`w-full relative max-[768px]:block max-[947px]:hidden max-[1074px]:h-[100px] bg-gradient-to-t from-white/10 to-[--background] max-[768px]:mt-20 max-[550px]:mt-30 p-4 ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    // style={{ minHeight: '160px' }}
    >
      {testimonials.map((testimonial, index) => (
        <div
          key={index}
          className={`w-full left-0 bottom-0 absolute p-4 transition-opacity duration-500 ${index === currentIndex ? 'opacity-100 z-10' : 'opacity-0 z-0'
            }`}
        >
          <div className="w-full flex items-center justify-between gap-4">
            <div className="w-16 h-16 max-[768px]:w-16 max-[768px]:h-16 max-[1074px]:w-8 max-[1074px]:h-8 max-[1200px]:w-12 max-[1200px]:h-12 relative">
              <Image
                src={testimonial.image}
                alt={`${testimonial.name} profile picture`}
                fill
                className="object-cover"
              />
            </div>
            <div className="flex-1 flex flex-col justify-between">
              <p className="font-semibold max-[1074px]:text-[12px] max-[1200px]:text-[16px] text-[20px]/6 truncate max-[768px]:text-[20px]/6">{testimonial.name}</p>
              <div className="truncate">
                <p className="text-[16px] max-[768px]:text-[16px] max-[1074px]:text-[12px] font-light">{testimonial.location} | {renderStars(testimonial.rating)}</p>
              </div>
            </div>
          </div>
          <div className="w-full tracking-tight mt-4 max-[1074px]:mt-2">
            <p className="text-[20px] max-[768px]:text-[20px] max-[1074px]:text-[12px] italic font-light max-[1200px]:text-[16px]">
              "{testimonial.text}"
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}