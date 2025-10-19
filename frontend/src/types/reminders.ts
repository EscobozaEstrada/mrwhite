export interface Reminder {
    id: number;
    pet_id?: number;
    reminder_type: ReminderType;
    title: string;
    description?: string;
    due_date: string;
    reminder_date?: string;
    status: ReminderStatus;
    send_email: boolean;
    send_push: boolean;
    days_before_reminder: number;
    health_record_id?: number;
    created_at: string;
    completed_at?: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
}

export enum ReminderType {
    VACCINATION = "vaccination",
    VET_APPOINTMENT = "vet_appointment",
    MEDICATION = "medication",
    GROOMING = "grooming",
    CHECKUP = "checkup",
    CUSTOM = "custom"
}

export enum ReminderStatus {
    PENDING = "pending",
    COMPLETED = "completed",
    OVERDUE = "overdue",
    CANCELLED = "cancelled"
}

export interface CreateReminderRequest {
    reminder_type: ReminderType;
    title: string;
    description?: string;
    due_date: string;
    pet_id?: number;
    reminder_date?: string;
    send_email?: boolean;
    send_push?: boolean;
    days_before_reminder?: number;
    health_record_id?: number;
    priority?: 'low' | 'medium' | 'high' | 'critical';
}

export interface ReminderSummary {
    total_reminders: number;
    overdue_reminders: number;
    upcoming_reminders: number;
    completed_reminders: number;
    reminder_types: Record<string, number>;
}

export interface ReminderUrgency {
    color: string;
    text: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
}

export interface ReminderCategory {
    value: ReminderType;
    label: string;
    icon: string;
    color: string;
    description: string;
}

export interface ReminderFilters {
    status?: ReminderStatus[];
    type?: ReminderType[];
    dateRange?: {
        start?: string;
        end?: string;
    };
    searchQuery?: string;
} 