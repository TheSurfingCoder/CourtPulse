import React from 'react'
import { MapPinIcon } from 'lucide-react'
export default function Header() {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200 px-4 py-3">
      <div className="flex items-center">
        <div className="flex items-center gap-2">
          <div className="bg-gradient-to-r from-orange-500 to-red-500 p-2 rounded-lg shadow-sm">
            <MapPinIcon className="h-5 w-5 text-white" />
          </div>
          <h1 className="text-xl font-bold text-gray-800">CourtPulse</h1>
        </div>
        <p className="ml-4 text-sm text-gray-500 hidden sm:block">
          Discover and explore sports courts near you
        </p>
      </div>
    </header>
  )
}