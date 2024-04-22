import { Charger } from "@/lib/types";

type ChargerProps = {
    charger: Charger;
}

export default function ChargerCard({ charger }: ChargerProps) {
    const getStatusColor = (): string => {
        if (!charger.operational) {
            return 'red';
        } else if (charger.assigned || charger.charging) {
            return 'yellow';
        } else {
            return 'green';
        }
    };

    const isChargerInUse = charger.assigned || charger.charging;

    return (
        <div className="flex flex-col gap-5 border border-gray-300 rounded-md shadow-sm p-4 w-64">
            <div className="flex items-center justify-between">
                <div>
                    <p className="font-medium">Charger {charger.id}</p>
                </div>
                <div style={{
                    height: '15px',
                    width: '15px',
                    borderRadius: '50%',
                    backgroundColor: getStatusColor(),
                    border: '1px solid black'
                }}/>
            </div>
            <div>
                {!charger.operational ? (
                    <p className="text-sm text-gray-500">Need of service</p>
                ) : isChargerInUse ? (
                    <p className="text-sm text-gray-500">
                        {charger.charging ?
                            <><span className="font-semibold">{charger.carId}</span> is charging</> :
                            charger.assigned && !charger.charging ?
                                <><span className="font-semibold">{charger.carId}</span> is assigned</> :
                                "Available"
                        }
                    </p>
                ) : (
                    <p className="text-sm text-gray-500">Available</p>
                )}
            </div>
        </div>
    );
}
