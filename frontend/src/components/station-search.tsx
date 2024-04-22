import {Station, StationData, StationDetails} from "@/lib/types";
import ChargerCard from "@/components/charger-card";
import QueueCard from "@/components/queue-card";

type StationSearchProps = {
    station: StationData

}
export default function StationSearch(props: StationSearchProps) {


    return (
        <div className="flex flex-col border border-gray-300 rounded-md shadow-sm p-4 w-80">
            <div className="mb-5">
                <p className="text-lg font-semibold">{props.station.name}</p>
            </div>
            <div className="flex flex-col gap-2">
                <div>
                    <p className="text-xs text-gray-500">
                        Number of available chargers: <span className="font-semibold">{props.station.availableChargers}</span>
                    </p>
                </div>
                <div>
                    <p className="text-xs text-gray-500">
                        Number of cars currently in queue: <span className="font-semibold">{props.station.queue.length}</span>
                    </p>
                </div>
            </div>
        </div>
    );

}