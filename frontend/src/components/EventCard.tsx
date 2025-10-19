import Image from "next/image";
import Link from "next/link";

interface EventCardProps {
  title: string;
  date: string;
  description: string;
  imageSrc: string;
  id?: string;
}

const EventCard = ({ title, date, description, imageSrc, id }: EventCardProps) => {
  return (
    <div className="max-[1300px]:p-6 max-[1300px]:gap-6 p-10 flex gap-10 items-center flex-row bg-white/10 text-white overflow-hidden rounded-lg shadow-lg w-full">
      <div className="relative h-[258px] w-[258px] min-w-[280px]">
        <Image
          src={imageSrc}
          alt={title}
          fill
          className="object-cover"
        />
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="text-2xl font-work-sans font-semibold max-[1300px]:text-[20px]">{title}</h3>
        <p className="text-sm text-gray-300">{date}</p>
        <div className="space-y-3">
          <p className="font-public-sans max-[1300px]:text-[14px]">{description}</p>
          <p className="font-public-sans max-[1300px]:text-[14px]">It is a fun day of showing puppies, dogs and meeting those who have Royal Frenchels of all ages. There are prizes, gifts, photo shoots and a parade along with the Royal Family Jazz Band playing joyfully in the background!</p>
          <p className="font-public-sans max-[1300px]:text-[14px]">Over the years the Royal Jazz Band has won local acclaim! This is a group of entertainers who have Royal Frenchels and who enjoy sharing the day by playing great music for all to enjoy.</p>
        </div>
        {id && (
          <Link href={`/events/${id}`} className="mt-4 text-sm text-blue-400 hover:text-blue-300">
            Learn more
          </Link>
        )}
      </div>
    </div>
  );
};

export default EventCard; 