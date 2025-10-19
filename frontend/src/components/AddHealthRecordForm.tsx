'use client';

import React, { useState } from 'react';
import { X, Calendar, DollarSign, FileText, Tag, User, Building, MapPin } from 'lucide-react';

// Types for form data
interface HealthRecordFormData {
    record_type: string;
    title: string;
    description: string;
    record_date: string;
    pet_id?: number;
    veterinarian_name: string;
    clinic_name: string;
    clinic_address: string;
    cost: string;
    insurance_covered: boolean;
    insurance_amount: string;
    notes: string;
    tags: string;
    vaccination_details?: {
        vaccine_name: string;
        vaccine_type: string;
        batch_number: string;
        manufacturer: string;
        administration_date: string;
        next_due_date: string;
        adverse_reactions: string;
    };
    medication_details?: {
        medication_name: string;
        dosage: string;
        frequency: string;
        start_date: string;
        end_date: string;
        prescribed_by: string;
        reason: string;
        side_effects: string;
    };
}

interface AddHealthRecordFormProps {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (data: HealthRecordFormData) => Promise<void>;
}

const RECORD_TYPES = [
    { value: 'vaccination', label: 'Vaccination' },
    { value: 'vet_visit', label: 'Vet Visit' },
    { value: 'medication', label: 'Medication' },
    { value: 'allergy', label: 'Allergy' },
    { value: 'surgery', label: 'Surgery' },
    { value: 'injury', label: 'Injury' },
    { value: 'checkup', label: 'Checkup' },
    { value: 'emergency', label: 'Emergency' },
    { value: 'dental', label: 'Dental Care' },
    { value: 'grooming', label: 'Grooming' }
];

