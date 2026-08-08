#!/usr/bin/env python3
"""Generate Fig2-Fig6."""

from __future__ import annotations

import importlib


def main() -> None:
    for module_name in ["plot_fig2", "plot_fig3", "plot_fig4", "plot_fig5", "plot_fig6"]:
        module = importlib.import_module(module_name)
        module.main()
        print(f"Generated {module_name}")


if __name__ == "__main__":
    main()
