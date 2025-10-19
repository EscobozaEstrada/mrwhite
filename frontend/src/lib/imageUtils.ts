import { ImageProps } from "next/image";

export type OptimizedImageProps = Omit<ImageProps, 'alt'> & {
  alt: string;
  priority?: boolean;
};

/**
 * Helper function to optimize images for SEO
 * - Ensures alt text is always provided
 * - Sets loading strategy based on priority
 * - Adds appropriate sizes attribute
 */
export function optimizeImage(props: OptimizedImageProps): ImageProps {
  const { priority = false, sizes = '100vw', ...rest } = props;

  return {
    ...rest,
    priority,
    loading: priority ? undefined : 'lazy',
    sizes,
    alt: props.alt || '',
  };
}

/**
 * Generate image metadata for structured data
 */
export function generateImageMetadata(
  src: string,
  width: number = 1200,
  height: number = 630,
  alt: string = 'Mr. White - AI Dog Care Assistant'
) {
  const baseUrl = process.env.NEXT_PUBLIC_FRONTEND_URL || 'https://mrwhiteaidogbuddy.com/';
  const fullSrc = src.startsWith('http') ? src : `${baseUrl}${src}`;

  return {
    url: fullSrc,
    width,
    height,
    alt,
  };
} 