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

¿Ya conoces MetaTrader? Cuatro pasos:

1. Copia el contenido de `mql5/` en la carpeta de datos de MetaTrader 5 (`Archivo → Abrir carpeta de datos → MQL5`):
   - `mql5/Experts/Leviathan.mq5` → `MQL5/Experts/`
   - `mql5/Include/Leviathan/` → `MQL5/Include/Leviathan/`
2. Compila `Leviathan.mq5` en MetaEditor (F7).
3. Arrastra el EA a un gráfico. Por defecto corre en **solo señales**: dibuja el setup (flecha + líneas de entrada/SL/TP), actualiza el panel y envía alertas (popup/push/email). Tú decides si tomar la operación.
4. Para dejarlo operar solo, cambia `Operating mode` a `Auto-trading` — después de haberlo backtesteado y entendido el riesgo.

### ¿Nunca has usado MetaTrader? Guía completa

**Fase 1 — Instalar (10 minutos, gratis, sin dinero real):**

1. Descarga **MetaTrader 5** desde metatrader5.com (o desde tu broker si ya tienes uno).
2. Ábrelo. La primera vez te pide una cuenta: elige **cuenta demo** (el servidor "MetaQuotes-Demo" sirve). Dinero ficticio — así se prueba todo durante semanas antes de siquiera pensar en fondos reales.
3. `Archivo → Abrir carpeta de datos`. Se abre un explorador; entra a la carpeta `MQL5`.
4. De este repo, copia:
   - `mql5/Experts/Leviathan.mq5` → a `MQL5/Experts/`
   - la carpeta `mql5/Include/Leviathan/` completa → a `MQL5/Include/`
5. De vuelta en MT5 presiona **F4** (abre MetaEditor). Abre `Experts/Leviathan.mq5` y presiona **F7** (compilar). El log de abajo debe decir `0 errors, 0 warnings` — eso genera el ejecutable `.ex5`.

**Fase 2 — Ponerlo en un gráfico:**

6. De vuelta en MT5, **Ctrl+N** abre el Navegador → `Asesores Expertos → Leviathan`.
7. Arrastra "Leviathan" a un gráfico, por ejemplo **EURUSD H1** (para cambiar timeframe: clic derecho en el gráfico → Periodicidad → H1).
8. En el diálogo que aparece, pestaña "Común": marca "Permitir trading algorítmico" y dale OK. Aparece el **panel oscuro** arriba a la izquierda.
9. Listo. Modo por defecto = **solo señales**: el bot NO opera. Cuando las tres condiciones se alinean (tendencia + ruptura de estructura + vela) dibuja la flecha y las líneas de Entrada/SL/TP y lanza la alerta con el lote sugerido. Tú decides si entrar manualmente.
10. Alertas al celular: instala la app móvil de MT5 y en el escritorio ve a `Herramientas → Opciones → Notificaciones` y pega tu MetaQuotes ID (la app lo muestra en Ajustes → Mensajes).

**Fase 3 — Backtest antes de creer en nada:**

11. **Ctrl+R** abre el Strategy Tester: elige Leviathan, un símbolo, un rango de fechas, modo "Cada tick basado en ticks reales", y presiona Iniciar. El modo visual te deja ver las señales en replay.
12. Para investigación seria (barridos de parámetros, walk-forward) usa el motor Python de abajo — el inicio rápido corre en tres comandos con los datos de ejemplo incluidos.

**Regla de oro: mínimo 1–2 meses en demo.** Con R:R 1:2 necesitas más de 33.3% de aciertos solo para empatar *antes* de costos — ver [Expectativas honestas](#expectativas-honestas).

### Uso diario del EA

- **Panel** (arriba a la izquierda): muestra modo, tendencia (BULLISH/BEARISH/NEUTRAL), última señal, R:R y la Entrada/SL/TP sugeridos del último setup. El botón inferior pausa/reanuda la detección de señales sin quitar el EA.
- **Cuando salta una señal**: aparecen una flecha + líneas punteadas de Entrada/SL/TP en el gráfico y recibes las alertas que hayas activado — `popup` en la terminal, `push` a la app móvil de MT5, `email`, y/o un **webhook** (pega una URL de webhook de Discord o Slack en `Webhook URL` y autorízala en `Herramientas → Opciones → Asesores Expertos → Permitir WebRequest`). En modo solo-señales no se opera nada — la alerta incluye el lote sugerido para que ejecutes manualmente.
- **Log de señales**: con `Log signals to file` activo (default), cada señal se agrega a `MQL5/Files/Leviathan_signals.csv` — un historial auditable para analizar después (o darle a Claude vía el servidor MCP de abajo).
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

## Integración con Claude / IA (servidor MCP)

Leviathan incluye un servidor [MCP](https://modelcontextprotocol.io) para que asistentes de IA (Claude Code, Claude Desktop o cualquier cliente MCP) manejen el backtester conversando — "backtestea este CSV con ATR 2.0", "barre el RR de 1.5 a 3 y hazle walk-forward al ganador", "lee el log de señales de mi EA y compáralo contra el backtest".

```bash
cd python && pip install -e .[mcp]
claude mcp add leviathan -- leviathan-mcp        # Claude Code
```

Herramientas expuestas (todas de solo lectura): `leviathan_run_backtest`, `leviathan_grid_search`, `leviathan_walk_forward`, `leviathan_describe_data`, `leviathan_get_strategy_spec`, `leviathan_read_ea_signals` (lee el log `Leviathan_signals.csv` del EA).

Una nota sobre "modelos de IA para trading", porque siempre sale el tema: la evidencia a la fecha dice que los modelos de predicción de precios sin ajuste (foundation models de series de tiempo, sentimiento estilo FinBERT) **no** dan ventaja lista para usar — las evaluaciones publicadas los muestran por debajo de baselines de gradient boosting en retornos, y a los modelos de sentimiento populares peor que el azar en el movimiento del día siguiente. Donde la IA sí ayuda demostrablemente es como **copiloto de investigación**: escribir y auditar estrategias, correr backtests honestos, cazar sobreajuste. Ese es exactamente el rol que este servidor MCP le da.

## Por qué MetaTrader 5 — y cuándo usar otra cosa

MT5 no es lock-in de proveedor; es el estándar de facto del forex retail. Para lo que este bot hace (forex/oro/índices, señales de acción del precio, ejecución manual o semi-auto) es la herramienta correcta: gratis, soportado por casi todo broker, tester integrado con ticks reales, alertas push al celular, corre en un VPS de $5.

El riesgo real de lock-in ya está neutralizado por diseño: la estrategia vive en [docs/STRATEGY.md](docs/STRATEGY.md) (papel, no plataforma) y el motor Python es pandas puro — MT5 es solo el adaptador de ejecución. Cambiar de plataforma después significa reescribir una capa delgada, no el proyecto.

Cuándo otro stack SÍ es mejor opción:

- **Cripto** → [freqtrade](https://www.freqtrade.io) (open source, exchanges reales, modo dry-run). El cripto por CFD de brokers MT5 tiene spreads terribles — no fuerces Leviathan ahí.
- **Acciones de EE.UU.** → API de Interactive Brokers.
- **Infraestructura de grado institucional** → [NautilusTrader](https://nautilustrader.io) — potente, pero la curva de aprendizaje no se justifica para esta clase de estrategia.
- **Qué evitar**: EAs cerrados de pago e indicadores propietarios de comunidades de pago — *eso* sí es lock-in real (a la caja negra de otro). Este repo existe precisamente para no depender de uno.

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
