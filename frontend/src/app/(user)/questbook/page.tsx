"use client";
import { FaStar, FaStarHalfAlt } from "react-icons/fa";
import { useState } from "react";
import { MessageCircle } from "lucide-react";
import Image from "next/image";

const QuestbookPage = () => {
    const [rating, setRating] = useState<number>(0);
    const [hoverRating, setHoverRating] = useState<number>(0);

    return (
        <div>
            <section className="max-w-[1440px] mx-auto flex gap-10 max-[1200px]:px-4 px-10 py-12 max-[1000px]:flex-col">
                <div className="w-1/2 max-[1000px]:w-full h-[697px] flex flex-col gap-10">
                
                    <div className="h-[145px] flex flex-col justify-center items-center gap-6 w-full bg-neutral-900 rounded-md">

                        <div className="flex gap-1">
                            <FaStar className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
                            <FaStar className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
                            <FaStar className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
                            <FaStar className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
                            <FaStarHalfAlt className="h-5 w-5 text-[var(--mrwhite-primary-color)]" />
                        </div>
                        <div className="flex gap-2">
                            <h2 className="text-white text-2xl font-bold">
                                4.7/5
                            </h2>

                            <h2 className="text-[var(--mrwhite-primary-color)] text-2xl font-light">
                                <span className="text-[var(--mrwhite-primary-color)] font-bold">170</span> ratings
                            </h2>
                        
                        </div>

                    </div>

                    {/* Review Form */}
                    <div className="bg-neutral-900 p-6 rounded-md">
                        <h2 className="text-white text-xl font-bold mb-4">Leave a message</h2>
                        
                        {/* Star Rating */}
                        <div className="flex mb-4">
                            {[1, 2, 3, 4, 5].map((star) => (
                                <span 
                                    key={star}
                                    className="cursor-pointer"
                                    onClick={() => setRating(star)}
                                    onMouseEnter={() => setHoverRating(star)}
                                    onMouseLeave={() => setHoverRating(0)}
                                >
                                    <FaStar 
                                        className={`h-6 w-6 ${
                                            (hoverRating || rating) >= star 
                                                ? "text-[var(--mrwhite-primary-color)]" 
                                                : "text-gray-600"
                                        }`}
                                    />
                                </span>
                            ))}
                            <span className="ml-2 text-gray-400 text-sm">Your rating here</span>
                        </div>
                        
                        {/* Form Inputs */}
                        <form className="flex flex-col gap-4">
                            {/* Name Input */}
                            <input 
                                type="text" 
                                placeholder="Name" 
                                className="bg-black border-none rounded p-3 text-white focus:outline-none focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                            />
                            
                            {/* Location Input */}
                            <input 
                                type="text" 
                                placeholder="Location" 
                                className="bg-black border-none rounded p-3 text-white focus:outline-none focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                            />
                            
                            {/* Message Textarea */}
                            <textarea 
                                placeholder="Your Message here" 
                                rows={5}
                                className="bg-black border-none rounded p-3 text-white resize-none focus:outline-none focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                            />
                            
                            {/* Submit Button */}
                            <button 
                                type="submit"
                                className="bg-[var(--mrwhite-primary-color)] text-black font-semibold py-3 rounded flex items-center justify-center mt-2"
                            >
                                <MessageCircle className="h-5 w-5 mr-2 fill-black" />
                                Leave Message
                            </button>
                        </form>
                    </div>

                </div>


                <div className="w-1/2 max-[1000px]:w-full flex flex-col gap-4">
                    {/* Review Card - Exactly matching the image */}
                    <div className="p-6 bg-neutral-900 rounded-md">
                        {/* User info and rating */}
                        <div className="flex items-center gap-3 mb-4">
                            {/* User image */}
                            <div className="relative w-12 h-12 rounded-md overflow-hidden bg-gray-700">
                                <div className="w-[48px] h-[48px] flex relative">
                                    <Image 
                                        src="/assets/john-doe.png" 
                                        alt="John Doe" 
                                        fill
                                        sizes="300px"
                                        priority
                                        className="object-cover"
                                    />
                                </div>
                            </div>
                            
                            {/* User name, location and rating */}
                            <div>
                                <div className="flex items-center gap-2">
                                    <h3 className="text-white font-medium">John Doe</h3>
                                    <div className="flex">
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStarHalfAlt className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                    </div>
                                    <span className="text-gray-400 text-sm">4.1/5</span>
                                </div>
                                <p className="text-gray-400 text-sm">Seattle, Washington</p>
                            </div>
                        </div>
                        
                        {/* Divider */}
                        <div className="bg-neutral-700 w-full h-px mb-4"></div>
                        
                        {/* Review text */}
                        <p className="text-white text-sm leading-relaxed">
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
                            incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
                            exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
                        </p>
                    </div>

                    <div className="p-6 bg-neutral-900 rounded-md">
                        {/* User info and rating */}
                        <div className="flex items-center gap-3 mb-4">
                            {/* User image */}
                            <div className="relative w-12 h-12 rounded-md overflow-hidden bg-gray-700">
                                <div className="w-[48px] h-[48px] flex relative">
                                    <Image 
                                        src="/assets/john-doe.png" 
                                        alt="John Doe" 
                                        fill
                                        sizes="300px"
                                        priority
                                        className="object-cover"
                                    />
                                </div>
                            </div>
                            
                            {/* User name, location and rating */}
                            <div>
                                <div className="flex items-center gap-2">
                                    <h3 className="text-white font-medium">John Doe</h3>
                                    <div className="flex">
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStarHalfAlt className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                    </div>
                                    <span className="text-gray-400 text-sm">4.1/5</span>
                                </div>
                                <p className="text-gray-400 text-sm">Seattle, Washington</p>
                            </div>
                        </div>
                        
                        {/* Divider */}
                        <div className="bg-neutral-700 w-full h-px mb-4"></div>
                        
                        {/* Review text */}
                        <p className="text-white text-sm leading-relaxed">
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
                            incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
                            exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
                        </p>
                    </div>

                    <div className="p-6 bg-neutral-900 rounded-md">
                        {/* User info and rating */}
                        <div className="flex items-center gap-3 mb-4">
                            {/* User image */}
                            <div className="relative w-12 h-12 rounded-md overflow-hidden bg-gray-700">
                                <div className="w-[48px] h-[48px] flex relative">
                                    <Image 
                                        src="/assets/john-doe.png" 
                                        alt="John Doe" 
                                        fill
                                        sizes="300px"
                                        priority
                                        className="object-cover"
                                    />
                                </div>
                            </div>
                            
                            {/* User name, location and rating */}
                            <div>
                                <div className="flex items-center gap-2">
                                    <h3 className="text-white font-medium">John Doe</h3>
                                    <div className="flex">
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStarHalfAlt className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                    </div>
                                    <span className="text-gray-400 text-sm">4.1/5</span>
                                </div>
                                <p className="text-gray-400 text-sm">Seattle, Washington</p>
                            </div>
                        </div>
                        
                        {/* Divider */}
                        <div className="bg-neutral-700 w-full h-px mb-4"></div>
                        
                        {/* Review text */}
                        <p className="text-white text-sm leading-relaxed">
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
                            incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
                            exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
                        </p>
                    </div>

                    <div className="p-6 bg-neutral-900 rounded-md">
                        {/* User info and rating */}
                        <div className="flex items-center gap-3 mb-4">
                            {/* User image */}
                            <div className="relative w-12 h-12 rounded-md overflow-hidden bg-gray-700">
                                <div className="w-[48px] h-[48px] flex relative">
                                    <Image 
                                        src="/assets/john-doe.png" 
                                        alt="John Doe" 
                                        fill
                                        sizes="300px"
                                        priority
                                        className="object-cover"    
                                    />
                                </div>
                            </div>
                            
                            {/* User name, location and rating */}
                            <div>
                                <div className="flex items-center gap-2">
                                    <h3 className="text-white font-medium">John Doe</h3>
                                    <div className="flex">
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStar className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                        <FaStarHalfAlt className="h-4 w-4 text-[var(--mrwhite-primary-color)]" />
                                    </div>
                                    <span className="text-gray-400 text-sm">4.1/5</span>
                                </div>
                                <p className="text-gray-400 text-sm">Seattle, Washington</p>
                            </div>
                        </div>
                        
                        {/* Divider */}
                        <div className="bg-neutral-700 w-full h-px mb-4"></div>
                        
                        {/* Review text */}
                        <p className="text-white text-sm leading-relaxed">
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor 
                            incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud 
                            exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
                        </p>
                    </div>

                </div>
            </section>
        </div>
    );
};

export default QuestbookPage;