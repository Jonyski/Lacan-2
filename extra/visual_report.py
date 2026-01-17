from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt


def generate_infographic(payload: Dict[str, Any], output_path: Path):
    """
    Gera um dashboard visual das análises clínicas:
    - Gráfico de barras do grau de risco dos casos.
    - Gráfico de setores com a taxa de sucesso da pipeline.
    """
    # 1. Preparação dos Dados
    results = payload.get("results", [])

    # Contagem de Riscos
    risk_counts = {"baixo": 0, "médio": 0, "alto": 0}
    for r in results:
        if r.get("ok") and r.get("output"):
            risk_obj = r["output"].get("risk_assessment", {})
            level = risk_obj.get("level", "").lower()
            if level in risk_counts:
                risk_counts[level] += 1

    # Dados de Sucesso/Falha
    total_ok = payload.get("ok", 0)
    total_failed = payload.get("failed", 0)

    # 2. Configuração do Estilo
    bg_color = "#09090f"
    plt.style.use("dark_background")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), facecolor=bg_color)
    ax1.set_facecolor(bg_color)
    ax2.set_facecolor(bg_color)

    # Título Geral
    fig.suptitle(
        f"Relatório do pipeline - {payload.get('total', 0)} arquivos analisados",
        fontsize=20,
        color="white",
        weight="bold",
    )

    # GRÁFICO DE BARRAS DO NÍVEL DE RISCO
    levels = ["Baixo", "Médio", "Alto"]
    counts = [risk_counts["baixo"], risk_counts["médio"], risk_counts["alto"]]
    colors_bar = ["#55c276", "#d1cd64", "#d6384d"]

    bars = ax1.bar(levels, counts, color=colors_bar, edgecolor=bg_color, zorder=3)
    ax1.set_title("Distribuição de Nível de Risco", fontsize=14, pad=15)
    ax1.set_ylabel("Quantidade de Casos")
    ax1.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)

    max_count = max(counts) if counts else 1
    ax1.set_ylim(0, max_count * 1.25)

    # Adiciona os números
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + (max_count * 0.02),
                f"{int(height)}",
                ha="center",
                va="bottom",
                fontsize=12,
                fontweight="bold",
                color="white",
            )

    # GRÁFICO DE SETORES DA TAXA DE SUCESSO DA PIPELINE
    sizes_pie = [total_ok, total_failed]
    colors_pie = ["#55c276", "#d6384d"]  # Verde e Vermelho
    explode = (0.05, 0)

    # CORREÇÃO 2: Função para ocultar 0%
    def func_autopct(pct):
        return f"{pct:.1f}%" if pct > 0 else ""

    if sum(sizes_pie) > 0:
        wedges, texts, autotexts = ax2.pie(
            sizes_pie,
            explode=explode,
            labels=None,
            colors=colors_pie,
            autopct=func_autopct,
            shadow=True,
            startangle=140,
            textprops={"fontsize": 14, "color": bg_color, "weight": "bold"},
        )
        # Legenda personalizada embaixo
        legend = ax2.legend(
            wedges,
            ["Sucesso", "Falha"],
            title="Status",
            loc="center",
            bbox_to_anchor=(0.5, -0.1),
            ncol=2,
            fontsize=12,
        )
        legend.get_frame().set_facecolor(bg_color)
        legend.get_frame().set_edgecolor("white")

    ax2.set_title("Taxa de Sucesso do Pipeline", fontsize=14)

    # 3. Finalização
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=100)
    print(f"Infográfico gerado com sucesso: {output_path}")
    plt.close(fig)
