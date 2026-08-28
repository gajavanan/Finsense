-- 001_initial_schema.sql
enable extension if not exists "uuid-ossp";

create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  email text,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists connected_accounts (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  provider text,
  account_name text,
  balance numeric default 0,
  created_at timestamptz default now()
);

create table if not exists transactions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  date date not null,
  description text not null,
  amount numeric not null,
  type text not null check (type in ('income','expense','transfer')),
  category text,
  payment_method text,
  merchant text,
  account text,
  notes text,
  created_at timestamptz default now()
);

create table if not exists budgets (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  category text not null,
  amount numeric not null,
  period text default 'monthly',
  month text,
  created_at timestamptz default now()
);

create table if not exists goals (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  target_amount numeric not null,
  current_amount numeric default 0,
  target_date date,
  category text,
  created_at timestamptz default now()
);

create table if not exists assets (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  symbol text,
  type text not null,
  quantity numeric not null,
  purchase_price numeric not null,
  current_price numeric,
  created_at timestamptz default now()
);

create table if not exists notifications (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  message text,
  type text default 'info',
  read boolean default false,
  created_at timestamptz default now()
);

create table if not exists agent_insights (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  content text,
  type text,
  created_at timestamptz default now()
);

create table if not exists agent_actions (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  action text not null,
  payload jsonb,
  created_at timestamptz default now()
);

create table if not exists chat_messages (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null,
  content text not null,
  created_at timestamptz default now()
);

create table if not exists agent_preferences (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade unique,
  preferences jsonb,
  created_at timestamptz default now()
);

create table if not exists upi_accounts (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  upi_id text not null,
  bank_name text,
  created_at timestamptz default now()
);

create table if not exists login_events (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  email text,
  user_agent text,
  ip text,
  created_at timestamptz default now()
);
