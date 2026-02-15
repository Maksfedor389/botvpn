# Telegram-бот для продажи VPN подписок (Xray + 3x-ui)

Готовый каркас Telegram-бота, который:

- показывает тарифы;
- принимает оплату переводом на номер телефона;
- собирает подтверждение платежа (скрин/файл/текст);
- отправляет заявку администратору на подтверждение;
- после подтверждения создает пользователя в 3x-ui и выдает доступ клиенту.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python bot.py
```

## Настройка `.env`

- `BOT_TOKEN` — токен Telegram-бота.
- `ADMIN_IDS` — id админов через запятую (`123,456`).
- `PAYMENT_PHONE` — номер телефона для перевода.
- `THREEXUI_BASE_URL` — URL панели 3x-ui (например `https://panel.example.com`).
- `THREEXUI_USERNAME` / `THREEXUI_PASSWORD` — логин/пароль панели.
- `THREEXUI_INBOUND_ID` — inbound id, куда добавляются клиенты.
- `DB_PATH` — путь к sqlite базе.
- `XRAY_ACCESS_TEMPLATE` — шаблон сообщения, которое получает клиент после успешной выдачи (поддерживает `{uuid}`, `{email}`, `{expiry_date}`).

## Логика работы

1. Пользователь выбирает тариф.
2. Бот просит контактный номер.
3. Бот выдает реквизиты для оплаты переводом на `PAYMENT_PHONE`.
4. Пользователь отправляет подтверждение оплаты.
5. Админ получает заявку и нажимает `✅ Подтвердить` или `❌ Отклонить`.
6. При подтверждении бот создает клиента в 3x-ui и отправляет доступ.

## Важно

- Параметры тарифов заданы в `config.py` (класс `Plan`).
- Добавление клиента в 3x-ui реализовано через API endpoint `/panel/api/inbounds/addClient`.
- Если ваша сборка 3x-ui отличается по API, поправьте `three_xui.py` под ваш вариант.


## Запуск в 3 команды

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt && python bot.py
```

> Перед запуском убедитесь, что заполнен файл `.env` (можно создать из `.env.example`).


## Запуск на сервере (чтобы работал всегда)

1. Подключитесь к серверу и установите базовые пакеты:

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip rsync
```

2. Скопируйте проект на сервер и заполните `/opt/botvpn/.env` (по образцу `.env.example`).

3. Установите и запустите systemd-сервис:

```bash
cd /opt/botvpn
sudo bash scripts/install_systemd.sh
```

4. Проверка и логи:

```bash
systemctl status botvpn --no-pager
journalctl -u botvpn -f
```

Если нужно перезапустить после обновления кода:

```bash
sudo systemctl restart botvpn
```

Шаблон сервиса лежит в `deploy/botvpn.service`.
