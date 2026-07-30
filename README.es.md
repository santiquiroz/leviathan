<!-- Traducido del README.md en inglés. Si editas el README en inglés, actualiza también este archivo. -->
# 🐙 Leviathan

**[English](README.md) | Español**

Bot de trading de **acción del precio** con filtro de tendencia, open source, para MetaTrader 5, con un motor de backtesting en Python fiel al EA.

> ## ⚠️ Descargo de responsabilidad
>
> Este software es **solo para fines educativos**. No es asesoría financiera. No arriesgues dinero que no puedas permitirte perder. **ÚSALO BAJO TU PROPIO RIESGO — los autores no asumen ninguna responsabilidad por tus resultados de trading.** Prueba siempre en una cuenta demo (Strategy Tester de MT5 / backtests en Python) antes de considerar dinero real. Operar instrumentos apalancados conlleva un alto riesgo de perder todo tu capital.

## Qué hace

Leviathan opera (o solo *señala* — ese es el modo por defecto) una receta clásica de acción del precio retail, únicamente cuando tres condiciones independientes se alinean en la última vela **cerrada**:

1. **Filtro de tendencia** — EMA(9) sobre EMA(21) y precio sobre EMA(200) para largos (espejo para cortos).
2. **Ruptura de estructura (BOS)** — el cierre rompe el máximo/mínimo de las últimas 20 velas.
3. **Gatillo de vela** — una vela **envolvente** (engulfing) o **pinbar** confirma el momentum.

El stop sale del ATR (o de la estructura), el objetivo de una relación riesgo:beneficio fija. Todo es configurable.

El reglamento completo, con las fórmulas exactas que comparten ambas implementaciones, está en [docs/STRATEGY.md](docs/STRATEGY.md) (en inglés).

## Dos implementaciones, una especificación

| | Expert Advisor MQL5 | Backtester Python |
|---|---|---|
| Propósito | Señales/trading en vivo + Strategy Tester | Investigación: backtests, barridos de parámetros, walk-forward |
| Ubicación | [`mql5/`](mql5/) | [`python/`](python/) |
| Dependencias | Solo MetaTrader 5 | pandas + numpy (matplotlib opcional) |
| Modo por defecto | **Solo señales** (alertas, panel, sin órdenes) | — |

Ambas siguen `docs/STRATEGY.md` al pie de la letra; cualquier diferencia de comportamiento entre ellas es un bug — repórtalo.

## Inicio rápido — EA MQL5

1. Copia el contenido de `mql5/` en la carpeta de datos de MetaTrader 5 (`Archivo → Abrir carpeta de datos → MQL5`):
   - `mql5/Experts/Leviathan.mq5` → `MQL5/Experts/`
   - `mql5/Include/Leviathan/` → `MQL5/Include/Leviathan/`
2. Compila `Leviathan.mq5` en MetaEditor (F7).
3. Arrastra el EA a un gráfico. Por defecto corre en **solo señales**: dibuja el setup (flecha + líneas de entrada/SL/TP), actualiza el panel y envía alertas (popup/push/email). Tú decides si tomar la operación.
4. Para dejarlo operar solo, cambia `Operating mode` a `Auto-trading` — después de haberlo backtesteado y entendido el riesgo.

### Uso diario del EA

- **Panel** (arriba a la izquierda): muestra modo, tendencia (BULLISH/BEARISH/NEUTRAL), última señal, R:R y la Entrada/SL/TP sugeridos del último setup. El botón inferior pausa/reanuda la detección de señales sin quitar el EA.
- **Cuando salta una señal**: aparecen una flecha + líneas punteadas de Entrada/SL/TP en el gráfico y recibes las alertas que hayas activado (`popup` en la terminal, `push` a la app móvil de MT5, `email`). En modo solo-señales no se opera nada — la alerta incluye el lote sugerido para que ejecutes manualmente.
- **Modo auto-trading**: usa tu modo de sizing (`Lote fijo` o `% de riesgo` del equity), respeta `Una sola posición concurrente` y aplica los opcionales: break-even, trailing por ATR, filtro de sesión, filtro de spread y límite de pérdida diaria. Un `Magic number` distinto por gráfico si corres varias instancias.
- **Strategy Tester**: el EA corre en el tester de MT5 (Ctrl+R) — usa "Cada tick basado en ticks reales" para los fills más realistas, y el modo visual para ver el panel y las señales en replay.

