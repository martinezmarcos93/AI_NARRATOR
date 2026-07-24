"""
Harness IA-vs-IA (Fase 20) — narrador real vs. jugador simulado, con
métricas de calidad cuantitativas sobre N turnos headless:

- leak_rate: fracción de turnos donde el narrador mencionó contenido
  marcado como secreto (fuga de Misterios/Frentes al jugador).
- dice_first_miss_rate: fracción de turnos donde el narrador narró un
  resultado sin tirada previa (ver narrator.core.dice_first_guard).

Uso:
    python scripts/playtest.py --turns 10 --archetype cauteloso
    python scripts/playtest.py --turns 10 --gate --max-leak-rate 0.1

Requiere Ollama corriendo con el modelo indicado. NO se ejecuta como
parte de ningún CI del estudio sin autorización aparte — es una
herramienta manual de verificación de calidad narrativa.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from narrator.agents.player_agent import ARCHETYPES, PlayerAgent  # noqa: E402
from narrator.core.dice_first_guard import check as dice_first_check  # noqa: E402


def detect_secret_leak(narrator_text: str, secrets: "list[str]") -> bool:
    """Heurística simple: ¿algún fragmento marcado "secreto" aparece
    literal en la narración? (detección literal — no parafraseada)."""
    t = (narrator_text or "").lower()
    return any(s.lower() in t for s in secrets if s)


def run_playtest(
    narrator_llm,
    player_llm,
    turns: int = 10,
    archetype: str = "cauteloso",
    secrets: "list[str] | None" = None,
    system_prompt: str = "Sos un narrador de rol.",
) -> dict:
    """Loop headless: el jugador simulado actúa, el narrador responde.
    No depende de la GUI ni del Orchestrator completo (mensajes mínimos)
    — así se puede testear con LLMs falsos, sin Ollama corriendo."""
    secrets = secrets or []
    player = PlayerAgent(player_llm, archetype=archetype)

    messages = [{"role": "system", "content": system_prompt}]
    leaks = 0
    dice_first_misses = 0
    scene = "La aventura comienza."

    for _ in range(turns):
        action = player.decide_action(scene)
        messages.append({"role": "user", "content": action})
        narrator_text = narrator_llm.chat(messages, max_tokens=200) or ""
        messages.append({"role": "assistant", "content": narrator_text})

        if detect_secret_leak(narrator_text, secrets):
            leaks += 1
        if dice_first_check(action, narrator_text, dice_rolled=False):
            dice_first_misses += 1

        scene = narrator_text

    return {
        "turns": turns,
        "leaks": leaks,
        "dice_first_misses": dice_first_misses,
        "leak_rate": leaks / turns if turns else 0.0,
        "dice_first_miss_rate": dice_first_misses / turns if turns else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Harness IA-vs-IA de playtest.")
    parser.add_argument("--turns", type=int, default=10)
    parser.add_argument("--archetype", default="cauteloso", choices=list(ARCHETYPES))
    parser.add_argument("--model", default="llama3.2")
    parser.add_argument("--gate", action="store_true", help="Exit code 1 si se superan umbrales.")
    parser.add_argument("--max-leak-rate", type=float, default=0.1)
    parser.add_argument("--max-dice-first-miss-rate", type=float, default=0.2)
    args = parser.parse_args()

    from narrator.core.llm_client import LLMClient

    llm = LLMClient(model=args.model)
    result = run_playtest(llm, llm, turns=args.turns, archetype=args.archetype)

    print(f"Turnos: {result['turns']}")
    print(f"Leak rate: {result['leak_rate']:.0%} ({result['leaks']}/{result['turns']})")
    print(
        f"Dice-first miss rate: {result['dice_first_miss_rate']:.0%} "
        f"({result['dice_first_misses']}/{result['turns']})"
    )

    if args.gate:
        if (result["leak_rate"] > args.max_leak_rate
                or result["dice_first_miss_rate"] > args.max_dice_first_miss_rate):
            print("GATE: FALLÓ — umbrales superados.")
            sys.exit(1)
        print("GATE: OK.")


if __name__ == "__main__":
    main()
