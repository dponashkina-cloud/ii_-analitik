import io
import re
import pandas as pd


# ========== КЛЮЧЕВЫЕ СЛОВА ==========
REPORT_MARKERS = {
    'баланс': 'Бухгалтерский баланс',
    'финансовых результатах': 'Отчёт о финансовых результатах',
    'прибылях и убытках': 'Отчёт о финансовых результатах',
    'движении денежных средств': 'Отчёт о движении денежных средств',
}

SKIP_KEYWORDS = [
    'итого по разделу', 'актив', 'пассив',
    'внеоборотные активы', 'оборотные активы',
    'капитал и резервы', 'долгосрочные обязательства',
    'краткосрочные обязательства', 'справочно',
    'наименование показателя', 'денежные потоки',
    'поступления - всего', 'платежи - всего',
    'в том числе', 'отчёт', 'отчет', 'бухгалтерский баланс',
]

# Диапазон допустимых годов
YEAR_MIN = 1990
YEAR_MAX = 2099


# ========== МЕХАНИЗМ 2: УНИВЕРСАЛЬНОЕ ЧТЕНИЕ ЛЕТ ==========
def extract_year(value):
    """Извлекает год из ячейки в разных форматах."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    # Ищем 4-значное число в диапазоне 1990-2099
    match = re.search(r'\b(19\d{2}|20\d{2})\b', s)
    if match:
        year = int(match.group(1))
        if YEAR_MIN <= year <= YEAR_MAX:
            return year
    return None


def is_year_cell(value):
    """Проверяет, является ли ячейка годом."""
    return extract_year(value) is not None


# ========== ЧИСТКА ЧИСЕЛ ==========
def clean_number(value):
    """Преобразует '2 075 419' -> 2075419, '—' -> None."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s in ('', '-', '—', '–', 'x', 'X', 'nan', 'None'):
        return None
    s = s.replace(' ', '').replace('\xa0', '').replace(',', '.')
    s = re.sub(r'[^\d\-\.]', '', s)
    if not s or s == '-':
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ========== ОПРЕДЕЛЕНИЕ ОТЧЁТА ==========
def find_report_title(row_values):
    text = ' '.join(str(v).lower() for v in row_values if pd.notna(v))
    for marker, title in REPORT_MARKERS.items():
        if marker in text:
            return title
    return None


# ========== МЕХАНИЗМ 1: ОПРЕДЕЛЕНИЕ ОРИЕНТАЦИИ ==========
def detect_orientation(df):
    """
    Определяет, где годы: в столбцах или в строках.
    Возвращает: ('columns', row_idx) | ('rows', col_idx) | (None, None)
    """
    # Ищем строку с 3+ годами (годы в столбцах — обычная ориентация)
    for idx in range(min(15, len(df))):
        row = df.iloc[idx].tolist()
        years_count = sum(1 for v in row if is_year_cell(v))
        if years_count >= 3:
            return ('columns', idx)

    # Ищем столбец с 3+ годами (годы в строках — надо транспонировать)
    for col_idx in range(min(5, len(df.columns))):
        col = df.iloc[:, col_idx].tolist()
        years_count = sum(1 for v in col if is_year_cell(v))
        if years_count >= 3:
            return ('rows', col_idx)

    return (None, None)


# ========== ПАРСИНГ ЛИСТА (годы в столбцах) ==========
def parse_columns_orientation(df, start_row, sheet_name):
    """Парсит лист, где годы в столбцах."""
    records = []

    # Извлекаем годы из строки-заголовка
    header_row = df.iloc[start_row].tolist()
    header_years = []
    header_positions = []
    for i, v in enumerate(header_row):
        year = extract_year(v)
        if year:
            header_years.append(year)
            header_positions.append(i)

    current_report = sheet_name

    for idx in range(start_row + 1, len(df)):
        row_values = df.iloc[idx].tolist()

        # Проверяем, не заголовок ли это нового отчёта
        report_title = find_report_title(row_values)
        if report_title:
            current_report = report_title
            continue

        metric_name = str(row_values[0]).strip() if row_values else ''
        if not metric_name:
            continue

        metric_lower = metric_name.lower()
        if any(skip in metric_lower for skip in SKIP_KEYWORDS):
            continue

        for year, pos in zip(header_years, header_positions):
            if pos >= len(row_values):
                continue
            value = clean_number(row_values[pos])
            if value is not None:
                records.append((current_report, metric_name, year, value))

    return records


