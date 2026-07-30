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

## Inicio rápido — Backtester Python

```bash
cd python
python -m venv .venv
source .venv/Scripts/activate   # Windows cmd: .venv\Scripts\activate.bat | Linux/macOS: source .venv/bin/activate
pip install -e .
leviathan-bt backtest --data ../data/sample/EURUSD_H1.csv --config examples/config.example.toml
```

Barrido de parámetros y walk-forward:

```bash
leviathan-bt sweep --data tus_datos.csv --config examples/config.example.toml --grid grid.json
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
