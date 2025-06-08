#  ФУНКЦІЯ НОРМАЛІЗАЦІЇ НОМЕРА ТЕЛЕФОНУ
def normalize_phone(phone: str) -> str:
    # Видаляє всі символи, крім цифр і плюса ("+")
    phone = re.sub(r"[^\d+]", "", phone)

    # Якщо номер починається з "0", замінюємо на "+380"
    if phone.startswith("0"):
        phone = "+380" + phone[1:]
    # Якщо номер починається з "380", додаємо "+"
    elif phone.startswith("380"):
        phone = "+" + phone
    # Якщо вже правильний формат — нічого не змінюємо
    elif phone.startswith("+380"):
        pass
    # Усі інші варіанти — помилка
    else:
        raise serializers.ValidationError({
            "phone": "Невірний формат телефону. Має бути у форматі +380XXXXXXXXX"
        })

    # Перевіряємо, що результат повністю відповідає шаблону +380XXXXXXXXX
    if not re.fullmatch(r"\+380\d{9}", phone):
        raise serializers.ValidationError({
            "phone": "Номер телефону має бути у форматі +380XXXXXXXXX"
        })

    return phone