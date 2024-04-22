
type QueueCardProps = {
    queue: string[];
}

export default function QueueCard({ queue }: QueueCardProps) {

    return (
        <div className="border flex flex-col gap-3 border-gray-300 rounded-md shadow-sm p-4">
            <div>
                <p className="font-medium"> Queue </p>

            </div>
            <div className="flex flex-col gap-2">
                {queue.map((car: string, index) => (
                    <p key={index} className="text-gray-500 text-sm"> Car: {car}</p>
                ))}
            </div>
        </div>

    );
}
