"use client"

import { motion } from "framer-motion"
import Image from "next/image"
import { ComponentProps, CSSProperties } from "react"
import { optimizeImage } from "@/lib/imageUtils"

interface ImagePopProps extends ComponentProps<typeof Image> {
  className?: string
  containerClassName?: string
  style?: CSSProperties
  overlay?: boolean
  priority?: boolean
  alt: string
  sizes?: string
}

export default function ImagePop({ 
  className = "", 
  containerClassName = "",
  style,
  overlay = false,
  priority = false,
  alt = "",
  sizes = "(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw",
  ...imageProps
}: ImagePopProps) {
  return (
    <motion.div 
      initial={{ scale: 0.8, opacity: 0 }}
      whileInView={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.6, ease: [0.25, 0.8, 0.25, 1] }}
      viewport={{ once: true, amount: 0.5 }}
      className={`relative ${containerClassName}`}
      style={style}
    >
      <div className="relative w-full h-full">
        <Image
          {...optimizeImage({
            ...imageProps,
            alt,
            priority,
            sizes,
            className: `absolute object-cover ${className}`
          })}
          fill
        />
      </div>
      {overlay && (
        <div className="absolute bottom-0 left-0 w-full h-16 pointer-events-none"></div>
      )}
    </motion.div>
  )
}
