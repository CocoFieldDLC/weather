# weather

Погода для Меш-сети: страница для людей и текстовый файл для автоответчика Meshtastic.

- `https://cocofielddlc.github.io/weather/` — обычная страница (рисуется JavaScript, в приложении её читать нельзя).
- `https://cocofielddlc.github.io/weather/pyatigorsk.txt` — **plain text**, одна строка:

  ```
  Погода в Пятигорске: Облачно, 20°C, облачность 80%, в ближайшее время осадков не ожидается
  ```

В шаблоне автоответчика:

```
%url("https://cocofielddlc.github.io/weather/pyatigorsk.txt")%
```

## Как обновляется

GitHub Pages не выполняет код, поэтому текст собирает GitHub Actions:

- `scripts/weather.py` — берёт Open-Meteo (при недоступности основного хоста — ensemble-хост),
  собирает русскую строку и пишет `<слаг>.txt` в корень репозитория.
- `.github/workflows/weather.yml` — запуск каждые 15 минут и вручную (`workflow_dispatch`),
  коммитит файл, если строка изменилась.

**Шаблон workflow лежит в `scripts/weather-workflow.yml`** — его нужно один раз скопировать в
`.github/workflows/weather.yml` через веб-интерфейс GitHub (Add file → Create new file → путь
`.github/workflows/weather.yml`). Токен, которым наполнялся репозиторий, не имеет права писать в
`.github/workflows`, поэтому файл не создан автоматически. Пока workflow нет, `pyatigorsk.txt`
остаётся тем, что лежит в репозитории.

Добавить город: дописать его в `CITIES` в `scripts/weather.py` (слаг, название в предложном
падеже, широта, долгота) — файл `<слаг>.txt` появится после следующего запуска.
