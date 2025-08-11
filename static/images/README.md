# Изображения и фоны

В этой папке находятся SVG и CSS-ресурсы в фиолетовой палитре для UI.

Состав:
- backgrounds.css — готовые классы для градиентных фонов и «дышащего» эффекта.
- bg-gradient-1.svg, bg-gradient-2.svg — абстрактные фоны (градиенты + волны/шум).
- bg-animated-wave.svg — анимированный фон с плавной волной (SVG SMIL).
- pattern-dots.svg — повторяющийся паттерн «точки».
- icon-video.svg, icon-arrow.svg — иконки для процесса конвертации.
- convert-flow.svg — иллюстрация конвертации: видео → обработка → файл.
- loader-spinner.svg — анимированный индикатор загрузки.
- pulse-bubble.svg — пульсирующая точка статуса.
- anim-arrow-loop.svg — анимированная «полоса-стрелка» для индикации прогресса.

Примеры использования:

CSS-градиенты:

<div class="bg-violet-linear" style="height:280px"></div>
<div class="bg-violet-radial" style="height:280px"></div>
<div class="bg-violet-conic" style="height:280px"></div>

Подключение CSS:
<link rel="stylesheet" href="/static/images/backgrounds.css" />

Фон через IMG или как background-image:
<img src="/static/images/bg-gradient-1.svg" alt="Violet gradient" />

.hero {
  background-image: url('/static/images/bg-gradient-2.svg');
  background-size: cover;
  background-position: center;
}

Анимированные SVG (inline):

<!-- Спиннер -->
<div aria-busy="true" aria-live="polite">
  <?xml version="1.0" encoding="UTF-8"?>
  <img src="/static/images/loader-spinner.svg" alt="Загрузка" />
</div>

<!-- Пульсация статуса -->
<img src="/static/images/pulse-bubble.svg" alt="Онлайн" />

<!-- Идёт конвертация -->
<img src="/static/images/anim-arrow-loop.svg" alt="В процессе" />

Примечание по GIF:
- Если необходим GIF, можно экспортировать анимацию из SVG с помощью ffmpeg или imageMagick:
  1) rsvg-convert -a -o frames/frame_%03d.png -w 480 -h 160 bg-animated-wave.svg
  2) ffmpeg -framerate 12 -i frames/frame_%03d.png -vf "palettegen" palette.png
  3) ffmpeg -framerate 12 -i frames/frame_%03d.png -i palette.png -lavfi "paletteuse" -loop 0 convert-animated.gif
- Либо используйте CSS-анимации из backgrounds.css без GIF.

