// Bu fayldakı dəyərlər BRAUZER üçündür — Supabase-in "publishable" (anon) açarı
// təhlükəsizdir, açıq şəkildə göstərilə bilər (service_role açarından fərqli olaraq).
// Supabase → Settings → API-dan götür.

const SUPABASE_URL = 'https://ixnnbybzhrgiyxjxwgoe.supabase.co'; // öz Project URL-in
const SUPABASE_ANON_KEY = 'sb_publishable_XXXXXXXXXXXXXXXXXXXXXXXX'; // öz publishable/anon açarın

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