### Ejecutable precompilado

Pronto habrá un `Leviathan.ex5` compilado adjunto en los [Releases de GitHub](https://github.com/santiquiroz/leviathan/releases), para que quien no programa lo suelte directo en `MQL5/Experts/` sin abrir MetaEditor. Mientras tanto, compilar desde el código toma unos dos minutos (pasos arriba) — y compilarlo tú mismo siempre es la opción más confiable para algo que puede tocar tu dinero.

## Inicio rápido — Backtester Python

```bash
cd python
python -m venv .venv
source .venv/Scripts/activate   # Windows cmd: .venv\Scripts\activate.bat | Linux/macOS: source .venv/bin/activate
pip install -e .
leviathan-bt backtest --data ../data/sample/EURUSD_H1.csv --config examples/config.example.toml
```

Flags útiles: `--out report.txt` guarda el reporte de texto, `--plot equity.png` guarda la curva de equity (requiere `pip install -e .[plot]`).

**Barrido de parámetros** — pon los valores a probar en un JSON:

```json
{ "atr_multiplier": [1.0, 1.5, 2.0], "risk_reward": [1.5, 2.0, 3.0], "structure_lookback": [10, 20, 30] }
```

```bash
leviathan-bt sweep --data tus_datos.csv --config examples/config.example.toml --grid grid.json --jobs 4
```

Imprime las 10 mejores combinaciones por profit factor (los sets con menos de 30 trades se descartan — evidencia insuficiente).

**Walk-forward** (la forma honesta de evaluar un barrido) — desde Python:

```python
from leviathan_bt import load_csv, load_toml
from leviathan_bt.sweep import walk_forward

df = load_csv("tus_datos.csv")
params, symbol, config = load_toml("examples/config.example.toml")
result = walk_forward(df, params, {"atr_multiplier": [1.0, 1.5, 2.0]}, symbol, config,
                      is_bars=4000, oos_bars=1000, step_bars=1000)
print(result["wf_efficiency"])   # R fuera de muestra / R en muestra — debajo de ~0.5 huele a sobreajuste
```

Fuentes de datos (ver loaders en `python/leviathan_bt/data.py`):
- **Export de MT5** (máxima fidelidad — mismo feed del broker que el EA).
- CSVs de klines de **Binance Vision** para cripto.
- **yfinance** para demos rápidas en velas diarias (`pip install -e .[data]` desde `python/`).

## Configuración

Todos los parámetros de la estrategia existen como inputs del EA y claves TOML. Los principales:

| Parámetro | Default | Significado |
|---|---|---|
| `riskReward` | 2.0 | Distancia del TP como múltiplo del SL |
| `slMode` | ATR | Stop por `ATR` o por `Swing` (estructura) |
| `atrPeriod` / `atrMultiplier` | 14 / 1.5 | Configuración del stop por ATR |
| `emaFast` / `emaSlow` / `emaTrend` | 9 / 21 / 200 | EMAs del filtro de tendencia |
| `structureLookback` | 20 | Velas para la ruptura de estructura |
| `useEngulfing` / `usePinbar` | true / true | Gatillos de entrada |
| `pinbarWickRatio` | 0.66 | Fracción mínima de mecha dominante |
| `sizingMode` | Lote fijo | `Lote fijo` o `% de riesgo` del equity |
| `onePositionOnly` | true | Una sola posición concurrente |

Extras (todos apagados por defecto): break-even a +1R, trailing stop por ATR y filtro de sesión (EA + backtester); filtro de spread máximo y límite de pérdida diaria (solo EA, modo auto).

## Familias de estrategias más usadas — y dónde encaja Leviathan

Los enfoques más comunes en algo trading retail, como contexto:

| Familia | Idea | Leviathan |
|---|---|---|
| **Trend following** | Operar en la dirección de la tendencia (medias móviles / timeframe mayor) | ✅ Núcleo: filtro EMA 9/21 + EMA 200 |
| **Breakout / estructura** | Entrar cuando el precio rompe un máximo/mínimo o rango reciente | ✅ Núcleo: gatillo de ruptura de estructura (BOS) |
| **Confirmación por velas** | Engulfing, pinbar, inside bar como timing de entrada | ✅ Núcleo: engulfing + pinbar (más patrones = PRs bienvenidos) |
| **Mean reversion** | Operar el retorno a la media (extremos de RSI, toques de Bollinger) | ❌ Tesis opuesta — pelearía con el filtro de tendencia; encaja mejor como módulo aparte |
| **Momentum / cruce de medias** | Entrar en el cruce mismo de la media rápida/lenta | Parcial — Leviathan usa el estado del cruce como *filtro*, no como entrada |
| **Grid / DCA** | Escalera de órdenes alrededor del precio, promediar | ❌ Fuera de alcance (freqtrade/OctoBot lo hacen bien para cripto) |
| **Scalping / HFT** | Muchas operaciones pequeñas en ticks/segundos | ❌ Fuera de alcance — requiere infraestructura que este proyecto evita a propósito |

Leviathan es un **sistema trend-following de rupturas con confirmación por velas** — la combinación que más enseñan los cursos de acción del precio retail. Esa popularidad es justo la razón para tener una implementación open source honesta y testeable.

## Expectativas honestas

Lee esto antes de soñar: la investigación académica (Marshall, Young & Rose 2006, *Journal of Banking & Finance*) **no encontró valor predictivo significativo en los patrones de velas por sí solos**. Backtests comunitarios ubican los sistemas de cruce de EMAs con expectativa positiva en solo ~8 de 12 combinaciones activo/timeframe — funcionan en tendencia y sangran en rango. Con R:R fijo de 1:2 el punto de equilibrio matemático es 33.3% de aciertos *antes* de costos, y solo el spread puede comerse 5–20% del riesgo por operación en stops intradía ajustados.

Leviathan trae defaults honestos, no ajustados a la curva. Trátalo como un **framework para probar ideas con rigor**, no como una máquina de dinero. El backtester modela spread, slippage, comisiones y el peor caso en velas ambiguas para que tus resultados pequen de conservadores.

## Estructura del repositorio

```
mql5/
  Experts/Leviathan.mq5          # orquestador delgado (OnInit/OnTick/OnDeinit)
  Include/Leviathan/*.mqh        # Signals, Risk, TradeManager, Filters, Broker, Alerts, Panel
python/
  leviathan_bt/                  # paquete de backtesting (engine, indicators, patterns, sweep, cli)
  tests/                         # suite pytest
  examples/config.example.toml
docs/STRATEGY.md                 # LA especificación — fuente única de verdad para ambas implementaciones
```

## Contribuir

PRs bienvenidos — ver [CONTRIBUTING.md](CONTRIBUTING.md). Cambios a la lógica de la estrategia deben actualizar `docs/STRATEGY.md` en el mismo PR. Nuevos patrones de entrada, filtros y loaders de datos son excelentes primeras contribuciones.

## Créditos

El concepto de la estrategia (filtro de tendencia por EMAs + ruptura de estructura + entradas por engulfing/pinbar) es una receta de acción del precio retail ampliamente enseñada; este proyecto es una implementación open source independiente y desde cero de ese concepto público. No se usó código de terceros.

## Licencia

[MIT](LICENSE)
