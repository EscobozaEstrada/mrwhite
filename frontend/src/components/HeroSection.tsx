"use client"

import { useImageCarousel } from '@/utils/imageCarousel';

interface HeroSectionProps {
  title: string;
  subtitle: string;
  images: string[];
  height?: string;
}

const HeroSection = ({ title, subtitle, images, height = "h-[250px] md:h-[400px]" }: HeroSectionProps) => {
  const currentBgIndex = useImageCarousel(images);

  return (
    <section className={`${height} flex flex-col justify-center items-center w-full relative overflow-hidden`}>
      {/* Background Images */}
      <div className="absolute inset-0 w-full h-full">
        {images.map((image, index) => (
          <div 
            key={index}
            className={`absolute inset-0 bg-cover bg-center transition-opacity duration-1000 ease-in-out`}
            style={{ 
              backgroundImage: `url('${image}')`,
              opacity: currentBgIndex === index ? 1 : 0 
            }}
          />
        ))}
      </div>
      <div className="absolute inset-0 bg-black/40 z-10"></div>
      <div className="z-20 px-4 text-center">
        <h1 className="text-[28px] md:text-[40px] font-work-sans font-semibold text-center">{title}</h1>
        <p className="text-[16px] md:text-[20px] font-public-sans font-light text-center">{subtitle}</p>
      </div>
    </section>
  );
};

export default HeroSection; 