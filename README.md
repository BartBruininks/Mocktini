<img width="700" height="158" alt="mocktini_logo" src="https://github.com/user-attachments/assets/59ec3578-f464-4d24-a44f-cad07d862217" />

# Mocktini

**Mocktini** is a 2D molecular dynamics (MD) simulator that runs entirely in your web browser — no installation required. It is designed to be approachable for students and researchers alike, while remaining grounded in the physics used in real simulation software.

Run it in your WEBGPU supporting browser by visiting: https://bartbruininks.github.io/Mocktini

> 💡 New to molecular dynamics? Check the [Wiki](wiki/Home.md) for background on concepts like the Mie potential, thermostats, and periodic boundary conditions.

---

## What Does It Do?

Mocktini lets you set up a box of particles, define how they interact, and watch them evolve over time according to Newton's laws of motion. You can tune temperature, particle types, (chain-like) molecules, and more — all in real time through an interactive control panel.

It is useful for:
- Visualising how particle interactions give rise to structure (liquid, gas, crystal)
- Exploring the effect of temperature, density, and interaction strength
- Building intuition for molecular behaviour, phase transitions, and diffusion
- Teaching and self-study in soft matter physics and statistical mechanics

---

## Getting Started

Download `mocktini.html` and open it in a modern browser (Chrome or Edge recommended for GPU acceleration). No server, no dependencies.

1. Set the number of particles (**N**) and box size (**L**) in the control panel
2. Choose your interaction parameters by setting the interaction table (default ε=1.0 for all)
3. Click **Fill** to populate the box with particles on a grid, then **Run** to start the simulation
4. Use **Clear** to remove all particles and start fresh at any time

