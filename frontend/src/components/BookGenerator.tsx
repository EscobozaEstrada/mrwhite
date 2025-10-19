import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { MdKeyboardVoice } from 'react-icons/md';
import { RxDimensions } from "react-icons/rx";
import { GoTypography } from 'react-icons/go';
import { IoMdColorPalette } from 'react-icons/io';
import { PiBooksFill } from 'react-icons/pi';

// Color options for the book
const fontColorOptions = [
	{ name: "Black", value: "#000000" },
	{ name: "Dark Gray", value: "#333333" },
	{ name: "Navy Blue", value: "#0A2342" },
	{ name: "Dark Brown", value: "#3A2618" }
];

const backgroundColorOptions = [
	{ name: "White", value: "#FFFFFF" },
	{ name: "Cream", value: "#FFF8E7" },
	{ name: "Light Gray", value: "#F5F5F5" },
	{ name: "Soft Blue", value: "#E6F3FF" }
];

interface BookGeneratorProps {
	isOpen: boolean;
	onClose: () => void;
}

// Create a wrapper component for Select to prevent sidebar closing
const SafeSelect = ({ children, ...props }: any) => {
	const selectRef = useRef<HTMLDivElement>(null);
	const [isOpen, setIsOpen] = useState(false);

	// Handle clicks when the dropdown is open
	useEffect(() => {
		if (!isOpen) return;

		// This function handles clicks outside the select
		const handleOutsideClick = (e: MouseEvent) => {
			// Get the target and select elements
			const target = e.target as Node;
			const selectElement = selectRef.current;
			const selectContent = document.querySelector('[data-radix-select-content]');

			// If click is inside select or its content, let it handle normally
			if (
				(selectElement && selectElement.contains(target)) ||
				(selectContent && selectContent.contains(target))
			) {
				return;
			}

			// For clicks outside, prevent sidebar closing
			e.stopPropagation();

			// Close the dropdown
			setIsOpen(false);
		};

		// Add listener with capture to intercept events before they reach the document
		document.addEventListener('mousedown', handleOutsideClick, true);

		return () => {
			document.removeEventListener('mousedown', handleOutsideClick, true);
		};
	}, [isOpen]);

	return (
		<div ref={selectRef} className="w-full">
			<Select
				{...props}
				onOpenChange={(open: boolean) => {
					setIsOpen(open);
					// If there's an onOpenChange prop, call it
					if (props.onOpenChange) {
						props.onOpenChange(open);
					}
				}}
			>
				{children}
			</Select>
		</div>
	);
};

