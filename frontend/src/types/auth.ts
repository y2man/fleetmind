export interface Org { id: string; name: string; country: string | null; timezone: string | null; fleet_size: number | null }
export interface User { id: string; email: string; full_name: string; phone: string | null; role: string; email_verified: boolean; organization: Org; permissions: string[] }
export interface TokenOut { access_token: string; user: User; dev_link?: string | null }
export interface Message { message: string; dev_link?: string | null }
export interface Member { id: string; email: string; full_name: string; role_name: string; is_active: boolean; email_verified: boolean; last_login_at: string | null }
export interface AuditEntry { id: string; action: string; user_id: string | null; entity_type: string | null; ip: string | null; created_at: string }
