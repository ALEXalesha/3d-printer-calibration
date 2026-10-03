"""Writes profiles/tests.json: the 10 tests in print order with names, hints, the result
helper and the parameters shown in the UI. Shared by both editions. Run after editing."""
import json
from pathlib import Path


def L(ru, en):
    return {"ru": ru, "en": en}


def P(key, type_, mn, mx, step, ru, en, digits=None):
    d = {"key": key, "type": type_, "min": mn, "max": mx, "step": step, "label": L(ru, en)}
    if digits is not None:
        d["digits"] = digits
    return d


TESTS = [
    dict(id="first_layer", minutes_hint=11, fast=False,
         name=L("Первый слой", "First layer"),
         look=L("9 квадратов по столу в один слой: везде ровно, без щелей и борозд.",
                "9 single-layer squares over the bed: smooth everywhere, no gaps, no ridges."),
         result=L("Если плохо - чистка и выравнивание стола, Z-смещение.",
                  "If not: clean and level the bed, adjust the Z offset."),
         helper=None, params=[]),
    dict(id="temp_tower", minutes_hint=75, fast=False,
         name=L("Башня температур", "Temperature tower"),
         look=L("Уровень с меньше всего нитей, без провиса моста, с гладкими стенками. Температура выдавлена на передней грани.",
                "The level with the fewest strings, no sagging bridge and smooth walls. The temperature is embossed on the front face."),
         result=L("«Температура сопла» в профиле пластика.", "\"Nozzle temperature\" in the filament profile."),
         helper=dict(kind="temp", input=L("Лучший уровень (число на грани), °C", "Best level (number on the face), °C")),
         params=[P("t_start", "int", 150, 350, 5, "Внизу, °C", "Bottom, °C"),
                 P("t_end", "int", 150, 350, 5, "Вверху, °C", "Top, °C"),
                 P("t_step", "int", 1, 20, 1, "Шаг, °C", "Step, °C")]),
    dict(id="flow", minutes_hint=19, fast=False,
         name=L("Поток", "Flow"),
         look=L("Плашка с самым гладким верхом: без щелей (мало) и бугров (много).",
                "The plate with the smoothest top: no gaps (too little) and no bumps (too much)."),
         result=L("«Коэффициент потока» × число / 100.", "\"Flow ratio\" × number / 100."),
         helper=dict(kind="flow", input=L("Лучшая плашка (число под ней), %", "Best plate (number below it), %")),
         params=[P("f_start", "int", 50, 120, 1, "Первая плашка, %", "First plate, %"),
                 P("f_step", "int", 1, 10, 1, "Шаг, %", "Step, %")]),
    dict(id="pressure_advance", minutes_hint=7, fast=False,
         name=L("Pressure advance", "Pressure advance"),
         look=L("Линия ровной толщины на переходах медленно-быстро. Подпись в тысячных: 025 = 0.025.",
                "The line of even width at the slow-fast transitions. Label in thousandths: 025 = 0.025."),
         result=L("«Pressure advance» (Klipper), «K» Linear Advance (Marlin), M572 (RRF).",
                  "\"Pressure advance\" (Klipper), Linear Advance \"K\" (Marlin), M572 (RRF)."),
         helper=dict(kind="pa", input=L("Лучшая линия (подпись справа)", "Best line (label on the right)")),
         params=[P("pa_start", "num", 0, 1.5, 0.005, "От", "From", 3),
                 P("pa_end", "num", 0.005, 2, 0.005, "До", "To", 3),
                 P("pa_step", "num", 0.001, 0.1, 0.001, "Шаг", "Step", 3)]),
    dict(id="retraction", minutes_hint=32, fast=False,
         name=L("Откат", "Retraction"),
         look=L("Наименьший откат без нитей между колоннами. Подпись в десятых мм: 08 = 0.8.",
                "The smallest retraction with no strings between the columns. Label in tenths of mm: 08 = 0.8."),
         result=L("«Длина отката» в профиле принтера.", "\"Retraction length\" in the printer profile."),
         helper=dict(kind="retraction", input=L("Лучший уровень (подпись на колонне)", "Best level (label on the column)")),
         params=[P("r_start", "num", 0.1, 10, 0.1, "Первый уровень, мм", "First level, mm", 2),
                 P("r_step", "num", 0.05, 2, 0.05, "Шаг, мм", "Step, mm", 2),
                 P("r_count", "int", 2, 12, 1, "Уровней", "Levels")]),
    dict(id="max_flow", minutes_hint=11, fast=True,
         name=L("Максимальный расход", "Max volumetric flow"),
         look=L("Высота, где стенка стала рваной или защёлкал экструдер; цифры на стенке - мм³/с.",
                "The height where the wall turns rough or the extruder clicks; numbers on the wall are mm³/s."),
         result=L("«Макс. объёмная скорость» = 80-90 % от предела.", "\"Max volumetric speed\" = 80-90 % of the limit."),
         helper=dict(kind="max_flow", input=L("Предел, мм³/с (цифра на стенке)", "Limit, mm³/s (number on the wall)")),
         params=[P("v_start", "num", 0.5, 60, 0.5, "Внизу, мм³/с", "Bottom, mm³/s", 1),
                 P("v_end", "num", 2, 80, 0.5, "Вверху, мм³/с", "Top, mm³/s", 1)]),
    dict(id="overhang_bridge", minutes_hint=56, fast=False,
         name=L("Нависания и мосты", "Overhangs and bridges"),
         look=L("Наибольший угол нависания без провиса (подписи 20-80° от вертикали); самый длинный ровный мост.",
                "The largest overhang angle without sagging (labels 20-80° from vertical); the longest clean bridge."),
         result=L("Где нужны поддержки.", "Where supports are needed."),
         helper=dict(kind="overhang", input=L("Наибольший ровный угол, °", "Largest clean angle, °")),
         params=[]),
    dict(id="ringing", minutes_hint=32, fast=True,
         name=L("Рябь (разгон)", "Ringing (acceleration)"),
         look=L("Пояс, с которого после углов появилась рябь. Номер пояса на передней стенке.",
                "The band where ripples appear after the corners. The band number is on the front wall."),
         result=L("Разгон наружных стенок - на пояс ниже.", "Outer wall acceleration - one band lower."),
         helper=dict(kind="ringing", input=L("Номер пояса, где появилась рябь", "Band number where ringing starts")),
         params=[P("a_start", "int", 100, 50000, 100, "Первый пояс, мм/с²", "First band, mm/s²"),
                 P("a_step", "int", 100, 10000, 100, "Шаг, мм/с²", "Step, mm/s²"),
                 P("a_count", "int", 2, 16, 1, "Поясов", "Bands")]),
    dict(id="tolerance", minutes_hint=45, fast=False,
         name=L("Зазоры", "Tolerances"),
         look=L("Наименьший зазор, где штырь выходит из рамки. Подпись в сотых мм: 15 = 0.15.",
                "The smallest gap where the peg comes out of its frame. Label in hundredths of mm: 15 = 0.15."),
         result=L("Зазор для подвижных и вставных деталей.", "Clearance for moving and press-fit parts."),
         helper=dict(kind="tolerance", input=L("Наименьший рабочий зазор (подпись)", "Smallest working gap (label)")),
         params=[P("gaps", "list", 0.02, 1.0, 0.01, "Зазоры, мм (через пробел)", "Gaps, mm (space separated)", 2)]),
    dict(id="cube", minutes_hint=18, fast=False,
         name=L("Кубик", "Cube"),
         look=L("Размеры по X, Y, Z штангенциркулем (передняя грань - с числом).",
                "Measure X, Y, Z with calipers (the front face has the number)."),
         result=L("Все стороны одинаково меньше или больше - поток или усадка; одна ось - натяжение её ремня.",
                  "All sides equally off - flow or shrinkage; one axis only - that axis' belt tension."),
         helper=dict(kind="cube", input=L("Измерено X Y Z, мм", "Measured X Y Z, mm")),
         params=[P("size", "int", 10, 40, 1, "Размер, мм", "Size, mm")]),
]

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "profiles" / "tests.json"
    doc = {"_comment": "Made by tools/make_tests_json.py. The 10 tests in print order.", "tests": TESTS}
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(out)
