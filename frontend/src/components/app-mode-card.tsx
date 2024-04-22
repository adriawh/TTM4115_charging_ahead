import {AppMode} from "@/lib/types";

type AppModeCard = {
    appMode: AppMode;
}

export default function AppModeCard({ appMode }: AppModeCard) {

    return (
        <div className="border flex gap-4 border-gray-300 rounded-md shadow-sm p-4 h-36">
            <div className="flex flex-col gap-4">
                <div>
                    <p className="font-medium">{appMode.name}</p>
                </div>
                <div className="w-64">
                    <p className="text-sm text-gray-500">{appMode.subtitle}</p>
                </div>
            </div>

        </div>

    );
}
