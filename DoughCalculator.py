"""Peddlin' pizza dough calculator (24 h room-temperature fermentation).

Run with:  .venv\\Scripts\\streamlit run DoughCalculator.py
"""

import sys
from datetime import date, datetime, time, timedelta

import streamlit as st

# Started with plain `python DoughCalculator.py` (e.g. VS Code's Run button)? Relaunch via Streamlit.
if __name__ == "__main__" and not st.runtime.exists():
    from streamlit.web import cli

    sys.argv = ["streamlit", "run", __file__, *sys.argv[1:]]
    sys.exit(cli.main())

# --- Reference recipe: 6 balls, 1 kg flour, proven 24 h schedule -------------------
REF_HYDRATION = 0.62
REF_SALT = 0.03
REF_FRESH_YEAST = 0.001  # 1 g fresh yeast per 1000 g flour
REF_PHASES = [(10, 23.0), (14, 18.0)]  # (hours, °C): bulk, then balls

# Yeast strength relative to instant dry yeast (doughrise): IDY : ADY : fresh = 1 : 1.5 : 3
YEAST_FACTOR = {"Fresh yeast": 3.0, "Active dry yeast (ADY)": 1.5, "Instant dry yeast (IDY)": 1.0}

# doughrise baseline: 0.2 % IDY for 12 h at 20 °C, rate doubles every +10 °C
DOUGHRISE_IDY = 0.002
DOUGHRISE_HOURS = 12
DOUGHRISE_TEMP = 20.0


def rate(temp_c):
    """Fermentation speed relative to 20 °C (Q10 = 2)."""
    return 2 ** ((temp_c - DOUGHRISE_TEMP) / 10)


def equivalent_hours(phases):
    """Total fermentation expressed as hours at 20 °C."""
    return sum(hours * rate(temp) for hours, temp in phases)


def doughrise_idy(phases):
    """Raw doughrise formula, extended to several phases. Fraction of flour weight."""
    return DOUGHRISE_IDY * DOUGHRISE_HOURS / equivalent_hours(phases)


REF_IDY = REF_FRESH_YEAST / YEAST_FACTOR["Fresh yeast"]
CALIBRATION = REF_IDY / doughrise_idy(REF_PHASES)


def calibrated_idy(phases):
    """doughrise model scaled so the reference schedule gives the recipe's 1 g fresh/kg."""
    return CALIBRATION * doughrise_idy(phases)


def fmt_dt(dt):
    return dt.strftime("%a %d %b, %H:%M")


st.set_page_config(page_title="Pizza Dough Calculator", page_icon="🍕", layout="wide")
st.title("🍕 Peddlin' Pizza Dough Calculator")
st.caption("24 h room-temperature fermentation: ~10 h bulk + 12–14 h in balls.")

# --- Sidebar inputs ----------------------------------------------------------------------
with st.sidebar:
    st.header("Dough")
    n_balls = st.number_input("Number of dough balls", min_value=1, max_value=60, value=6, step=1)
    ball_weight = st.number_input(
        "Dough ball weight (g)", min_value=150, max_value=450, value=275, step=5,
        help="The reference recipe (1 kg flour, 62 %) yields 6 × ~275 g. "
             "Classic Neapolitan is 250–280 g.",
    )
    hydration = st.slider("Hydration (%)", min_value=55, max_value=80, value=62, step=1) / 100
    salt_pct = st.number_input("Salt (% of flour)", min_value=0.0, max_value=4.0,
                               value=REF_SALT * 100, step=0.1, format="%.1f") / 100
    strong_share = st.slider(
        "Strong 01 flour in blend (%)", min_value=0, max_value=20, value=10, step=1,
        help="Rest is 00 Napoletana (W310). 5–20 % 01 (e.g. Uniqua) supports long fermentation.",
    ) / 100

    st.header("Fermentation")
    c1, c2 = st.columns(2)
    bulk_h = c1.number_input("Bulk (h)", min_value=0.0, max_value=48.0, value=10.0, step=0.5)
    bulk_t = c2.number_input("Bulk °C", min_value=4.0, max_value=32.0, value=23.0, step=0.5,
                             help="Dough temperature at the end of mixing.")
    c1, c2 = st.columns(2)
    ball_h = c1.number_input("Balls (h)", min_value=1.0, max_value=48.0, value=14.0, step=0.5)
    ball_t = c2.number_input("Balls °C", min_value=4.0, max_value=32.0, value=18.0, step=0.5,
                             help="Room temperature during ball fermentation (recipe: 17–19 °C).")

    yeast_type = st.selectbox("Yeast type", list(YEAST_FACTOR), index=0)
    yeast_mode = st.radio(
        "Yeast amount",
        ["Calibrated to recipe (recommended)", "Raw doughrise formula", "Manual"],
    )
    manual_pct = None
    if yeast_mode == "Manual":
        manual_pct = st.number_input(f"{yeast_type} (% of flour)", min_value=0.0, max_value=5.0,
                                     value=0.1, step=0.01, format="%.3f") / 100

