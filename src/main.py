# Импорт необходимых библиотек и модулей
import flet as ft                                  # Фреймворк для создания кроссплатформенных приложений с современным UI
from api.openrouter import OpenRouterClient        # Клиент для взаимодействия с AI API через OpenRouter
from ui.styles import AppStyles                    # Модуль с настройками стилей интерфейса
from ui.components import MessageBubble, ModelSelector, AuthScreen, PinScreen  # Компоненты пользовательского интерфейса
from utils.cache import ChatCache                  # Модуль для кэширования истории чата
from utils.logger import AppLogger                 # Модуль для логирования работы приложения
from utils.analytics import Analytics              # Модуль для сбора и анализа статистики использования
from utils.monitor import PerformanceMonitor       # Модуль для мониторинга производительности
import asyncio                                     # Библиотека для асинхронного программирования
import time                                        # Библиотека для работы с временными метками
import json                                        # Библиотека для работы с JSON-данными
from datetime import datetime                      # Класс для работы с датой и временем
import os                                          # Библиотека для работы с операционной системой

class ChatApp:
    """
    Основной класс приложения чата.
    Управляет всей логикой работы приложения, включая UI и взаимодействие с API.
    """
    def __init__(self):
        """
        Инициализация основных компонентов приложения:
        - API клиент для связи с языковой моделью
        - Система кэширования для сохранения истории
        - Система логирования для отслеживания работы
        - Система аналитики для сбора статистики
        - Система мониторинга для отслеживания производительности
        """
        # Инициализация основных компонентов
        self.cache = ChatCache()                   # Инициализация системы кэширования
        self.logger = AppLogger()                  # Инициализация системы логирования
        self.api_client = OpenRouterClient()       # Создание клиента для работы с AI API
        self.analytics = Analytics(self.cache)     # Инициализация системы аналитики с передачей кэша
        self.monitor = PerformanceMonitor()        # Инициализация системы мониторинга

        # Состояние аутентификации
        self.is_authenticated = False              # Флаг аутентификации
        self.auth_screen = None                    # Экран ввода API ключа
        self.pin_screen = None                     # Экран ввода PIN-кода
        
        # Создание компонента для отображения баланса API
        self.balance_text = ft.Text(
            "Баланс: Загрузка...",                # Начальный текст до загрузки реального баланса
            **AppStyles.BALANCE_TEXT               # Применение стилей из конфигурации
        )
        
        # Создание директории для экспорта истории чата
        self.exports_dir = "exports"               # Путь к директории экспорта
        os.makedirs(self.exports_dir, exist_ok=True)  # Создание директории, если её нет
        
    def load_chat_history(self):
        """
        Загрузка истории чата из кэша и отображение её в интерфейсе.
        Сообщения добавляются в обратном порядке для правильной хронологии.
        """
        try:
            history = self.cache.get_chat_history()    # Получение истории из кэша
            for msg in reversed(history):              # Перебор сообщений в обратном порядке
                # Распаковка данных сообщения в отдельные переменные
                _, model, user_message, ai_response, timestamp, tokens = msg
                # Добавление пары сообщений (пользователь + AI) в интерфейс
                self.chat_history.controls.extend([
                    MessageBubble(                     # Создание пузырька сообщения пользователя
                        message=user_message,
                        is_user=True
                    ),
                    MessageBubble(                     # Создание пузырька ответа AI
                        message=ai_response,
                        is_user=False
                    )
                ])
        except Exception as e:
            # Логирование ошибки при загрузке истории
            self.logger.error(f"Ошибка загрузки истории чата: {e}")

    def update_balance(self):
        """
        Обновление отображаемого баланса API.
        Запрашивает актуальный баланс через API клиент и обновляет его в интерфейсе.
        """
        try:
            # Запрос баланса через API клиент
            balance = self.api_client.get_balance()
            
            # Обновление текста с балансом
            self.balance_text.value = f"Баланс: {balance}"
            
            # Обновление цвета текста в зависимости от наличия ошибки
            if balance == "Ошибка":
                self.balance_text.color = ft.Colors.RED_500
            else:
                self.balance_text.color = ft.Colors.GREEN_500
                
            # Обновление интерфейса - этот вызов теперь безопасен
            # после добавления компонента на страницу
            if hasattr(self.balance_text, "_Control__page") and self.balance_text._Control__page:
                self.balance_text.update()
            
            # Логирование события
            self.logger.debug(f"Баланс обновлен: {balance}")
            
        except Exception as e:
            # Обработка ошибок при обновлении баланса
            self.balance_text.value = "Баланс: Ошибка"
            self.balance_text.color = ft.Colors.RED_500
            if hasattr(self.balance_text, "_Control__page") and self.balance_text._Control__page:
                self.balance_text.update()
            
            # Логирование ошибки
            self.logger.error(f"Ошибка обновления баланса: {e}")
            
    def main(self, page: ft.Page):
        """
        Основная функция инициализации интерфейса приложения.
        Создает все элементы UI и настраивает их взаимодействие.
        
        Args:
            page (ft.Page): Объект страницы Flet для размещения элементов интерфейса
        """
        # Применение базовых настроек страницы из конфигурации стилей
        for key, value in AppStyles.PAGE_SETTINGS.items():
            setattr(page, key, value)

        AppStyles.set_window_size(page)    # Установка размеров окна приложения
        
        # Определение колбэков для аутентификации
        def on_auth_success():
            """Вызывается после успешной аутентификации"""
            self.logger.info("Аутентификация успешна")
            self.is_authenticated = True
            self.initialize_main_interface(page)
            page.update()
            
        def on_api_key_validated():
            """Вызывается после успешной валидации API ключа"""
            self.logger.info("API ключ успешно проверен")
            # Обновляем API клиент с новым ключом
            api_key = self.cache.get_api_key()
            if api_key:
                self.api_client.api_key = api_key
            on_auth_success()
            
        def on_reset_api_key():
            """Вызывается при сбросе API ключа"""
            self.logger.info("API ключ сброшен")
            self.is_authenticated = False
            # Удаляем все элементы со страницы
            page.controls.clear()
            # Создаем и показываем экран ввода API ключа
            self.auth_screen = AuthScreen(on_api_key_validated, self.api_client, self.cache)
            page.add(self.auth_screen)
            page.update()

        # Проверка наличия сохраненных данных аутентификации
        if self.cache.has_auth_data():
            # Если данные есть, показываем экран ввода PIN-кода
            self.logger.info("Найдены данные аутентификации, показываем экран ввода PIN")
            self.pin_screen = PinScreen(on_auth_success, on_reset_api_key, self.cache)
            page.add(self.pin_screen)
        else:
            # Если данных нет, показываем экран ввода API ключа
            self.logger.info("Данные аутентификации не найдены, показываем экран ввода API ключа")
            self.auth_screen = AuthScreen(on_api_key_validated, self.api_client, self.cache)
            page.add(self.auth_screen)
            
        # Запуск монитора
        self.monitor.get_metrics()
        
        # Логирование запуска
        self.logger.info("Приложение запущено")
            
    def initialize_main_interface(self, page: ft.Page):
        """
        Инициализация основного интерфейса приложения после успешной аутентификации.
        
        Args:
            page (ft.Page): Объект страницы Flet для размещения элементов интерфейса
        """
        # Очистка страницы
        page.controls.clear()
        
        # Обновление баланса API
        # self.update_balance() - перемещаем этот вызов в конец функции
        
        # Инициализация выпадающего списка для выбора модели AI
        models = self.api_client.available_models
        self.model_dropdown = ModelSelector(models)
        self.model_dropdown.value = models[0]["id"] if models else None

        # Создание контейнера для истории чата
        self.chat_history = ft.ListView(
            **AppStyles.CHAT_HISTORY
        )
        
        # Поле ввода сообщения
        message_input_overrides = {
            "border": ft.InputBorder.UNDERLINE,
            "multiline": True,  # Переопределяем multiline=False из стилей
            "min_lines": 1,
            "max_lines": 5,
            "expand": True,
            "on_submit": self.send_message_callback,
            "hint_text": "Введите сообщение..."  # Переопределяем стандартную подсказку
        }
        message_input_props = {**AppStyles.MESSAGE_INPUT, **message_input_overrides}
        self.message_input = ft.TextField(**message_input_props)
        
        # Кнопка отправки сообщения
        send_button_overrides = {
            "icon": ft.Icons.SEND_ROUNDED,
            "tooltip": "Отправить",
            "on_click": self.send_message_callback
        }
        send_button_props = {**AppStyles.SEND_ICON_BUTTON, **send_button_overrides}
        self.send_button = ft.IconButton(**send_button_props)
        
        # Кнопка очистки истории
        clear_button_overrides = {
            "icon": ft.Icons.DELETE_OUTLINE,
            "tooltip": "Очистить историю",
            "on_click": self.confirm_clear_history_callback
        }
        clear_button_props = {**AppStyles.CLEAR_ICON_BUTTON, **clear_button_overrides}
        self.clear_button = ft.IconButton(**clear_button_props)
        
        # Кнопка экспорта истории
        export_button_overrides = {
            "icon": ft.Icons.DOWNLOAD_OUTLINED,
            "tooltip": "Экспорт истории",
            "on_click": self.save_dialog_callback
        }
        export_button_props = {**AppStyles.EXPORT_ICON_BUTTON, **export_button_overrides}
        self.export_button = ft.IconButton(**export_button_props)
        
        # Контейнер с кнопками управления
        buttons_row = ft.Row(
            controls=[
                self.send_button,
                self.clear_button,
                self.export_button
            ],
            **AppStyles.CONTROLS_ROW
        )
        
        # Контейнер с полем ввода и кнопками
        controls_column = ft.Column(
            controls=[
                self.message_input,
                buttons_row
            ],
            **AppStyles.CONTROLS_COLUMN
        )
        
        # Загрузка истории чата из кэша
        self.load_chat_history()
        
        # Контейнер для отображения баланса
        balance_container = ft.Container(
            content=self.balance_text,
            **AppStyles.BALANCE_CONTAINER
        )
        
        # Создание колонки выбора модели
        model_selection = ft.Column(
            controls=[
                self.model_dropdown.search_field,
                self.model_dropdown,
                balance_container
            ],
            **AppStyles.MODEL_SELECTION_COLUMN
        )
        
        # Создание основной колонки приложения
        self.main_column = ft.Column(
            controls=[
                model_selection,
                self.chat_history,
                controls_column
            ],
            **AppStyles.MAIN_COLUMN
        )
        
        # Добавление основной колонки на страницу
        page.add(self.main_column)
        
        # Теперь обновляем баланс после добавления компонентов на страницу
        self.update_balance()
    
    # Колбэки для обработки событий
    async def send_message_callback(self, e):
        await self.send_message(e.page, self.message_input.value)
        
    async def confirm_clear_history_callback(self, e):
        await self.confirm_clear_history(e)
        
    async def save_dialog_callback(self, e):
        await self.save_dialog(e)
        
    async def send_message(self, page, message):
        """
        Асинхронная функция отправки сообщения.
        
        Args:
            page (ft.Page): Объект страницы Flet
            message (str): Текст сообщения для отправки
        """
        if not message:
            return

        try:
            # Визуальная индикация процесса
            self.message_input.border_color = ft.Colors.BLUE_400
            page.update()

            # Сохранение данных сообщения
            start_time = time.time()
            user_message = message
            self.message_input.value = ""
            page.update()

            # Добавление сообщения пользователя
            self.chat_history.controls.append(
                MessageBubble(message=user_message, is_user=True)
            )

            # Индикатор загрузки
            loading = ft.ProgressRing()
            self.chat_history.controls.append(loading)
            page.update()

            # Асинхронная отправка запроса
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.api_client.send_message(
                    user_message, 
                    self.model_dropdown.value
                )
            )

            # Удаление индикатора загрузки
            self.chat_history.controls.remove(loading)

            # Обработка ответа
            if "error" in response:
                response_text = f"Ошибка: {response['error']}"
                tokens_used = 0
                self.logger.error(f"Ошибка API: {response['error']}")
            else:
                response_text = response["choices"][0]["message"]["content"]
                tokens_used = response.get("usage", {}).get("total_tokens", 0)

            # Сохранение в кэш
            self.cache.save_message(
                model=self.model_dropdown.value,
                user_message=user_message,
                ai_response=response_text,
                tokens_used=tokens_used
            )

            # Добавление ответа в чат
            self.chat_history.controls.append(
                MessageBubble(message=response_text, is_user=False)
            )

            # Обновление аналитики
            response_time = time.time() - start_time
            self.analytics.track_message(
                model=self.model_dropdown.value,
                message_length=len(user_message),
                response_time=response_time,
                tokens_used=tokens_used
            )

            # Обновление баланса API
            self.update_balance()

            # Логирование метрик
            self.monitor.log_metrics(self.logger)
            page.update()

        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            self.message_input.border_color = ft.Colors.RED_500

            # Показ уведомления об ошибке
            self.show_error_snack(page, f"Ошибка отправки сообщения: {str(e)}")
    
    # Вспомогательные методы
    def show_error_snack(self, page, message: str):
        """Показ уведомления об ошибке"""
        snack = ft.SnackBar(                  # Создание уведомления
            content=ft.Text(
                message,
                color=ft.Colors.RED_500
            ),
            bgcolor=ft.Colors.GREY_900,
            duration=5000,
        )
        page.overlay.append(snack)            # Добавление уведомления
        snack.open = True                     # Открытие уведомления
        page.update()                         # Обновление страницы
        
    def close_dialog(self, dialog, page):
        """Закрытие диалогового окна"""
        dialog.open = False                   # Закрытие диалога
        page.update()                         # Обновление страницы
                                
        if dialog in page.overlay:            # Удаление из overlay
            page.overlay.remove(dialog)
            
    async def show_analytics(self, e):
        """Показ статистики использования"""
        page = e.page
        stats = self.analytics.get_statistics()    # Получение статистики

        # Создание диалога статистики
        dialog = ft.AlertDialog(
            title=ft.Text("Аналитика"),
            content=ft.Column([
                ft.Text(f"Всего сообщений: {stats['total_messages']}"),
                ft.Text(f"Всего токенов: {stats['total_tokens']}"),
                ft.Text(f"Среднее токенов/сообщение: {stats['tokens_per_message']:.2f}"),
                ft.Text(f"Сообщений в минуту: {stats['messages_per_minute']:.2f}")
            ]),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda e: self.close_dialog(dialog, page)),
            ],
        )

        page.overlay.append(dialog)           # Добавление диалога
        dialog.open = True                    # Открытие диалога
        page.update()                         # Обновление страницы
    
    async def clear_history(self, e):
        """
        Очистка истории чата.
        """
        try:
            # Очистка истории в базе данных
            self.cache.clear_history()
            
            # Очистка интерфейса
            self.chat_history.controls.clear()
            e.page.update()
            
            # Логирование события
            self.logger.info("История чата очищена")
            
        except Exception as e:
            self.logger.error(f"Ошибка очистки истории: {e}")
            self.show_error_snack(e.page, f"Ошибка очистки истории: {str(e)}")
    
    async def confirm_clear_history(self, e):
        """Подтверждение очистки истории"""
        page = e.page
        
        def close_dlg(e):                     # Функция закрытия диалога
            self.close_dialog(dialog, page)

        async def clear_confirmed(e):         # Функция подтверждения очистки
            await self.clear_history(e)
            self.close_dialog(dialog, page)
            

        # Создание диалога подтверждения
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтверждение удаления"),
            content=ft.Text("Вы уверены? Это действие нельзя отменить!"),
            actions=[
                ft.TextButton("Отмена", on_click=close_dlg),
                ft.TextButton("Очистить", on_click=clear_confirmed),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.overlay.append(dialog)
        dialog.open = True
        page.update()
     
    async def save_dialog(self, e):
        """
        Сохранение истории диалога в JSON файл.
        """
        page = e.page
        try:
            # Получение истории из кэша
            history = self.cache.get_chat_history()

            # Форматирование данных для сохранения
            dialog_data = []
            for msg in history:
                dialog_data.append({
                    "timestamp": str(msg[4]),
                    "model": msg[1],
                    "user_message": msg[2],
                    "ai_response": msg[3],
                    "tokens": msg[5]
                })

            # Создание имени файла с текущей датой и временем
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.exports_dir}/chat_history_{now}.json"

            # Сохранение данных в JSON файл
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(dialog_data, f, ensure_ascii=False, indent=4)

            # Уведомление об успешном сохранении
            snack = ft.SnackBar(
                content=ft.Text(f"История сохранена в {filename}"),
                bgcolor=ft.Colors.GREEN_700,
                duration=5000,
            )
            page.overlay.append(snack)
            snack.open = True
            page.update()

            # Логирование события
            self.logger.info(f"История диалога сохранена в {filename}")

        except Exception as e:
            self.logger.error(f"Ошибка сохранения: {e}")
            self.show_error_snack(page, f"Ошибка сохранения: {str(e)}")

def main():
    """Точка входа в приложение"""
    app = ChatApp()                              # Создание экземпляра приложения
    ft.app(target=app.main)                      # Запуск приложения

if __name__ == "__main__":
    main()                                       # Запуск если файл запущен напрямую
