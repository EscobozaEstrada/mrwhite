export interface User {
    id: string;
    name: string;
    email: string;
    created_at: string;
    is_premium: boolean;
    subscription_status?: string;
    subscription_start_date?: string;
    subscription_end_date?: string;
    last_payment_date?: string;
    payment_failed?: boolean;
    stripe_customer_id?: string;
    stripe_subscription_id?: string;
    credits_balance?: number;
    dog_image?: string;
}