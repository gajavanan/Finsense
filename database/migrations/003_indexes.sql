create index if not exists idx_tx_user_date on transactions(user_id, date desc);
create index if not exists idx_tx_user_category on transactions(user_id, category);
create index if not exists idx_tx_user_type on transactions(user_id, type);
create index if not exists idx_budgets_user on budgets(user_id);
create index if not exists idx_goals_user on goals(user_id);
create index if not exists idx_assets_user on assets(user_id);
create index if not exists idx_notifications_user on notifications(user_id, created_at desc);
create index if not exists idx_chat_user on chat_messages(user_id, created_at);
create index if not exists idx_login_user on login_events(user_id, created_at desc);
