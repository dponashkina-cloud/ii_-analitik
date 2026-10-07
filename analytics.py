"""
Модуль аналитики — точные расчёты по финансовым данным.
GigaChat вызывает эти функции вместо того, чтобы считать сам.
"""


class Analytics:
    def __init__(self, records):
        """
        records: список кортежей (отчёт, показатель, год, значение)
        """
        self.records = records or []
        # Индекс: {(показатель_lower, год): значение}
        self.index = {}
        for report, metric, year, value in self.records:
            key = (metric.lower().strip(), int(year))
            # Если показатель уже есть — суммируем (на случай дублей)
            self.index[key] = self.index.get(key, 0) + value

    # ========== СПИСКИ ==========
    def list_metrics(self):
        """Все уникальные показатели в таблице."""
        metrics = sorted({m for _, m, _, _ in self.records})
        return metrics

    def list_years(self):
        """Все уникальные годы в таблице."""
        years = sorted({int(y) for _, _, y, _ in self.records})
        return years

    def list_reports(self):
        """Все уникальные отчёты."""
        return sorted({r for r, _, _, _ in self.records})

    # ========== ПОИСК ПОКАЗАТЕЛЯ ==========
    def find_metrics(self, name_part):
        """
        Ищет показатели, содержащие name_part (без учёта регистра).
        Возвращает список подходящих названий.
        """
        name_part_lower = name_part.lower().strip()
        matches = [
            m for m in self.list_metrics()
            if name_part_lower in m.lower()
        ]
        return matches

    # ========== ЗНАЧЕНИЯ ==========
    def get_value(self, metric, year):
        """Значение показателя за конкретный год. None если нет."""
        key = (metric.lower().strip(), int(year))
        return self.index.get(key)

    def get_all_for_year(self, year):
        """Все показатели за год. {показатель: значение}."""
        year = int(year)
        result = {}
        for report, metric, y, value in self.records:
            if int(y) == year:
                result[metric] = result.get(metric, 0) + value
        return result

    def get_series(self, metric):
        """
        Временной ряд показателя: {год: значение}.
        Возвращает все годы, где есть данные.
        """
        metric_lower = metric.lower().strip()
        result = {}
        for report, m, year, value in self.records:
            if m.lower().strip() == metric_lower:
                result[int(year)] = result.get(int(year), 0) + value
        return dict(sorted(result.items()))

    # ========== СРАВНЕНИЯ ==========
    def compare_years(self, metric, year1, year2):
        """
        Сравнение показателя между двумя годами.
        Возвращает: {
            'metric': ..., 'year1': ..., 'value1': ...,
            'year2': ..., 'value2': ...,
            'diff': ..., 'percent_change': ...
        }
        """
        v1 = self.get_value(metric, year1)
        v2 = self.get_value(metric, year2)

        if v1 is None:
            return {'error': f'Нет данных: «{metric}» за {year1} год'}
        if v2 is None:
            return {'error': f'Нет данных: «{metric}» за {year2} год'}

        diff = v2 - v1
        percent = (diff / v1 * 100) if v1 != 0 else None

        return {
            'metric': metric,
            'year1': int(year1),
            'value1': v1,
            'year2': int(year2),
            'value2': v2,
            'diff': diff,
            'percent_change': percent,
        }

    def growth_rate(self, metric, year1, year2):
        """Только процент изменения (для краткости)."""
        cmp = self.compare_years(metric, year1, year2)
        if 'error' in cmp:
            return cmp
        return {
            'metric': metric,
            'from': int(year1),
            'to': int(year2),
            'percent_change': cmp['percent_change'],
        }

    # ========== АНАЛИЗ ==========
    def top_metrics_for_year(self, year, limit=5):
        """Топ-N показателей за год по абсолютному значению."""
        all_vals = self.get_all_for_year(year)
        sorted_items = sorted(
            all_vals.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        return sorted_items[:limit]

    def find_max_year(self, metric):
        """Год с максимальным значением показателя."""
        series = self.get_series(metric)
        if not series:
            return {'error': f'Нет данных по показателю «{metric}»'}
        max_year = max(series, key=series.get)
        return {
            'metric': metric,
            'year': max_year,
            'value': series[max_year],
        }

    def find_min_year(self, metric):
        """Год с минимальным значением показателя."""
        series = self.get_series(metric)
        if not series:
            return {'error': f'Нет данных по показателю «{metric}»'}
        min_year = min(series, key=series.get)
        return {
            'metric': metric,
            'year': min_year,
            'value': series[min_year],
        }


if __name__ == '__main__':
    print("Модуль analytics.py готов.")
