# Импорт необходимых библиотек и модулей
import flet as ft                  # Фреймворк для создания пользовательского интерфейса
from ui.styles import AppStyles    # Импорт стилей приложения
import asyncio                     # Библиотека для асинхронного программирования

class MessageBubble(ft.Container):
    """
    Компонент "пузырька" сообщения в чате.
    
    Наследуется от ft.Container для создания стилизованного контейнера сообщения.
    Отображает сообщения пользователя и AI с разными стилями и позиционированием.
    
    Args:
        message (str): Текст сообщения для отображения
        is_user (bool): Флаг, указывающий, является ли это сообщением пользователя
    """
    def __init__(self, message: str, is_user: bool):
        # Инициализация родительского класса Container
        super().__init__()
        
        # Очистка сообщения от тегов
        cleaned_message = self.clean_message(message)
        
        # Настройка отступов внутри пузырька
        self.padding = 10
        
        # Настройка скругления углов пузырька
        self.border_radius = 10
        
        # Установка цвета фона в зависимости от отправителя:
        # - Синий для сообщений пользователя
        # - Серый для сообщений AI
        self.bgcolor = ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_700
        
        # Установка выравнивания пузырька:
        # - Справа для сообщений пользователя
        # - Слева для сообщений AI
        self.alignment = ft.alignment.center_right if is_user else ft.alignment.center_left
        
        # Настройка внешних отступов для создания эффекта диалога:
        # - Отступ слева для сообщений пользователя
        # - Отступ справа для сообщений AI
        # - Небольшие отступы сверху и снизу для разделения сообщений
        self.margin = ft.margin.only(
            left=50 if is_user else 0,      # Отступ слева
            right=0 if is_user else 50,      # Отступ справа
            top=5,                           # Отступ сверху
            bottom=5                         # Отступ снизу
        )
        
        # Создание содержимого пузырька
        self.content = ft.Column(
            controls=[
                # Текст сообщения с настройками отображения
                ft.Text(
                    value=cleaned_message,                # Очищенный текст сообщения
                    color=ft.Colors.WHITE,                # Белый цвет текста
                    size=16,                              # Размер шрифта
                    selectable=True,                      # Возможность выделения текста
                    weight=ft.FontWeight.W_400            # Нормальная толщина шрифта
                )
            ],
            tight=True  # Плотное расположение элементов в колонке
        )

    def clean_message(self, message: str) -> str:
        """
        Очищает сообщение от HTML-подобных тегов.
        
        Args:
            message (str): Исходное сообщение
            
        Returns:
            str: Очищенное сообщение
        """
        import re
        # Удаление HTML-подобных тегов (например <prompt>, <assistant>)
        return re.sub(r'<[^>]+>', '', message)


class ModelSelector(ft.Dropdown):
    """
    Выпадающий список для выбора AI модели с функцией поиска.
    
    Наследуется от ft.Dropdown для создания кастомного выпадающего списка
    с дополнительным полем поиска для фильтрации моделей.
    
    Args:
        models (list): Список доступных моделей в формате:
                      [{"id": "model-id", "name": "Model Name"}, ...]
    """
    def __init__(self, models: list):
        # Инициализация родительского класса Dropdown
        super().__init__()
        
        # Применение стилей из конфигурации к компоненту
        for key, value in AppStyles.MODEL_DROPDOWN.items():
            setattr(self, key, value)
            
        # Настройка внешнего вида выпадающего списка
        self.label = None                    # Убираем текстовую метку
        self.hint_text = "Выбор модели"      # Текст-подсказка
        
        # Создание списка опций из предоставленных моделей
        self.options = [
            ft.dropdown.Option(
                key=model['id'],             # ID модели как ключ
                text=model['name']           # Название модели как отображаемый текст
            ) for model in models
        ]
        
        # Сохранение полного списка опций для фильтрации
        self.all_options = self.options.copy()
        
        # Установка начального значения (первая модель из списка)
        self.value = models[0]['id'] if models else None
        
        # Создание поля поиска для фильтрации моделей
        self.search_field = ft.TextField(
            on_change=self.filter_options,        # Функция обработки изменений
            hint_text="Поиск модели",            # Текст-подсказка в поле поиска
            **AppStyles.MODEL_SEARCH_FIELD       # Применение стилей из конфигурации
        )

    def filter_options(self, e):
        """
        Фильтрация списка моделей на основе введенного текста поиска.
        
        Args:
            e: Событие изменения текста в поле поиска
        """
        # Получение текста поиска в нижнем регистре
        search_text = self.search_field.value.lower() if self.search_field.value else ""
        
        # Если поле поиска пустое - показываем все модели
        if not search_text:
            self.options = self.all_options
        else:
            # Фильтрация моделей по тексту поиска
            # Ищем совпадения в названии или ID модели
            self.options = [
                opt for opt in self.all_options
                if search_text in opt.text.lower() or search_text in opt.key.lower()
            ]
        
        # Обновление интерфейса для отображения отфильтрованного списка
        e.page.update()


