# The Mie Potential and Why We Use It

> 💡 Mocktini's non-bonded particles attract and repel through the **Mie 2-4 potential** — a softer cousin of the famous Lennard-Jones 12-6. This page explains what it is, why the soft "2-4" exponents suit a 2D simulation, and why we *shift* it at the cutoff.

## The idea

Two neutral particles feel a competition: they are pushed apart when they overlap (Pauli repulsion) and pulled together at moderate range (dispersion attraction). The **Mie potential** captures both with a difference of two powers of $\sigma/r$:

$$U(r) = C\,\varepsilon\left[\left(\frac{\sigma}{r}\right)^{n} - \left(\frac{\sigma}{r}\right)^{m}\right], \qquad C = \frac{n}{n-m}\left(\frac{n}{m}\right)^{\frac{m}{n-m}}$$

- $\varepsilon$ — **interaction strength** (the depth of the attractive well)
- $\sigma$ — **particle size** (sets the effective diameter)
- $n, m$ — the repulsive and attractive exponents

The classic Lennard-Jones potential is the Mie $n=12,\,m=6$ case. Mocktini instead uses $n=4,\,m=2$, the **Mie 2-4**, for which $C = 4$:

$$U_\text{Mie 2-4}(r) = 4\varepsilon\left[\left(\frac{\sigma}{r}\right)^{4} - \left(\frac{\sigma}{r}\right)^{2}\right]$$

Both forms have their minimum of depth $-\varepsilon$, but the 2-4 sits at $r_\text{min}=\sqrt{2}\,\sigma \approx 1.41\,\sigma$ with a **much broader, gentler well**, while LJ 12-6 has a sharp minimum at $2^{1/6}\sigma \approx 1.12\,\sigma$.

## Why soft exponents in 2D

The shallow, wide 2-4 well lets particles **overlap a little more before being strongly repelled**, which is a reasonable picture for coarse-grained or colloidal "blobs" rather than hard atoms. It matters especially in 2D: the softer potential **broadens the liquid regime** and keeps the system from snapping into a crystal as readily as LJ 12-6 does. In practice that means more of the interesting, fluid-like behaviour you actually want to watch.

```python
import numpy as np
import matplotlib.pyplot as plt

BLUE, ORANGE, GREY = "#4da6ff", "#ff8c1a", "#8a8a8a"

def mie(r, eps=1.0, sigma=1.0, n=4, m=2):
    C = (n / (n - m)) * (n / m) ** (m / (n - m))   # = 4 for both 2-4 and 12-6
    sr = sigma / r
    return C * eps * (sr**n - sr**m)

r, rc = np.linspace(0.9, 3.0, 600), 2.5
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.9))

# Panel A — softness: 2-4 vs 12-6
a1.plot(r, mie(r, n=12, m=6), color=ORANGE, lw=2.2, label="Lennard-Jones 12-6")
a1.plot(r, mie(r, n=4,  m=2), color=BLUE,   lw=2.2, label="Mie 2-4 (Mocktini)")
a1.set_ylim(-1.3, 2.0); a1.set_xlabel("r / σ"); a1.set_ylabel("U / ε"); a1.legend()

# Panel B — the energy shift near the cutoff
sel = (r >= 1.3) & (r <= 2.85)
a2.plot(r[sel], mie(r[sel]),                  color=GREY, ls="--", lw=2.0, label="raw Mie 2-4")
a2.plot(r[sel], mie(r[sel]) - mie(rc),        color=BLUE, lw=2.4,        label="shifted: U − U(r_c)")
a2.axvline(rc, color=GREY, ls=":"); a2.set_xlabel("r / σ"); a2.set_ylabel("U / ε"); a2.legend()
plt.tight_layout(); plt.show()
```

![Mie 2-4 vs Lennard-Jones, and the energy shift](img/mie_potential.png)

*Left: the Mie 2-4 well is broader and softer than LJ 12-6. Right: subtracting $U(r_c)$ lifts the curve so the energy passes through zero exactly at the cutoff.*

## Why we shift it

A simulation can't sum interactions over infinitely many neighbours, so we **cut them off** at a distance $r_c$ (default $2.5$). But the raw potential is not zero there — at $r_c=2.5\,\sigma$ the Mie 2-4 still sits at $U(r_c)\approx-0.54\,\varepsilon$. If we simply truncated, a pair crossing the cutoff would see the energy **jump** from $-0.54\,\varepsilon$ to $0$, injecting or removing energy out of nowhere.

The fix is to **shift** the potential down by that constant so it reaches zero continuously:

$$U_\text{shifted}(r) = U(r) - U(r_c), \qquad r < r_c$$

Now there is no energy discontinuity as neighbours come and go. The *force*, though, is a subtler story — and for a potential as soft as the 2-4, subtle enough to be worth a closer look.

<details>
<summary>🔬 <b>In depth</b> — the force law and the well</summary>

*Sections marked 🔬 In depth go into the maths and trade-offs: handy if you work in the field, safe to skip otherwise.*

The force is $\mathbf{F} = -\nabla U$. For the Mie 2-4, the magnitude along $\hat{\mathbf r}$ works out to

$$F(r) = -\frac{\mathrm dU}{\mathrm dr} = \frac{8\varepsilon}{r}\left[2\left(\frac{\sigma}{r}\right)^{4} - \left(\frac{\sigma}{r}\right)^{2}\right]$$

which is exactly what the engine computes (as `f_mag = 8ε(2x² − x)/r²` with `x = σ²/r²`, then multiplied by the separation vector).

