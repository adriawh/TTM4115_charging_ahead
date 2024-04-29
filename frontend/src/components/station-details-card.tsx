"use client"

import {StationDetails} from "@/lib/types";
import ChargerCard from "@/components/charger-card";
import QueueCard from "@/components/queue-card";

type StationDetailsProps = {
    stationDetails: StationDetails

}
export default function StationDetailsCard(props: StationDetailsProps) {

    console.log("STation name", props.stationDetails.stationName)


    return (
        <div className="flex flex-col">
            <div className="mb-5">
                <p className="text-lg font-semibold">Station {props.stationDetails.stationName}</p>
            </div>
            <div className="flex flex-col gap-10">
                <div className="w-full flex flex-wrap gap-2">
                    {props.stationDetails.chargers.map((charger, index) => (
                        <div className="p-2" key={index}>
                            <ChargerCard charger={charger}/>
                        </div>
                    ))}
                </div>
                <div className="w-full p-2">
                    <div style={{height: '100%'}}>
                        <QueueCard queue={props.stationDetails.queue}/>
                    </div>
                </div>
            </div>
        </div>
    );

}