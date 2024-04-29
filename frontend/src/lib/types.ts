

export type StationDetails = {
    id: string
    stationName: string,
    availableChargers: number,
    unavailableChargers: number,
    queue: string[],
    chargers: Charger[]
}


export type Charger = {
    id: string,
    carId: string,
    operational: boolean,
    charging: boolean,
    assigned: boolean
}

export type AppMode = {
    name: string,
    subtitle: string,
    avatar: string,
    href: string
}


export type StationData = {
    id: string;
    name: string;
    availableChargers: number;
    queue: string[];
}

export type Station = {
    command: string;
    stations: StationData[];
}

