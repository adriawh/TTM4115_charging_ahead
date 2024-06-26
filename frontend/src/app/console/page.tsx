"use client"

import { useEffect, useState } from 'react';
import mqtt from 'mqtt';
import {Station} from "@/lib/types";
import StationSearch from "@/components/station-search";
import { Input,  Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';


const MQTT_BROKER = 'broker.hivemq.com';
const MQTT_PORT = 8000;
const MQTT_TOPIC_INPUT = 'charging_ahead/queue/server_input';
const MQTT_TOPIC_OUTPUT = 'charging_ahead/queue/server_output';

export default function Console() {
    const [client, setClient] = useState<mqtt.MqttClient>();
    const [stations, setStations] = useState<Station>();

    console.log("Stations", stations)

    useEffect(() => {
        const connectUrl = `ws://${MQTT_BROKER}:${MQTT_PORT}/mqtt`;
        const client = mqtt.connect(connectUrl);
        client.on('connect', () => {
            console.log('Connected to MQTT Broker');
            client.subscribe(MQTT_TOPIC_OUTPUT);
        });

        client.on('message', (topic, payload) => {
            const message = JSON.parse(payload.toString());

            console.log("Data fra server", message)

            if (message.command === 'available_chargers') {
                setStations(message);
            }
        });

        setClient(client);

        return () => {
            client.end();
        };
    }, []);

    const publishCommand = (command: any) => {
        if (client) {
            const payload = JSON.stringify(command);
            client.publish(MQTT_TOPIC_INPUT, payload, { qos: 2 });
        }
    };


    const handleChargerStatus = (searchString: string) => {
        const command = { command: "status_available_charger", search_string: searchString };
        publishCommand(command);
    };


    return (
        <div className="flex flex-col gap-5">
            <div className="w-full max-w-6xl p-5">
                <div className="mb-32">
                    <h1 className="font-bold text-3xl text-center">Car Interface</h1>
                </div>
                <div className="flex flex-col">
                    <div className="mb-8">
                        <p className="text-lg font-bold"> Charging stations </p>
                    </div>
                    <div className="mb-8">
                        <Input
                            placeholder="Search for location..."
                            onChange={(e) => handleChargerStatus(e.target.value)}
                            style={{width: 320}}
                            suffix={<SearchOutlined/>}
                        />
                    </div>
                    <div>
                        {stations?.stations ? (
                            <div className="flex flex-col gap-7 items-center">
                                {stations.stations.map((station, index) => (
                                    <StationSearch key={index} station={station} publishCommand={publishCommand} />
                                ))}
                            </div>
                        ) : <Empty/>
                        }
                    </div>
                </div>
            </div>
        </div>
    );
}

