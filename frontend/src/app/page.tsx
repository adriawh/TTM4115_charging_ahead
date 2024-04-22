"use client"


import {AppMode} from "@/lib/types";
import AppModeCard from "@/components/app-mode-card";
import Link from "next/link";


export default function Home() {

    const appModes: AppMode[] = [
        {
            name: "Tesla Console",
            subtitle: "The ui for the tesla. Here you can go into queue and see available chargers",
            avatar: "",
            href: "/console"
        },
        {
            name: "Dashboard",
            subtitle: "A dashboard for statistics. Get an overview of all the chargers and queue",
            avatar: "",
            href: "/dashboard"
    }]

    return (
        <main>
            <div className="mb-32">
                <p className="font-bold text-3xl text-center"> Charging Ahead - TTM4115 </p>
            </div>
            <div className="flex gap-2">
                {appModes.map((appMode, index) => (
                    <Link key={index} href={appMode.href}>
                        <AppModeCard appMode={appMode}/>
                    </Link>

                ))}
            </div>

        </main>
    );

}
