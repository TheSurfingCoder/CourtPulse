'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { toast } from 'sonner';

interface CourtData {
  id: number;
  name: string | null;
  type: string;
  lat: number;
  lng: number;
  surface: string;
  is_public: boolean | null;
  has_lights: boolean | null;
  school: boolean;
  cluster_group_name: string | null;
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
    has_lights: '',
    school: ''
  });

  const [sportOptions, setSportOptions] = useState<string[]>([]);
  const [surfaceOptions, setSurfaceOptions] = useState<string[]>([]);
  const [isLoadingMetadata, setIsLoadingMetadata] = useState(false);

  // Fetch metadata on mount
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        setIsLoadingMetadata(true);
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';
        const response = await fetch(`${apiUrl}/api/courts/metadata`);
        if (response.ok) {
          const result = await response.json();
          if (result.success && result.data) {
            setSportOptions(result.data.sports || []);
            setSurfaceOptions(result.data.surfaceTypes || []);
          }
        }
      } catch (error) {
        console.error('Failed to fetch metadata:', error);
        toast.error('Unable to load edit options', {
          description: 'Sport and surface options may be unavailable.'
        });
      } finally {
        setIsLoadingMetadata(false);
      }
    };

    fetchMetadata();
  }, []);

  useEffect(() => {
    if (court) {
      setFormData({
        cluster_group_name: court.cluster_group_name || '',
        name: court.name || '',
        type: court.type || '',
        surface: court.surface || '',
        is_public: court.is_public ? 'true' : (court.is_public === false ? 'false' : ''),
        has_lights: court.has_lights ? 'true' : (court.has_lights === false ? 'false' : ''),
        school: court.school ? 'true' : 'false'
      });
    }
  }, [court]);

  if (!isOpen || !court) return null;

  // Validate form and return array of errors
  const validateForm = (): string[] => {
    const errors: string[] = [];
    
    if (!formData.cluster_group_name.trim()) {
      errors.push('Main title is required');
    } else if (formData.cluster_group_name.trim().length < 2) {
      errors.push('Main title must be at least 2 characters');
    } else if (formData.cluster_group_name.trim().length > 100) {
      errors.push('Main title must be less than 100 characters');
    }
    
    if (!formData.type) {
      errors.push('Sport type is required');
    }
    
    if (!formData.surface) {
      errors.push('Surface type is required');
    }
    
    if (formData.name && formData.name.trim().length > 100) {
      errors.push('Court name must be less than 100 characters');
    }
    
    return errors;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate before submitting
    const errors = validateForm();
    if (errors.length > 0) {
      toast.error('Please fix the following errors', {
        description: errors.join('. ')
      });
      return;
    }
    
    const updatedCourt: CourtData = {
      ...court,
      cluster_group_name: formData.cluster_group_name.trim() || null,
      name: formData.name.trim() || null,
      type: formData.type.trim() || court.type,
      surface: formData.surface.trim() || court.surface,
      is_public: formData.is_public === 'true' ? true : formData.is_public === 'false' ? false : null,
      has_lights: formData.has_lights === 'true' ? true : formData.has_lights === 'false' ? false : null,
      school: formData.school === 'true'
    };

    onSave(updatedCourt);
    onClose();
  };

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
              Has Lights
            </label>
            <select
              value={formData.has_lights}
              onChange={(e) => setFormData({ ...formData, has_lights: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Unknown</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
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

