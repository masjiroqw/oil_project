import asyncio
import os

import gspread

from logger_config import setup_logger
from src.schemas.schema import FinancialTuple, FuelTuple, StationType

logger = setup_logger()

class SheetsService:
    """Запись отчётов в Google таблицу"""

    # Тип заправки -> название листа (должно точно совпадать с названием вкладки)
    FUEL_SHEETS = {
        StationType.NYAGAN: "Остаток Нягань",
        StationType.YNYGAN: "Остаток Уньюган",
    }
    FINANCIAL_SHEETS = {
        StationType.NYAGAN: "Закуп,реализация Нягань",
        StationType.YNYGAN: "Закуп, реализация Уньюган",
    }

    # Топливный отчёт: колонка E (ДТ) — по ней ищем первую пустую строку
    FUEL_COLUMN = 5
    FUEL_RANGE = "E{row}:H{row}"        # E — ДТ, F — АИ-95, G — АИ-92, H — goal

    # Финансовый отчёт: колонка D (Реализация наличные) — по ней ищем первую пустую строку
    FINANCIAL_COLUMN = 4
    FINANCIAL_RANGE = "D{row}:F{row}"   # D — реализация наличные, E — реализация безнал, F — сдано

    def __init__(self) -> None:
        gc = gspread.service_account(filename=os.environ["GOOGLE_CREDENTIALS"])
        self.spreadsheet = gc.open_by_key(os.environ["SHEET_ID"])

    def _append(self, sheet_name: str, column: int, range_template: str, values: list) -> int:
        """Пишет values в первую пустую строку листа (пустую по колонке column)."""
        ws = self.spreadsheet.worksheet(sheet_name)

        # col_values возвращает значения колонки до последней заполненной ячейки,
        # значит следующая строка после них — первая пустая
        row = len(ws.col_values(column)) + 1

        ws.update(
            [values],
            range_template.format(row=row),
            value_input_option="USER_ENTERED",  # чтобы числа легли как числа, а не текст
        )
        return row

    async def save_fuel_report(self, report: FuelTuple) -> None:
        sheet = self.FUEL_SHEETS[StationType(report.station_type)]
        values = [report.total_diesel, report.total_95, report.total_92, report.goal]
        # gspread синхронный, поэтому запускаем в отдельном потоке
        row = await asyncio.to_thread(self._append, sheet, self.FUEL_COLUMN, self.FUEL_RANGE, values)
        logger.info(f"Fuel report saved to sheet '{sheet}', row {row}")

    async def save_financial_report(self, report: FinancialTuple) -> None:
        sheet = self.FINANCIAL_SHEETS[StationType(report.station_type)]
        values = [report.cash, report.card, report.submitted]
        row = await asyncio.to_thread(self._append, sheet, self.FINANCIAL_COLUMN, self.FINANCIAL_RANGE, values)
        logger.info(f"Financial report saved to sheet '{sheet}', row {row}")
