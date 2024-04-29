import { StationData } from "@/lib/types";
import {Button} from "antd";
import {PlugZap2} from "lucide-react";



type StationSearchProps = {
    station: StationData
    publishCommand: (command: any) => void;

}
export default function StationSearch(props: StationSearchProps) {
    const { station, publishCommand } = props;

    const registerToQueue = () => {
        const carId = generateRandomId();
        const command = { command: "register_to_queue", station_id: station.id, car_id: carId };
        publishCommand(command);
    };

    function generateRandomId() {
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < 10; i++) {
            result += characters.charAt(Math.floor(Math.random() * characters.length));
        }
        return result;
    }

    return (
        <div className="flex flex-col border border-gray-300 rounded-md shadow-sm p-4 w-80">
            <div className="flex justify-between">
                <div className="mb-5">
                    <p className="text-lg font-semibold">{station.name}</p>
                </div>
                <div className="mb-20 items-center flex text-center">
                      <Button
                          icon={<PlugZap2 height={18} width={18} />}
                          onClick={registerToQueue}
                          style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                      >
                          Add to queue
                      </Button>
                </div>
            </div>
            <div className="flex flex-col gap-2">
                <div>
                    <p className="text-xs text-gray-500">
                        Number of available chargers: <span className="font-semibold">{station.availableChargers} / {station.chargers.length}</span>
                    </p>
                </div>
                <div>
                    <p className="text-xs text-gray-500">
                        Number of cars currently in queue: <span className="font-semibold">{station.queue.length}</span>
                    </p>
                </div>
            </div>
        </div>
    );
}