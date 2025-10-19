"use client"

import FadeInSection from "@/components/FadeInSection";
import ImagePop from "@/components/ImagePop";
import Image from "next/image";
import EventCard from "@/components/EventCard";

const HubPage = () => {
    // Sample events data - in a real app, this would come from an API or database
    const events = [
        {
            id: "royal-frenchel-day",
            title: "Royal Frenchel Day",
            date: "August 31st 2019",
            description: "Royal Frenchel Day is a fun celebration those who have Royal Frenchel Bulldogs gather– The Royal Family Annual Reunion! Anahata Graceland \"Windy\" the creator of the breed, the staff of Royal Frenchel Bulldogs and volunteers puts on the event to honor the growing \"Royal Family\" and share with the local community about this great French Bulldog hybrid.",
            imageSrc: "/assets/event.png"
        },
        {
            id: "puppy-training-workshop",
            title: "Puppy Training Workshop",
            date: "October 15th 2023",
            description: "Learn essential training techniques for your new puppy. Covering basic commands, socialization, and behavior management.",
            imageSrc: "/assets/event.png"
        },
        {
            id: "dog-health-seminar",
            title: "Dog Health Seminar",
            date: "November 5th 2023",
            description: "Join our veterinarians for a comprehensive seminar on maintaining your dog's health. Topics include nutrition, preventative care, and common health issues.",
            imageSrc: "/assets/event.png"
        }
    ];

    return (
        <div className="flex flex-col gap-y-24 overflow-x-hidden">

            {/* SECTION 1  */}
            <section className="h-[400px] max-[850px]:h-[200px] flex flex-col justify-center items-center w-full relative bg-[url('/assets/event-hero.png')] bg-cover bg-center">
                <div className="absolute inset-0 bg-black/40"></div>
                <div className="z-20">
                    <h1 className="max-[1200px]:text-[32px] text-[40px] font-work-sans font-semibold text-center">Mr White Events</h1>
                    <p className="max-[1200px]:text-[16px] text-[20px] font-public-sans font-light text-center">A list of events hosted by Mr White </p>
                </div>
            </section>

            {/* EVENTS SECTION */}
            <section className="max-w-[1440px] mx-auto flex flex-col gap-10 justify-center items-center px-10 pb-16 w-full">
                    <h2 className="text-3xl font-work-sans font-semibold mb-8 text-center">Upcoming & Past Events</h2>
                    <div className="flex flex-col gap-8 w-full">
                        {events.map((event) => (
                            <EventCard
                                key={event.id}
                                id={event.id}
                                title={event.title}
                                date={event.date}
                                description={event.description}
                                imageSrc={event.imageSrc}
                            />
                        ))}
                    </div>
            </section>

        </div>
    )
}

export default HubPage;