const BookGenerator: React.FC<BookGeneratorProps> = ({ isOpen, onClose }) => {
	const [toneOfVoice, setToneOfVoice] = useState("mr-white");
	const [bookDimensions, setBookDimensions] = useState("15x7");
	const [typography, setTypography] = useState("poppins");
	const [wordCount, setWordCount] = useState("6000");
	const [template, setTemplate] = useState("pet-story");
	const [storyline, setStoryline] = useState("");

	// Add state for font and background colors
	const [fontColor, setFontColor] = useState(fontColorOptions[0].value);
	const [bgColor, setBgColor] = useState(backgroundColorOptions[0].value);

	// State to track which color picker is currently open
	const [activeColorPicker, setActiveColorPicker] = useState<'font' | 'background' | null>(null);

	const handleGenerateBook = () => {
		// Implement book generation logic
		console.log("Generating book with:", {
			toneOfVoice,
			bookDimensions,
			typography,
			wordCount,
			template,
			storyline,
			fontColor,
			bgColor
		});
		// After generation is complete, you might want to close the sidebar or show a success message
	};

	// Function to handle clicking on a color option
	const handleColorSelect = (color: string, type: 'font' | 'background') => {
		if (type === 'font') {
			setFontColor(color);
		} else {
			setBgColor(color);
		}
		setActiveColorPicker(null);
	};

	return (
		<div
			className='flex flex-col gap-10'
			onClick={(e) => e.stopPropagation()}
			onMouseDown={(e) => e.stopPropagation()}
		>
			<div className="flex h-full gap-10 max-[850px]:flex-col max-[600px]:w-full">

				<div className="w-1/2 max-[850px]:w-full flex flex-col gap-6">

					<div className="bg-black rounded-sm p-4 flex flex-col gap-6">
						<h1 className=''>
							<MdKeyboardVoice className='w-6 h-6 text-[var(--mrwhite-primary-color)] inline-block mr-2' />
							Tone of Voice
						</h1>
						{/* dropdown select with dummy options and default selected also a chevron icon */}
						<div className="flex items-center gap-2">
							<SafeSelect value={toneOfVoice} onValueChange={setToneOfVoice}>
								<SelectTrigger>
									<SelectValue placeholder="Select a tone" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="mr-white">Mr. White Voice (Default)</SelectItem>
									<SelectItem value="friendly">Friendly</SelectItem>
									<SelectItem value="professional">Professional</SelectItem>
									<SelectItem value="casual">Casual</SelectItem>
								</SelectContent>
							</SafeSelect>
						</div>
						{/* <div> */}
						<p className="font-bold">Description:</p>
						<p>A calm, soulful narrator who writes as if they're gently walking beside you and your dog's life story. </p>
						<p className="font-extralight italic">"From the moment she curled up in your lap to her first joyful run in the snow, Bella's story unfolded like a melody you both knew by heart…" </p>
						{/* </div> */}
					</div>

					<div className="bg-black rounded-sm p-4 flex flex-col gap-4">
						<h1>
							<RxDimensions className='w-6 h-6 text-[var(--mrwhite-primary-color)] inline-block mr-2' />
							Book Dimensions
						</h1>
						{/* dropdown select with dummy options and default selected */}
						<div className="flex items-center gap-2">
							<SafeSelect value={bookDimensions} onValueChange={setBookDimensions}>
								<SelectTrigger>
									<SelectValue placeholder="Select dimensions" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="15x7">15" height x 7" width</SelectItem>
									<SelectItem value="12x9">12" height x 9" width</SelectItem>
									<SelectItem value="10x10">10" height x 10" width</SelectItem>
								</SelectContent>
							</SafeSelect>
						</div>
					</div>

					<div className="bg-black rounded-sm flex flex-col gap-4 p-4">
						<h1>
							<GoTypography className='w-6 h-6 text-[var(--mrwhite-primary-color)] inline-block mr-2' />
							Typography
						</h1>
						{/* dropdown select with dummy options and default selected */}
						<div className="flex items-center gap-2">
							<SafeSelect value={typography} onValueChange={setTypography}>
								<SelectTrigger>
									<SelectValue placeholder="Select a font" />
								</SelectTrigger>
								<SelectContent>
									<SelectItem value="poppins">Poppins</SelectItem>
									<SelectItem value="roboto">Roboto</SelectItem>
									<SelectItem value="opensans">Open Sans</SelectItem>
									<SelectItem value="lora">Lora</SelectItem>
								</SelectContent>
							</SafeSelect>
						</div>
					</div>

					<div className='max-[600px]:w-full w-[568px] h-[246px] bg-black rounded-sm p-4 flex flex-col gap-4'>
						<h1>
							<IoMdColorPalette className='w-6 h-6 text-[var(--mrwhite-primary-color)] inline-block mr-2' />
							Coloring
						</h1>
						<div className='flex gap-2'>
							<div className='w-[106px] h-[162px] bg-white/10 rounded-sm flex flex-col gap-2 items-center justify-center relative'>
								<h1>Font:</h1>
								<div
									className="w-[64px] h-[64px] rounded-sm cursor-pointer border border-white/20 hover:border-white/50"
									style={{ backgroundColor: fontColor }}
									onClick={() => setActiveColorPicker(activeColorPicker === 'font' ? null : 'font')}
								></div>
								<h1>{fontColor}</h1>

								{/* Font color picker dropdown */}
								{activeColorPicker === 'font' && (
									<div className="absolute top-full left-0 mt-2 bg-neutral-800 border border-neutral-700 rounded-md shadow-lg z-50 p-2 w-[150px]">
										<div className="grid grid-cols-2 gap-2">
											{fontColorOptions.map((color) => (
												<div
													key={color.value}
													className="flex flex-col items-center cursor-pointer hover:bg-neutral-700 p-1 rounded"
													onClick={() => handleColorSelect(color.value, 'font')}
												>
													<div
														className="w-8 h-8 rounded-sm border border-white/20"
														style={{ backgroundColor: color.value }}
													></div>
													<span className="text-xs mt-1">{color.name}</span>
												</div>
											))}
										</div>
									</div>
								)}
							</div>

							<div className='w-[106px] h-[162px] bg-white/10 rounded-sm flex flex-col gap-2 items-center justify-center relative'>
								<h1>Background:</h1>
								<div
									className="w-[64px] h-[64px] rounded-sm cursor-pointer border border-white/20 hover:border-white/50"
									style={{ backgroundColor: bgColor }}
									onClick={() => setActiveColorPicker(activeColorPicker === 'background' ? null : 'background')}
								></div>
								<h1>{bgColor}</h1>

								{/* Background color picker dropdown */}
								{activeColorPicker === 'background' && (
									<div className="absolute top-full left-0 mt-2 bg-neutral-800 border border-neutral-700 rounded-md shadow-lg z-50 p-2 w-[150px]">
										<div className="grid grid-cols-2 gap-2">
											{backgroundColorOptions.map((color) => (
												<div
													key={color.value}
													className="flex flex-col items-center cursor-pointer hover:bg-neutral-700 p-1 rounded"
													onClick={() => handleColorSelect(color.value, 'background')}
												>
													<div
														className="w-8 h-8 rounded-sm border border-white/20"
														style={{ backgroundColor: color.value }}
													></div>
													<span className="text-xs mt-1">{color.name}</span>
												</div>
											))}
										</div>
									</div>
								)}
							</div>
						</div>
					</div>

				</div>

				<div className="w-1/2 max-[850px]:w-full bg-black rounded-sm p-4 flex flex-col gap-4">
					<h1>
						<PiBooksFill className='w-6 h-6 text-[var(--mrwhite-primary-color)] inline-block mr-2' />
						Storyline
					</h1>

					<h1>
						Desired Wordcount
					</h1>
					<div className="flex items-center gap-2">
						<SafeSelect value={wordCount} onValueChange={setWordCount}>
							<SelectTrigger>
								<SelectValue placeholder="Select wordcount" />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="3000">3,000 words</SelectItem>
								<SelectItem value="6000">6,000 words</SelectItem>
								<SelectItem value="10000">10,000 words</SelectItem>
								<SelectItem value="15001">15,000 words</SelectItem>
							</SelectContent>
						</SafeSelect>
					</div>

					<h1>
						Select Template
					</h1>
					<div className="flex items-center gap-2">
						<SafeSelect value={template} onValueChange={setTemplate}>
							<SelectTrigger>
								<SelectValue placeholder="Select a template" />
							</SelectTrigger>
							<SelectContent>
								<SelectItem value="pet-story">Pet Story</SelectItem>
								<SelectItem value="adventure">Adventure</SelectItem>
								<SelectItem value="memoir">Memoir</SelectItem>
								<SelectItem value="custom">Custom</SelectItem>
							</SelectContent>
						</SafeSelect>
					</div>

					<div>
						<h1>Create your own storyline</h1>
						<p className="text-sm text-neutral-400">Provide information on which HUB elements the book should include.</p>
					</div>

					{/* a textarea with a placeholder of "Write your story here..." */}
					<Textarea
						placeholder="Write the story of my trip to Hawaii with my dog in a creative way .. that shares about all of the loving sweet moments I had with him with photos."
						className="w-full h-full bg-white/10 resize-none rounded-sm"
						value={storyline}
						onChange={(e) => setStoryline(e.target.value)}
					/>
				</div>

			</div>

			<div className='flex justify-end'>
				<Button onClick={handleGenerateBook}>Generate Book</Button>
			</div>
		</div>
	);
};

export default BookGenerator; 