# ========== ПАРСИНГ ЛИСТА (годы в строках) ==========
def parse_rows_orientation(df, year_col, sheet_name):
    """Парсит лист, где годы в строках — транспонируем логику."""
    records = []

    # Извлекаем годы из столбца
    header_years = []
    header_rows = []
    for idx in range(len(df)):
        year = extract_year(df.iloc[idx, year_col])
        if year:
            header_years.append(year)
            header_rows.append(idx)

    # Показатели — в других столбцах (кроме столбца с годами)
    metric_columns = [c for c in range(len(df.columns)) if c != year_col]

    for col_idx in metric_columns:
        # Название показателя — в первой строке с текстом
        metric_name = None
        for idx in range(min(10, len(df))):
            val = str(df.iloc[idx, col_idx]).strip()
            if val and not is_year_cell(val) and clean_number(val) is None:
                metric_name = val
                break

        if not metric_name:
            continue

        metric_lower = metric_name.lower()
        if any(skip in metric_lower for skip in SKIP_KEYWORDS):
            continue

        for year, row_idx in zip(header_years, header_rows):
            if col_idx >= len(df.columns):
                continue
            value = clean_number(df.iloc[row_idx, col_idx])
            if value is not None:
                records.append((sheet_name, metric_name, year, value))

    return records


# ========== ГЛАВНАЯ ФУНКЦИЯ ПАРСИНГА ==========
def parse_excel(file_bytes):
    """
    Читает Excel и возвращает:
    (records, raw_text, error)
    - records: список (отчёт, показатель, год, значение)
    - raw_text: сырой текст для fallback в GigaChat (если парсер не справился)
    """
    try:
        sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None, header=None)
    except Exception as e:
        return None, None, f"Не удалось прочитать Excel: {e}"

    all_records = []
    raw_parts = []

    for sheet_name, df in sheets.items():
        if df.empty:
            continue

        df = df.fillna('')

        # Сохраняем сырой текст листа (для fallback)
        raw_text = df.to_csv(index=False, sep='|')
        raw_parts.append(f"### Лист: {sheet_name}\n{raw_text}")

        # Определяем ориентацию
        orientation, pos = detect_orientation(df)

        if orientation == 'columns':
            records = parse_columns_orientation(df, pos, sheet_name)
            all_records.extend(records)
        elif orientation == 'rows':
            records = parse_rows_orientation(df, pos, sheet_name)
            all_records.extend(records)
        else:
            # Не смогли определить ориентацию — этот лист пропускаем,
            # но сырой текст сохраняем для fallback
            continue

    raw_full = "\n\n".join(raw_parts)

    if not all_records:
        return None, raw_full, "Не удалось найти структурированные данные (fallback)."

    return all_records, raw_full, None


# ========== ФОРМИРОВАНИЕ ТЕКСТА ДЛЯ GIGACHAT ==========
def records_to_text(records):
    """Преобразует записи в читаемый текст для GigaChat."""
    if not records:
        return ""

    by_report = {}
    for report, metric, year, value in records:
        by_report.setdefault(report, []).append((metric, year, value))

    parts = []
    for report, items in by_report.items():
        parts.append(f"### {report}")

        metrics = {}
        for metric, year, value in items:
            metrics.setdefault(metric, {})[year] = value

        all_years = sorted({y for _, y, _ in items})

        header = "| Показатель | " + " | ".join(str(y) for y in all_years) + " |"
        separator = "|" + "---|" * (len(all_years) + 1)

        rows = [header, separator]
        for metric, year_values in metrics.items():
            row = f"| {metric} |"
            for y in all_years:
                v = year_values.get(y)
                if v is None:
                    row += " — |"
                else:
                    row += f" {int(v):,} |".replace(",", " ")
            rows.append(row)

        parts.append("\n".join(rows))
        parts.append("")

    return "\n".join(parts)


if __name__ == '__main__':
    print("Модуль parser.py готов.")
