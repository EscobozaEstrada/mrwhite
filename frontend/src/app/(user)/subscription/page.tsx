"use client"
import FadeInSection from "@/components/FadeInSection";
import StepsAnimated from "@/components/StepsAnimated";
import SubscriptionCard from "@/components/SubscriptionCard";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { TbLogin } from "react-icons/tb";
import { useRouter } from "next/navigation";


const steps = [
	{
		id: 1,
		title: "Sign up",
		description: "Create your account in moments — join the Companion Crew. Use the Elite Pack as a full member — to start your journey with Mr. White and your companion."
	},
	{
		id: 2,
		title: "Choose Your Subscription",
		description: "Join the Companion Crew for free to get daily tips on X or unlock all benefits with the Elite Pack membership for $19.95 monthly or $278 yearly (saving $70)."
	},
	{
		id: 3,
		title: "Access Your Personal Portal",
		description: "Step into your personal portal with Mr. White, where tailored guidance, records, and wisdom for you and your dog are available 24/7."
	}
];

const SubscriptionPage = () => {
	const { user, setUser } = useAuth();
	const router = useRouter();
	return (
		<div className="flex flex-col gap-y-24">

			{/* SECTION 1  */}
			<section className="h-[400px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/subscription-hero.png')] bg-cover bg-center">
				<div className="absolute inset-0 bg-black/40"></div>
				<div className="z-20">
					<h1 className="max-[1200px]:text-[32px] text-[40px] font-work-sans font-semibold text-center">Subscription</h1>
					<p className="max-[1200px]:text-[16px] text-[20px] font-public-sans font-light text-center">Mr. White's available subscriptions</p>
				</div>
			</section>

			{/* SECTION 2 */}
			{!user && <section className="max-[1200px]:px-4 px-10 flex flex-col justify-center items-center gap-y-10">

				<div className="flex flex-col items-center">
					<h1 className="text-[32px] font-semibold font-work-sans">Get Started with Mr. White in 3 Easy Steps</h1>
					<p className="text-[20px] font-light font-public-sans">A short guide on how to get started with Mr White.</p>
				</div>

				<div className="flex max-[1024px]:flex-col flex-row gap-6 lg:gap-8 w-full">
					{steps.map((step, index) => (
						<div
							key={step.id}
							className="flex-1 bg-white/10 p-6 hover:border-gray-700 transition-all duration-300 hover:shadow-xl hover:shadow-gray-900/20 rounded-sm"
						>
							<div className="flex items-start gap-4">
								<div className={`flex-shrink-0 w-[40px] h-[40px] rounded-full flex items-center justify-center font-semibold text-black text-[24px] font-work-sans bg-[var(--mrwhite-primary-color)] ${index % 2 === 0 ? 'self-start' : 'self-center'} max-[1024px]:self-start`}>
									{step.id}
								</div>
								<div className="flex-1">
									<h3 className="text-white font-semibold font-work-sans text-[20px] mb-1">
										{step.title}
									</h3>
									<p className="text-gray-300 font-public-sans text-[16px] tracking-tight">
										{step.description}
									</p>
								</div>
							</div>
						</div>
					))}
				</div>

				<Button onClick={() => {
					localStorage.setItem('redirectAfterLogin', '/subscription');
					router.push('/login');
				}} className="font-work-sans w-[297px] font-medium text-[20px] flex items-center gap-[10px] h-[47px]">
					<TbLogin className="!w-6 !h-6" />
					Signup & Login
				</Button>

			</section>}

			{/* SECTION 3 */}
			<section className={`${user ? 'pt-0' : ''} max-w-[1440px] mx-auto min-h-screen max-[1200px]:px-4 py-16 mb-10 px-10 flex flex-col justify-center md:justify-between items-center gap-10`}>

				<FadeInSection className="w-[1344px]flex flex-col gap-[12px] items-center">
					<h2 className="text-[32px] max-[1200px]:text-center font-semibold font-work-sans tracking-tighter">Subscriptions, Mr. White has?</h2>
					<p className="text-[20px] max-[1200px]:text-[16px] text-center font-light font-public-sans">Mr. White's available subscriptions</p>
				</FadeInSection>

				<div className="flex max-[1200px]:flex-col max-[1200px]:items-center gap-[40px]">

					<SubscriptionCard
						title="Mr. White's Companion Crew - FREE Plan"
						subtitle="Enjoy a FREE account with Benefits of Mr. White"
						description="Mr. White guides dogs and their humans toward a fulfilling life with free daily tips on X and other socials @MrWhiteAIBuddy and his website at Mr.WhiteAIBuddy.com. Discover toys, rituals, and training to deepen your bond, plus proven products for health and care, backed by Anahata Graceland's 50+ years of expertise."
						price="Free!"
						priceSubtext="*Lifetime free subscription"
						amount={0}
						features={[
							{
								title: "Access Your Personal Portal Anytime",
								image: "/assets/subscription-1.webp",
								description: "Step into your personal portal with Mr. White, where tailored guidance, and wisdom for you and your companion are available 24/7. It also includes an ongoing history of your priceless queries about your dog."
							},
							{
								title: "Unlock Expert Canine Knowledge",
								image: "/assets/subscription-1.webp",
								description: "Gain insight into your dog's history, needs, and bond with humans through Mr.White's vast data and real-world experience. Get tailored input on questions you raise such as: training and activity recommendations to strengthen your connection. Benefit from fun events, networks, and practices that honor dogs as souls, fostering happier lives together."
							},
							{
								title: "Top Product Recommendations with Care",
								image: "/assets/subscription-3.webp",
								description: "Mr. White reviews products with Anahata Graceland's 50+ years of expertise—those used in her kennel earn a star, as do all we recommend. We focus on quality, longevity, safety, and dog approval, gathering marketplace feedback to ensure the best. With little pet industry regulation, we deliver trusted choices."
							},
							{
								title: "A Unique Dog Lover's Community",
								image: "/assets/subscription-4.webp",
								description: "Mr. White Gathers his pack members to share the unending knowledge and great ideas person to person. Meet new friends, create meet-ups and enjoy accessing a resource that will last a lifetime."
							},
							{
								title: "A Thriving Network for Dog Welfare Professionals ",
								image: "/assets/subscription-5.webp",
								description: "Mr. White supports veterinarians, groomers, trainers, product companies, event organizers, educators, nonprofits, dog park leaders, and wellness practitioners with reduced-rate pack membership. Access dog family records, exchange insights in a fun network, and connect with families to grow your craft and deliver quality care. "
							}
						]}
					/>

					<SubscriptionCard
						title="Mr. White's Elite Pack"
						subtitle="Everything in the FREE Account Plus these Invaluable Services"
						description="Unlock the Elite Pack and step into (Your Dog's Name) Legacy of Love Living Hub, your AI-powered sanctuary for celebrating and caring for your cherished companion. This one-of-a-kind living hub securely stores vital records, sets timely medication alerts, tracks vaccinations, and beautifully organizes stories and photos from your shared journey. It's truly designed to keep every memory you cherish while helping life move smoothly and safely. Plus, you can effortlessly print a custom book of any section you choose, with Mr. White guiding you every step of the way. Inspired by The Way of the Dog by Anahata Graceland, this innovative personal assistant captures every milestone and joy you've shared—offering a connection and memory archive unmatched anywhere else."
						price="$19.95/Month - Save 20% on yearly plan"
						priceSubtext="Includes dedicated human support!"
						amount={19.95}
						features={[
							{
								title: "Comprehensive Memory & Care Archive",
								image: "/assets/subscription-6.webp",
								description: "Securely store vital records, vaccination history, medication alerts, vet visits, milestones, photos, and stories—all organized beautifully in one place and accessible 24/7. Preserve every cherished moment while keeping your dog's care on track."
							},
							{
								title: "Personalized Health & Savings Tracker",
								image: "/assets/subscription-7.webp",
								description: "Avoid duplicate vet costs with your pups full health history at your fingertips. Receive expert care tips and timely reminders tailored to support extending your dog's life and wellbeing."
							},
							{
								title: "BlockchainDNA NFT Legacy",
								image: "/assets/subscription-8.webp",
								description: "Protect your family bond with a unique BlockchainDNA NFT that verifies your dog's records on the blockchain, ensuring an unbreakable, verifiable legacy passed down through generations, fully transferrable."
							},
							{
								title: "Interspecies Culture & Bonding Guidance",
								image: "/assets/subscription-9.webp",
								description: "With over 50 years of experience, Anahata Graceland and Mr. White offer unique insights and guidance to help you nurture a deep, respectful relationship that honors your dog and helps you build a bond as equals each with your own roles in one family."
							},
							{
								title: "Trusted Local Services & Dog-Friendly Travel",
								image: "/assets/subscription-10.webp",
								description: "Easily find and review vets, groomers, and discover dog-friendly hotels, restaurants, and destinations—making every outing a joyful adventure."
							},

							{
								title: "Turn Memories into a Treasured Book",
								image: "/assets/subscription-10.webp",
								description: "One of the most special features of your Living Legacy of Love Dog Hub subscription is the ability to create a beautifully personalized book. Whether you want to commemorate your dog's first birthday, a memorable milestone, or simply preserve your favorite photos and stories, you can easily select any section of the Living Hub to print as a keepsake. This tangible collection of memories is perfect for sharing with family and friends or cherishing for years to come—a lasting tribute to the unique journey you share with your companion."
							},
							{
								title: "Private Dog Family Community",
								image: "/assets/subscription-11.webp",
								description: "Connect with fellow dog lovers in an exclusive space to share stories, plan meetups, and strengthen your bonds within a warm, vibrant community."
							},
							{
								title: "Exclusive Discounts & Early Access",
								image: "/assets/subscription-12.webp",
								description: "Enjoy lifetime 5% discounts on qualified recommended products and get first access to new offerings from trusted partners."
							},
							{
								title: "Fetch Subscription – Hassle-Free Essentials Tracking",
								image: "/assets/subscription-12.webp",
								description: "Never worry about running out—get personalized alerts on food, medications, supplements, and more, right on your phone, supported by Mr. White."
							}
						]}
						isPremium={true}
					/>

				</div>

			</section>

		</div>
	)
}

export default SubscriptionPage;