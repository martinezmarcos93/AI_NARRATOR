# AI NARRATOR — Motor de Rol con Agentes y Ollama

> Sistema narrador de TTRPG impulsado por LLMs locales. Un ecosistema de agentes especializados mantiene la coherencia del mundo mientras un modelo pequeño (7B) narra las escenas.
>
> **Principio fundamental:** El LLM es el pincel, no el cerebro. El sistema mantiene la coherencia; el modelo solo pinta las escenas.

---

## Instalación rápida

### 1. Ollama (IA local)
```bash
# Instalar Ollama → https://ollama.com
ollama pull mistral        # ~4GB - buena calidad narrativa (recomendado)
ollama pull llama3.2       # ~2GB - más rápido, menor calidad
ollama pull llama3.1:8b    # ~5GB - mejor calidad
ollama pull gemma3:12b     # ~8GB - excelente
```

### 2. Dependencias Python
```bash
pip install dearpygui requests PyMuPDF pyyaml python-frontmatter jinja2
```

### 3. Ejecutar
```bash
python narrator.py
```

---

## Cómo usar

### Flujo básico
1. **Abrir** → se conecta a Ollama automáticamente
2. **Cargar PDF** → seleccioná el manual de tu juego de rol
3. **Construir Vault** → los agentes analizan el manual y crean el mundo (NPCs, locaciones, frentes)
4. **Crear personaje** → el narrador te guía con menús basados en el sistema detectado
5. **Jugar** → escribí acciones, usá los dados, el mundo reacciona
6. **Guardar sesión** → continuar después desde donde dejaste

### Panel de dados
Seleccioná cantidad y tipo (D4 / D6 / D8 / D10 / D12 / D20). El resultado se envía al narrador con un click.

### Acciones rápidas
Botones preconfigurados: Atacar, Investigar, Negociar, Huir, Descansar, Situación.

---

## Arquitectura

```
PDF
 └─► [Extractor Agent]
          │
          ▼
     VAULT (MD/YAML)          ← memoria compartida entre agentes
     NPCs/ Locaciones/
     Frentes/ Misterios/
          │
          ▼
     [Orquestador]            ← Python puro, sin LLM
     /      |      \
[Narrador] [Mundo] [NPCs]
    │          │       │
    └──────────┴───────┘
          │
          ▼
     GUI (Dear PyGui)
```

Cada agente recibe **solo el fragmento del vault que necesita**. Esto permite usar modelos de 7B con contexto limitado (~2000 palabras) sin perder coherencia.

### Módulos

| Módulo | Responsabilidad |
|--------|----------------|
| `core/llm_client.py` | Wrapper Ollama (streaming + sync) |
| `core/retriever.py` | Búsqueda en vault por tipo / keyword |
| `core/state_manager.py` | Relojes de frentes, flags, historial de sesiones |
| `core/prompt_builder.py` | Ensambla prompts desde system YAML + vault |
| `agents/orchestrator.py` | Orquestador central (Python puro) |
| `agents/extractor_agent.py` | PDF → vault (pipeline de worldbuilding) |
| `agents/narrator_agent.py` | Post-procesamiento de respuestas del narrador |
| `agents/npc_routines.py` | Simulación de comportamiento de NPCs |

---

## Sistemas de juego soportados

| Sistema | Archivo config | Estado |
|---------|---------------|--------|
| Vampiro: La Mascarada V20 | `systems/vtm_v20.yaml` | Completo |
| Dungeons & Dragons 5e | `systems/dnd_5e.yaml` | Completo |
| La Llamada de Cthulhu 7e | `systems/coc_7e.yaml` | Completo |
| Pathfinder 2e | `systems/pathfinder_2e.yaml` | Completo |
| Genérico (cualquier TTRPG) | `systems/generic.yaml` | Completo |

La detección de sistema es automática al cargar el PDF. Para cambiarlo manualmente, editá `sistema_activo` en `config.yaml`.

---

## Vault y Obsidian

El vault es una carpeta de archivos Markdown con frontmatter YAML, 100% compatible con [Obsidian](https://obsidian.md).

```
vault/
  00_Dashboard.md       ← punto de entrada con estado de campaña
  NPCs/                 ← un archivo por NPC
  Locaciones/           ← un archivo por locación
  Cofradias/            ← facciones, coteries, manadas
  Frentes/              ← amenazas activas con relojes
  Misterios/            ← investigaciones con nodos y pistas
  Recursos/             ← bangs, tablas, handouts
  Sesiones/             ← log de sesiones
```

**Podés abrir `vault/` como vault de Obsidian** para navegar el mundo, editar NPCs manualmente, ver el graph de conexiones entre entidades, y usar Dataview para dashboards dinámicos.

El sistema narrador lee y escribe el vault en tiempo real. Los cambios que hacés en Obsidian se reflejan en la próxima sesión.

---

## Configuración

`config.yaml` controla el sistema activo, modelo LLM y rutas:

```yaml
sistema_activo: "vtm_v20"   # vtm_v20 | dnd_5e | coc_7e | pathfinder_2e | generic
llm:
  model: "mistral:7b"       # modelo de Ollama a usar
  base_url: "http://localhost:11434"
```

---

## Modelos recomendados

| Modelo | RAM | Calidad narrativa |
|--------|-----|-------------------|
| llama3.2 | ~2GB | ★★★☆☆ |
| mistral:7b | ~4GB | ★★★★☆ |
| llama3.1:8b | ~5GB | ★★★★☆ |
| gemma3:12b | ~8GB | ★★★★★ |

---

## Roadmap

Ver [`ROADMAP.md`](ROADMAP.md) para el estado detallado de desarrollo.

### Fase 1 — Narrador con jugador humano
- [x] GUI funcional (Dear PyGui) con dados, log de sesión, hoja de personaje
- [x] Integración Ollama con streaming
- [x] Carga y detección automática de sistema desde PDF
- [x] Arquitectura de agentes (core/ + agents/)
- [x] Sistemas: VtM V20, D&D 5e, CoC 7e, Pathfinder 2e, Genérico
- [x] Vault compatible con Obsidian
- [x] Extractor agent (PDF → vault automático)
- [ ] Búsqueda semántica en vault (ChromaDB)
- [ ] Soporte multi-PDF

### Fase 2 — IA vs IA (investigación)
- [ ] Agente jugador IA que recibe escena y devuelve acción
- [ ] Loop autónomo narrador/jugador
- [ ] Métricas de coherencia narrativa emergente

---

## Problemas comunes

**Sin Ollama**: Asegurate de que Ollama esté corriendo (`ollama serve`)

**GUI no abre**: Verificá Dear PyGui (`pip install dearpygui`)

**PDF no se carga**: Verificá PyMuPDF (`pip install PyMuPDF`)

**El narrador no actualiza la hoja**: Pedile explícitamente que guarde los datos en formato JSON
