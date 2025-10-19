'use client';

import { useRef, useEffect } from 'react';
import { motion, useAnimation, useInView } from 'framer-motion';
import { PiBoneFill } from 'react-icons/pi';

type ShakingIconProps = {
  icon: React.ReactNode;
}

export default function ShakingIcon({ icon}: ShakingIconProps) {
  const iconRef = useRef(null);
  const inView = useInView(iconRef, { once: false, amount: 0.5 });
  const controls = useAnimation();

  useEffect(() => {
    if (inView) {
      controls.start('shake');
    }
  }, [inView, controls]);

  const circularShake = {
    initial: { rotate: 0, x: 0, y: 0 },
    shake: {
      rotate: [0, 10, -10, 8, -8, 5, -5, 0],
      x: [0, 1, -1, 1, -1, 0.5, -0.5, 0],
      y: [0, -1, 1, -1, 1, -0.5, 0.5, 0],
      transition: { duration: 0.8, ease: 'easeInOut' },
    },
  };

  return (
    <motion.span
      ref={iconRef}
      variants={circularShake}
      initial="initial"
      animate={controls}
      className="text-xl inline-block"
    >
      {icon}
    </motion.span>
  );
}