# --- Calculations ------------------------------------------------------------------------
phases = [(bulk_h, bulk_t), (ball_h, ball_t)]
factor = YEAST_FACTOR[yeast_type]
calibrated_pct = calibrated_idy(phases) * factor
doughrise_pct = doughrise_idy(phases) * factor
yeast_pct = {"Calibrated to recipe (recommended)": calibrated_pct,
             "Raw doughrise formula": doughrise_pct,
             "Manual": manual_pct}[yeast_mode]

# Ball weight is fixed: flour follows from the total dough weight and baker's percentages
total_dough = n_balls * ball_weight
flour = total_dough / (1 + hydration + salt_pct + yeast_pct)
flour_00 = flour * (1 - strong_share)
flour_01 = flour * strong_share
water = flour * hydration
salt = flour * salt_pct
yeast = flour * yeast_pct

# --- Ingredients ---------------------------------------------------------------------------
st.subheader(f"Ingredients for {n_balls} × {ball_weight} g = {total_dough:,} g dough")

m = st.columns(4)
m[0].metric("Flour", f"{flour:.0f} g")
m[1].metric("Water", f"{water:.0f} g", f"{hydration:.0%} hydration", delta_color="off")
m[2].metric("Salt", f"{salt:.1f} g")
m[3].metric(yeast_type, f"{yeast:.2f} g", f"{yeast_pct:.3%} of flour", delta_color="off")

st.dataframe(
    [
        {"Ingredient": "00 flour (Dallagiovanna Napoletana, W310)", "Grams": round(flour_00),
         "Baker's %": f"{1 - strong_share:.0%} of flour"},
        {"Ingredient": "01 strong flour (Dallagiovanna Uniqua)", "Grams": round(flour_01),
         "Baker's %": f"{strong_share:.0%} of flour"},
        {"Ingredient": "Water", "Grams": round(water), "Baker's %": f"{hydration:.1%}"},
        {"Ingredient": "Fine sea salt", "Grams": round(salt, 1), "Baker's %": f"{salt_pct:.1%}"},
        {"Ingredient": yeast_type, "Grams": round(yeast, 2), "Baker's %": f"{yeast_pct:.3%}"},
    ],
    hide_index=True,
    width="stretch",
)

if yeast < 2:
    st.info(
        f"**Tiny yeast amount?** Most kitchen scales can't weigh {yeast:.2f} g accurately. "
        f"Dissolve 1 g {yeast_type.lower()} in 100 g water and use **{yeast * 100:.0f} g** of "
        f"that solution, taking that water off the {water:.0f} g you add."
    )

# --- Yeast model explanation -------------------------------------------------------------------
with st.expander("🧪 How the yeast amount is calculated", expanded=False):
    ref_eq = equivalent_hours(REF_PHASES)
    cur_eq = equivalent_hours(phases)
    st.markdown(
        f"""
**1. Two-phase fermentation.** Yeast works faster when it's warmer: the activity roughly
doubles for every +10 °C (Q10 = 2). Each phase is converted to *equivalent hours at 20 °C*:
"""
    )
    st.latex(r"E = \sum_i t_i \cdot 2^{(T_i - 20)/10}")
    st.markdown(
        f"""
Your schedule: {bulk_h:g} h @ {bulk_t:g} °C + {ball_h:g} h @ {ball_t:g} °C → **E = {cur_eq:.1f} h**.
The reference recipe (10 h @ 23 °C + 14 h @ 18 °C) gives E = {ref_eq:.1f} h.

**2. The doughrise formula.** [doughrise](https://doughrise.store/pages/yeast-by-time-temperature-calculator)
starts from 0.2 % instant yeast for 12 h at 20 °C and scales inversely with time:
"""
    )
    st.latex(r"\text{IDY\%} = 0.2\% \cdot \frac{12\,\text{h}}{E}")
    st.markdown(
        f"""
For the reference schedule that gives {doughrise_idy(REF_PHASES):.3%} IDY
≈ **{doughrise_idy(REF_PHASES) * 3 * 1000:.1f} g fresh yeast per kg flour**. The proven recipe uses
only **1 g fresh per kg**. The doughrise model overestimates long ferments: it scales linearly
with time, while yeast multiplies during the fermentation.

**3. Calibration.** We keep the doughrise *shape* (time and temperature scaling) but scale it
so the reference schedule gives exactly the recipe's 1 g fresh yeast per kg.
Calibration factor = **{CALIBRATION:.2f}**:
"""
    )
    st.latex(r"\text{yeast} = 1\,\text{g fresh/kg} \cdot \frac{E_\text{ref}}{E}")
    st.markdown(
        f"""
| Model | {yeast_type} for your schedule |
|---|---|
| Calibrated to recipe | {calibrated_pct:.3%} → **{flour * calibrated_pct:.2f} g** |
| Raw doughrise | {doughrise_pct:.3%} → {flour * doughrise_pct:.2f} g |

Yeast types are converted with IDY : ADY : fresh = 1 : 1.5 : 3. Stray far from the reference
schedule (very short, very warm or fridge temperatures) and every model becomes a starting
estimate. Watch the dough, not the clock.
"""
    )

