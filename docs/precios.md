# Precios

[Volver al README](../README.md)

`precios.py` convierte el texto del precio que aparece en la página en un
importe numérico y un código de moneda. La base de datos guarda los dos por
separado, junto con el texto original (ver [Base de datos](base-de-datos.md)).

```python
from precios import parsear_precio, extraer_precio_numerico, extraer_moneda

parsear_precio('1.299,99 €')          # (1299.99, 'EUR')
extraer_precio_numerico('$1,299.99')  # 1299.99
extraer_moneda('£12.50')              # 'GBP'
```

## Ejemplos

| Texto | Importe | Moneda |
|-------|---------|--------|
| `1.299,99 €` | 1299.99 | EUR |
| `€ 1.299,99` | 1299.99 | EUR |
| `1.299.999,50 €` | 1299999.5 | EUR |
| `$1,299.99` | 1299.99 | USD |
| `1,299.99 $` | 1299.99 | USD |
| `£12.50` | 12.5 | GBP |
| `¥1,000` | 1000.0 | JPY |
| `1 299,99 €` (espacio normal, duro o estrecho) | 1299.99 | EUR |
| `EUR 1.299,99`, `1.299,99 eur` | 1299.99 | EUR |
| `USD 10` | 10.0 | USD |
| `1299` | 1299.0 | (ninguna) |
| `12,5` | 12.5 | (ninguna) |
| `1.299` | 1299.0 | (ninguna) |
| `0,999` | 0.999 | (ninguna) |
| `Desde 19,99 €` | 19.99 | EUR |
| `-20% 1.299,99 €` | 1299.99 | EUR |
| `Ahorra 15% hoy: 85,00` | 85.0 | (ninguna) |
| `Gratis`, `N/A`, `20%`, texto vacío | (ninguno) | (ninguna) |

## Reglas

- Monedas reconocidas: los símbolos `€`, `$`, `£` y `¥` y los códigos `EUR`,
  `USD`, `GBP` y `JPY` (en mayúsculas o minúsculas), delante o detrás del
  número, con o sin espacio. `$` se interpreta siempre como USD y `¥` como JPY.
- Si aparecen tanto el punto como la coma, el que va último es el separador
  decimal: `1.299,99` y `1,299.99` son 1299.99.
- Si solo hay un tipo de separador y aparece varias veces, es de miles:
  `1.000.000` es 1000000.
- Si solo hay un separador y le siguen exactamente tres cifras, se toma como
  separador de miles (`1.299` es 1299), salvo que la parte entera sea `0`
  (`0,999` es 0.999). Con otro número de cifras es decimal (`12,5` es 12.5).
- Los grupos de tres cifras separados por espacios (normales, duros o
  estrechos) se unen: `1 299,99` es 1299.99.
- Si el texto tiene varios números, se usa el que va pegado a una moneda
  (`-20% 1.299,99 €` da 1299.99). Si ninguno va pegado a una moneda, se usa el
  primer número que no sea un porcentaje.
- Si no hay ningún número reconocible, el importe y la moneda quedan vacíos
  (`None`); en la base de datos se conserva el texto original.

## Dónde se usa

- Al guardar productos: `precio` (número), `moneda` y `precio_texto`, y un
  registro en el historial cada vez que el importe se ha podido interpretar.
- En el comparador: solo se calcula la diferencia entre dos productos si tienen
  la misma moneda (o si a alguno le falta).
- En la interfaz web y en el menú, para mostrar los precios con su símbolo.

## Limitaciones

- `1.299` se lee como 1299, aunque en inglés podría ser 1,299. Los precios con
  tres decimales (por ejemplo, de combustible) se interpretan mal por la misma
  regla.
- Si un texto contiene el precio anterior y el actual (`Antes 29,99 € Ahora
  19,99 €`), se toma el primero.
- `$` puede ser otra moneda (dólar canadiense, australiano, peso...) y `¥`
  puede ser yuan; se tratan como USD y JPY.
