'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

interface CourtData {
  id: number;
  name: string;
  type: string;
  lat: number;
  lng: number;
  surface: string;
  is_public: boolean;
  school: boolean;
  cluster_group_name: string;
  created_at: string;
  updated_at: string;
}

interface EditCourtModalProps {
  isOpen: boolean;
  onClose: () => void;
  court: CourtData | null;
  onSave: (updatedCourt: CourtData) => void;
}

export default function EditCourtModal({ isOpen, onClose, court, onSave }: EditCourtModalProps) {
  const [formData, setFormData] = useState({
    cluster_group_name: '',
    name: '',
    type: '',
    surface: '',
    is_public: '',
    school: ''
  });

  useEffect(() => {
    if (court) {
      setFormData({
        cluster_group_name: court.cluster_group_name || '',
        name: court.name || '',
        type: court.type || '',
        surface: court.surface || '',
        is_public: court.is_public ? 'true' : (court.is_public === false ? 'false' : ''),
        school: court.school ? 'true' : 'false'
      });
    }
  }, [court]);

  if (!isOpen || !court) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const updatedCourt: CourtData = {
      ...court,
      cluster_group_name: formData.cluster_group_name.trim() || null,
      name: formData.name.trim() || null,
      type: formData.type.trim() || court.type,
      surface: formData.surface.trim() || court.surface,
      is_public: formData.is_public === 'true' ? true : formData.is_public === 'false' ? false : court.is_public,
      school: formData.school === 'true'
    };

    onSave(updatedCourt);
    onClose();
  };

  const sportOptions = ['basketball', 'tennis', 'soccer', 'volleyball', 'pickleball'];
  const surfaceOptions = ['asphalt', 'concrete', 'grass', 'clay', 'other'];

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Edit Court</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Main Title (Display Name)
            </label>
            <input
              type="text"
              value={formData.cluster_group_name}
              onChange={(e) => setFormData({ ...formData, cluster_group_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Rolph Playground"
              required
            />
            <p className="text-xs text-gray-500 mt-1">This is the main title shown on the map</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Court Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., basketball court (2 hoops)"
            />
            <p className="text-xs text-gray-500 mt-1">Optional: specific court name</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sport Type
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select sport...</option>
              {sportOptions.map((sport) => (
                <option key={sport} value={sport}>
                  {sport.charAt(0).toUpperCase() + sport.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Surface
            </label>
            <select
              value={formData.surface}
              onChange={(e) => setFormData({ ...formData, surface: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="">Select surface...</option>
              {surfaceOptions.map((surface) => (
                <option key={surface} value={surface}>
                  {surface.charAt(0).toUpperCase() + surface.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Public Access
            </label>
            <select
              value={formData.is_public}
              onChange={(e) => setFormData({ ...formData, is_public: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Unknown</option>
              <option value="true">Public</option>
              <option value="false">Private</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              School
            </label>
            <select
              value={formData.school}
              onChange={(e) => setFormData({ ...formData, school: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            >
              <option value="false">No</option>
              <option value="true">Yes</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

