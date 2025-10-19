"use client"

import CompanyNameSection from "@/components/CompanyNameSection";
import FadeInSection from "@/components/FadeInSection";
import ImagePop from "@/components/ImagePop";
import ShakingIcon from "@/components/ShakingIcon";
import { Button } from "@/components/ui/button";
import { motion } from "motion/react";
import Image from "next/image";
import { AiFillLike } from "react-icons/ai";
import { BiSolidBookAlt } from "react-icons/bi";
import { BsFillQuestionCircleFill, BsListCheck } from "react-icons/bs";
import { FaUserGraduate } from "react-icons/fa";
import { PiBoneFill, PiBookOpen, PiInfo } from "react-icons/pi";

const WayOfDogPage = () => {
	return (
		<div className="flex flex-col overflow-x-hidden">

			{/* SECTION 1  */}
			<section className="h-[400px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/way-of-dog-hero.webp')] bg-cover bg-center">
				<div className="absolute inset-0 bg-black/40"></div>
				<div className="z-20">
					<h1 className="max-[1200px]:text-[30px] text-[40px] font-work-sans font-semibold text-center">Welcome to The Way of the Dog</h1>
					<p className="max-[1200px]:text-[16px] text-[20px] font-public-sans font-light text-center">A Guide to Intuitive Bonding and Creating</p>
					<p className="max-[1200px]:text-[16px] text-[20px] font-public-sans font-light text-center">an Interspecies Culture with Your Dog </p>
				</div>
			</section>

			{/* SECTION 2 */}
			<section className="max-w-[1440px] mx-auto py-16 max-[850px]:py-0 mt-10 max-[1200px]:px-4 px-10">

				<div className="flex flex-col">

					<div className="flex gap-10 max-[850px]:flex-col">

						<div className="w-1/2 max-[850px]:w-full flex flex-col gap-6 justify-center font-public-sans font-extralight">

							<h1 className="text-[32px] font-work-sans font-semibold">A Message from Anahata Graceland</h1>
							<p className="font-public-sans font-extralight">The Way of the Dog wasn't something I sat down to invent. It revealed itself slowly, through the decades I spent living closely with dogs, raising and caring for them, listening, loving, and learning. And most especially, through the quiet guidance of Mr. White for his 16 years of life.
								He was my teacher, my mirror, and my heart. Now he returns in his next form, not just as memory, but as the spirit behind mrwhiteaidogbuddy.com. </p>
							<p className="font-public-sans font-extralight">"What you're about to explore is unlike anything else:A living guide that helps you deepen your intuitive bond with your dog in real time, at your pace, in your voice, and with support every step of the way.</p>

						</div>

						<div className="relative max-w-full w-1/2 h-[380px] max-[850px]:w-full">
							<ImagePop
								src="/assets/way-of-dog-anhata.webp"
								alt="way-of-dog-anhata"
								fill
								className="rounded-sm"
								containerClassName="w-full h-full"
								overlay={true}
							/>
							<p className="absolute bottom-5 left-5 text-[16px] text-semibold font-public-sans text-sm bg-black px-2 py-1 rounded-sm flex items-center gap-2 z-10 max-[1260px]:text-[14px] max-[1260px]:tracking-tighter max-[850px]:text-[12px]">
								<PiInfo />
								Small Steps, Big Love - Exercises That Help You Truly See Each Other
							</p>
						</div>

					</div>


					<div className="flex gap-10 mt-20 max-[850px]:flex-col-reverse">

						<div className="relative max-w-full w-1/2 max-[850px]:h-[400px] max-[850px]:w-full">
							<ImagePop
								src="/assets/way-of-dog-space-dog.webp"
								alt="way-of-dog-anhata"
								fill
								className="rounded-sm"
								containerClassName="w-full h-full"
								overlay={true}
							/>
						</div>

						<div className="w-1/2 max-[850px]:w-full flex flex-col gap-6 font-public-sans font-extralight">

							<h1 className="text-[32px] font-work-sans font-semibold">What The Way of the Dog Offers</h1>
							<p className="font-public-sans font-light">This isn't just an introduction. It's a doorway.</p>
							<div className="flex flex-col gap-4">
								<p>Here, you can engage with the entire book directly inside your journey. You don't just read it, you live it. Your dog will be so happy!</p>
								<ul className="list-disc pl-4">
									<li>Ask to read a chapter </li>
									<li>Jump into any exercise or checklist </li>
									<li>Let Mr. White lead you through it, curated to your life, your questions, and your dog's personality</li>
								</ul>
							</div>
							<p>Everything in the book from Generating Love to Intuitive Bonding to Consistency for Trust is here and waiting for you to step in.</p>
							<p>This is the central hub of The Way of the Dog while it uses all of the Legacy of Love Dog Hub at the same time for you to experience top notch care and support. Your dog journal will grow into quite a fun experience and the book you will be able to create out of it will be remarkable!</p>

						</div>

					</div>
				</div>

			</section>

			{/* SECTION 3 */}
			<section className="max-w-[1440px] mx-auto py-16 max-[1200px]:px-4 px-10 flex flex-col gap-10">

				<div>
					<h1 className="text-[32px] font-semibold font-work-sans">What Awaits You Inside</h1>
					<p className="font-extralight font-public-sans">When you begin exploring, here's what you'll have access to:</p>
				</div>

				<div className="flex gap-8 max-[850px]:flex-col">
					<div className="w-1/2 max-[850px]:w-full flex flex-col gap-8">
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							whileInView={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.1 }}
							viewport={{ once: true, amount: 0.4 }}
							className="flex flex-col gap-6 p-8 bg-white/10 font-public-sans rounded-sm">
							<p className="flex items-center gap-2 font-semibold font-public-sans">
								<BiSolidBookAlt className="inline-block text-[var(--mrwhite-primary-color)]" />
								Full Access to the Book
							</p>
							<div className="h-[1px] bg-black"></div>
							<div className="flex flex-col gap-4 font-extralight">
								<p>All 19 chapters of The Way of the Dog</p>
								<ul className="list-disc pl-6">
									<li>Soulful teachings on bonding, communication, health, routine, grief, legacy, joy, and play </li>
									<li>Breed-specific insights, personal reflections, rituals, and Final Fetches that are summaries of wisdom worth reflecting on </li>
								</ul>
							</div>
						</motion.div>

						<motion.div
							initial={{ opacity: 0, y: 20 }}
							whileInView={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.3 }}
							viewport={{ once: true, amount: 0.4 }}
							className="flex flex-col gap-6 p-8 bg-white/10 font-public-sans rounded-sm">
							<p className="flex items-center gap-2 font-semibold font-public-sans">
								<FaUserGraduate className="inline-block text-[var(--mrwhite-primary-color)]" />
								Mr. White as Your Guide
							</p>
							<div className="h-[1px] bg-black"></div>
							<div className="flex flex-col gap-4 font-extralight">
								<p>Warm, emotionally intelligent support </p>
								<ul className="list-disc pl-6">
									<li>Suggestions tailored to your pace and interests </li>
									<li>Thoughtful prompts that open your awareness and deepen your connection </li>
									<li>Optional support in creating a rhythm or pathway through the book's content </li>
								</ul>
							</div>
						</motion.div>

						<motion.div
							initial={{ opacity: 0, y: 20 }}
							whileInView={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.5 }}
							viewport={{ once: true, amount: 0.4 }}
							className="flex flex-col gap-6 p-8 bg-white/10 font-public-sans rounded-sm">
							<p className="flex items-center gap-2 font-semibold font-public-sans">
								<BsListCheck className="inline-block text-[var(--mrwhite-primary-color)]" />
								Checklists That Bring your Days to Life
							</p>
							<div className="h-[1px] bg-black"></div>
							<div className="flex flex-col gap-4 font-extralight">
								<p>You'll also find lovingly designed, practical checklists to anchor your daily connection: </p>
								<ul className="list-disc pl-6">
									<li>Living the Way of the Dog – Daily reminders to stay present and attuned</li>
									<li>Magical Moments – Creative ways to integrate tech + love</li>
									<li>Health Check-In Checklist – A simple body-mind-emotion scan</li>
									<li>New Dog Welcome – For blending your household with grace</li>
									<li>Prepared Pets Checklist – For safety and readiness, inspired by Anahata's book Prepared Pets</li>
								</ul>
							</div>
						</motion.div>
					</div>

					<div className="w-1/2 max-[850px]:w-full flex flex-col gap-8">
						<motion.div
							initial={{ opacity: 0, y: 20 }}
							whileInView={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.2 }}
							viewport={{ once: true, amount: 0.4 }}
							className="flex flex-col gap-6 p-8 bg-white/10 font-public-sans rounded-sm">
							<p className="flex items-center gap-2 font-semibold font-public-sans tracking-tighter">
								<BsFillQuestionCircleFill className="inline-block text-[var(--mrwhite-primary-color)]" />
								Small Steps, Big Love - Exercises That Help You Truly See Each Other
							</p>
							<div className="h-[1px] bg-black"></div>
							<div className="flex flex-col gap-4 font-extralight">
								<div>
									<p className="tracking-tight">The Soul Sketch – Describe your dog's essence, not what they do, but who they are </p>
									<ul className="list-disc pl-6">
										<li>Five-Minute Hands on Play Ritual – A short daily time to connect without agenda </li>
										<li>Who Is Your Dog in the Classroom of Life? – A personality lens to help you see them more fully </li>
										<li>The Curiosity Invitation – Join your dog in their world for 10 minutes and narrate what you discover </li>
										<li>The Memory Walk – A reflective journey through your dog's favorite spots, toys, people and friends </li>
									</ul>
								</div>

								<div>
									<p className="tracking-tight">You'll also find powerful guided rituals like: </p>
									<ul className="list-disc pl-6">
										<li>The Love Equation in Action </li>
										<li>The Emotional Bonding Ritual </li>
										<li>The Dog Wisdom Pledge </li>
									</ul>
								</div>
							</div>
						</motion.div>


						<motion.div
							initial={{ opacity: 0, y: 20 }}
							whileInView={{ opacity: 1, y: 0 }}
							transition={{ duration: 0.5, delay: 0.4 }}
							viewport={{ once: true, amount: 0.4 }}
							className="flex flex-col gap-6 p-8 bg-white/10 font-public-sans rounded-sm">
							<p className="flex items-center gap-2 text-[20px] font-semibold font-public-sans">
								<AiFillLike className="inline-block text-[var(--mrwhite-primary-color)]" />
								And Yes... You Also Get the Legacy of Love Dog Hub
							</p>
							<div className="h-[1px] bg-black"></div>
							<div className="flex flex-col gap-4 font-extralight">
								<p>Alongside your journey through the book, you'll have it seamlessly adding to the full Legacy of Love Dog Hub, which includes: </p>
								<ul className="list-disc pl-6">
									<li>Guided journaling </li>
									<li>Milestone + health tracking </li>
									<li>Memory and photo capture </li>
									<li>Curated keepsake book creation </li>
									<li>AI reflections + check-ins from Mr. White </li>
									<li>Save entries from any exercise, ritual, or insight</li>
								</ul>
							</div>
						</motion.div>
					</div>
				</div>

			</section>

			{/* SECTION 4 */}
			<section className="max-w-[1440px] mx-auto py-16 max-[850px]:pt-0 max-[1200px]:px-4 px-10">

				<div className="flex flex-col">

					<div className="flex gap-10 max-[850px]:flex-col">

						<div className="w-1/2 max-[850px]:w-full flex flex-col gap-6 justify-center font-public-sans font-extralight">

							<h1 className="text-[32px] font-work-sans font-semibold">Capturing the Story That Only You Can Tell </h1>
							<div>
								<p className="font-public-sans font-extralight">Every journal entry, photo, checklist, and milestone you track becomes part of your dog's legacy, a life lived together, full of presence, growth, and quiet joy. </p>
								<p className="font-public-sans font-extralight">Over time, the Hub collects these moments into something extraordinary:a personalized keepsake book that you can hold in your hands or have digitally. </p>
							</div>

							<ul className="list-disc pl-6">
								<li>Add photos of everyday life or special occasions like his 1st year birthday or the trip you took to the mountains </li>
								<li>Write short stories or memory notes. Mr. White can help you find the words </li>
								<li>Record firsts, favorite quirks, big moments, and quiet ones too </li>
								<li> Reflect on the love you've built, and the bond that keeps deepening </li>
							</ul>

							<div>
								<p>Your keepsake book is more than a memory, it's a celebration. A way to honor your dog not just in passing, but in presence today. </p>
								<p>It becomes a treasure. A record of a relationship that mattered. Something only you can create.
									And Mr. White will walk with you the entire way. </p>
							</div>

							<p>Let me know if you'd like this styled with a soft border or paired with an image (like a photo book, pawprint, or moment-in-time snapshot). It's a gorgeous moment to bring visual warmth to the page. </p>

						</div>

						<div className="relative max-w-full w-1/2 max-[850px]:w-full max-[850px]:h-[400px] max-[500px]:h-[200px]">
							<ImagePop
								src="/assets/way-of-dog-team-1.webp"
								alt="way-of-dog-anhata"
								fill
								className="rounded-sm"
								containerClassName="w-full h-full"
								overlay={true}
							/>
						</div>

					</div>


					<div className="flex gap-10 mt-20 max-[850px]:flex-col-reverse">

						<div className="relative max-w-full w-1/2 max-[850px]:w-full max-[850px]:h-[350px] max-[500px]:h-[200px]">
							<ImagePop
								src="/assets/way-of-dog-team-2.webp"
								alt="way-of-dog-space-dog"
								fill
								className="rounded-sm"
								containerClassName="w-full h-full"
								overlay={true}
							/>
						</div>

						<div className="w-1/2 max-[850px]:w-full flex flex-col gap-6 font-public-sans font-extralight">

							<h1 className="text-[32px] font-work-sans font-semibold">Begin Your Journey</h1>
							<div className="flex flex-col gap-4">
								<p>You can start by asking Mr. White: </p>
								<ul className="list-disc pl-4">
									<li>"Lets start at the beginning, Mr White I want it all!" </li>
									<li>"What's the first exercise I should do?" </li>
									<li>"Take me to the chapter on communication." </li>
									<li>"I want to start journaling today—what's a good place to begin?" </li>
								</ul>
							</div>

							<div>
								<p>Or just say:"Lead me, Mr. White." </p>
								<p>Whether you take a single step or walk the full path, you're entering something rare : A sacred rhythm of love. A way of living with your dog that will stay with you forever. </p>
							</div>

						</div>

					</div>



				</div>

			</section>

		</div>
	)
}

export default WayOfDogPage;