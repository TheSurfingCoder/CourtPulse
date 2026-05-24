'use client';

import { useState } from 'react';
import { X, MapPin } from 'lucide-react';

interface CreateCourtModalProps {
  isOpen: boolean;
  onClose: () => void;
  lat: number | null;
  lng: number | null;
  onCreated: (data: {
    cluster_group_name: string;
    name: string | null;
    type: string;
    lat: number;
    lng: number;
    surface: string;
    is_public: boolean;
    has_lights: boolean | null;
  }) => Promise<void>;
  availableSports: string[];
  availableSurfaces: string[];
}

export default function CreateCourtModal({
  isOpen,
  onClose,
  lat,
  lng,
  onCreated,
  availableSports,
  availableSurfaces,
}: CreateCourtModalProps) {
  const [formData, setFormData] = useState({
    cluster_group_name: '',
    name: '',
    type: '',
    surface: '',
    is_public: 'true',
    has_lights: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  if (!isOpen || lat === null || lng === null) return null;

  const validate = (): string[] => {
    const errs: string[] = [];
    if (!formData.cluster_group_name.trim()) {
      errs.push('Facility name is required');
    } else if (formData.cluster_group_name.trim().length < 2) {
      errs.push('Facility name must be at least 2 characters');
    } else if (formData.cluster_group_name.trim().length > 100) {
      errs.push('Facility name must be less than 100 characters');
    }
    if (!formData.type) errs.push('Sport type is required');
    if (!formData.surface) errs.push('Surface type is required');
    if (formData.name.trim().length > 100) errs.push('Court name must be less than 100 characters');
    return errs;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs = validate();
    if (errs.length > 0) {
      setErrors(errs);
      return;
    }
    setErrors([]);
    setIsSubmitting(true);
    try {
      await onCreated({
        cluster_group_name: formData.cluster_group_name.trim(),
        name: formData.name.trim() || null,
        type: formData.type,
        lat,
        lng,
        surface: formData.surface,
        is_public: formData.is_public === 'true',
        has_lights: formData.has_lights === 'true' ? true : formData.has_lights === 'false' ? false : null,
      });
      // Only reset the form on success. On failure the parent re-throws after
      // showing an error toast, so the user can fix and retry without re-typing.
      setFormData({ cluster_group_name: '', name: '', type: '', surface: '', is_public: 'true', has_lights: '' });
    } catch {
      // User-facing error already toasted by the parent; swallow here so React
      // doesn't log an unhandled rejection.
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold">Add Court</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        <div className="px-6 pt-4 flex items-center gap-2 text-sm text-gray-500">
          <MapPin className="h-4 w-4 text-blue-500 shrink-0" />
          <span>{lat.toFixed(5)}, {lng.toFixed(5)}</span>
        </div>

        {errors.length > 0 && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <ul className="text-sm text-red-700 space-y-1">
              {errors.map((err, i) => <li key={i}>{err}</li>)}
            </ul>
          </div>
        )}

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Facility Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.cluster_group_name}
              onChange={(e) => setFormData({ ...formData, cluster_group_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., Rolph Playground"
              autoFocus
            />
            <p className="text-xs text-gray-500 mt-1">The main name shown on the map</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Court Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., basketball court (2 hoops)"
            />
            <p className="text-xs text-gray-500 mt-1">Optional: specific court identifier</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Sport Type <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select sport...</option>
              {availableSports.map((sport) => (
                <option key={sport} value={sport}>{sport.charAt(0).toUpperCase() + sport.slice(1)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Surface <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.surface}
              onChange={(e) => setFormData({ ...formData, surface: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Select surface...</option>
              {availableSurfaces.filter(s => s.toLowerCase() !== 'unknown').map((surface) => (
                <option key={surface} value={surface}>{surface.charAt(0).toUpperCase() + surface.slice(1)}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Public Access</label>
            <select
              value={formData.is_public}
              onChange={(e) => setFormData({ ...formData, is_public: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="true">Public</option>
              <option value="false">Private</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Has Lights</label>
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

          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? 'Adding...' : 'Add Court'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