class AuthScreen(ft.Container):
    """
    Экран авторизации для ввода API ключа OpenRouter.ai.
    
    Запрашивает у пользователя API ключ и проверяет его валидность.
    При успешной проверке генерирует PIN-код и сохраняет его вместе с ключом.
    """
    def __init__(self, on_api_key_validated, api_client, cache):
        """
        Инициализация экрана авторизации.
        
        Args:
            on_api_key_validated (callable): Функция обратного вызова при успешной валидации
            api_client: Клиент API для проверки ключа
            cache: Объект кэша для сохранения данных аутентификации
        """
        super().__init__()
        
        # Сохранение переданных параметров
        self.on_api_key_validated = on_api_key_validated
        self.api_client = api_client
        self.cache = cache
        
        # Настройка контейнера
        self.padding = 20
        self.alignment = ft.alignment.center
        self.expand = True
        
        # Поле ввода API ключа
        self.api_key_field = ft.TextField(
            label="API ключ OpenRouter.ai",
            hint_text="Введите ваш API ключ",
            password=True,
            can_reveal_password=True,
            width=400,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700,
            autofocus=True
        )
        
        # Текст для отображения статуса
        self.status_text = ft.Text(
            value="",
            color=ft.Colors.RED_500,
            size=14,
            visible=False
        )
        
        # Кнопка проверки ключа
        self.validate_button = ft.ElevatedButton(
            text="Проверить ключ",
            width=200,
            on_click=self.validate_api_key
        )
        
        # Создание интерфейса экрана
        self.content = ft.Column(
            controls=[
                ft.Text(
                    value="Добро пожаловать в AI Chat",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE
                ),
                ft.Text(
                    value="Для начала работы введите ваш API ключ OpenRouter.ai",
                    size=16,
                    color=ft.Colors.WHITE70
                ),
                ft.Container(height=20),  # Отступ
                self.api_key_field,
                self.status_text,
                ft.Container(height=10),  # Отступ
                self.validate_button
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
        )
    
    async def validate_api_key(self, e):
        """
        Проверка введенного API ключа.
        
        Проверяет валидность ключа через API,
        при успешной проверке генерирует PIN-код.
        """
        # Получение введенного ключа
        api_key = self.api_key_field.value
        
        # Проверка на пустой ключ
        if not api_key:
            self.show_error("Введите API ключ")
            return
        
        # Визуальная индикация процесса проверки
        self.validate_button.disabled = True
        self.status_text.value = "Проверка ключа..."
        self.status_text.color = ft.Colors.BLUE_400
        self.status_text.visible = True
        e.page.update()
        
        try:
            # Временная установка API ключа для проверки
            original_key = self.api_client.api_key
            self.api_client.api_key = api_key
            
            # Проверка баланса для подтверждения валидности ключа
            balance = self.api_client.get_balance()
            
            # Если ключ не валидный, API вернет "Ошибка"
            if balance == "Ошибка":
                self.show_error("Неверный API ключ")
                self.api_client.api_key = original_key
                return
            
            # Генерация PIN-кода (4 цифры)
            import random
            pin = ''.join([str(random.randint(0, 9)) for _ in range(4)])
            
            # Сохранение ключа и PIN-кода
            success = self.cache.save_auth_data(api_key, pin)
            
            if success:
                # Показ сгенерированного PIN-кода пользователю
                self.show_pin_dialog(e.page, pin)
            else:
                self.show_error("Ошибка сохранения данных")
                self.api_client.api_key = original_key
        
        except Exception as ex:
            # Обработка ошибок во время проверки
            self.show_error(f"Ошибка: {str(ex)}")
            self.validate_button.disabled = False
            e.page.update()
    
    def show_error(self, message):
        """
        Отображение сообщения об ошибке.
        """
        self.status_text.value = message
        self.status_text.color = ft.Colors.RED_500
        self.status_text.visible = True
        self.validate_button.disabled = False
        self.api_key_field.border_color = ft.Colors.RED_500
        self.api_key_field.update()
        self.status_text.update()
        self.validate_button.update()
    
    def show_pin_dialog(self, page, pin):
        """
        Отображение диалога с PIN-кодом.
        
        Args:
            page: Объект страницы Flet
            pin (str): Сгенерированный PIN-код
        """
        def close_dialog(e):
            dialog.open = False
            page.update()
            
            # Вызов функции обратного вызова после успешной валидации
            self.on_api_key_validated()
        
        # Создание диалога с PIN-кодом
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("PIN-код создан"),
            content=ft.Column(
                controls=[
                    ft.Text("Ваш PIN-код для входа в приложение:"),
                    ft.Text(
                        value=pin,
                        size=36,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.BLUE_500,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Text(
                        "Запомните или запишите этот PIN-код. "
                        "Он будет использоваться для входа в приложение.",
                        size=14,
                        color=ft.Colors.GREY_400
                    )
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            ),
            actions=[
                ft.ElevatedButton(
                    text="Понятно",
                    on_click=close_dialog
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        # Отображение диалога
        page.overlay.append(dialog)
        dialog.open = True
        page.update()


class PinScreen(ft.Container):
    """
    Экран ввода PIN-кода для входа в приложение.
    
    Запрашивает у пользователя 4-значный PIN-код и проверяет его корректность.
    """
    def __init__(self, on_pin_validated, on_reset_api_key, cache):
        """
        Инициализация экрана ввода PIN-кода.
        
        Args:
            on_pin_validated (callable): Функция обратного вызова при успешной валидации
            on_reset_api_key (callable): Функция обратного вызова при сбросе ключа
            cache: Объект кэша для проверки PIN-кода
        """
        super().__init__()
        
        # Сохранение переданных параметров
        self.on_pin_validated = on_pin_validated
        self.on_reset_api_key = on_reset_api_key
        self.cache = cache
        
        # Настройка контейнера
        self.padding = 20
        self.alignment = ft.alignment.center
        self.expand = True
        
        # Поле ввода PIN-кода
        self.pin_field = ft.TextField(
            label="PIN-код",
            hint_text="Введите 4-значный PIN",
            password=True,
            can_reveal_password=True,
            width=200,
            border_color=ft.Colors.BLUE_400,
            focused_border_color=ft.Colors.BLUE_700,
            autofocus=True,
            max_length=4,
            text_align=ft.TextAlign.CENTER
        )
        
        # Текст для отображения статуса
        self.status_text = ft.Text(
            value="",
            color=ft.Colors.RED_500,
            size=14,
            visible=False
        )
        
        # Кнопка проверки PIN-кода
        self.validate_button = ft.ElevatedButton(
            text="Войти",
            width=200,
            on_click=self.validate_pin
        )
        
        # Кнопка сброса API ключа
        self.reset_button = ft.TextButton(
            text="Сбросить API ключ",
            on_click=self.confirm_reset_api_key
        )
        
        # Создание интерфейса экрана
        self.content = ft.Column(
            controls=[
                ft.Text(
                    value="Вход в AI Chat",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE
                ),
                ft.Text(
                    value="Введите ваш PIN-код для входа",
                    size=16,
                    color=ft.Colors.WHITE70
                ),
                ft.Container(height=20),  # Отступ
                self.pin_field,
                self.status_text,
                ft.Container(height=10),  # Отступ
                self.validate_button,
                self.reset_button
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10
        )
    
    def validate_pin(self, e):
        """
        Проверка введенного PIN-кода.
        """
        # Получение введенного PIN-кода
        pin = self.pin_field.value
        
        # Проверка на пустой PIN-код
        if not pin:
            self.show_error("Введите PIN-код")
            return
        
        # Проверка длины PIN-кода
        if len(pin) != 4:
            self.show_error("PIN-код должен содержать 4 цифры")
            return
        
        # Проверка, что PIN-код состоит только из цифр
        if not pin.isdigit():
            self.show_error("PIN-код должен содержать только цифры")
            return
        
        # Проверка PIN-кода в базе данных
        is_valid = self.cache.check_pin(pin)
        
        if is_valid:
            # Если PIN-код верный, вызываем функцию обратного вызова
            self.on_pin_validated()
        else:
            # Если PIN-код неверный, показываем ошибку
            self.show_error("Неверный PIN-код")
    
    def show_error(self, message):
        """
        Отображение сообщения об ошибке.
        """
        self.status_text.value = message
        self.status_text.color = ft.Colors.RED_500
        self.status_text.visible = True
        self.pin_field.border_color = ft.Colors.RED_500
        self.pin_field.update()
        self.status_text.update()
    
    def confirm_reset_api_key(self, e):
        """
        Подтверждение сброса API ключа.
        """
        def close_dialog(e):
            dialog.open = False
            e.page.update()
        
        def reset_confirmed(e):
            # Сброс API ключа в базе данных
            self.cache.reset_auth_data()
            # Закрытие диалога
            close_dialog(e)
            # Вызов функции обратного вызова
            self.on_reset_api_key()
        
        # Создание диалога подтверждения
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Подтверждение сброса"),
            content=ft.Text(
                "Вы уверены, что хотите сбросить API ключ? "
                "Вам придется ввести новый ключ и получить новый PIN-код."
            ),
            actions=[
                ft.TextButton("Отмена", on_click=close_dialog),
                ft.TextButton("Сбросить", on_click=reset_confirmed),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # Отображение диалога
        e.page.overlay.append(dialog)
        dialog.open = True
        e.page.update()
