-- Əgər db/schema.sql-ı ARTIQ Supabase-də işə salmısansa, bu faylı SQL Editor-da
-- əlavə olaraq işə sal ki, mövcud employees cədvəli Google girişini dəstəkləsin.
-- (Yeni quraşdırmalarda buna ehtiyac yoxdur — schema.sql onsuz da yenilənib.)

alter table employees alter column password_hash drop not null;
alter table employees add column if not exists auth_provider text default 'email';

create table if not exists qr_sessions (
  id uuid primary key default uuid_generate_v4(),
  status text not null default 'pending' check (status in ('pending','confirmed','expired')),
  token text,
  user_payload jsonb,
  created_at timestamptz default now()
);
create index if not exists idx_qr_sessions_created on qr_sessions(created_at);
