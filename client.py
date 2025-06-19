#!/usr/bin/env python3
"""
Клиент для отправки файлов на сервер через GET-запросы с данными в query параметрах
"""

import requests
import base64
import os
import sys
from pathlib import Path
import urllib.parse
import json
import time

class FileTransferClient:
    def __init__(self, server_url='http://193.222.99.46:8080'):
        self.server_url = server_url.rstrip('/')
        self.chunk_size = 1024 * 8  # 8KB chunks (учитывая ограничения URL)
    
    def upload_file(self, file_path, show_progress=True):
        """Загрузка файла на сервер"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"❌ Файл не найден: {file_path}")
            return False
        
        if not file_path.is_file():
            print(f"❌ Указанный путь не является файлом: {file_path}")
            return False
        
        filename = file_path.name
        file_size = file_path.stat().st_size
        
        print(f"📤 Загрузка файла: {filename}")
        print(f"📏 Размер файла: {file_size} байт")
        
        # Читаем файл и разбиваем на куски
        chunks = []
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
        
        total_chunks = len(chunks)
        print(f"📦 Количество кусков: {total_chunks}")
        
        # Отправляем куски
        for i, chunk in enumerate(chunks):
            if not self._send_chunk(filename, chunk, i, total_chunks, show_progress):
                return False
        
        print(f"✅ Файл {filename} успешно загружен!")
        return True
    
    def _send_chunk(self, filename, chunk_data, chunk_index, total_chunks, show_progress=True):
        """Отправка одного куска данных"""
        try:
            # Кодируем данные в base64
            encoded_data = base64.b64encode(chunk_data).decode('utf-8')
            
            # Подготавливаем параметры
            params = {
                'filename': filename,
                'data': encoded_data,
                'chunk': str(chunk_index),
                'total': str(total_chunks),
                'final': 'true' if chunk_index == total_chunks - 1 else 'false'
            }
            
            # Формируем URL с параметрами
            url = f"{self.server_url}/upload"
            
            if show_progress:
                progress = ((chunk_index + 1) / total_chunks) * 100
                print(f"⏳ Отправка куска {chunk_index + 1}/{total_chunks} ({progress:.1f}%)")
            
            # Отправляем GET-запрос
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if show_progress and 'message' in result:
                        print(f"   {result['message']}")
                    return True
                except json.JSONDecodeError:
                    print(f"⚠️  Получен некорректный JSON ответ")
                    return True  # Продолжаем, возможно сервер просто вернул текст
            else:
                print(f"❌ Ошибка отправки куска {chunk_index + 1}: {response.status_code}")
                print(f"   {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"⏰ Таймаут при отправке куска {chunk_index + 1}")
            return False
        except requests.exceptions.ConnectionError:
            print(f"🔌 Ошибка соединения при отправке куска {chunk_index + 1}")
            return False
        except Exception as e:
            print(f"❌ Неожиданная ошибка при отправке куска {chunk_index + 1}: {str(e)}")
            return False
    
    def get_server_status(self):
        """Получение статуса сервера"""
        try:
            response = requests.get(f"{self.server_url}/status", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Ошибка получения статуса: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Ошибка соединения с сервером: {str(e)}")
            return None
    
    def test_connection(self):
        """Проверка соединения с сервером"""
        print(f"🔍 Проверка соединения с {self.server_url}")
        status = self.get_server_status()
        
        if status:
            print("✅ Соединение установлено")
            print(f"📊 Статус сервера: {status.get('status', 'unknown')}")
            files = status.get('uploaded_files', [])
            if files:
                print(f"📁 Файлы на сервере ({len(files)}):")
                for file in files:
                    print(f"   - {file}")
            else:
                print("📁 На сервере пока нет файлов")
            return True
        else:
            print("❌ Не удалось подключиться к серверу")
            return False

def main():
    """Главная функция клиента"""
    if len(sys.argv) < 2:
        print("🚀 File Transfer Client")
        print()
        print("Использование:")
        print(f"  {sys.argv[0]} <путь_к_файлу> [url_сервера]")
        print(f"  {sys.argv[0]} --status [url_сервера]")
        print(f"  {sys.argv[0]} --test [url_сервера]")
        print()
        print("Примеры:")
        print(f"  {sys.argv[0]} document.pdf")
        print(f"  {sys.argv[0]} image.jpg http://192.168.1.100:8080")
        print(f"  {sys.argv[0]} --status")
        print(f"  {sys.argv[0]} --test http://example.com:8080")
        return
    
    # Определяем URL сервера
    server_url = 'http://193.222.99.46:8080'
    if len(sys.argv) > 2:
        server_url = sys.argv[2]
    
    client = FileTransferClient(server_url)
    
    # Обработка команд
    if sys.argv[1] == '--status':
        status = client.get_server_status()
        if status:
            print("📊 Статус сервера:")
            print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif sys.argv[1] == '--test':
        client.test_connection()
    
    else:
        # Загрузка файла
        file_path = sys.argv[1] || '/root/full-backup.tar.gz'
        
        # Сначала проверяем соединение
        if not client.test_connection():
            print("❌ Невозможно установить соединение с сервером")
            return
        
        print()
        
        # Загружаем файл
        start_time = time.time()
        success = client.upload_file(file_path)
        end_time = time.time()
        
        if success:
            duration = end_time - start_time
            print(f"⏱️  Время загрузки: {duration:.2f} секунд")

if __name__ == '__main__':
    main()
