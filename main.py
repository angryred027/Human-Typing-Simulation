import argparse
from humantyping.simulation import run_monte_carlo, demo_single_run
from humantyping.config import RHYTHM_PRESETS, DEFAULT_RHYTHM

def main():
    typing_text = """from module import Class1
import asyncio

async def example():
instance = Class1(
    # keyword_arg=value,
)
instance.method1()
"""
    parser = argparse.ArgumentParser(description="Keyboard Typing Simulation via Markov Chains")
    parser.add_argument("text", nargs="?", default=typing_text, help="The text to simulate")
    parser.add_argument("--mode", choices=["demo", "montecarlo"], default="demo", help="Execution mode")
    parser.add_argument("--n", type=int, default=100, help="Number of simulations for Monte Carlo")
    parser.add_argument("--wpm", type=float, default=60.0, help="Target average speed (Words Per Minute)")
    parser.add_argument("--rhythm", choices=sorted(RHYTHM_PRESETS), default=DEFAULT_RHYTHM,
                        help="Pause rhythm: writing / coding / messaging")

    args = parser.parse_args()

    if args.mode == "demo":
        demo_single_run(args.text, args.wpm, rhythm=args.rhythm)
    elif args.mode == "montecarlo":
        run_monte_carlo(args.text, args.wpm, n_simulations=args.n, rhythm=args.rhythm)

if __name__ == "__main__":
    main()
