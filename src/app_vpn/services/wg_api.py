import os
import httpx
import aiofiles
import aiohttp
import tempfile
import requests
from django.conf import settings

WG_API_URL = settings.WG_API_URL
WG_API_TOKEN = settings.WG_API_TOKEN


def create_wg_client(data: dict) -> dict | None:
    headers = {"Authorization": f"Bearer {WG_API_TOKEN}"}
    try:
        response = requests.post(f"{WG_API_URL}/api/clients", headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        # логировать или пробросить ошибку
        return None


def delete_wg_client(wg_id: int) -> bool:
    headers = {"Authorization": f"Bearer {WG_API_TOKEN}"}
    try:
        response = requests.delete(f"{WG_API_URL}/api/clients/{wg_id}", headers=headers)
        return response.status_code == 200
    except requests.RequestException:
        return False


async def disable_wg_client(client_id: int) -> bool:
    headers = {"Authorization": f"Bearer {WG_API_TOKEN}"}
    url = f"{WG_API_URL}/api/clients/{client_id}"
    payload = {"enable": False}

    try:
        response = requests.patch(url, headers=headers, json=payload)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка при отключении клиента {client_id}: {e}")
        return False


def get_client_config(wg_id: int) -> str | None:
    headers = {"Authorization": f"Bearer {WG_API_TOKEN}"}
    try:
        response = requests.get(f"{WG_API_URL}/api/clients/{wg_id}?format=conf", headers=headers)
        if response.ok:
            return response.text
        return None
    except requests.RequestException:
        return None


async def download_config_file(wg_id: int) -> str | None:
    config_text = get_client_config(wg_id)
    if not config_text:
        return None

    # создаем временный файл
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".conf")
    async with aiofiles.open(tmp_file.name, mode='w') as f:
        await f.write(config_text)
    return tmp_file.name


async def get_qr_code(wg_id: int) -> str | None:
    headers = {"Authorization": f"Bearer {WG_API_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WG_API_URL}/api/clients/{wg_id}?format=qr", headers=headers) as resp:
                if resp.status != 200:
                    return None
                img_data = await resp.read()

        # сохраняем как временное изображение
        tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        async with aiofiles.open(tmp_img.name, mode="wb") as f:
            await f.write(img_data)
        return tmp_img.name

    except aiohttp.ClientError:
        return None
