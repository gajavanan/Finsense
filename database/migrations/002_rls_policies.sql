-- 002_rls_policies.sql
alter table profiles enable row level security;
alter table connected_accounts enable row level security;
alter table transactions enable row level security;
alter table budgets enable row level security;
alter table goals enable row level security;
alter table assets enable row level security;
alter table notifications enable row level security;
alter table agent_insights enable row level security;
alter table agent_actions enable row level security;
alter table chat_messages enable row level security;
alter table agent_preferences enable row level security;
alter table upi_accounts enable row level security;
alter table login_events enable row level security;

-- Helper: all policies use auth.uid() = user_id (or id for profiles)
create policy "Users can manage own profile" on profiles for all using (auth.uid() = id) with check (auth.uid() = id);
create policy "Users manage own connected_accounts" on connected_accounts for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own transactions" on transactions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own budgets" on budgets for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own goals" on goals for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own assets" on assets for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own notifications" on notifications for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own agent_insights" on agent_insights for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own agent_actions" on agent_actions for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own chat_messages" on chat_messages for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own agent_preferences" on agent_preferences for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own upi_accounts" on upi_accounts for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "Users manage own login_events" on login_events for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
