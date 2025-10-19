"use client"

import Image from "next/image"
import { motion } from "framer-motion"

interface CompanyLogo {
  src: string
  alt: string
}

interface CompanyNameSectionProps {
  companies: CompanyLogo[]
}

export default function CompanyNameSection({ companies }: CompanyNameSectionProps) {
  return (
    <section className="py-8 md:py-16 flex flex-col justify-center items-center">
      <motion.div 
        layout
        className="flex gap-[10px] flex-wrap justify-center px-4"
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        variants={{
          visible: {
            transition: {
              staggerChildren: 0.2
            }
          }
        }}
      >
        {companies.map((company, index) => (
          <motion.div 
            key={index} 
            layout
            className="w-[320px] h-[120px] relative"
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { 
                opacity: 1, 
                y: 0,
                transition: {
                  duration: 0.5,
                  ease: "easeOut"
                }
              }
            }}
            whileHover={{ scale: 1.05 }}
          >
            <Image 
              src={company.src} 
              alt={company.alt} 
              fill 
              sizes="250px"
              priority
              className="object-contain" 
            />
          </motion.div>
        ))}
      </motion.div>
    </section>
  )
} 