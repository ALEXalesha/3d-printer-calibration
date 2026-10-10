# Changelog

## 1.0.0 - 2026-10-10

The first release. Two editions with the same core: a page (browser, GitHub Pages and
Electron) and a Python program with a Qt window. Both write the same G-code byte for byte.

- Ten calibration tests: first layer, temperature tower, flow, pressure advance,
  retraction, max volumetric flow, overhangs and bridges, ringing, tolerances, 20 mm cube.
  Time and grams for each, a preview (top and front views, 3D in the page) and a helper
  that turns "the best line" into the number for the slicer profile.
- For the Elegoo Centauri Carbon profile the output is byte for byte the G-code of the
  original script, printed and checked on the real printer (20 files, PETG and PLA).
- Your own G-code sets the printer up: the start and end code and the firmware come from a
  file sliced by OrcaSlicer, ElegooSlicer, Bambu Studio, PrusaSlicer, SuperSlicer or Cura.
- 14 printer profiles (Klipper, Marlin, RepRapFirmware, delta; popular printers marked
  "not checked"), 5 materials, nozzles 0.2 to 0.8 mm.
- A G-code check reads every file back: bed limits, Z, speeds, extrusion, temperatures,
  layer time, commands of another firmware.
- Save into a folder or a zip; own profiles to a file; five themes (glass, light, night, warm,
  formal), Russian and English; the window remembers its size and place.

## 1.0.0 - 2026-10-10 (по-русски)

Первый выпуск. Две версии с одним ядром: страница (браузер, GitHub Pages и Electron) и
программа на Python с окном Qt. Обе пишут одинаковый G-code байт в байт.

- Десять калибровочных тестов: первый слой, башня температур, поток, опережение давления,
  откат, максимальный расход, нависания и мосты, рябь, зазоры, кубик 20 мм. Для каждого -
  время и граммы, предпросмотр (вид сверху и спереди, на странице ещё 3D) и помощник,
  который превращает «лучшую линию» в число для профиля слайсера.
- Для профиля Elegoo Centauri Carbon результат байт в байт совпадает с G-code исходного
  скрипта, напечатанным и проверенным на настоящем принтере (20 файлов, PETG и PLA).
- Свой G-code настраивает принтер: начальный и конечный код и прошивка берутся из файла
  OrcaSlicer, ElegooSlicer, Bambu Studio, PrusaSlicer, SuperSlicer или Cura.
- 14 профилей принтеров (Klipper, Marlin, RepRapFirmware, дельта; популярные принтеры с
  пометкой «не проверено»), 5 пластиков, сопла от 0.2 до 0.8 мм.
- Проверка G-code перечитывает каждый файл: границы стола, Z, скорости, экструзия,
  температуры, время слоя, команды чужой прошивки.
- Сохранение в папку или zip, свои профили в файл; пять тем (стекло, светлая, ночная,
  тёплая, строгая), русский и английский; окно запоминает размер и место.