# --- Water temperature helper -------------------------------------------------------------------
st.subheader("🌡️ Water temperature")
st.caption("Hit the target dough temperature at the end of mixing: water = 3 × target − flour − room − friction.")
w = st.columns(4)
target_t = w[0].number_input("Target dough °C", min_value=15.0, max_value=30.0, value=bulk_t, step=0.5,
                             help="Recipe: 23–24 °C. Defaults to your bulk temperature.")
room_t = w[1].number_input("Room °C", min_value=5.0, max_value=35.0, value=20.0, step=0.5)
flour_t = w[2].number_input("Flour °C", min_value=5.0, max_value=35.0, value=20.0, step=0.5,
                            help="Usually the same as the room, unless the flour is stored somewhere cold.")
friction = w[3].number_input("Mixing friction °C", min_value=0.0, max_value=20.0, value=2.0, step=0.5,
                             help="Heat added by mixing. Hand mixing ≈ 1–3 °C, stand/spiral mixer ≈ 8–14 °C.")
water_t = 3 * target_t - room_t - flour_t - friction

st.metric("Water temperature", f"{water_t:.1f} °C")
if water_t < 2:
    st.warning("That's colder than ice water can get. Chill the flour, or accept a slightly warmer dough.")
elif water_t > 40:
    st.warning("Water above ~40 °C stresses the yeast. Warm the flour or room instead.")

# --- Timeline -----------------------------------------------------------------------------------------
st.subheader("🕒 Timeline")
t = st.columns(2)
bake_date = t[0].date_input("Bake date", value=date.today() + timedelta(days=1))
bake_time = t[1].time_input("Bake time", value=time(19, 0), step=900)

bake_at = datetime.combine(bake_date, bake_time)
ball_at = bake_at - timedelta(hours=ball_h)
mix_at = ball_at - timedelta(hours=bulk_h)

st.dataframe(
    [
        {"When": fmt_dt(mix_at), "Step": "Mix the dough", "Duration": "~20 min"},
        {"When": fmt_dt(mix_at), "Step": f"Bulk fermentation at ~{bulk_t:g} °C", "Duration": f"{bulk_h:g} h"},
        {"When": fmt_dt(ball_at), "Step": f"Divide into {n_balls} × {ball_weight} g and ball",
         "Duration": "~15 min"},
        {"When": fmt_dt(ball_at), "Step": f"Ball fermentation at ~{ball_t:g} °C", "Duration": f"{ball_h:g} h"},
        {"When": fmt_dt(bake_at), "Step": "Stretch and bake", "Duration": ""},
    ],
    hide_index=True,
    width="stretch",
)

# --- Method -------------------------------------------------------------------------------------------
st.subheader("📋 Method")
st.markdown(
    f"""
1. **Dissolve the yeast.** Weigh **{water:.0f} g water at {water_t:.0f} °C** and dissolve
   **{yeast:.2f} g {yeast_type.lower()}** in it. Optionally add a bit of honey (makes the crust a bit more crunchy).
2. **Mix the dough.** Gradually add the flour (**{flour_00:.0f} g 00 + {flour_01:.0f} g 01**),
   mixing by hand or in a dough tray. Add **{salt:.1f} g fine sea salt** while mixing and work the
   dough until it is smooth. Aim for a dough temperature of **~{target_t:g} °C**.
3. **Bulk fermentation.** Cover and leave at room temperature for **{bulk_h:g} h** (until {fmt_dt(ball_at)}).
4. **Ball and shape.** Divide into **{n_balls} × {ball_weight} g** and shape into tight, smooth balls.
5. **Ball fermentation.** Put the balls in a covered dough tray at **~{ball_t:g} °C** for
   **{ball_h:g} h** ({bulk_h + ball_h:g} h in total), then stretch and bake on {fmt_dt(bake_at)}.
"""
)