> 💾 **Saving your work**: Mocktini has first-class support for saving and sharing — both molecule definitions and complete simulation states can be exported as files and reloaded later. See [Saving and Sharing](#saving-and-sharing) below.

---

## The Physics

### Particle Interactions — The Mie 2-4 Potential

Particles interact through the **Mie 2-4 potential**, a cousin of the well-known Lennard-Jones potential:

$$U(r) = 4\varepsilon \left[ \left(\frac{\sigma}{r}\right)^4 - \left(\frac{\sigma}{r}\right)^2 \right] - U(r_c)$$

The two key parameters are:
- **ε (epsilon)** — interaction strength (how strongly two particle types attract each other)
- **σ (sigma)** — particle size (controls the effective diameter)

The exponents 4 and 2 make this potential *softer* than the classic Lennard-Jones 12-6, which means particles can overlap slightly more before being strongly repelled. This is sometimes a better model for coarse-grained or colloidal systems. Especially in 2D this is a much nicer potential, for it broadens the liquid regime of the particles, making everything a lot less crystalline compared to 12-6 LJ. 

The potential is **shifted** so that it smoothly reaches zero at the cutoff distance *r*c, avoiding energy discontinuities.

> 📖 [Wiki: The Mie potential and why we use it](wiki/Mie-Potential.md)

### Particle Types, Properties, and the Epsilon Matrix

Mocktini supports up to **4 bead types** (labelled 0–3). Each particle carries a small set of properties — some defined *per type*, others *per individual particle*:

- **type** (0–3) — *per particle*; selects which row/column of the interaction tables applies
- **σ (size)** — *per type*; the effective diameter in the Mie potential (mixed for unlike pairs)
- **mass** — *per type*; affects the dynamics (how quickly particles respond to forces) but not the equilibrium structure
- **charge** *q* — *per individual particle* (default 0); drives the optional DSF electrostatics described below

Interactions *between* types are controlled by a 4×4 **epsilon matrix** — you can make some pairs strongly attractive and others nearly non-interacting, which is a simple way to model selective affinity or segregation. All particles use the same cutoff which can be set manually (default *r*c=2.5), it is best to use a cutoff which is at least 2-3 times the largest sigma.

### Electrostatics — The Damped Shifted Force (DSF) Potential

Beyond the Mie potential, particles carrying a non-zero **charge** *q* also interact through a **Damped Shifted Force (DSF)** electrostatic potential — a cutoff-friendly form of the 1/*r* Coulomb interaction. When all charges are at their default of 0, the term is skipped entirely, so electrostatics is fully opt-in. Electrostatics are treated as a 2D slice in a 3D world, for 2D electrostatics are even more long ranged. This gives visually pleasing electrostatics, but this is by no means accurate for a true abstract 2D system — we cheat!

The pair energy (for *r* < *r*c) is:

$$U(r) = K_e\, q_i q_j \left[ \frac{\mathrm{erfc}(\alpha r)}{r} - \frac{\mathrm{erfc}(\alpha r_c)}{r_c} + F_\text{shift}\,(r - r_c) \right]$$

Two parameters control it:
- **K_e** — the linear Coulomb strength. Scales all electrostatic forces and energies uniformly.
- **α (alpha)** — the DSF damping (inverse screening length). This one is *non-linear*: small α approaches a bare 1/*r* Coulomb interaction (long-range), while large α screens it heavily (short-range). It changes the *shape* of the interaction, not just its scale.

Like the Mie potential, the DSF form is **shifted** so that both the energy *and* the force go smoothly to zero at the cutoff *r*c — there is no impulsive kick as pairs cross the cutoff, which matters for energy conservation. The same erfc approximation is used on the CPU and GPU paths, so the two engines agree to within floating-point precision.

> ⚠️ DSF — like all cutoff electrostatics — assumes the simulation box is **net-neutral**. A non-zero total charge Σ*q* introduces a spurious self-interaction, so the live stats bar reports Σ*q* to let you check.

> 📖 [Wiki: DSF electrostatics](wiki/DSF-Electrostatics.md)

### Bonds, Angles, and Molecules
Particles can be connected using two kinds of bonded interactions:
- **Harmonic bonds**: U = k/2 · (r − r₀)², a spring between two bonded particles
- **Signed-angle quadratic**: U = k/2 · (θ − θ₀)², a bending stiffness over three connected particles, where θ = atan2(d₁ × d₂, d₁ · d₂) ∈ (−π, π] is the **signed** 2D angle between the two bond vectors. Unlike a conventional harmonic angle, this formulation is chirality-sensitive: clockwise and counterclockwise bends are distinguished, and θ₀ can span the full range −180° < θ₀ ≤ 180°.

An important detail: **every bonded pair automatically gets a non-bonded exclusion**. This means the **non-bonded interactions — both the Mie 2-4 potential and the DSF electrostatics —** are *not* computed between particles that are directly bonded or share an angle, on both the CPU and GPU engines.


Mocktini supports three ways to build molecules:

**Interactive Assembly** — use Bond Edit and Angle Edit modes to connect individual particles already in the simulation into custom structures by clicking, then export the result as a molecule file. When a group of particles is selected, both modes also expose a **batch panel**: write a rest length / stiffness to every bond (or angle) in the selection at once, snap them all to the current geometry, or use **Autobond** / **Autoangle** to generate topology automatically — Autobond bonds every selected pair within the chosen distance, and Autoangle creates an angle across every bonded triple inside the selection. This makes it practical to wire up a large assembly in a few clicks rather than bond-by-bond.

**Import from file** — load a molecule definition from a JSON file. Imported molecules appear in the species list and can be placed, mixed with other species, edited, and copied.

> 📖 [Wiki: Bonded interactions](wiki/Bonded-Interactions.md)

### Boundary Conditions

The simulation box uses **periodic boundary conditions (PBC)** — particles that exit one side re-enter from the opposite side, mimicking an infinite bulk system. When **gravity** is enabled, the vertical boundaries switch to reflective walls instead, so particles pile up under gravity rather than looping.

> 📖 [Wiki: Periodic boundary conditions](wiki/Periodic-Boundary-Conditions.md)

---

## Integration and Temperature Control

### Integrators

Each simulation step advances the equations of motion using one of two integrators:

| Name | Description |
|------|-------------|
| **Velocity Verlet (VV)** | The standard MD integrator — time-reversible, energy-conserving in the absence of a thermostat |
| **Stochastic Dynamics (SD / BAOAB)** | A Langevin integrator that couples each particle to a heat bath via random kicks and friction. Implicitly controls temperature without a separate thermostat step |

> 📖 [Wiki: Integrators in molecular dynamics](wiki/Integrators.md)

### Thermostat

When using Velocity Verlet, temperature is controlled by the **Bussi–Donadio–Parrinello** (stochastic velocity rescaling) thermostat. It periodically rescales particle velocities toward the target temperature *T*, while preserving the correct equilibrium fluctuations, it samples the canonical (NVT) ensemble.

The coupling strength is set by the time constant **τ_T**: larger values mean softer, slower coupling to the target temperature.

> 📖 [Wiki: Thermostats — what they are and why you need one](wiki/Thermostats.md)

---

## Simulation Engines

Mocktini runs the same physics on two different backends:

| Engine | How it works | Best for |
|--------|-------------|----------|
| **CPU** | Pure JavaScript, runs on any device | Debugging, small systems (N < ~2,000), real-time performance, browsers without WebGPU |
| **GPU** | WebGPU compute shaders (WGSL) | Large systems (N < ~200,000), real-time performance |

The GPU path uses the same force expressions as the CPU path — results are physically identical (but not of equal precision). Force computation uses a **cell list** neighbour scheme on both paths for O(N) scaling.

> 📖 [Wiki: Neighbor Scheme - maintaining scalability](wiki/Neighbor-Scheme.md)

---

## The Control Panel

### Simulation Settings
- **Fill** — populate the box with particles on a regular grid at the current N and species ratios (no retries)
- **Clear** — remove all particles from the box and set the box size
- **Undo / Redo** — step backwards and forwards through your last actions (up to 5), using the **Undo** / **Redo** buttons or **Ctrl+Z** / **Ctrl+Shift+Z**. History covers edits, placements, moves, Clear, Load, and Run, so you can always step back one action — including undoing a run that exploded, or a misclicked Load.
- **Reset** — return to the starting point: the last loaded state file, or the initial fill if nothing was loaded. Reset is itself undoable, so a misclicked Reset can be stepped back like any other action.
- **Steps per frame** — how many MD steps to compute before redrawing
- **Integrator** — choose Velocity Verlet or Stochastic Dynamics
- **T (target temperature)** — the temperature the thermostat aims for
- **dt (timestep)** — the length of each MD step; smaller is more accurate but slower
- **Thermostat interval / τ_T** — how often and how strongly temperature is corrected
- **Gravity** — applies a downward force on all particles

### Particle and Molecule Setup
- **N** — number of particles
- **L** — simulation box side length
- **Spacing** — initial grid spacing used for the filling grid
- **Species ratios** — relative amounts of each monomer type and molecule/assemblies
- **Mass per type** — particle masses (affects dynamics but not equilibrium structure)
- **Molecule files** — import molecule definitions from JSON, or export any built or assembled molecule for sharing

### Interactions
- **ε matrix** — attraction/repulsion strength between each pair of types
- **σ per type** — effective particle diameter per type
- **r*c* (cutoff)** — distance beyond which interactions are ignored
- **K_e (electrostatic strength)** — overall scale of the DSF electrostatic interaction
- **α (electrostatic damping)** — DSF screening parameter (inverse screening length); higher values screen charges more strongly

### Rendering
- **Colour mode** — how particles are coloured: **Type** (by bead type), **Molecule** (each molecule its own colour), **Velocity** (mapped to speed), or **Charge** (diverging blue → grey → red by the sign and magnitude of *q*)
- **Particle radius** — visual size on screen (does not affect physics)

---

## Interactive Modes

Mocktini has several mouse interaction modes, switchable via the mode bar or with single-key shortcuts: **C** (Camera), **S** (Select), **P** (Particle), **B** (Bond Edit), and **A** (Angle Edit). Pressing **Esc** cancels an in-progress placement.

| Mode | What it does |
|------|-------------|
| **Camera** | Pan (drag) and zoom (scroll) the view |
| **Select** | Rubber-band select molecules |
| **Place** | Click to place individual particles or whole molecules |
| **Bond Edit** | Click two particles to create or inspect a bond |
| **Angle Edit** | Click three particles to define an angle constraint |
| **Particle** | Rubber-band select individual beads; set their **type** or **charge** via the inspect bar (or quick-set type with keys 0–3) |

Selected bonds and angles display their current length or angle in real time, and you can snap the value to the current geometry with the **⌖ snap** button. In Particle mode the inspect bar shows the selected beads' type and charge, which you can edit directly with the **Apply** and **Set** buttons.

When you enter Bond Edit or Angle Edit mode with a *selection* held (rather than clicking a single pair/triple), the inspect bar switches to a **batch panel** that acts on the whole selection: write a rest length or stiffness to every bond/angle at once (commit with **Enter**), snap them all to the current geometry, or run **Autobond** / **Autoangle** to create new topology across the selection in one step. It's the fastest way to turn a cluster of placed particles into a bonded molecule.

> 📖 [Wiki: Building molecules interactively](wiki/Interactive-Assembly.md)

---

## Statistics Bar

The live stats bar at the top of the canvas displays:

| Stat | Meaning |
|------|---------|
| **Engine** | CPU or GPU |
| **Step** | Total number of MD steps taken |
| **T inst** | Instantaneous temperature (from kinetic energy) |
| **T set** | Target temperature |
| **KE / N** | Kinetic energy per particle |
| **PE / N** | Potential energy per particle |
| **E tot / N** | Total energy per particle |
| **N** | Current number of particles |
| **Σq** | Net charge of the box; should be ~0 for physically meaningful DSF electrostatics |
| **ms / frame** | Wall-clock time per rendered frame |
| **dt** | Current timestep (ramps up gradually on initialisation) |
| **Mode** | The active mouse interaction mode |

---

## Saving and Sharing

Sharing and saving work is a core feature of Mocktini. There are two levels of what you can save:

### Molecule Files

Any selection (one or multiple molecules) you build — by assembling particles interactively — can be exported as a compact **JSON molecule file**. This file encodes the molecule's bead types, per-bead charges, bond topology, angle topology, and all parameters. You can then:
- **Import** it back into Mocktini at any time (it appears in the species list and can be placed freely)
- **Share** it with collaborators, who load it in their own copy of Mocktini
- **Combine** multiple imported molecules with monomers in any ratio

Molecule files are the right format when you want to share a *building block*, not a whole experiment. They describe the molecule itself — its connectivity (bonds and angles), its bead types, and any per-bead charges. They do *not* carry the global non-bonded settings such as the ε matrix, σ per type, the cutoff, or the electrostatic K_e/α; those belong to the simulation as a whole rather than to any one molecule.

### Complete State Files

A **state file** captures everything: all particle positions, velocities, and charges, all bonds and angles, all simulation parameters, and the current step count. It is a full snapshot of the simulation at a moment in time. You can:
- Save a state, continue running, and reload the snapshot later to branch the simulation
- Share a state file so someone else can continue from exactly where you left off, or reproduce a specific configuration
- Use it as a reproducible starting point for a classroom exercise or publication figure

### URL State

All control panel parameters (box size, interaction strengths, electrostatics, etc.) are also encoded live in the browser URL. Copying the URL from the address bar captures your current setup and can be bookmarked or shared directly — though it does not include live particle positions the way a state file does.

---

## Versioning

Mocktini uses semantic versioning (`MAJOR.MINOR.PATCH`):
- **MAJOR** — breaking change to URL parameters or file format
- **MINOR** — new user-visible feature
- **PATCH** — bug fix, performance improvement, or annotation

Current version: **v1.2.3**

---

## Limitations and Known Caveats

- The simulation is strictly **2D** — this changes some thermodynamic quantities compared to 3D (e.g. the equipartition theorem gives 2 rather than 3 degrees of freedom per particle)
- The GPU engine requires a browser with **WebGPU** support (Safari, Chrome or Edge; Firefox support is in progress)
- Very large systems (N > ~100,000) may slow down even on the GPU path depending on hardware

---

## Acknowledgements

Mocktini was built by Dr. Bart MH Bruininks as a passion project during his appointment at the Univeristy of Groningen (2026). It is a single-file, self-contained educational tool for exploring 2D soft matter physics interactively in the browser available under the MIT License.

AI was heavily used in this project and therefore I think it is in place to make some shoutouts to projects that no doubt have influenced this software: [Interactive MD](https://physics.weber.edu/schroeder/md/), [GROMACS](https://www.gromacs.org/), [OpenMM](https://openmm.org/), [CHARMM](https://www.charmm.org/), [OpenMD](https://openmd.org/), [AMBER](https://ambermd.org), [LAMMPS](https://www.lammps.org/), [NAMD](https://www.ks.uiuc.edu/Research/namd/), [ESPResSo](https://espressomd.org/) and many more. It should be clear that this project sits on the shoulders of giants.

Special thanks to SJ Marrink, AH de Vries, MSSH Westendorp, M Bzoflu and the rest of the MD group for supporting me during the development of this program - you are the best!