const AddHealthRecordForm: React.FC<AddHealthRecordFormProps> = ({
    isOpen,
    onClose,
    onSubmit
}) => {
    const [formData, setFormData] = useState<HealthRecordFormData>({
        record_type: '',
        title: '',
        description: '',
        record_date: '',
        veterinarian_name: '',
        clinic_name: '',
        clinic_address: '',
        cost: '',
        insurance_covered: false,
        insurance_amount: '',
        notes: '',
        tags: '',
    });

    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState<{ [key: string]: string }>({});

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        const { name, value, type } = e.target;

        if (type === 'checkbox') {
            const checked = (e.target as HTMLInputElement).checked;
            setFormData(prev => ({ ...prev, [name]: checked }));
        } else {
            setFormData(prev => ({ ...prev, [name]: value }));
        }

        // Clear error when user starts typing
        if (errors[name]) {
            setErrors(prev => ({ ...prev, [name]: '' }));
        }
    };

    const handleNestedInputChange = (section: 'vaccination_details' | 'medication_details', field: string, value: string) => {
        setFormData(prev => ({
            ...prev,
            [section]: {
                ...prev[section],
                [field]: value
            }
        }));
    };

    const validateForm = (): boolean => {
        const newErrors: { [key: string]: string } = {};

        if (!formData.record_type) newErrors.record_type = 'Record type is required';
        if (!formData.title) newErrors.title = 'Title is required';
        if (!formData.record_date) newErrors.record_date = 'Date is required';

        // Validate cost if provided
        if (formData.cost && isNaN(parseFloat(formData.cost))) {
            newErrors.cost = 'Cost must be a valid number';
        }

        // Validate insurance amount if provided
        if (formData.insurance_amount && isNaN(parseFloat(formData.insurance_amount))) {
            newErrors.insurance_amount = 'Insurance amount must be a valid number';
        }

        // Type-specific validation
        if (formData.record_type === 'vaccination' && formData.vaccination_details) {
            if (!formData.vaccination_details.vaccine_name) {
                newErrors.vaccine_name = 'Vaccine name is required';
            }
            if (!formData.vaccination_details.administration_date) {
                newErrors.administration_date = 'Administration date is required';
            }
        }

        if (formData.record_type === 'medication' && formData.medication_details) {
            if (!formData.medication_details.medication_name) {
                newErrors.medication_name = 'Medication name is required';
            }
            if (!formData.medication_details.start_date) {
                newErrors.start_date = 'Start date is required';
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!validateForm()) return;

        setLoading(true);
        try {
            await onSubmit(formData);
            // Reset form
            setFormData({
                record_type: '',
                title: '',
                description: '',
                record_date: '',
                veterinarian_name: '',
                clinic_name: '',
                clinic_address: '',
                cost: '',
                insurance_covered: false,
                insurance_amount: '',
                notes: '',
                tags: '',
            });
            onClose();
        } catch (error) {
            console.error('Error submitting form:', error);
        } finally {
            setLoading(false);
        }
    };

    const showVaccinationDetails = formData.record_type === 'vaccination';
    const showMedicationDetails = formData.record_type === 'medication';

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center p-6 border-b">
                    <h2 className="text-2xl font-bold text-gray-900">Add Health Record</h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Basic Information */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Record Type *
                            </label>
                            <select
                                name="record_type"
                                value={formData.record_type}
                                onChange={handleInputChange}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                                <option value="">Select record type</option>
                                {RECORD_TYPES.map(type => (
                                    <option key={type.value} value={type.value}>
                                        {type.label}
                                    </option>
                                ))}
                            </select>
                            {errors.record_type && (
                                <p className="mt-1 text-sm text-red-600">{errors.record_type}</p>
                            )}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Title *
                            </label>
                            <input
                                type="text"
                                name="title"
                                value={formData.title}
                                onChange={handleInputChange}
                                placeholder="Brief description of the record"
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            {errors.title && (
                                <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                            )}
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                <Calendar className="w-4 h-4 inline mr-1" />
                                Date *
                            </label>
                            <input
                                type="date"
                                name="record_date"
                                value={formData.record_date}
                                onChange={handleInputChange}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                            {errors.record_date && (
                                <p className="mt-1 text-sm text-red-600">{errors.record_date}</p>
                            )}
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                <Tag className="w-4 h-4 inline mr-1" />
                                Tags
                            </label>
                            <input
                                type="text"
                                name="tags"
                                value={formData.tags}
                                onChange={handleInputChange}
                                placeholder="Comma-separated tags"
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>

                    {/* Description */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            <FileText className="w-4 h-4 inline mr-1" />
                            Description
                        </label>
                        <textarea
                            name="description"
                            value={formData.description}
                            onChange={handleInputChange}
                            rows={3}
                            placeholder="Detailed description of the health record"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>

                    {/* Provider Information */}
                    <div className="border-t pt-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Provider Information</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <User className="w-4 h-4 inline mr-1" />
                                    Veterinarian Name
                                </label>
                                <input
                                    type="text"
                                    name="veterinarian_name"
                                    value={formData.veterinarian_name}
                                    onChange={handleInputChange}
                                    placeholder="Dr. Smith"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <Building className="w-4 h-4 inline mr-1" />
                                    Clinic Name
                                </label>
                                <input
                                    type="text"
                                    name="clinic_name"
                                    value={formData.clinic_name}
                                    onChange={handleInputChange}
                                    placeholder="Animal Hospital"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>
                        </div>

                        <div className="mt-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                <MapPin className="w-4 h-4 inline mr-1" />
                                Clinic Address
                            </label>
                            <textarea
                                name="clinic_address"
                                value={formData.clinic_address}
                                onChange={handleInputChange}
                                rows={2}
                                placeholder="Street address, City, State, ZIP"
                                className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>

                    {/* Cost Information */}
                    <div className="border-t pt-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Cost Information</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    <DollarSign className="w-4 h-4 inline mr-1" />
                                    Cost
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    name="cost"
                                    value={formData.cost}
                                    onChange={handleInputChange}
                                    placeholder="0.00"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                                {errors.cost && (
                                    <p className="mt-1 text-sm text-red-600">{errors.cost}</p>
                                )}
                            </div>

                            <div>
                                <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 mb-2">
                                    <input
                                        type="checkbox"
                                        name="insurance_covered"
                                        checked={formData.insurance_covered}
                                        onChange={handleInputChange}
                                        className="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50"
                                    />
                                    <span>Insurance Covered</span>
                                </label>
                            </div>

                            {formData.insurance_covered && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Insurance Amount
                                    </label>
                                    <input
                                        type="number"
                                        step="0.01"
                                        name="insurance_amount"
                                        value={formData.insurance_amount}
                                        onChange={handleInputChange}
                                        placeholder="0.00"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                    {errors.insurance_amount && (
                                        <p className="mt-1 text-sm text-red-600">{errors.insurance_amount}</p>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Vaccination Details */}
                    {showVaccinationDetails && (
                        <div className="border-t pt-6">
                            <h3 className="text-lg font-medium text-gray-900 mb-4">Vaccination Details</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Vaccine Name *
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.vaccination_details?.vaccine_name || ''}
                                        onChange={(e) => handleNestedInputChange('vaccination_details', 'vaccine_name', e.target.value)}
                                        placeholder="DHPP, Rabies, etc."
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                    {errors.vaccine_name && (
                                        <p className="mt-1 text-sm text-red-600">{errors.vaccine_name}</p>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Vaccine Type
                                    </label>
                                    <select
                                        value={formData.vaccination_details?.vaccine_type || ''}
                                        onChange={(e) => handleNestedInputChange('vaccination_details', 'vaccine_type', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="">Select type</option>
                                        <option value="core">Core</option>
                                        <option value="non-core">Non-core</option>
                                        <option value="lifestyle">Lifestyle</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Administration Date *
                                    </label>
                                    <input
                                        type="date"
                                        value={formData.vaccination_details?.administration_date || ''}
                                        onChange={(e) => handleNestedInputChange('vaccination_details', 'administration_date', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                    {errors.administration_date && (
                                        <p className="mt-1 text-sm text-red-600">{errors.administration_date}</p>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Next Due Date
                                    </label>
                                    <input
                                        type="date"
                                        value={formData.vaccination_details?.next_due_date || ''}
                                        onChange={(e) => handleNestedInputChange('vaccination_details', 'next_due_date', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Batch Number
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.vaccination_details?.batch_number || ''}
                                        onChange={(e) => handleNestedInputChange('vaccination_details', 'batch_number', e.target.value)}
                                        placeholder="Batch/Lot number"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Manufacturer
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.vaccination_details?.manufacturer || ''}
                                        onChange={(e) => handleNestedInputChange('vaccination_details', 'manufacturer', e.target.value)}
                                        placeholder="Vaccine manufacturer"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>
                            </div>

                            <div className="mt-4">
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Adverse Reactions
                                </label>
                                <textarea
                                    value={formData.vaccination_details?.adverse_reactions || ''}
                                    onChange={(e) => handleNestedInputChange('vaccination_details', 'adverse_reactions', e.target.value)}
                                    rows={3}
                                    placeholder="Any adverse reactions or side effects"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>
                        </div>
                    )}

                    {/* Medication Details */}
                    {showMedicationDetails && (
                        <div className="border-t pt-6">
                            <h3 className="text-lg font-medium text-gray-900 mb-4">Medication Details</h3>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Medication Name *
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.medication_details?.medication_name || ''}
                                        onChange={(e) => handleNestedInputChange('medication_details', 'medication_name', e.target.value)}
                                        placeholder="Medication name"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                    {errors.medication_name && (
                                        <p className="mt-1 text-sm text-red-600">{errors.medication_name}</p>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Dosage
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.medication_details?.dosage || ''}
                                        onChange={(e) => handleNestedInputChange('medication_details', 'dosage', e.target.value)}
                                        placeholder="e.g., 10mg, 1 tablet"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Frequency
                                    </label>
                                    <select
                                        value={formData.medication_details?.frequency || ''}
                                        onChange={(e) => handleNestedInputChange('medication_details', 'frequency', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    >
                                        <option value="">Select frequency</option>
                                        <option value="once_daily">Once daily</option>
                                        <option value="twice_daily">Twice daily</option>
                                        <option value="three_times_daily">Three times daily</option>
                                        <option value="every_other_day">Every other day</option>
                                        <option value="weekly">Weekly</option>
                                        <option value="as_needed">As needed</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Prescribed By
                                    </label>
                                    <input
                                        type="text"
                                        value={formData.medication_details?.prescribed_by || ''}
                                        onChange={(e) => handleNestedInputChange('medication_details', 'prescribed_by', e.target.value)}
                                        placeholder="Veterinarian name"
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        Start Date *
                                    </label>
                                    <input
                                        type="date"
                                        value={formData.medication_details?.start_date || ''}
                                        onChange={(e) => handleNestedInputChange('medication_details', 'start_date', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                    {errors.start_date && (
                                        <p className="mt-1 text-sm text-red-600">{errors.start_date}</p>
                                    )}
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">
                                        End Date
                                    </label>
                                    <input
                                        type="date"
                                        value={formData.medication_details?.end_date || ''}
                                        onChange={(e) => handleNestedInputChange('medication_details', 'end_date', e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    />
                                </div>
                            </div>

                            <div className="mt-4">
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Reason for Medication
                                </label>
                                <textarea
                                    value={formData.medication_details?.reason || ''}
                                    onChange={(e) => handleNestedInputChange('medication_details', 'reason', e.target.value)}
                                    rows={2}
                                    placeholder="Reason for prescribing this medication"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>

                            <div className="mt-4">
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Side Effects
                                </label>
                                <textarea
                                    value={formData.medication_details?.side_effects || ''}
                                    onChange={(e) => handleNestedInputChange('medication_details', 'side_effects', e.target.value)}
                                    rows={2}
                                    placeholder="Any observed side effects"
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>
                        </div>
                    )}

                    {/* Notes */}
                    <div className="border-t pt-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Additional Notes
                        </label>
                        <textarea
                            name="notes"
                            value={formData.notes}
                            onChange={handleInputChange}
                            rows={4}
                            placeholder="Any additional notes, observations, or important information"
                            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                    </div>

                    {/* Submit Buttons */}
                    <div className="flex justify-end space-x-4 pt-6 border-t">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-6 py-2 border border-gray-300 rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading}
                            className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {loading ? 'Saving...' : 'Save Health Record'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddHealthRecordForm; 