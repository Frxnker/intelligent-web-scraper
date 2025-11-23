# 🚀 Guía Rápida - Funcionalidades Avanzadas

## 📄 Paginación Automática

Scrapea múltiples páginas de forma automática:

```bash
python main_avanzado.py
# Opción 2: Scrapear con paginación
```

**Ejemplo:**
- URL: `https://www.pccomponentes.com/portatiles`
- Páginas: 5
- Resultado: 100+ productos de 5 páginas guardados en BD

## 💰 Comparador de Precios

Compara el mismo producto entre diferentes sitios:

```bash
python main_avanzado.py
# Opción 3: Comparar precios
```

**Ejemplo:**
- Sitio 1: PcComponentes (portátiles gaming)
- Sitio 2: Amazon (laptops gaming)
- Resultado: Tabla comparativa con mejores precios

**Salida:**
```
1. Lenovo Legion 5...
   PcComponentes: €1049 ✓ (más barato)
   Amazon: €1199
   💰 Diferencia: €150 (14.3%)

💰 Ahorro potencial: €350
```

## 💾 Base de Datos SQLite

Todos los productos se guardan automáticamente en `output/scraper.db`

**Ver productos guardados:**
```bash
python main_avanzado.py
# Opción 4: Ver productos
```

**Buscar productos:**
```bash
python main_avanzado.py
# Opción 5: Buscar
# Buscar: "lenovo"
```

**Estadísticas:**
```bash
python main_avanzado.py
# Opción 6: Ver estadísticas
```

Resultado:
```
📦 Total productos: 347
🔄 Total scraping jobs: 12

📊 Productos por sitio:
  pccomponentes: 150
  amazon: 120
  ebay: 77
```

## ⏰ Programación Automática

Programa tareas para scrapear automáticamente cada X minutos/horas:

```bash
python main_avanzado.py
# Opción 8: Crear tarea
```

**Ejemplo:**
```
Nombre: Portátiles Gaming
URL: https://www.pccomponentes.com/gaming
Intervalo: 60 minutos (cada hora)
Páginas: 3
```

**Iniciar el programador:**
```bash
python main_avanzado.py
# Opción 10: Iniciar programador
# (Se ejecuta en segundo plano)
```

El programador:
- ✅ Scrapea automáticamente cada X minutos
- ✅ Guarda todo en la base de datos
- ✅ Registra historial de precios
- ✅ Se ejecuta hasta que lo detengas (Ctrl+C)

**Ver tareas activas:**
```bash
python main_avanzado.py
# Opción 9: Ver tareas
```

## 📊 Casos de Uso Reales

### 1. Monitor de Precios de GPU
```
Tarea: Monitorear RTX 4090
URL: https://www.pccomponentes.com/gpu-rtx-4090
Intervalo: 30 minutos
```
El scraper te avisa cuando hay cambios de precio.

### 2. Comparador Diario
```
Scraping programado:
- 8:00 AM → PcComponentes
- 8:10 AM → Amazon
Comparación automática de resultados
```

### 3. Análisis de Mercado
```
Scrapear 10 páginas de:
- Portátiles (500+ productos)
- Análisis de precios promedio
- Detectar ofertas (base de datos histórica)
```

## 🛠️ Uso Programático

### Paginación en código:
```python
from scraper_selenium import SeleniumScraper
from paginacion import scrapear_con_paginacion

scraper = SeleniumScraper(headless=True)
datos = scrapear_con_paginacion(
    scraper, 
    'https://example.com/productos',
    max_paginas=5
)
```

### Comparador en código:
```python
from comparador import comparar_sitios
from scraper_selenium import SeleniumScraper

coincidencias = comparar_sitios(
    'https://pccomponentes.com/portatiles',
    'https://amazon.es/s?k=laptop',
    SeleniumScraper,
    'PcComponentes',
    'Amazon',
    umbral=0.7
)
```

### Base de datos en código:
```python
from database import ScraperDB

with ScraperDB() as db:
    # Insertar productos
    db.insertar_productos_bulk(productos, 'amazon')
    
    # Buscar
    resultados = db.buscar_productos('gaming')
    
    # Estadísticas
    stats = db.obtener_estadisticas()
```

## 💡 Tips

1. **Paginación**: Empieza con 2-3 páginas para probar
2. **Comparador**: Usa URLs de la misma categoría (ej: ambos portátiles)
3. **Programador**: No pongas intervalos < 15 minutos (respeta los servidores)
4. **Base de datos**: Limpia datos antiguos cada 30 días (opción 7)

## ⚠️ Notas Importantes

- El scraper respeta los sitios (delays automáticos)
- Para programación 24/7, ejecuta en servidor/VPS
- La base de datos guarda historial de precios
- Los archivos CSV/JSON se siguen generando

## 🎯 Próximos Pasos

¿Qué más necesitas?
- Notificaciones por email/Telegram
- Dashboard web (Flask)
- API REST
- Proxy/VPN rotation
- Soporte para más sitios específicos

¡Dime y lo agrego!
