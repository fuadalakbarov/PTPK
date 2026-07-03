-- GDRTI Performans İdarəetmə Sistemi — Supabase/PostgreSQL sxemi

create extension if not exists "uuid-ossp";

-- SEKTORLAR
create table if not exists sectors (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  description text,
  color text default '#6366f1',
  sort_order int default 0,
  created_at timestamptz default now()
);

-- İŞÇİLƏR (həm admin, həm employee bu cədvəldə, role ilə ayrılır)
create table if not exists employees (
  id uuid primary key default uuid_generate_v4(),
  sector_id uuid references sectors(id) on delete set null,
  full_name text not null,
  position text,
  email text unique not null,
  password_hash text, -- Google ilə qeydiyyatda boş qala bilər
  auth_provider text default 'email' check (auth_provider in ('email','google')),
  role text not null default 'employee' check (role in ('admin','employee')),
  photo_url text,
  phone text,
  is_active boolean default true,
  created_at timestamptz default now()
);

-- TAPŞIRIQLAR
create table if not exists tasks (
  id uuid primary key default uuid_generate_v4(),
  employee_id uuid references employees(id) on delete cascade,
  assigned_by uuid references employees(id) on delete set null,
  title text not null,
  description text,
  due_date date,
  status text not null default 'pending' check (status in ('pending','in_progress','completed','overdue','cancelled')),
  quality_score int check (quality_score between 0 and 100),
  points numeric default 0,
  created_at timestamptz default now(),
  completed_at timestamptz
);

-- MESAJLAR
create table if not exists messages (
  id uuid primary key default uuid_generate_v4(),
  sender_id uuid references employees(id) on delete cascade,
  receiver_id uuid references employees(id) on delete cascade,
  content text not null,
  is_read boolean default false,
  created_at timestamptz default now()
);

-- KALENDAR HADİSƏLƏRİ
create table if not exists calendar_events (
  id uuid primary key default uuid_generate_v4(),
  sector_id uuid references sectors(id) on delete cascade,
  employee_id uuid references employees(id) on delete cascade,
  created_by uuid references employees(id) on delete set null,
  title text not null,
  description text,
  event_date date not null,
  event_time time,
  type text default 'event' check (type in ('event','meeting','deadline','reminder')),
  created_at timestamptz default now()
);

create index if not exists idx_employees_sector on employees(sector_id);
create index if not exists idx_tasks_employee on tasks(employee_id);
create index if not exists idx_tasks_status on tasks(status);
create index if not exists idx_messages_receiver on messages(receiver_id);
create index if not exists idx_calendar_date on calendar_events(event_date);

-- QR İLƏ GİRİŞ SESSİYALARI (kompüterdə QR göstərilir, telefonla təsdiqlənir)
create table if not exists qr_sessions (
  id uuid primary key default uuid_generate_v4(),
  status text not null default 'pending' check (status in ('pending','confirmed','expired')),
  token text,
  user_payload jsonb,
  created_at timestamptz default now()
);
create index if not exists idx_qr_sessions_created on qr_sessions(created_at);

-- Nümunə sektorlar
insert into sectors (name, description, color, sort_order) values
  ('Ümumi Təhsil Sektoru', 'Ümumi təhsil müəssisələrinin fəaliyyətinə nəzarət', '#6366f1', 1),
  ('Məktəbəqədər Təhsil Sektoru', 'Bağça və məktəbəqədər müəssisələr', '#8b5cf6', 2),
  ('PTPK (Psixoloji-Tibbi-Pedaqoji Komissiya)', 'Uşaqların qiymətləndirilməsi və dəstək', '#06b6d4', 3),
  ('Kadr və Sənədləşmə Sektoru', 'Kadr işləri və sənəd dövriyyəsi', '#f59e0b', 4)
on conflict do nothing;
