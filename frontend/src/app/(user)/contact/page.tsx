"use client"

import ShakingIcon from "@/components/ShakingIcon";
import { Button } from "@/components/ui/button";
import Image from "next/image";
import { useState, useEffect } from "react";
import { IoChatbubble } from "react-icons/io5";
import axios from "axios";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";
import { motion } from "motion/react";

const ContactPage = () => {
	const { user } = useAuth();
	const [isLoading, setIsLoading] = useState(false);
	const [submitSuccess, setSubmitSuccess] = useState(false);
	const [submitError, setSubmitError] = useState("");
	const [validationErrors, setValidationErrors] = useState({
		name: "",
		email: "",
		message: "",
		subject: ""
	});

	const [contactForm, setContactForm] = useState({
		name: '',
		email: '',
		phone: '',
		message: '',
		subject: ''
	});
	
	// Auto-hide success message after 5 seconds
	useEffect(() => {
		if (submitSuccess) {
			const timer = setTimeout(() => {
				setSubmitSuccess(false);
			}, 5000);
			
			return () => clearTimeout(timer);
		}
	}, [submitSuccess]);
	
	// Auto-hide error message after 5 seconds
	useEffect(() => {
		if (submitError) {
			const timer = setTimeout(() => {
				setSubmitError("");
			}, 5000);
			
			return () => clearTimeout(timer);
		}
	}, [submitError]);

	const validateForm = () => {
		let isValid = true;
		const errors = {
			name: "",
			email: "",
			message: "",
			subject: ""
		};

		if (!contactForm.name.trim()) {
			errors.name = "Name is required";
			isValid = false;
		}

		if (!contactForm.email.trim()) {
			errors.email = "Email is required";
			isValid = false;
		} else if (!/\S+@\S+\.\S+/.test(contactForm.email)) {
			errors.email = "Email is invalid";
			isValid = false;
		}

		if (!contactForm.message.trim()) {
			errors.message = "Message is required";
			isValid = false;
		}

		if (!contactForm.subject.trim()) {
			errors.subject = "Subject is required";
			isValid = false;
		}

		setValidationErrors(errors);
		return isValid;
	};

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();

		// Validate form
		if (!validateForm()) {
			return;
		}

		// Clear previous status
		setSubmitError("");
		setSubmitSuccess(false);
		setIsLoading(true);

		try {
			const response = await axios.post(
				`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/contact/`,
				contactForm,
				{ withCredentials: true } // Send cookies for user identification
			);

			// Reset form
			setContactForm({
				name: '',
				email: '',
				phone: '',
				message: '',
				subject: ''
			});

			setSubmitSuccess(true);
		} catch (error: any) {
			console.error("Error submitting contact form:", error);
			if (error?.response?.data?.message) {
				setSubmitError(error.response.data.message);
			} else {
				setSubmitError("An error occurred. Please try again later.");
			}
		} finally {
			setIsLoading(false);
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === 'Enter' && !isLoading) {
			e.preventDefault();
			handleSubmit(e);
		}
	};

	// Clear validation error when user types in a field
	const handleInputChange = (field: string, value: string) => {
		setContactForm({ ...contactForm, [field]: value });
		if (validationErrors[field as keyof typeof validationErrors]) {
			setValidationErrors({
				...validationErrors,
				[field]: ""
			});
		}
	};

	// Animation variants
	const formContainerVariants = {
		hidden: { opacity: 0 },
		visible: {
			opacity: 1,
			transition: {
				staggerChildren: 0.1,
				delayChildren: 0.2
			}
		}
	};

	const formItemVariants = {
		hidden: { opacity: 0, y: 20 },
		visible: {
			opacity: 1,
			y: 0,
			transition: {
				duration: 0.5,
				ease: [0.25, 0.1, 0.25, 1.0] as const
			}
		}
	};

	const imageVariants = {
		hidden: { opacity: 0, x: 50 },
		visible: {
			opacity: 1,
			x: 0,
			transition: {
				duration: 0.7,
				ease: [0.25, 0.1, 0.25, 1.0] as const
			}
		}
	};

	return (
		<div className="flex flex-col gap-y-24">

			{/* SECTION 1  */}
			<section className="h-[400px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/contact-hero.png')] bg-cover bg-center">
				<div className="absolute inset-0 bg-black/40"></div>
				<div className="z-20">
					<h1 className="max-[1200px]:text-[32px] text-[40px] font-work-sans font-semibold text-center">Contact</h1>
					<p className="max-[1200px]:text-[16px] text-[20px] font-public-sans font-light text-center">Can we help you? Let us know your needs.</p>
				</div>
			</section>

			{/* SECTION 2 */}
			<section className="max-[1100px]:px-4 px-10 max-[1100px]:flex-col max-[1100px]:items-center flex">

				<motion.div
					className="w-1/2 max-[1100px]:w-full p-4"
					initial="hidden"
					whileInView="visible"
					viewport={{ once: true, amount: 0.3 }}
					variants={formContainerVariants}
				>
					<form onSubmit={handleSubmit} onKeyDown={handleKeyDown} className="flex flex-col gap-y-4" noValidate>
						<div className="relative flex flex-col gap-y-4">
							<motion.div variants={formItemVariants} className="flex flex-col">
								<input
									type="text"
									placeholder="Full Name*"
									name="full-name"
									value={contactForm.name}
									onChange={(e) => handleInputChange("name", e.target.value)}
									className={`w-full border rounded-[5px] bg-white/10 py-3 pl-4 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] font-work-sans font-light ${validationErrors.name ? 'border-red-500' : ''}`}
									autoComplete="full-name"
								/>
								{validationErrors.name && (
									<span className="text-red-500 font-public-sans text-sm mt-1">{validationErrors.name}</span>
								)}
							</motion.div>

							<motion.div variants={formItemVariants} className="flex flex-col">
								<input
									type="email"
									placeholder="E-mail*"
									name="email"
									value={contactForm.email}
									onChange={(e) => handleInputChange("email", e.target.value)}
									className={`w-full border rounded-[5px] bg-white/10 py-3 pl-4 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] font-work-sans font-light ${validationErrors.email ? 'border-red-500' : ''}`}
									autoComplete="email"
								/>
								{validationErrors.email && (
									<span className="text-red-500 font-public-sans text-sm mt-1">{validationErrors.email}</span>
								)}
							</motion.div>

							<motion.div variants={formItemVariants}>
								<input
									type="tel"
									placeholder="Phone number"
									name="phone-number"
									value={contactForm.phone}
									onChange={(e) => handleInputChange("phone", e.target.value)}
									className="w-full border rounded-[5px] bg-white/10 py-3 pl-4 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] font-work-sans font-light"
									autoComplete="tel"
								/>
							</motion.div>

							<motion.div variants={formItemVariants} className="flex flex-col">
								<input
									type="text"
									placeholder="Subject*"
									name="subject"
									value={contactForm.subject}
									onChange={(e) => handleInputChange("subject", e.target.value)}
									className={`w-full border rounded-[5px] bg-white/10 py-3 pl-4 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] font-work-sans font-light ${validationErrors.subject ? 'border-red-500' : ''}`}
									autoComplete="subject"
								/>
								{validationErrors.subject && (
									<span className="text-red-500 font-public-sans text-sm mt-1">{validationErrors.subject}</span>
								)}
							</motion.div>

							<motion.div variants={formItemVariants} className="flex flex-col">
								<textarea
									placeholder="Write your message here*"
									name="message"
									value={contactForm.message}
									onChange={(e) => handleInputChange("message", e.target.value)}
									className={`w-full border rounded-[5px] bg-white/10 py-3 pl-4 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] font-work-sans font-light resize-none h-[160px] ${validationErrors.message ? 'border-red-500' : ''}`}
								/>
								{validationErrors.message && (
									<span className="text-red-500 font-public-sans text-sm mt-1">{validationErrors.message}</span>
								)}
							</motion.div>
						</div>

						{submitError && (
							<motion.div
								className="text-red-500 mt-2"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								transition={{ duration: 0.3 }}
							>
								{submitError}
							</motion.div>
						)}

						{submitSuccess && (
							<motion.div
								className="text-green-500 mt-2"
								initial={{ opacity: 0 }}
								animate={{ opacity: 1 }}
								transition={{ duration: 0.5 }}
							>
								Your message has been sent successfully. We'll get back to you soon!
							</motion.div>
						)}

						<motion.div variants={formItemVariants}>
							<Button
								type="submit"
								disabled={isLoading}
								className="px-4 self-center py-2 mt-4 flex items-center w-[289px] max-[350px]:w-full h-[47px] gap-[10px] text-[20px] font-medium font-work-sans mx-auto"
							>
								{isLoading ? (
									<div className="relative w-12 h-6">
										<Image
											src="/assets/running-dog.gif"
											alt="Loading"
											fill
											priority
											className="object-cover"
										/>
									</div>
								) : (
									<ShakingIcon icon={<IoChatbubble className="w-[20px] h-[20px]" />} />
								)}
								{isLoading ? 'Sending...' : 'Send Message'}
							</Button>
						</motion.div>
					</form>
				</motion.div>

				<motion.div
					className="w-1/2 max-[1100px]:w-full max-[1100px]:flex max-[1100px]:justify-center flex justify-end"
					initial="hidden"
					whileInView="visible"
					viewport={{ once: true, amount: 0.3 }}
					variants={imageVariants}
				>
					<Image src="/assets/contact-dog.png" alt="contact" width={540} height={621} />
				</motion.div>

			</section>
		</div>
	)
}

export default ContactPage;