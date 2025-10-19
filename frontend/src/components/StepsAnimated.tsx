'use client';

import { useEffect, useRef } from 'react';
import { motion, useAnimation, useInView } from 'framer-motion';

const steps = [
  {
    title: 'Sign Up',
    description:
      'Create your account in moments—join the Companion Crew for free or the Elite Pack as a full member—to start your journey with Mr. White and your companion.',
  },
  {
    title: 'Choose Your Subscription',
    description:
      'Discover your personal portal with two plans: the free Companion Crew and the Elite Pack Premium. The Companion Crew offers 24/7 tailored guidance, wisdom, and a history of your dog queries. Upgrade to the Elite Pack to unlock the Legacy of Love Living Hub—a unique, AI-powered space to to honor your dog’s life and keep their care organized with ease.',
  },
  {
    title: 'Access Your Personal Portal',
    description:
      'Step into your personal portal with Mr. White, where tailored guidance, records, and wisdom for you and your dog are available 24/7.',
  },
];

interface StepsAnimatedProps {
  direction: 'flex-col' | 'flex-row';
  background: string;
  className?: string;
}

export default function StepsAnimated({ direction, background, className = '' }: StepsAnimatedProps) {
  const containerRef = useRef(null);
  const inView = useInView(containerRef, { once: true, amount: 0.3 });
  const controls = useAnimation();

  useEffect(() => {
    if (inView) controls.start('visible');
  }, [inView, controls]);

  const containerVariants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: 'easeOut' },
    },
  };

  return (
    <motion.div
      ref={containerRef}
      className={`w-full flex ${className || direction} gap-[24px]`}
      variants={containerVariants}
      initial="hidden"
      animate={controls}
    >
      {steps.map((step, index) => (
        <motion.div
          key={index}
          variants={itemVariants}
          className={`flex items-center gap-[24px] ${background} rounded-sm px-4 py-4`}
        >
          <div className={`flex-shrink-0 h-[32px] w-[32px] md:h-[40px] md:w-[40px] text-black bg-[var(--mrwhite-primary-color)] rounded-full flex items-center justify-center text-[20px] md:text-[24px] font-semibold font-work-sans`}>
            {index + 1}
          </div>
          <div className="flex-1 flex flex-col">
            <h3 className="text-[20px] font-semibold font-work-sans">{step.title}</h3>
            <p className="text-[16px] text-justify font-light font-public-sans tracking-tighter">{step.description}</p>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}