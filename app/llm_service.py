import json

models = [
  'gemini-3.8-flash',
  'gemini-3.7-flash',
  'gemini-3.6-flash',
  'gemini-3.5-flash',
  'gemini-3.5-flash-lite',
  'gemini-3.1-flash-lite',
]


def generate_product_card(ai_client, product_file_path):
    model_count = -1
    with open(product_file_path, "r", encoding='utf-8') as file:
        product_data = file.read()
    with open("promt.txt", "r", encoding='utf-8') as file:
        promt_text = file.read()

    try:
        if not isinstance(json.loads(product_data), dict):
            return "Содержание файла не является словарем", None
    except Exception as ex:
        return "Не смог преобразовать файл в JSON формат: " + str(ex), None

    while model_count < len(models) - 1:
        model_count += 1
        try:
            chat = ai_client.chats.create(model=models[model_count])
            response = chat.send_message(promt_text + product_data)
            return response.text, chat
        except Exception as ex:
            print(f"Модель {models[model_count]} недоступна: {ex.message}")

    return "Ни одна модель не смогла сгенерировать результат.", None

def validate_ai_response(ai_response: str):
    response_mandatory_items = ["seo_title", "seo_description", "characteristics", "search_queries",
                       "commercial_block", "missing_data", "warnings"]
    commercial_mandatory_items = ["purpose", "target_audience", "features", "what_to_clarify"]
    errors = []
    response = None

    if not isinstance(ai_response, str):
        return ["Ответ AI должен быть строкой."]
    try: response = json.loads(ai_response)
    except json.JSONDecodeError as ex:
        return ["Неверный синтаксис JSON: " + str(ex)]

    if not isinstance(response, dict):
        return ["Корневой элемент JSON должен быть объектом."]

    missing_keys = set(response_mandatory_items) - set(response.keys())
    if missing_keys:
        return [f"Отсутствуют обязательные поля: {missing_keys}"]

    seo_title = response["seo_title"]
    if not isinstance(seo_title, str):
        errors.append("SEO заголовок должен быть строкой.")
    elif len(seo_title) > 70:
        errors.append(f"SEO заголовок должен быть объемом не более 70 символов, сейчас символов "
                    f"{len(seo_title)}. Уменьши количество символов в заголовке, "
                    f"но не убирай слишком много информации, особенно важной")

    seo_description = response["seo_description"]
    if not isinstance(seo_description, str):
        errors.append("SEO писание должен быть строкой.")

    if not isinstance(response["characteristics"], list):
        errors.append("characteristics должен быть списком.")
    else:
        for id, el in enumerate(response["characteristics"]):
            if not isinstance(el, dict):
                errors.append(f"Элемент characteristics[{id}] не является объектом")
                continue
            if not isinstance(el.get("name"), str):
                errors.append(f"Внутри characteristics[{id}] отсутствует поле name")
            if not isinstance(el.get("value"), str):
                errors.append(f"Внутри characteristics[{id}] отсутствует поле value")

    search_queries = response["search_queries"]
    if not isinstance(search_queries, list):
        errors.append("search_queries должен быть списком.")
    elif not 3 <= len(search_queries) <= 5:
        errors.append("Количество поисковых запросов должно быть от 3 до 5.")
    elif not all(isinstance(query, str) for query in search_queries):
        errors.append("Все поисковые запросы должны быть строками.")

    commercial_block = response["commercial_block"]
    if not isinstance(commercial_block, dict):
        errors.append("Commercial блок должен быть объектом JSON.")
    else:
        missing_commercial_keys = set(commercial_mandatory_items) - set(commercial_block.keys())
        if missing_commercial_keys:
            errors.append(f"Внутри блока commercial отсутствуют следующие поля: {missing_commercial_keys}")
        else:
            for key in ["purpose", "target_audience", "features"]:
                if not isinstance(commercial_block[key], str):
                    errors.append(f"Поле commercial_block[{key}] должно быть строкой")
            what_to_clarify = commercial_block["what_to_clarify"]
            if not isinstance(what_to_clarify, list):
                errors.append("commercial_block[what_to_clarify] должен быть списком")
            elif not all(isinstance(el, str) for el in what_to_clarify):
                errors.append("Все элементы commercial_block[what_to_clarify] должны быть строками")

    if isinstance(seo_description, str) and isinstance(response["warnings"], list) and all(isinstance(item, str) for item in response["warnings"]):
        description_length = len(seo_description)
        warnings = response["warnings"]

        if description_length > 1200:
            errors.append(f"SEO-описание не должно превышать 1200 символов. Сейчас: {description_length}.")

        elif description_length < 800 and not any(warnings):
            errors.append(f"SEO-описание содержит {description_length} символов. Если информации "
                          f"недостаточно для 800 символов, добавь соответствующее предупреждение в warnings.")


    return errors


def validate_product_characteristics(ai_response: str, product_file_path: str):
    errors = []

    try:
        with open(product_file_path, "r", encoding="utf-8") as file:
            product_data = json.load(file)

        response = json.loads(ai_response)

    except (OSError, json.JSONDecodeError) as ex:
        return [f"Не удалось проверить характеристики: {ex}"]

    source_specs = product_data.get("specs", {})
    expected_specs = product_data.get("expected_specs", [])
    result_specs = response.get("characteristics", [])

    if not isinstance(source_specs, dict): return ["Поле specs во входном JSON должно быть объектом."]
    if not isinstance(expected_specs, list): return ["Поле expected_specs должно быть списком."]
    if not isinstance(result_specs, list): return ["characteristics в ответе AI должен быть списком."]

    result_dict = {}
    for item in result_specs:
        if not isinstance(item, dict):
            continue

        name = item.get("name")
        value = item.get("value")

        if isinstance(name, str) and isinstance(value, str):
            result_dict[name.strip().casefold()] = value

    for name, value in source_specs.items():
        normalized_name = str(name).strip().casefold()

        if value is None or str(value).strip() == "": expected_value = "Данных нет"
        else: expected_value = str(value)

        if normalized_name not in result_dict: errors.append(f"В результате отсутствует характеристика: {name}")

        elif result_dict[normalized_name] != expected_value:
            errors.append(f"Изменено значение характеристики '{name}'. Ожидалось: '{expected_value}', "
                f"получено: '{result_dict[normalized_name]}'.")

    expected_names = {str(name).strip().casefold() for name in expected_specs}
    source_names = {str(name).strip().casefold() for name in source_specs.keys()}

    for name in expected_specs:
        normalized_name = str(name).strip().casefold()

        if normalized_name not in source_names:
            if normalized_name not in result_dict:
                errors.append(f"Отсутствует ожидаемая характеристика: {name}")

            elif result_dict[normalized_name] != "Данных нет":
                errors.append(f"Характеристика '{name}' должна иметь значение 'Данных нет', так как отсутствует во входных данных.")

    allowed_names = source_names | expected_names

    for name in result_dict:
        if name not in allowed_names:
            errors.append(f"Добавлена неизвестная характеристика: {name}")

    return errors
