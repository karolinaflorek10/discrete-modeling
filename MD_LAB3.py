import random
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.widgets import Button, CheckButtons, RadioButtons, TextBox

DEFAULT_RULE_STR = "000000000022212022000000000"

CMAP = ListedColormap(["#E8E4D9", "#2E8B57", "#D9381E"])


def decode_rule(rule_input: str) -> dict:
    """Decodes a rule from a 27-character ternary string {0,1,2} or a decimal integer."""
    rule_input = rule_input.strip()

    if rule_input.isdigit() and len(rule_input) != 27:
        num = int(rule_input)
        if not (0 <= num < 3**27):
            raise ValueError(f"Number must be in range 0 - {3**27 - 1}.")
        trits = []
        for _ in range(27):
            trits.append(str(num % 3))
            num //= 3
        rule_str = "".join(reversed(trits))
    else:
        if len(rule_input) != 27 or any(c not in "012" for c in rule_input):
            raise ValueError("Rule must contain exactly 27 digits {0, 1, 2} or be a valid decimal number.")
        rule_str = rule_input

    transitions = {}
    for idx in range(27):
        val = 26 - idx
        l = val // 9
        c = (val % 9) // 3
        r = val % 3
        transitions[(l, c, r)] = int(rule_str[idx])

    return transitions


def step(grid: list[int], transitions: dict, boundary: str) -> list[int]:
    n = len(grid)
    new_grid = [0] * n
    for i in range(n):
        c = grid[i]
        if boundary == "periodic":
            l, r = grid[(i - 1) % n], grid[(i + 1) % n]
        elif boundary == "absorbing":
            l = grid[i - 1] if i > 0 else 0
            r = grid[i + 1] if i < n - 1 else 0
        else:
            l = grid[i - 1] if i > 0 else grid[i]
            r = grid[i + 1] if i < n - 1 else grid[i]
        new_grid[i] = transitions[(l, c, r)]
    return new_grid


def simulate_history(initial_grid: list[int], steps: int, transitions: dict, boundary: str):
    history = [initial_grid.copy()]
    grid = initial_grid.copy()
    for _ in range(steps):
        if grid.count(2) == 0:
            break
        grid = step(grid, transitions, boundary)
        history.append(grid.copy())
    return history


