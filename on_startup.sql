DROP TABLE IF EXISTS bot_users;
CREATE TABLE IF NOT exists bot_users (
	id SERIAL not null,
	name text not null,
	email text null,
	password text not null
);
insert into bot_users (name, password, email) values ('alex', '1111', 'aleksey.zadonsky@gmail.com');
insert into bot_users (name, password, email) values ('dima', '1111', 'azadonsky@vk.com');
insert into bot_users (name, password, email) values ('max', '1111', 'rrr@gmail.com');


DROP TABLE IF EXISTS bot_logs;
CREATE TABLE IF NOT exists bot_logs (
	id SERIAL not null,
	username text,
	log text,
	dtime timestamp DEFAULT now() NULL
);


DROP TABLE IF EXISTS bot_menu;
CREATE TABLE IF NOT exists bot_menu (
	menu_id integer not null,
	menu_item text not null,
	menu_name text not null,
	menu_action text null
);
INSERT INTO bot_menu (menu_id, menu_item, menu_name, menu_action) VALUES
(2, 'base', 'Пройти опрос', '/poll'),
(3, 'base', 'Назад', '/start'),
(1, 'base', 'Посмотреть котика', '/cats'),
(2, 'alexeyzadonsky', 'Посмотреть котика', '/cats'),
(3, 'alexeyzadonsky', 'Список пользователей 👥', '/users'),
(4, 'alexeyzadonsky', 'Последние логи', '/logs'),
(5, 'alexeyzadonsky', 'Пройти опрос', '/poll'),
(6, 'alexeyzadonsky', 'Назад', '/start');

