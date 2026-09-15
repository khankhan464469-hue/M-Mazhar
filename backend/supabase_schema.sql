create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  role text not null,
  created_at timestamptz not null default now()
);

alter table public.profiles
add column if not exists email text;

alter table public.profiles
drop constraint if exists profiles_role_check;

alter table public.profiles
add constraint profiles_role_check
check (role in ('customer', 'admin'));

create index if not exists profiles_role_idx on public.profiles(role);

alter table public.profiles enable row level security;

drop policy if exists "Users can read own profile" on public.profiles;
create policy "Users can read own profile"
on public.profiles
for select
using (auth.uid() = id);

drop policy if exists "Users can insert own profile" on public.profiles;
create policy "Users can insert own profile"
on public.profiles
for insert
with check (auth.uid() = id and role in ('customer', 'admin'));

drop policy if exists "Users can update own profile name" on public.profiles;
create policy "Users can update own profile name"
on public.profiles
for update
using (auth.uid() = id)
with check (auth.uid() = id and role in ('customer', 'admin'));
