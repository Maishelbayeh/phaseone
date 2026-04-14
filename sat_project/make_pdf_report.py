from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.image as mpimg


def create_pdf_with_results(
    batch_plot_path: Path,
    single_plot_path: Path,
    output_pdf_path: Path,
) -> Path:
    """Create a single PDF page with two result images and explanatory notes."""
    # Load images
    batch_img = mpimg.imread(str(batch_plot_path))
    single_img = mpimg.imread(str(single_plot_path))

    # Compose PDF page
    fig = plt.figure(figsize=(11.0, 8.5), dpi=150)  # landscape letter
    fig.suptitle("3-SAT Hill Climbing — Results Summary", fontsize=16, fontweight="bold", y=0.98)

    # Top: batch runtime plot
    ax1 = plt.subplot2grid((2, 2), (0, 0), colspan=2)
    ax1.imshow(batch_img)
    ax1.axis("off")
    ax1.set_title("Batch runtime vs. number of variables (by clause density)")

    batch_caption = (
        "As n increases, mean runtime rises sharply. Higher clause density (m/n) is harder:\n"
        "m/n = 6.0 tends to be the slowest, followed by 4.3, then 3.0. This reflects a tighter\n"
        "search landscape with fewer easy improvements at higher densities."
    )
    ax1.text(
        0.01,
        -0.12,
        batch_caption,
        transform=ax1.transAxes,
        ha="left",
        va="top",
        fontsize=10,
    )

    # Bottom-left: single run convergence
    ax2 = plt.subplot2grid((2, 2), (1, 0))
    ax2.imshow(single_img)
    ax2.axis("off")
    ax2.set_title("Single run convergence (merit over improving moves/restarts)")

    single_caption = (
        "Rapid early gains followed by plateaus indicate local optima. Occasional jumps show\n"
        "successful restarts that discover better basins. Example shown reaches ~877/900 clauses\n"
        "at n=150, m=900 (ratio=6.0) — strong but not fully satisfying all clauses."
    )

    # Bottom-right: text panel (duplicate caption for readability and a small legend)
    ax3 = plt.subplot2grid((2, 2), (1, 1))
    ax3.axis("off")
    text = (
        "Notes:\n"
        "• Batch plot: runtime grows with n; higher m/n increases difficulty.\n"
        "• Single run: hill climbing plus random restarts; plateaus imply local optima.\n"
        "• Restarts help escape local maxima by re-sampling assignments.\n"
        "\n"
        f"{single_caption}"
    )
    ax3.text(0.0, 1.0, text, ha="left", va="top", fontsize=10, family="monospace", linespacing=1.4)

    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(str(output_pdf_path), format="pdf")
    plt.close(fig)
    return output_pdf_path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    results_dir = project_root / "results"
    plots_dir = results_dir / "plots"

    batch_plot = plots_dir / "batch_runtime_vs_num_variables.png"
    single_plot = plots_dir / "gui_single_convergence.png"
    output_pdf = results_dir / "Two_Results_Report.pdf"

    if not batch_plot.exists() or not single_plot.exists():
        raise FileNotFoundError(
            f"Missing plot(s). Ensure both exist:\n - {batch_plot}\n - {single_plot}\n"
            "Run the GUI (single and batch) to generate them."
        )

    created = create_pdf_with_results(batch_plot, single_plot, output_pdf)
    print(f"PDF created at: {created}")


if __name__ == "__main__":
    main()

