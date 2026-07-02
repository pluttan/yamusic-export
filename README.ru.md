![Header](header.png)

<div align="center">

# yamusic-export

**Экспортёр библиотеки Яндекс Музыки с импортом в ListenBrainz**

[![License](https://img.shields.io/badge/license-MIT-2C2C2C?style=for-the-badge&labelColor=1E1E1E)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-2C2C2C?style=for-the-badge&logo=python&labelColor=1E1E1E)]()
[![Yandex Music](https://img.shields.io/badge/yandex-music-2C2C2C?style=for-the-badge&labelColor=1E1E1E)]()

</div>

Выгружает лайкнутые треки и плейлисты аккаунта Яндекс Музыки в JSON, скачивает аудиофайлы со встроенными метаданными (теги ID3/MP4 + обложки) и импортирует историю прослушиваний в ListenBrainz. Полный пайплайн: от экспорта до локальной библиотеки и истории скробблов.

## ■ Возможности

- ❖ **Экспорт библиотеки** — лайкнутые треки и плейлисты в структурированный JSON
- ❖ **Скачивание аудио** — полные треки в mp3/m4a с раскладкой по папкам исполнитель/альбом
- ❖ **Теги метаданных** — теги ID3 (MP3) и MP4: исполнитель, название, альбом, год, обложка
- ❖ **Импорт в ListenBrainz** — загружает историю прослушиваний как исторические скробблы (пачками по 1000)
- ❖ **Фикс DNS для IPv4** — патчит socket для предпочтения IPv4 на хостах, где IPv6 не маршрутизируется
- ❖ **Прогресс-бары** — прогресс загрузки на базе tqdm

## ■ Стек

<div align="center">

| Компонент | Технология |
|-----------|------------|
| API Client | yandex-music (Python SDK) |
| Tagging | mutagen (ID3, MP4) |
| Import | ListenBrainz REST API |
| Downloads | requests + tqdm |

</div>

## ■ Запуск

```bash
make install        # создать venv, установить зависимости
make export         # экспортировать лайкнутые треки + плейлисты в data/*.json
make download       # скачать аудиофайлы в data/music/library/
make all            # install + export + download

# Импорт в ListenBrainz
venv/bin/python import_lbz.py --token-file <path>
```

## ■ License

MIT © [pluttan](https://github.com/pluttan)
