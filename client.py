#!/usr/bin/env python3
"""
Устойчивый клиент для передачи файлов в условиях проблемной сети
"""

import requests
import base64
import os
import sys
from pathlib import Path
import json
import time
import urllib.parse

class RobustFileTransferClient:
    def __init__(self, server_url='http://193.222.99.46:8080'):
        self.server_url = server_url.rstrip('/')
        self.chunk_size = 512  # Очень маленькие куски для проблемной сети
        self.max_retries = 5
        self.retry_delay = 2
        
        # Настройки для проблемной сети
        self.session = requests.Session()
        self.session.headers.update({
            'Connection': 'close',  # Закрываем соединение после каждого запроса
            'User-Agent': 'FileTransfer/1.0'
        })
    
    def upload_file(self, file_path, show_progress=True):
        """Загрузка файла с повторными попытками"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            print(f"❌ Файл не найден: {file_path}")
            return False
        
        filename = file_path.name
        file_size = file_path.stat().st_size
        
        print(f"📤 Загрузка файла: {filename} ({file_size} байт)")
        print(f"🔧 Размер куска: {self.chunk_size} байт")
        
        # Читаем файл и разбиваем на очень маленькие куски
        chunks = []
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
        
        total_chunks = len(chunks)
        print(f"📦 Всего кусков: {total_chunks}")
        
        # Отправляем куски с повторными попытками
        successful_chunks = 0
        for i, chunk in enumerate(chunks):
            success = False
            for attempt in range(self.max_retries):
                if self._send_chunk_safe(filename, chunk, i, total_chunks, attempt + 1):
                    successful_chunks += 1
                    success = True
                    break
                else:
                    if attempt < self.max_retries - 1:
                        print(f"   ⏳ Попытка {attempt + 2} через {self.retry_delay} сек...")
                        time.sleep(self.retry_delay)
            
            if not success:
                print(f"❌ Не удалось отправить кусок {i + 1} после {self.max_retries} попыток")
                return False
            
            if show_progress and (i + 1) % 10 == 0:
                progress = ((i + 1) / total_chunks) * 100
                print(f"📊 Прогресс: {i + 1}/{total_chunks} ({progress:.1f}%)")
        
        print(f"✅ Файл {filename} успешно загружен! ({successful_chunks}/{total_chunks} кусков)")
        return True
    
    def _send_chunk_safe(self, filename, chunk_data, chunk_index, total_chunks, attempt):
        """Безопасная отправка куска с минимальными настройками"""
        try:
            # Кодируем данные в base64
            encoded_data = base64.b64encode(chunk_data).decode('utf-8')
            
            # Очень простые параметры
            params = {
                'f': filename,  # Сокращенные имена параметров
                'd': encoded_data,
                'c': str(chunk_index),
                't': str(total_chunks),
                'end': '1' if chunk_index == total_chunks - 1 else '0'
            }
            
            # Простой GET запрос с минимальными настройками
            url = f"{self.server_url}/upload"
            
            print(f"🔄 Кусок {chunk_index + 1}/{total_chunks} (попытка {attempt})")
            
            # Очень консервативные настройки
            response = requests.get(
                url, 
                params=params, 
                timeout=10,
                headers={'Connection': 'close'}
            )
            
            if response.status_code == 200:
                print(f"   ✓ Отправлено")
                return True
            else:
                print(f"   ✗ Ошибка {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"   ⏰ Таймаут")
            return False
        except requests.exceptions.ConnectionError:
            print(f"   🔌 Ошибка соединения")
            return False
        except Exception as e:
            print(f"   ❌ Ошибка: {str(e)}")
            return False
    
    def test_connection_simple(self):
        """Простая проверка соединения"""
        try:
            print(f"🔍 Проверка {self.server_url}")
            response = requests.get(
                f"{self.server_url}/", 
                timeout=5,
                headers={'Connection': 'close'}
            )
            if response.status_code == 200:
                print("✅ Сервер отвечает")
                return True
            else:
                print(f"⚠️ Сервер вернул код {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка подключения: {str(e)}")
            return False
    
    def send_test_data(self):
        """Отправка тестовых данных"""
        test_data = b"Hello World Test"
        encoded = base64.b64encode(test_data).decode('utf-8')
        
        try:
            params = {
                'f': 'test.txt',
                'd': encoded,
                'c': '0',
                't': '1',
                'end': '1'
            }
            
            response = requests.get(
                f"{self.server_url}/upload",
                params=params,
                timeout=10,
                headers={'Connection': 'close'}
            )
            
            if response.status_code == 200:
                print("✅ Тестовая передача успешна")
                return True
            else:
                print(f"❌ Тест не прошел: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка теста: {str(e)}")
            return False

def main():
    if len(sys.argv) < 2:
        print("🚀 Устойчивый File Transfer Client")
        print("Использование:")
        print(f"  {sys.argv[0]} <файл> [сервер]")
        print(f"  {sys.argv[0]} --test [сервер]")
        print("Примеры:")
        print(f"  {sys.argv[0]} document.txt")
        print(f"  {sys.argv[0]} --test http://192.168.1.100:8080")
        return
    
    server_url = 'http://localhost:8080'
    if len(sys.argv) > 2:
        server_url = sys.argv[2]
    
    client = RobustFileTransferClient(server_url)
    
    if sys.argv[1] == '--test':
        print("🧪 Запуск диагностики сети...")
        client.test_connection_simple()
        print("📤 Тест передачи данных...")
        client.send_test_data()
    else:
        file_path = sys.argv[1]
        print("🔧 Режим для проблемной сети активирован")
        
        if client.test_connection_simple():
            print()
            start_time = time.time()
            success = client.upload_file(file_path)
            end_time = time.time()
            
            if success:
                print(f"⏱️ Время: {end_time - start_time:.1f} сек")
        else:
            print("❌ Сервер недоступен")

if __name__ == '__main__':
    main()
