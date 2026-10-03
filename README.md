# careers-ai

Servicio de IA **sin estado** del módulo Careers de Stockline. No guarda datos de nadie: `api-careers`
(.NET) le manda lo que necesita y recibe un resultado. Derivado del prototipo `carrera`.

| Endpoint | Hace |
|---|---|
| `POST /v1/rank` | Ordena ofertas contra una hoja de vida: reglas duras + afinidad semántica (bge-m3) + tecnologías en común, con explicación por oferta. Lo que aún no tiene vector se calcula en segundo plano y vuelve como `pendientes`. |
| `POST /v1/adapt` | Elige y ordena partes de la hoja de vida para una oferta. El modelo (qwen3:8b) **no escribe texto**; una compuerta compara el resultado con el original y, si algo no cuadra, devuelve el original. |
| `POST /v1/letter` | Carta de presentación por plantilla, solo con tecnologías que están en la hoja de vida **y** en la oferta. |
| `POST /v1/render` | Hoja de vida → LaTeX → PDF (latexmk en un contenedor sin red). |

Todas exigen la cabecera `X-Api-Key`. El servicio escucha solo en `127.0.0.1`.

## Ejecutar

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
./dev.sh          # :8930, necesita Ollama (bge-m3, qwen3:8b) y Docker Engine para el PDF
.venv/bin/pytest
```

## Decisiones

- **Las ofertas son texto de terceros.** Nunca se interpretan como instrucciones: la carta es una plantilla,
  el modelo solo devuelve índices y nombres que ya existen en la hoja de vida, y una oferta con
  «ignora lo anterior» no cambia el puntaje ni el contenido.
- **Sin estado de negocio.** Solo hay un caché de vectores (`cache/embeddings.db`), que se puede borrar.
- **Embeddings:** GPU primero; si Ollama devuelve 500 (bge-m3 produce NaN en fp16 con algunos textos cortos),
  ese lote se repite en CPU.
