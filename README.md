# VPN Subscription Bot + WireGuard API (Django + Aiogram)

<div align="center">

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Packaged with Poetry](https://img.shields.io/badge/packaging-poetry-cyan.svg)](https://python-poetry.org/)<br>
[![!Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)](https://ubuntu.com/)
[![!Debian](https://img.shields.io/badge/Debian-A81D33?style=for-the-badge&logo=debian&logoColor=white)](https://www.debian.org/)
[![!Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![!PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![!Wireguard](https://img.shields.io/badge/Wireguard-88171A?style=for-the-badge&logo=wireguard&logoColor=white)](https://www.wireguard.com/)
[![!Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org/)

</div>

## Contents tree:

1. [Description](#description)
2. [Stack](#stack)
3. [Before you start...](#before-you-start)
4. [Setup guide](#setup)


## Description

This bot is designed to manage Wireguard VPN server. It can automatically connect and disconnect users, generate QR codes for mobile clients, and also can be used as a payment system for VPN services.


## Stack

- **Django** — Backend
- **aiogram v3** — TelegramBot
- **[wg-rest-api](https://github.com/leonovk/wg-rest-api)** — REST API WireGuard


## Before you start...
1. You need to manually install Wireguard on your server. You can find installation guide [here](https://www.wireguard.com/install/).
2. You need to configure Wireguard server. You can find configuration guide [here (RUS)](https://t.me/t0digital/32).
3. You need to create a bot using [BotFather](https://t.me/BotFather).


## ⚙️ Setup guide

#### 1. Clone the repository:

```bash
git clone https://github.com/eastsidekillas/wg-pay-bot.git
cd vpn-bot
```

#### 2. Install Docker

https://docs.docker.com/engine/install/debian/

#### 2. Create a .env file in your project folder and fill it with your data. You can use the following example as a template or use the example.env file (they are the same thing)


```
# Main Django
DJANGO_SECRET_KEY=secret-key
DEBUG=True
PUBLIC_HOST=ip or domain

# Bot Settings
BOT_TOKEN= token
WG_HOST_URL= wg-rest-api host
WG_HOST_API_TOKEN= wg-rest-api token
BOT_ADMINS= id user tg
ADMIN_PAYMENT_PHONE= phone

# postgresql
#DATABASE_ENGINE=django.db.backends.postgresql
#DATABASE_NAME=vpn
#DATABASE_USER=vpn
#DATABASE_PASSWORD=vpn
#DATABASE_HOST=localhost
#DATABASE_PORT=5432

# sqlite
#DATABASE_ENGINE=django.db.backends.sqlite3
#DATABASE_NAME=db.sqlite3


# Other settings
MEDIA_ROOT=media
MEDIA_URL=media/

```

#### 3. Build project

```bash
docker-compose build
```

#### 4. Create superuser

```bash
docker-compose exec app python manage.py createsuperuser
```

#### 5. Run bot and Django

```bash
docker-compose up -d
```