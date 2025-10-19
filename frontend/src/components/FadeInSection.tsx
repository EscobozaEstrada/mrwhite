'use client';

import { useRef } from 'react';
import { motion, useScroll, useTransform } from "motion/react";
import { useEffect } from 'react';

interface Props {
  children: React.ReactNode;
  className?: string;
}

export default function FadeInSection({ children, className }: Props) {
  const ref = useRef(null);
  // Track this element's position as it moves through the viewport
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"]
  });
  
  // Transform scroll progress to opacity
  const opacity = useTransform(
    scrollYProgress,
    [0, 0.3, 0.6, 1], // scroll progress points
    [0, 0.3, 0.8, 1]   // opacity values at each point
  );

  return (
    <motion.div
      ref={ref}
      style={{ opacity }}
      className={className}
    >
      {children}
    </motion.div>
  );
}