"use client"

import { useEffect, useState } from 'react';
import mqtt from 'mqtt';
import { StationDetails } from "@/lib/types";
import StationDetailsCard from "@/components/station-details-card";

export default function Dashboard() {
    const [data, setData] = useState<StationDetails[]>();

    console.log("STATE", data)
    console.log("quueue", data?.[0]?.queue)

    useEffect(() => {
        const client = mqtt.connect('ws://broker.hivemq.com:8000/mqtt');

        client.on('connect', () => {
            console.log('Connected');
            client.subscribe('charging_ahead/dashboard/update', function (err) {
                if (!err) {
                    console.log('Subscribed to topic');
                }
            });
        });

        client.on('message', function (topic, message) {
            const msg = message.toString();
            const jsonData = JSON.parse(msg);

            console.log("Updated data", jsonData)

            const newStations: StationDetails[] = Array.isArray(jsonData) ? jsonData : [jsonData];

            setData(currentData => {
                if (!currentData || currentData.length === 0) {
                    return newStations;
                }

                const updatedData: StationDetails[] = currentData.map((station: StationDetails) => {
                    const updateStation = newStations.find(ns => ns.id === station.id);
                    if (updateStation) {
                        return convertStationData(updateStation)
                    }
                    return station;
                });

                return updatedData;
            });
        });

        return () => {
            client.end();
        };
    }, []);

    function convertStationData(station: StationDetails) {
        return {
            id: station.id,
            stationName: station.stationName,
            availableChargers: station.availableChargers,
            unavailableChargers: station.unavailableChargers,
            queue: station.queue,
            chargers: station.chargers.map((charger: any) => ({
                id: charger.id,
                carId: charger.carId,
                operational: charger.operational,
                charging: charger.charging,
                assigned: charger.assigned
            }))
        };
    }

    return (
        <main className="flex flex-col">
            <div className="w-full max-w-6xl p-5">
                <div className="mb-32">
                    <h1 className="font-bold text-3xl text-center">Dashboard</h1>
                </div>
                <div>
                    {data && (
                        <div className="flex flex-col gap-20 items-center">
                            {data.map((stationDetails: StationDetails, index) => (
                                <StationDetailsCard key={index} stationDetails={stationDetails} />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </main>
    );

}
