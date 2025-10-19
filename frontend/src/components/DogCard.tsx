"use client";

import Image from "next/image";
import { motion } from "framer-motion"; // ✅ Use framer-motion instead of motion/react

interface DogCardProps {
  imageSrc: string;
  imageAlt: string;
  title: string;
  description: string[];
  delay?: number;
}

export function DogCard({ imageSrc, imageAlt, title, description, delay = 0 }: DogCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease: "easeOut" }}
      viewport={{ once: true, amount: 0.5 }}
      className="bg-black rounded-sm overflow-hidden shadow-lg w-[432px] max-[450px]:w-full max-[1024px]:h-fit h-[575px]"
    >
      <div className="w-full h-[240px] relative">
        <Image
          src={imageSrc}
          alt={imageAlt}
          fill
          sizes="250px"
          priority
          className="object-cover"
        />
      </div>
      <div className="w-full p-6">
        <h3 className="text-[20px] font-semibold mb-2">{title}</h3>
        <div className="flex flex-col gap-4">
          {
            description.map((item, index) => (
              <p key={index} className="font-light font-public-sans">{item}</p>
            ))
          }
        </div>
      </div>
    </motion.div>
  );
}