Setting $F=0$ gives the well minimum at $(\sigma/r)^2 = \tfrac12$, i.e. $r_\text{min}=\sqrt{2}\,\sigma$, where $U=-\varepsilon$.

</details>

<details>
<summary>🔬 <b>In depth</b> — the force at the cutoff, and choosing r_c</summary>

The energy shift removes the *energy* jump, but it subtracts a **constant** — and a constant has zero slope, so it leaves the force untouched. The force therefore does **not** reach zero at $r_c$; it drops there discontinuously, by an amount $F(r_c)$. For the soft 2-4 that step is not small:

$$|F(r_c = 2.5\,\sigma)| \approx 0.35\,\varepsilon/\sigma,$$

about **9× larger** than Lennard-Jones 12-6 at the same cutoff ($\approx 0.039$). The 2.5σ cutoff is an LJ habit; the longer-ranged 2-4 simply isn't finished decaying there.

So shouldn't we *force*-shift it as well, the way [DSF electrostatics](DSF-Electrostatics) does? Tempting — but here it backfires. A force shift adds a linear ramp $\propto (r - r_c)\,F(r_c)$, and when $F(r_c)$ is large that ramp distorts the potential badly: at $r_c = 2.5\,\sigma$ it shrinks the well from $-0.46\,\varepsilon$ to $-0.10\,\varepsilon$ (left panel) and pushes the minimum outward. The cure is worse than the disease, precisely *because* the well is soft. DSF gets away with the same trick only because Coulomb is monotonic — there is no well to wreck. We are looking into implementing some form of switch function used in other engines like Gromacs, but this will require further research.

The real lever is the cutoff itself (right panel): $|F(r_c)|$ for the 2-4 does not fall to LJ-at-2.5 levels until $r_c \approx 5.5$–$6\,\sigma$. In practice:

- **Keep the energy-shift and rely on temperature control.** Mocktini runs with a thermostat (Bussi) or Langevin dynamics (BAOAB), which absorbs the small drift the force step would otherwise cause. This is fine for structure and thermodynamics; just be aware that strict NVE will drift.
- **For cleaner energetics, widen the cutoff** toward ~3.5–4σ or beyond (neighbour work grows with $r_c^2$, so it isn't free). At a wide cutoff the residual force is genuinely small, and a force-shift — if you wanted one — becomes a harmless correction rather than a distortion.

```python
import numpy as np
import matplotlib.pyplot as plt

BLUE, ORANGE, GREY = "#4da6ff", "#ff8c1a", "#8a8a8a"

def mie(r, n=4, m=2):
    C = (n / (n - m)) * (n / m) ** (m / (n - m)); sr = 1.0 / r
    return C * (sr**n - sr**m)

def mie_force(r, n=4, m=2):                  # signed F = -dU/dr  (negative = attractive)
    C = (n / (n - m)) * (n / m) ** (m / (n - m)); sr = 1.0 / r
    return (C / r) * (n * sr**n - m * sr**m)

rc = 2.5
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.9))

# Left — what a force-shift does to the soft well
r = np.linspace(1.0, rc, 400)
u_es = mie(r) - mie(rc)                       # energy-shifted (Mocktini's choice)
u_sf = u_es + (r - rc) * mie_force(rc)        # + force-shift ramp → F(r_c) = 0
a1.plot(r, u_es, color=BLUE,   lw=2.4, label=f"energy-shifted (well {u_es.min():.2f} ε)")
a1.plot(r, u_sf, color=ORANGE, lw=2.4, label=f"+force-shifted (well {u_sf.min():.2f} ε)")
a1.set_xlabel("r / σ"); a1.set_ylabel("U / ε"); a1.legend()

# Right — |F(r_c)| vs cutoff
rcx = np.linspace(1.6, 7.0, 400)
a2.semilogy(rcx, np.abs(mie_force(rcx, 4, 2)),  color=BLUE,   lw=2.4, label="Mie 2-4")
a2.semilogy(rcx, np.abs(mie_force(rcx, 12, 6)), color=ORANGE, lw=2.4, label="LJ 12-6")
a2.axvline(2.5, color=GREY, ls=":"); a2.set_xlabel("cutoff r_c / σ")
a2.set_ylabel("|F(r_c)| / (ε/σ)"); a2.legend()
plt.tight_layout(); plt.show()
```

![Force-shift distortion, and the force at the cutoff vs cutoff distance](img/mie_cutoff.png)

*Left: force-shifting at 2.5σ guts the soft well. Right: the 2-4 force at the cutoff stays an order of magnitude above LJ until $r_c \approx 6\,\sigma$.*

</details>

## In Mocktini

| Control | Symbol | Where | Default |
|---|---|---|---|
| Interaction strength | $\varepsilon$ | 4×4 ε matrix (per type pair) | 1.0 |
| Particle size | $\sigma$ | σ per type | 1.0 |
| Cutoff | $r_c$ | Interactions panel | 2.5 |

For unlike pairs the size is mixed from the two per-type $\sigma$ values. As a rule of thumb keep $r_c \gtrsim 2.5\,\sigma$ — but bear in mind the soft 2-4 is longer-ranged than Lennard-Jones, so for clean energetics a more generous cutoff (≈3.5–4× the largest $\sigma$) is preferable to the LJ-style 2.5σ. See the in-depth note above for why.

---

📖 Related: [DSF electrostatics](DSF-Electrostatics) · [Bonded interactions](Bonded-Interactions) · [Periodic boundary conditions](Periodic-Boundary-Conditions)