class MatplotlibCropApp:
    def __init__(self):
        plt.rcParams["toolbar"] = "None"
        self.fig = plt.figure(figsize=(13.5, 7.8))
        self.fig.canvas.manager.set_window_title("1D Cellular Automaton - Crop Blight Simulation")
        self.fig.patch.set_facecolor("#F4F5F7")

        self.ax_left = self.fig.add_axes([0.33, 0.25, 0.30, 0.66])
        self.ax_right = self.fig.add_axes([0.67, 0.25, 0.30, 0.66])
        self.ax_single = self.fig.add_axes([0.33, 0.25, 0.64, 0.66])

        self.ax_log = self.fig.add_axes([0.33, 0.03, 0.64, 0.16])
        self.ax_log.set_facecolor("#1E1E1E")
        self.ax_log.set_xticks([])
        self.ax_log.set_yticks([])
        self.log_text = self.ax_log.text(
            0.015, 0.88, "", color="#E0E0E0", fontsize=8.5, family="monospace", va="top"
        )

        legend_elements = [
            Patch(facecolor="#E8E4D9", edgecolor="#888", label="0: Empty soil / dead"),
            Patch(facecolor="#2E8B57", edgecolor="#888", label="1: Healthy crop"),
            Patch(facecolor="#D9381E", edgecolor="#888", label="2: Infected plant"),
        ]
        self.fig.legend(
            handles=legend_elements, loc="upper right", bbox_to_anchor=(0.97, 0.97), ncol=3, frameon=True
        )

        self._build_controls()
        self.run_single()
        plt.show()

    def _build_controls(self):
        self.fig.text(0.02, 0.94, "1D AUTOMATON: CROP BLIGHT", fontsize=12, fontweight="bold", color="#1B4332")

        self.fig.text(0.02, 0.89, "Field size N (10-150):", fontsize=8.5, fontweight="bold")
        ax_n = self.fig.add_axes([0.18, 0.88, 0.11, 0.032])
        self.tb_size = TextBox(ax_n, "", initial="60")

        self.fig.text(0.02, 0.845, "Time steps t (5-120):", fontsize=8.5, fontweight="bold")
        ax_t = self.fig.add_axes([0.18, 0.835, 0.11, 0.032])
        self.tb_steps = TextBox(ax_t, "", initial="40")

        self.fig.text(0.02, 0.80, "Sowing density (0.1-1.0):", fontsize=8.5, fontweight="bold")
        ax_d = self.fig.add_axes([0.18, 0.79, 0.11, 0.032])
        self.tb_density = TextBox(ax_d, "", initial="0.90")

        self.fig.text(0.02, 0.75, "Rule code (27 digits 0/1/2 or int):", fontsize=8.5, fontweight="bold")
        ax_r = self.fig.add_axes([0.02, 0.71, 0.27, 0.032])
        self.tb_rule = TextBox(ax_r, "", initial=DEFAULT_RULE_STR)
        self.tb_rule.text_disp.set_fontsize(7.5)

        self.fig.text(0.02, 0.675, "Rule wizard:", fontsize=8.5, fontweight="bold")
        ax_chk = self.fig.add_axes([0.02, 0.565, 0.27, 0.105])
        ax_chk.set_facecolor("#FFFFFF")
        self.chk_wizard = CheckButtons(
            ax_chk,
            [
                "Infects with 1 infected neighbor",
                "Infects with 2 infected neighbors",
                "Infected (2) survives next step",
            ],
            [True, True, False],
        )
        for lbl in self.chk_wizard.labels:
            lbl.set_fontsize(8)
        self.chk_wizard.on_clicked(self._update_rule_from_wizard)

        self.fig.text(0.02, 0.535, "Boundary condition:", fontsize=8.5, fontweight="bold")
        ax_bnd = self.fig.add_axes([0.02, 0.435, 0.27, 0.095])
        ax_bnd.set_facecolor("#FFFFFF")
        self.rb_boundary = RadioButtons(
            ax_bnd,
            ["periodic", "absorbing", "reflecting"],
            active=0,
        )
        for lbl in self.rb_boundary.labels:
            lbl.set_fontsize(8)

        self.fig.text(0.02, 0.405, "Initial outbreak:", fontsize=8.5, fontweight="bold")
        ax_seed = self.fig.add_axes([0.02, 0.33, 0.27, 0.07])
        ax_seed.set_facecolor("#FFFFFF")
        self.rb_seed = RadioButtons(ax_seed, ["center", "left"], active=0)
        for lbl in self.rb_seed.labels:
            lbl.set_fontsize(8)

        ax_btn_run = self.fig.add_axes([0.02, 0.27, 0.27, 0.042])
        self.btn_run = Button(ax_btn_run, "▶ Run simulation", color="#2D6A4F", hovercolor="#1B4332")
        self.btn_run.label.set_color("white")
        self.btn_run.label.set_fontweight("bold")
        self.btn_run.on_clicked(lambda _: self.run_single())

        ax_btn_cmp = self.fig.add_axes([0.02, 0.22, 0.27, 0.038])
        self.btn_cmp = Button(ax_btn_cmp, "⚖ Compare boundary conditions", color="#E2E8F0", hovercolor="#CBD5E1")
        self.btn_cmp.on_clicked(lambda _: self.run_compare())

        ax_btn_anl = self.fig.add_axes([0.02, 0.172, 0.27, 0.038])
        self.btn_anl = Button(ax_btn_anl, "📊 Analyze critical density", color="#E2E8F0", hovercolor="#CBD5E1")
        self.btn_anl.on_clicked(lambda _: self.run_analysis())

        self.fig.text(0.02, 0.14, "Test scenarios:", fontsize=8.5, fontweight="bold", color="#555")

        ax_p1 = self.fig.add_axes([0.02, 0.10, 0.27, 0.032])
        self.btn_p1 = Button(ax_p1, "1. Sparse sowing (40%) - isolation", color="#D8F3DC", hovercolor="#B7E4C7")
        self.btn_p1.label.set_fontsize(8)
        self.btn_p1.on_clicked(lambda _: self._apply_preset(60, 35, "0.40", 0, 0, "single"))

        ax_p2 = self.fig.add_axes([0.02, 0.062, 0.27, 0.032])
        self.btn_p2 = Button(ax_p2, "2. Dense monoculture (95%)", color="#D8F3DC", hovercolor="#B7E4C7")
        self.btn_p2.label.set_fontsize(8)
        self.btn_p2.on_clicked(lambda _: self._apply_preset(60, 45, "0.95", 0, 0, "single"))

        ax_p3 = self.fig.add_axes([0.02, 0.024, 0.27, 0.032])
        self.btn_p3 = Button(ax_p3, "3. Edge outbreak (comparison)", color="#D8F3DC", hovercolor="#B7E4C7")
        self.btn_p3.label.set_fontsize(8)
        self.btn_p3.on_clicked(lambda _: self._apply_preset(35, 30, "0.92", 0, 1, "compare"))

    def _update_rule_from_wizard(self, _):
        c1, c2, surv = self.chk_wizard.get_status()
        chars = []
        for idx in range(27):
            val = 26 - idx
            l, c, r = val // 9, (val % 9) // 3, val % 3
            inf = (1 if l == 2 else 0) + (1 if r == 2 else 0)
            if c == 0:
                chars.append("0")
            elif c == 2:
                chars.append("2" if surv else "0")
            else:
                chars.append("2" if ((inf == 1 and c1) or (inf == 2 and c2)) else "1")
        self.tb_rule.set_val("".join(chars))

    def _apply_preset(self, size, steps, density, bnd_idx, seed_idx, mode):
        self.tb_size.set_val(str(size))
        self.tb_steps.set_val(str(steps))
        self.tb_density.set_val(density)
        self.rb_boundary.set_active(bnd_idx)
        self.rb_seed.set_active(seed_idx)
        if mode == "single":
            self.run_single()
        else:
            self.run_compare()

    def _set_log(self, msg: str, is_error: bool = False):
        self.log_text.set_color("#FF6B6B" if is_error else "#E0E0E0")
        self.log_text.set_text(msg)
        self.fig.canvas.draw_idle()

    def _validate(self):
        try:
            size = int(self.tb_size.text.strip())
            if not (10 <= size <= 150):
                raise ValueError("INPUT ERROR: Field size N must be an integer between 10 and 150.")

            steps = int(self.tb_steps.text.strip())
            if not (5 <= steps <= 120):
                raise ValueError("INPUT ERROR: Time steps t must be between 5 and 120.")

            density = float(self.tb_density.text.strip().replace(",", "."))
            if not (0.1 <= density <= 1.0):
                raise ValueError("INPUT ERROR: Sowing density must be between 0.1 and 1.0.")

            transitions = decode_rule(self.tb_rule.text)
            boundary = self.rb_boundary.value_selected.split()[0]
            seed_center = self.rb_seed.value_selected.startswith("center")
            return size, steps, density, transitions, boundary, seed_center
        except ValueError as e:
            self._set_log(str(e), is_error=True)
            return None

    def _plot_grid(self, ax, history: list[list[int]], title: str):
        ax.clear()
        ax.imshow(history, cmap=CMAP, vmin=0, vmax=2, aspect="auto", interpolation="nearest")
        ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
        ax.set_xlabel("Cell index (1D field)", fontsize=8.5)
        ax.set_ylabel("Time step t", fontsize=8.5)
        ax.tick_params(labelsize=8)

    def run_single(self):
        params = self._validate()
        if not params:
            return
        size, steps, density, transitions, boundary, seed_center = params

        grid = [1 if random.random() < density else 0 for _ in range(size)]
        grid[size // 2 if seed_center else 0] = 2
        init_h = grid.count(1)

        hist = simulate_history(grid, steps, transitions, boundary)
        fin_h = hist[-1].count(1)
        pct = (fin_h / init_h * 100) if init_h > 0 else 0.0

        self.ax_left.set_visible(False)
        self.ax_right.set_visible(False)
        self.ax_single.set_visible(True)
        self._plot_grid(self.ax_single, hist, f"Time evolution (boundary condition: {boundary})")

        self._set_log(
            f"SIMULATION FINISHED AFTER {len(hist)-1} STEPS (max_t={steps}, N={size}, density={density*100:.0f}%)\n"
            f"Initial state: healthy plants = {init_h}, infected = 1\n"
            f"Final state:   survived healthy = {fin_h} / {init_h} ({pct:.1f}%), dead = {hist[-1].count(0)}"
        )

    def run_compare(self):
        params = self._validate()
        if not params:
            return
        size, steps, density, transitions, _, seed_center = params

        base_grid = [1 if random.random() < density else 0 for _ in range(size)]
        base_grid[size // 2 if seed_center else 0] = 2
        init_h = base_grid.count(1)

        hp = simulate_history(base_grid, steps, transitions, "periodic")
        ha = simulate_history(base_grid, steps, transitions, "absorbing")

        self.ax_single.set_visible(False)
        self.ax_left.set_visible(True)
        self.ax_right.set_visible(True)

        self._plot_grid(self.ax_left, hp, "PERIODIC boundary")
        self._plot_grid(self.ax_right, ha, "ABSORBING boundary")

        sp, sa = hp[-1].count(1), ha[-1].count(1)
        seed_label = "center" if seed_center else "left edge"
        self._set_log(
            f"BOUNDARY CONDITION COMPARISON (identical grid: N={size}, density={density*100:.0f}%, outbreak={seed_label}):\n"
            f"1. Periodic:  survived {sp:2d}/{init_h} ({sp/max(init_h,1)*100:5.1f}%) | outbreak duration: {len(hp)-1} steps\n"
            f"2. Absorbing: survived {sa:2d}/{init_h} ({sa/max(init_h,1)*100:5.1f}%) | outbreak duration: {len(ha)-1} steps"
        )

    def run_analysis(self):
        params = self._validate()
        if not params:
            return
        size, steps, _, transitions, _, _ = params
        trials = 30

        densities = list(range(10, 105, 10))
        avg_p, avg_a = [], []

        for d_int in densities:
            d = d_int / 100.0
            sp_l, sa_l = [], []
            for _ in range(trials):
                g = [1 if random.random() < d else 0 for _ in range(size)]
                g[size // 2] = 2
                ih = max(g.count(1), 1)
                sp_l.append(simulate_history(g, steps, transitions, "periodic")[-1].count(1) / ih * 100)
                sa_l.append(simulate_history(g, steps, transitions, "absorbing")[-1].count(1) / ih * 100)
            avg_p.append(sum(sp_l) / trials)
            avg_a.append(sum(sa_l) / trials)

        self.ax_left.set_visible(False)
        self.ax_right.set_visible(False)
        self.ax_single.set_visible(True)
        self.ax_single.clear()

        self.ax_single.plot(densities, avg_p, marker="o", linewidth=2, color="#D9381E", label="Periodic (loop)")
        self.ax_single.plot(densities, avg_a, marker="s", linewidth=2, color="#2E8B57", label="Absorbing (border)")
        self.ax_single.set_title(f"Critical crop density analysis (N={size}, avg of {trials} trials)", fontweight="bold")
        self.ax_single.set_xlabel("Initial field sowing density [%]")
        self.ax_single.set_ylabel("Average survived crop percentage [%]")
        self.ax_single.set_ylim(-5, 105)
        self.ax_single.grid(True, linestyle="--", alpha=0.5)
        self.ax_single.legend()

        row1 = "Density:   " + " ".join(f"{d:5d}%" for d in densities)
        row2 = "Periodic:  " + " ".join(f"{v:5.1f}%" for v in avg_p)
        row3 = "Absorbing: " + " ".join(f"{v:5.1f}%" for v in avg_a)
        self._set_log(f"CRITICAL DENSITY ANALYSIS RESULTS (averaged over {trials} simulations):\n{row1}\n{row2}\n{row3}")


if __name__ == "__main__":
    MatplotlibCropApp()